"""Tests of opening the data store, against a real SQLite file in the test's own folder."""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import Engine, event
from sqlalchemy.exc import IntegrityError

from motosphere.db.sqlite import text_of, version_of
from motosphere.db.store import StoreError, open_store

PARENT = "CREATE TABLE parent (id INTEGER PRIMARY KEY)"
CHILD = "CREATE TABLE child (parent_id INTEGER NOT NULL REFERENCES parent (id))"
A_PARENT = "INSERT INTO parent (id) VALUES (1)"
AN_ORPHAN = "INSERT INTO child (parent_id) VALUES (7)"
BROKEN_KEY = "FOREIGN KEY constraint failed"


def with_parent_and_child(path: Path) -> Engine:
    engine = open_store(path)
    with engine.begin() as connection:
        connection.exec_driver_sql(PARENT)
        connection.exec_driver_sql(CHILD)
    return engine


def tables(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM sqlite_master ORDER BY name")
        return [str(name) for (name,) in found]


def parents(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(connection.exec_driver_sql("SELECT count(*) FROM parent").scalar_one())


def fail_after(engine: Engine, *statements: str) -> None:
    """Do the statements as one piece of work, and fail before it is committed."""
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
        raise RuntimeError("the work failed part-way")


def this_sqlite() -> str:
    connection = sqlite3.connect(":memory:")
    try:
        return text_of(version_of(connection))
    finally:
        connection.close()


def test_opening_a_store_makes_its_file_and_its_folder(tmp_path: Path) -> None:
    path = tmp_path / "a folder" / "inside it" / "store.sqlite3"

    open_store(path)

    assert path.is_file()


def test_a_store_can_be_opened_again_before_anything_was_written(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite3"
    open_store(path)

    assert tables(open_store(path)) == []


def test_a_relative_path_is_taken_from_the_folder_the_store_was_opened_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    engine = open_store(Path("kept here") / "store.sqlite3")
    monkeypatch.chdir(elsewhere)

    with engine.begin() as connection:
        connection.exec_driver_sql(PARENT)

    assert (tmp_path / "kept here" / "store.sqlite3").stat().st_size > 0
    assert list(elsewhere.iterdir()) == []


def test_a_row_without_its_parent_is_refused_on_the_first_connection(tmp_path: Path) -> None:
    engine = open_store(tmp_path / "store.sqlite3")

    with engine.connect() as connection:
        connection.exec_driver_sql(PARENT)
        connection.exec_driver_sql(CHILD)
        with pytest.raises(IntegrityError, match=BROKEN_KEY):
            connection.exec_driver_sql(AN_ORPHAN)


def test_a_row_without_its_parent_is_refused_on_every_later_connection(tmp_path: Path) -> None:
    engine = with_parent_and_child(tmp_path / "store.sqlite3")

    for _ in range(3):
        with engine.connect() as connection, pytest.raises(IntegrityError, match=BROKEN_KEY):
            connection.exec_driver_sql(AN_ORPHAN)


def test_a_row_without_its_parent_is_refused_on_two_connections_open_at_once(
    tmp_path: Path,
) -> None:
    engine = with_parent_and_child(tmp_path / "store.sqlite3")

    with engine.connect() as first, engine.connect() as second:
        with pytest.raises(IntegrityError, match=BROKEN_KEY):
            first.exec_driver_sql(AN_ORPHAN)
        first.rollback()
        with pytest.raises(IntegrityError, match=BROKEN_KEY):
            second.exec_driver_sql(AN_ORPHAN)


def test_a_row_without_its_parent_is_refused_when_the_store_is_opened_again(
    tmp_path: Path,
) -> None:
    path = tmp_path / "store.sqlite3"
    with_parent_and_child(path)

    with open_store(path).connect() as connection, pytest.raises(IntegrityError, match=BROKEN_KEY):
        connection.exec_driver_sql(AN_ORPHAN)


def test_a_row_with_its_parent_is_accepted(tmp_path: Path) -> None:
    engine = with_parent_and_child(tmp_path / "store.sqlite3")

    with engine.begin() as connection:
        connection.exec_driver_sql(A_PARENT)
        connection.exec_driver_sql("INSERT INTO child (parent_id) VALUES (1)")

    assert parents(engine) == 1


def test_work_that_is_committed_is_there_when_the_store_is_opened_again(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite3"
    engine = with_parent_and_child(path)

    with engine.begin() as connection:
        connection.exec_driver_sql(A_PARENT)

    assert parents(open_store(path)) == 1


def test_a_row_of_work_that_fails_is_taken_back(tmp_path: Path) -> None:
    engine = with_parent_and_child(tmp_path / "store.sqlite3")

    with pytest.raises(RuntimeError, match="part-way"):
        fail_after(engine, A_PARENT)

    assert parents(engine) == 0


def test_a_new_table_of_work_that_fails_is_taken_back(tmp_path: Path) -> None:
    engine = open_store(tmp_path / "store.sqlite3")

    with pytest.raises(RuntimeError, match="part-way"):
        fail_after(engine, PARENT, A_PARENT)

    assert tables(engine) == []


def test_work_that_is_not_committed_is_not_kept(tmp_path: Path) -> None:
    engine = with_parent_and_child(tmp_path / "store.sqlite3")

    with engine.connect() as connection:
        connection.exec_driver_sql(A_PARENT)

    assert parents(engine) == 0


def test_every_connection_is_closed_after_use(tmp_path: Path) -> None:
    engine = with_parent_and_child(tmp_path / "store.sqlite3")
    opened: list[object] = []
    closed: list[object] = []
    event.listen(engine, "connect", lambda connection, _record: opened.append(connection))
    event.listen(engine, "close", lambda connection, _record: closed.append(connection))

    for _ in range(3):
        assert parents(engine) == 0

    assert len(opened) == 3
    assert closed == opened


def test_the_file_can_be_removed_after_use(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite3"
    engine = with_parent_and_child(path)
    assert parents(engine) == 0

    path.unlink()

    assert not path.exists()


def test_an_sqlite_that_is_too_old_is_refused_in_one_sentence_and_nothing_is_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("motosphere.db.sqlite.LEAST_VERSION", (99, 0, 0))

    with pytest.raises(StoreError) as refusal:
        open_store(tmp_path / "a folder" / "store.sqlite3")

    assert str(refusal.value) == (
        f"The data store cannot be opened: SQLite {this_sqlite()} is older than 99.0.0, "
        "the least version the data store works with."
    )
    assert list(tmp_path.iterdir()) == []


def test_everything_the_sqlite_lacks_is_in_the_one_sentence(tmp_path: Path) -> None:
    def lacking() -> list[str]:
        return ["this SQLite has no JSON functions", "this SQLite has no full-text search (FTS5)"]

    with pytest.raises(StoreError) as refusal:
        open_store(tmp_path / "store.sqlite3", lacking)

    assert str(refusal.value) == (
        "The data store cannot be opened: this SQLite has no JSON functions; "
        "this SQLite has no full-text search (FTS5)."
    )
    assert list(tmp_path.iterdir()) == []


def test_a_folder_is_refused_and_named_with_its_whole_path(tmp_path: Path) -> None:
    folder = tmp_path / "store.sqlite3"
    folder.mkdir()

    with pytest.raises(StoreError) as refusal:
        open_store(Path("store.sqlite3"))

    assert str(refusal.value) == (
        f"The data store cannot be opened: {folder.resolve()} is a folder, not a file."
    )
    assert list(folder.iterdir()) == []


def test_a_file_that_is_not_a_database_is_refused_and_left_as_it_was(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite3"
    notes = b"These are somebody's notes, not a database.\n" * 40
    path.write_bytes(notes)

    with pytest.raises(StoreError) as refusal:
        open_store(path)

    assert str(refusal.value) == (
        f"The data store cannot be opened: {path.resolve()} cannot be read as an SQLite "
        "database (file is not a database)."
    )
    assert path.read_bytes() == notes


def test_a_folder_that_cannot_be_made_is_refused(tmp_path: Path) -> None:
    taken = tmp_path / "taken"
    taken.write_text("a file where the store's folder should be", encoding="utf-8")

    with pytest.raises(StoreError) as refusal:
        open_store(taken / "store.sqlite3")

    assert str(refusal.value).startswith(
        f"The data store cannot be opened: the folder {taken.resolve()} cannot be made ("
    )
    assert taken.is_file()
