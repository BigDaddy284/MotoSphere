"""Tests of the ``migrate`` command with a history of migrations, against a real SQLite file.

The pipeline's own list of migrations is still empty, and a command that
runs in a process of its own cannot be given another. So these tests call
:func:`motosphere.cli.main` in the test's process, with a list of their own
in the place of the pipeline's. The store is a real file, and nothing else
is replaced. ``test_command_line.py`` runs the command in a process of its
own, with the pipeline's list.
"""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Connection

from motosphere.cli import main
from motosphere.core.logging_config import HANDLER_NAME
from motosphere.db import migrations
from motosphere.db.migrations import Migration, schema_version
from motosphere.db.store import open_store


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


def tables(path: Path) -> list[str]:
    with open_store(path).connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM sqlite_master ORDER BY name")
        return [str(name) for (name,) in found]


def test_a_store_that_is_not_there_is_made_at_the_newest_schema(
    place: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    history(monkeypatch, *THREE)

    assert main(["migrate"]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"A new data store was made: {place} is at schema version 3.\n"
    assert captured.err == ""
    assert schema_version(open_store(place)) == 3
    assert tables(place) == ["first", "second", "third"]


def test_a_second_run_says_the_store_is_up_to_date_and_changes_nothing(
    place: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    history(monkeypatch, *THREE)
    main(["migrate"])
    capsys.readouterr()
    before = place.read_bytes()

    assert main(["migrate"]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"The data store is up to date: {place} is at schema version 3.\n"
    assert captured.err == ""
    assert place.read_bytes() == before


def test_a_store_is_given_the_migrations_it_lacks(
    place: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    history(monkeypatch, *THREE[:1])
    main(["migrate"])
    capsys.readouterr()
    history(monkeypatch, *THREE)

    assert main(["migrate"]) == 0

    captured = capsys.readouterr()
    assert captured.out == (
        f"The data store was brought up to date: {place} went from schema version 1 to 3.\n"
    )
    assert captured.err == ""
    assert tables(place) == ["first", "second", "third"]


def test_a_store_newer_than_the_code_is_refused_in_one_line_and_left_as_it_is(
    place: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    history(monkeypatch, *THREE)
    main(["migrate"])
    capsys.readouterr()
    before = place.read_bytes()
    history(monkeypatch, *THREE[:2])

    assert main(["migrate"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "The data store cannot be brought up to date: its schema is version 3, "
        "and this MotoSphere knows only the versions 0 to 2.\n"
    )
    assert place.read_bytes() == before


def test_an_error_inside_a_migration_is_not_caught(
    place: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    error = RuntimeError("the migration failed part-way")

    def fail(_connection: Connection) -> None:
        raise error

    history(monkeypatch, make("first"), fail, make("third"))

    with pytest.raises(RuntimeError) as caught:
        main(["migrate"])

    assert caught.value is error
    assert capsys.readouterr().out == ""
    assert schema_version(open_store(place)) == 1
    assert tables(place) == ["first"]


def test_a_relative_store_path_is_taken_from_the_current_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # The shared fixture has made tmp_path the current folder.
    monkeypatch.setenv("MOTOSPHERE_STORE_PATH", "data/store.sqlite3")
    history(monkeypatch, *THREE)
    place = (tmp_path / "data" / "store.sqlite3").resolve()

    assert main(["migrate"]) == 0

    assert capsys.readouterr().out == (
        f"A new data store was made: {place} is at schema version 3.\n"
    )
    assert schema_version(open_store(place)) == 3
