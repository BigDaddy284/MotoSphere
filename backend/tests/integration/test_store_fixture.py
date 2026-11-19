"""Tests of the fixture that gives every test a real data store of its own."""

from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

CONFTEST = Path(__file__).parents[1] / "conftest.py"

# Tests for pytest to run by itself, with this project's fixtures. Four of
# them leave connections to their store open; the others say what must be
# true afterwards.
LEAVING_CONNECTIONS_OPEN = """
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

KEPT = []
RAW = []
FILES = []


def leave_a_connection_open(store):
    connection = store.connect()
    connection.exec_driver_sql("SELECT count(*) FROM sqlite_master").scalar_one()
    KEPT.append(connection)
    RAW.append(connection.connection.dbapi_connection)
    FILES.append(Path(store.url.database))


def test_one_that_closes_a_connection_and_leaves_another_open(store):
    with store.connect() as connection:
        connection.exec_driver_sql("SELECT count(*) FROM sqlite_master").scalar_one()
    leave_a_connection_open(store)


def test_the_next_test_has_a_store_of_its_own(store):
    assert Path(store.url.database) != FILES[0]
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE mine (id INTEGER PRIMARY KEY)")


def test_one_that_leaves_two_connections_open(store):
    leave_a_connection_open(store)
    leave_a_connection_open(store)


def test_one_that_leaves_a_session_open(store):
    session = Session(store)
    session.execute(text("SELECT count(*) FROM sqlite_master")).scalar_one()
    KEPT.append(session)
    RAW.append(session.connection().connection.dbapi_connection)
    FILES.append(Path(store.url.database))


def test_one_that_drops_a_connection_without_closing_it(store):
    connection = store.connect()
    connection.exec_driver_sql("SELECT count(*) FROM sqlite_master").scalar_one()
    RAW.append(connection.connection.dbapi_connection)
    FILES.append(Path(store.url.database))
    del connection


def test_one_that_closes_what_it_opened(store):
    with store.connect() as connection:
        connection.exec_driver_sql("SELECT count(*) FROM sqlite_master").scalar_one()
    with Session(store) as session:
        session.execute(text("SELECT count(*) FROM sqlite_master")).scalar_one()


@pytest.mark.parametrize("left_open", range(5))
def test_every_connection_left_open_was_closed(left_open):
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        RAW[left_open].execute("SELECT 1")


@pytest.mark.parametrize("left_open", range(5))
def test_every_file_can_be_removed(left_open):
    FILES[left_open].unlink(missing_ok=True)

    assert not FILES[left_open].exists()
"""


def tables(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM sqlite_master ORDER BY name")
        return [str(name) for (name,) in found]


@pytest.mark.parametrize("turn", ["first", "second", "third"])
def test_every_test_has_an_empty_store_and_can_write_the_same_key(store: Engine, turn: str) -> None:
    assert tables(store) == []

    with store.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE parent (id INTEGER PRIMARY KEY, turn TEXT)")
        connection.exec_driver_sql("INSERT INTO parent (id, turn) VALUES (1, ?)", (turn,))

    assert tables(store) == ["parent"]


def test_the_store_is_a_real_sqlite_file_in_the_tests_own_folder(
    store: Engine, tmp_path: Path
) -> None:
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE parent (id INTEGER PRIMARY KEY)")

    assert store.url.database == str(tmp_path / "store.sqlite3")
    assert (tmp_path / "store.sqlite3").read_bytes().startswith(b"SQLite format 3\x00")


def test_the_store_is_opened_the_way_the_pipeline_opens_it(store: Engine) -> None:
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql(
            "CREATE TABLE child (parent_id INTEGER NOT NULL REFERENCES parent (id))"
        )

    with store.connect() as connection, pytest.raises(IntegrityError, match="FOREIGN KEY"):
        connection.exec_driver_sql("INSERT INTO child (parent_id) VALUES (7)")


def test_a_test_that_leaves_connections_open_is_an_error_and_they_are_closed_for_it(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(CONFTEST.read_text(encoding="utf-8"))
    pytester.makepyfile(LEAVING_CONNECTIONS_OPEN)

    result = pytester.runpytest_subprocess("-p", "no:cacheprovider", "-W", "error", timeout=120)

    result.assert_outcomes(passed=16, errors=4)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at teardown of test_one_that_closes_a_connection_and_leaves_another_open*",
            "*Connections to its store that the test left open: 1. They were closed for it.",
            "*ERROR at teardown of test_one_that_leaves_two_connections_open*",
            "*Connections to its store that the test left open: 2. They were closed for it.",
            "*ERROR at teardown of test_one_that_leaves_a_session_open*",
            "*Connections to its store that the test left open: 1. They were closed for it.",
            "*ERROR at teardown of test_one_that_drops_a_connection_without_closing_it*",
            "*Connections to its store that the test left open: 1. They were closed for it.",
        ]
    )
