"""Tests of the store a command is given to work on, against a real SQLite file.

Like the tests of ``schema`` in ``test_schema_command.py``, most of these
use a list of migrations of their own in the place of the pipeline's, so
that a store can lack some of them. The store is a real file, made by
the real ``migrate`` command or by SQLite alone, and nothing else is
replaced.

A store that is not given must be left exactly as it was. So every test
of a refusal compares the file byte for byte, and the test without a
file looks for one afterwards.
"""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import Connection

from motosphere.cli import main
from motosphere.cli.store import MIGRATE_FIRST, StoreNotReadyError, store_to_work_on
from motosphere.core.logging_config import HANDLER_NAME
from motosphere.core.settings import get_settings
from motosphere.db import migrations
from motosphere.db.migrations import APPLICATION_ID, MIGRATIONS, Migration, schema_version
from motosphere.db.work import unit_of_work


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:
    """Undo every change main() makes to the root logger."""
    root = logging.getLogger()
    original_level = root.level
    yield
    for handler in [handler for handler in root.handlers if handler.name == HANDLER_NAME]:
        root.removeHandler(handler)
    root.setLevel(original_level)


def make(table: str) -> Migration:
    def migration(connection: Connection) -> None:
        connection.exec_driver_sql(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")

    return migration


THREE = (make("first"), make("second"), make("third"))


@pytest.fixture
def place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Where the settings say the store is: a file and a folder that are not there yet."""
    path = tmp_path / "data" / "store.sqlite3"
    monkeypatch.setenv("MOTOSPHERE_STORE_PATH", str(path))
    return path.resolve()


def history(monkeypatch: pytest.MonkeyPatch, *the_migrations: Migration) -> None:
    monkeypatch.setattr(migrations, "MIGRATIONS", the_migrations)


def with_sqlite_alone(path: Path, *statements: str) -> None:
    """Make the file at ``path`` as another program would: with SQLite and nothing else."""
    path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(path, autocommit=True)) as connection:
        for statement in statements:
            connection.execute(statement)


def read_with_sqlite_alone(path: Path, question: str) -> list[tuple[object, ...]]:
    with closing(sqlite3.connect(path, autocommit=True)) as connection:
        return [tuple(row) for row in connection.execute(question)]


def refusal() -> str:
    """What is said when the store of the settings is asked for and not given."""
    with pytest.raises(StoreNotReadyError) as raised:
        store_to_work_on(get_settings())
    return str(raised.value)


def test_where_there_is_no_store_none_is_given_and_none_is_made(
    place: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history(monkeypatch, *THREE)

    assert refusal() == (
        f"There is no data store: {place} does not exist. Run `python -m motosphere migrate` first."
    )
    assert not place.exists()
    assert not place.parent.exists()


def test_a_store_at_the_newest_schema_is_given(
    place: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history(monkeypatch, *THREE)
    main(["migrate"])

    store = store_to_work_on(get_settings())

    assert store.url.database == str(place)
    assert schema_version(store) == 3
    with unit_of_work(store) as work:
        work.connection().exec_driver_sql("INSERT INTO third (id) VALUES (7)")
    assert read_with_sqlite_alone(place, "SELECT id FROM third") == [(7,)]


def test_the_store_is_given_opened_as_every_store_is_opened(
    place: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history(monkeypatch, *THREE)
    main(["migrate"])

    store = store_to_work_on(get_settings())

    with store.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1


def test_a_store_at_the_newest_schema_of_the_pipeline_is_given(place: Path) -> None:
    main(["migrate"])

    store = store_to_work_on(get_settings())

    assert store.url.database == str(place)
    assert schema_version(store) == len(MIGRATIONS)


@pytest.mark.parametrize(
    ("had", "sentence"),
    [
        (0, "lacks 3 migrations: {place} is at schema version 0, and the newest is version 3."),
        (1, "lacks 2 migrations: {place} is at schema version 1, and the newest is version 3."),
        (2, "lacks 1 migration: {place} is at schema version 2, and the newest is version 3."),
    ],
    ids=["a new, empty file", "one of three", "two of three"],
)
def test_a_store_that_lacks_migrations_is_not_given_and_is_not_given_them(
    had: int, sentence: str, place: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history(monkeypatch, *THREE[:had])
    main(["migrate"])
    before = place.read_bytes()
    history(monkeypatch, *THREE)

    assert refusal() == ("The data store " + sentence.format(place=place) + " " + MIGRATE_FIRST)
    assert place.read_bytes() == before
    assert list(place.parent.iterdir()) == [place]


@pytest.mark.parametrize(
    "statements",
    [
        ["CREATE TABLE theirs (id INTEGER PRIMARY KEY)"],
        ["PRAGMA application_id = 1196444487"],
        [f"PRAGMA application_id = {APPLICATION_ID}", "PRAGMA user_version = 4"],
        [f"PRAGMA application_id = {APPLICATION_ID}", "PRAGMA user_version = -1"],
    ],
    ids=[
        "the database of another program",
        "the mark of another application",
        "a store newer than the code",
        "a version below zero",
    ],
)
def test_a_store_migrate_would_refuse_is_refused_in_the_same_words_and_left_as_it_is(
    statements: list[str],
    place: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history(monkeypatch, *THREE)
    with_sqlite_alone(place, *statements)
    before = place.read_bytes()

    said = refusal()

    assert place.read_bytes() == before
    assert main(["migrate"]) == 1
    assert capsys.readouterr().err == said + "\n"


def test_a_file_that_is_no_database_is_refused_in_one_line_and_left_as_it_is(
    place: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history(monkeypatch, *THREE)
    place.parent.mkdir()
    place.write_bytes(b"These are notes, not a database.\n" * 40)

    said = refusal()

    assert said.startswith(
        f"The data store cannot be opened: {place} cannot be read as an SQLite database ("
    )
    assert "\n" not in said
    assert place.read_bytes() == b"These are notes, not a database.\n" * 40


def test_a_folder_where_the_store_should_be_is_refused_in_one_line(place: Path) -> None:
    place.mkdir(parents=True)

    assert refusal() == f"The data store cannot be opened: {place} is a folder, not a file."
    assert list(place.iterdir()) == []


def test_a_relative_store_path_is_taken_from_the_current_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The shared fixture has made tmp_path the current folder.
    monkeypatch.setenv("MOTOSPHERE_STORE_PATH", "data/store.sqlite3")
    history(monkeypatch, *THREE)
    place = (tmp_path / "data" / "store.sqlite3").resolve()

    assert refusal() == f"There is no data store: {place} does not exist. {MIGRATE_FIRST}"

    main(["migrate"])

    assert store_to_work_on(get_settings()).url.database == str(place)


@pytest.mark.parametrize("had", [2, 3], ids=["refused", "given"])
def test_no_connection_to_the_store_is_left_open(
    had: int, place: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history(monkeypatch, *THREE[:had])
    main(["migrate"])
    history(monkeypatch, *THREE)

    try:
        store_to_work_on(get_settings())
    except StoreNotReadyError:
        assert had == 2
    else:
        assert had == 3

    # A connection that had read the store and was left open would still
    # hold it: SQLite then gives it to no other connection for itself alone,
    with closing(sqlite3.connect(place, timeout=0, autocommit=True)) as alone:
        alone.execute("BEGIN EXCLUSIVE")
        alone.execute("ROLLBACK")
    # and Windows removes no file that a connection has open.
    place.unlink()
    assert not place.exists()
