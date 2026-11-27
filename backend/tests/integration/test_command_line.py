"""Integration tests that run the real ``python -m motosphere`` command as a separate process.

Each test runs the command in an empty working directory, so no real ``.env``
file is read, and with every ``MOTOSPHERE_`` variable removed from the
environment except the ones the test sets itself.
"""

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import motosphere
from motosphere.core.settings import ENV_PREFIX
from motosphere.db.migrations import MIGRATIONS
from motosphere.publish.manifest import Manifest

TIMEOUT_SECONDS = 60
USAGE_PREFIX = "usage: python -m motosphere "


def _run(
    cwd: Path, *arguments: str, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = {
        name: value for name, value in os.environ.items() if not name.upper().startswith(ENV_PREFIX)
    }
    if extra_env is not None:
        env.update(extra_env)
    # The command is fixed (this Python running the motosphere module) and no shell is used.
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "motosphere", *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def _assert_one_configuration_error(result: subprocess.CompletedProcess[str], name: str) -> None:
    assert result.returncode == 2
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert len(lines) == 1, result.stderr
    assert lines[0].startswith("Configuration error: ")
    assert name in lines[0]


def test_version_command(tmp_path: Path) -> None:
    result = _run(tmp_path, "version")

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"motosphere {motosphere.__version__}\n"
    assert result.stderr == ""


def test_no_command_prints_usage_and_fails(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith(USAGE_PREFIX)


def test_unknown_command_prints_usage_and_fails(tmp_path: Path) -> None:
    result = _run(tmp_path, "serve")

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith(USAGE_PREFIX)
    assert "'serve'" in result.stderr


def test_help_succeeds(tmp_path: Path) -> None:
    result = _run(tmp_path, "--help")

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(USAGE_PREFIX)
    assert result.stderr == ""


def test_invalid_environment_variable_exits_with_code_2(tmp_path: Path) -> None:
    result = _run(tmp_path, "version", extra_env={"MOTOSPHERE_LOG_LEVEL": "LOUD"})

    _assert_one_configuration_error(result, "log_level")


def test_dotenv_file_in_the_working_directory_is_read(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("MOTOSPHERE_ENVIRONMENT=staging\n", encoding="utf-8")

    result = _run(tmp_path, "version")

    _assert_one_configuration_error(result, "environment")


def test_removed_server_setting_is_rejected(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("MOTOSPHERE_API_PORT=8000\n", encoding="utf-8")

    result = _run(tmp_path, "version")

    _assert_one_configuration_error(result, "api_port")


def test_export_command_writes_a_valid_manifest(tmp_path: Path) -> None:
    before = datetime.now(UTC).replace(microsecond=0)

    result = _run(tmp_path, "export", "--out", "site/data")

    after = datetime.now(UTC)
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{Path('site', 'data', 'manifest.json')}\n"
    directory = tmp_path / "site" / "data"
    content = (directory / "manifest.json").read_bytes()
    assert b"\r" not in content
    assert content.endswith(b"}\n")
    manifest = Manifest.model_validate_json(content)
    assert manifest.application_version == motosphere.__version__
    assert before <= manifest.generated_at <= after
    assert sorted(entry.name for entry in directory.iterdir()) == ["manifest.json"]


def test_export_twice_differs_only_in_the_generation_time(tmp_path: Path) -> None:
    first = _run(tmp_path, "export", "--out", "first")
    second = _run(tmp_path, "export", "--out", "second")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    first_data = json.loads((tmp_path / "first" / "manifest.json").read_bytes())
    second_data = json.loads((tmp_path / "second" / "manifest.json").read_bytes())
    assert list(first_data) == sorted(first_data)
    assert list(second_data) == list(first_data)
    del first_data["generated_at"]
    del second_data["generated_at"]
    assert first_data == second_data


def test_export_into_a_file_fails_with_one_line(tmp_path: Path) -> None:
    existing = tmp_path / "data"
    existing.write_bytes(b"not a directory\n")

    result = _run(tmp_path, "export", "--out", "data")

    assert result.returncode == 1
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert len(lines) == 1, result.stderr
    assert lines[0].startswith("Export failed: cannot write to data: ")
    assert existing.read_bytes() == b"not a directory\n"


def test_migrate_makes_the_store_where_there_is_none(tmp_path: Path) -> None:
    store = (tmp_path / "store" / "motosphere.sqlite3").resolve()

    result = _run(tmp_path, "migrate")

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"A new data store was made: {store} is at schema version {len(MIGRATIONS)}.\n"
    )
    assert result.stderr == ""
    assert store.is_file()


def test_migrate_a_second_time_says_the_store_is_up_to_date_and_changes_nothing(
    tmp_path: Path,
) -> None:
    store = (tmp_path / "elsewhere" / "data.sqlite3").resolve()
    setting = {"MOTOSPHERE_STORE_PATH": str(Path("elsewhere", "data.sqlite3"))}
    first = _run(tmp_path, "migrate", extra_env=setting)
    before = store.read_bytes()

    second = _run(tmp_path, "migrate", extra_env=setting)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert second.stdout == (
        f"The data store is up to date: {store} is at schema version {len(MIGRATIONS)}.\n"
    )
    assert second.stderr == ""
    assert store.read_bytes() == before
    assert not (tmp_path / "store").exists()


def test_migrate_refuses_the_database_of_another_program_in_one_line(tmp_path: Path) -> None:
    theirs = (tmp_path / "theirs.sqlite3").resolve()
    with closing(sqlite3.connect(theirs, autocommit=True)) as connection:
        connection.execute("CREATE TABLE theirs (id INTEGER PRIMARY KEY)")
    before = theirs.read_bytes()

    result = _run(tmp_path, "migrate", extra_env={"MOTOSPHERE_STORE_PATH": "theirs.sqlite3"})

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == (
        f"The data store cannot be brought up to date: {theirs} is not a store of "
        "MotoSphere's (it is not a new, empty file, and it does not carry MotoSphere's mark).\n"
    )
    assert theirs.read_bytes() == before


def test_migrate_refuses_a_file_that_is_no_database_in_one_line(tmp_path: Path) -> None:
    notes = (tmp_path / "notes.txt").resolve()
    notes.write_bytes(b"These are notes, not a database.\n" * 40)

    result = _run(tmp_path, "migrate", extra_env={"MOTOSPHERE_STORE_PATH": "notes.txt"})

    assert result.returncode == 1
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert len(lines) == 1, result.stderr
    assert lines[0].startswith(
        f"The data store cannot be opened: {notes} cannot be read as an SQLite database ("
    )
    assert notes.read_bytes() == b"These are notes, not a database.\n" * 40


def test_schema_says_that_there_is_no_store_and_makes_none(tmp_path: Path) -> None:
    store = (tmp_path / "store" / "motosphere.sqlite3").resolve()

    result = _run(tmp_path, "schema")

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"There is no data store: {store} does not exist.\n"
    assert result.stderr == ""
    assert list(tmp_path.iterdir()) == []


def test_schema_says_that_a_migrated_store_is_up_to_date_and_changes_nothing(
    tmp_path: Path,
) -> None:
    store = (tmp_path / "store" / "motosphere.sqlite3").resolve()
    made = _run(tmp_path, "migrate")
    before = store.read_bytes()

    result = _run(tmp_path, "schema")

    assert made.returncode == 0, made.stderr
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"The data store is up to date: {store} is at schema version {len(MIGRATIONS)}.\n"
    )
    assert result.stderr == ""
    assert store.read_bytes() == before
    assert list(store.parent.iterdir()) == [store]


def test_schema_refuses_the_database_of_another_program_in_one_line(tmp_path: Path) -> None:
    theirs = (tmp_path / "theirs.sqlite3").resolve()
    with closing(sqlite3.connect(theirs, autocommit=True)) as connection:
        connection.execute("CREATE TABLE theirs (id INTEGER PRIMARY KEY)")
    before = theirs.read_bytes()

    result = _run(tmp_path, "schema", extra_env={"MOTOSPHERE_STORE_PATH": "theirs.sqlite3"})

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == (
        f"The data store cannot be brought up to date: {theirs} is not a store of "
        "MotoSphere's (it is not a new, empty file, and it does not carry MotoSphere's mark).\n"
    )
    assert theirs.read_bytes() == before


def test_schema_refuses_a_file_that_is_no_database_in_one_line(tmp_path: Path) -> None:
    notes = (tmp_path / "notes.txt").resolve()
    notes.write_bytes(b"These are notes, not a database.\n" * 40)

    result = _run(tmp_path, "schema", extra_env={"MOTOSPHERE_STORE_PATH": "notes.txt"})

    assert result.returncode == 1
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert len(lines) == 1, result.stderr
    assert lines[0].startswith(
        f"The data store cannot be opened: {notes} cannot be read as an SQLite database ("
    )
    assert notes.read_bytes() == b"These are notes, not a database.\n" * 40


def test_countries_loads_the_countries_into_a_migrated_store_and_then_adds_nothing(
    tmp_path: Path,
) -> None:
    store = (tmp_path / "store" / "motosphere.sqlite3").resolve()
    _run(tmp_path, "migrate")
    of_the_release = "Of the 249 countries of release 4.20.1 of iso-codes, "

    result = _run(tmp_path, "countries")

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"{of_the_release}249 were added to the data store {store} and none was there already.\n"
    )
    assert result.stderr == ""
    with closing(sqlite3.connect(store)) as connection:
        assert connection.execute("SELECT count(*) FROM country").fetchall() == [(249,)]
        assert connection.execute("SELECT name FROM source").fetchall() == [("iso-codes",)]
    before = store.read_bytes()

    again = _run(tmp_path, "countries")

    assert again.returncode == 0, again.stderr
    assert again.stdout == (
        f"{of_the_release}none was added to the data store {store} and 249 were there already.\n"
    )
    assert again.stderr == ""
    assert store.read_bytes() == before


def test_countries_without_a_store_says_what_to_do_and_makes_none(tmp_path: Path) -> None:
    store = (tmp_path / "store" / "motosphere.sqlite3").resolve()

    result = _run(tmp_path, "countries")

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == (
        f"There is no data store: {store} does not exist. "
        "Run `python -m motosphere migrate` first.\n"
    )
    assert list(tmp_path.iterdir()) == []
