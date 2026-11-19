"""Tests of the ``schema`` command with a history of migrations, against a real SQLite file.

Like the tests of ``migrate`` in ``test_migrate_command.py``, these call
:func:`motosphere.cli.main` in the test's process, with a list of
migrations of their own in the place of the pipeline's, which is still
empty. The store is a real file, and nothing else is replaced.
``test_command_line.py`` runs the command in a process of its own, with the
pipeline's list.

The command must never write. So every test that gives it a file compares
the file byte for byte, and the test without a file looks for one
afterwards.
"""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import Connection

from motosphere.cli import main
from motosphere.core.logging_config import HANDLER_NAME
from motosphere.db import migrations
from motosphere.db.migrations import APPLICATION_ID, Migration


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


def test_where_there_is_no_store_the_command_says_so_and_makes_none(
    place: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    history(monkeypatch, *THREE)

    assert main(["schema"]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"There is no data store: {place} does not exist.\n"
    assert captured.err == ""
    assert not place.exists()
    assert not place.parent.exists()


def test_a_store_at_the_newest_schema_is_up_to_date(
    place: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    history(monkeypatch, *THREE)
    main(["migrate"])
    capsys.readouterr()
    before = place.read_bytes()

    assert main(["schema"]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"The data store is up to date: {place} is at schema version 3.\n"
    assert captured.err == ""
    assert place.read_bytes() == before
    assert list(place.parent.iterdir()) == [place]


@pytest.mark.parametrize(
    ("had", "sentence"),
    [
        (0, "lacks 3 migrations: {place} is at schema version 0, and the newest is version 3."),
        (1, "lacks 2 migrations: {place} is at schema version 1, and the newest is version 3."),
        (2, "lacks 1 migration: {place} is at schema version 2, and the newest is version 3."),
    ],
    ids=["a new, empty file", "one of three", "two of three"],
)
def test_a_store_that_lacks_migrations_is_told_how_many_and_is_not_given_them(
    had: int,
    sentence: str,
    place: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history(monkeypatch, *THREE[:had])
    main(["migrate"])
    capsys.readouterr()
    before = place.read_bytes()
    history(monkeypatch, *THREE)

    assert main(["schema"]) == 0

    captured = capsys.readouterr()
    assert captured.out == "The data store " + sentence.format(place=place) + "\n"
    assert captured.err == ""
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

    code = main(["schema"])

    said = capsys.readouterr()
    assert place.read_bytes() == before
    assert main(["migrate"]) == 1
    refusal = capsys.readouterr()
    assert code == 1
    assert said.out == ""
    assert said.err == refusal.err


def test_a_file_that_is_no_database_is_refused_in_one_line_and_left_as_it_is(
    place: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    history(monkeypatch, *THREE)
    place.parent.mkdir()
    place.write_bytes(b"These are notes, not a database.\n" * 40)

    assert main(["schema"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(
        f"The data store cannot be opened: {place} cannot be read as an SQLite database ("
    )
    assert captured.err.count("\n") == 1
    assert place.read_bytes() == b"These are notes, not a database.\n" * 40


def test_a_folder_where_the_store_should_be_is_refused_in_one_line(
    place: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    place.mkdir(parents=True)

    assert main(["schema"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"The data store cannot be opened: {place} is a folder, not a file.\n"
    assert list(place.iterdir()) == []


def test_a_relative_store_path_is_taken_from_the_current_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # The shared fixture has made tmp_path the current folder.
    monkeypatch.setenv("MOTOSPHERE_STORE_PATH", "data/store.sqlite3")
    history(monkeypatch, *THREE)
    place = (tmp_path / "data" / "store.sqlite3").resolve()

    assert main(["schema"]) == 0
    assert capsys.readouterr().out == f"There is no data store: {place} does not exist.\n"

    main(["migrate"])
    capsys.readouterr()

    assert main(["schema"]) == 0
    assert capsys.readouterr().out == (
        f"The data store is up to date: {place} is at schema version 3.\n"
    )
