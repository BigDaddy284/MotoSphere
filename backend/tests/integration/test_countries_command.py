"""Tests of the ``countries`` command, run for real against a real SQLite file.

These call :func:`motosphere.cli.main` in the test's process. The store
is a real file, made by the real ``migrate`` command with the pipeline's
own migrations, and the countries are those of the reference file that
comes with the pipeline. What the command leaves in the store is read
with SQLite alone, and what it must leave as it is was written the same
way, as a person or another program would have written it.
``test_command_line.py`` runs the command in a process of its own.

A command that refuses must leave the store as it was, and so must one
that finds nothing to add. So those tests compare the file byte for
byte.
"""

import logging
import socket
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from motosphere.cli import main
from motosphere.core.logging_config import HANDLER_NAME
from motosphere.db import migrations
from motosphere.db.migrations import MIGRATIONS
from motosphere.db.store import open_store
from motosphere.db.work import unit_of_work
from motosphere.reference import countries as reference_file
from motosphere.reference.countries import CountriesFileError, countries_of_the_project
from motosphere.reference.countries_source import CountriesSourceError, source_of_the_countries

# What the first line says, before the place of the store and after it.
OF_THE_RELEASE = "Of the 249 countries of release 4.20.1 of iso-codes, "
IN_THE_QUEUE = "and what the release says waits in the review queue."


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:
    """Undo every change main() makes to the root logger."""
    root = logging.getLogger()
    original_level = root.level
    yield
    for handler in [handler for handler in root.handlers if handler.name == HANDLER_NAME]:
        root.removeHandler(handler)
    root.setLevel(original_level)


@pytest.fixture
def place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Where the settings say the store is: a file and a folder that are not there yet."""
    path = tmp_path / "data" / "store.sqlite3"
    monkeypatch.setenv("MOTOSPHERE_STORE_PATH", str(path))
    return path.resolve()


@pytest.fixture
def store(place: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    """A store at the newest schema with nothing in it, made by the real ``migrate`` command."""
    assert main(["migrate"]) == 0
    capsys.readouterr()
    return place


@pytest.fixture
def loaded(store: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    """A store the real command has loaded the countries into."""
    assert main(["countries"]) == 0
    capsys.readouterr()
    return store


def read(path: Path, statement: str) -> list[tuple[object, ...]]:
    """Ask the file at ``path`` with SQLite alone."""
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(statement).fetchall()


def by_hand(path: Path, *statements: str | tuple[str, tuple[str, ...]]) -> None:
    """Change the file at ``path`` as another program would: with SQLite and nothing else.

    A statement is given alone, or with the values for its question marks.
    """
    with closing(sqlite3.connect(path, autocommit=True)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for statement in statements:
            if isinstance(statement, str):
                connection.execute(statement)
            else:
                connection.execute(*statement)


# A country put in by hand says of itself what the row of Andorra says.
ONE_MORE = (
    "INSERT INTO country (alpha_2, alpha_3, name, source_id, source_address, collected_at, "
    "published_on, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) "
    "SELECT ?, ?, ?, source_id, source_address, collected_at, published_on, last_verified_at, "
    "extraction_method, confidence, verification_status, created_at, updated_at "
    "FROM country WHERE alpha_2 = 'AD'"
)
GONE = "DELETE FROM country WHERE alpha_2 = ?"


def first_line(place: Path, added: str, there: str) -> str:
    return f"{OF_THE_RELEASE}{added} added to the data store {place} and {there} there already.\n"


def test_on_a_new_store_every_country_of_the_file_is_added_and_the_command_says_so(
    store: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["countries"]) == 0

    captured = capsys.readouterr()
    assert captured.out == first_line(store, "249 were", "none was")
    assert captured.err == ""
    of_the_file = sorted(
        (country.alpha_2, country.alpha_3, country.name) for country in countries_of_the_project()
    )
    assert len(of_the_file) == 249
    assert read(store, "SELECT alpha_2, alpha_3, name FROM country ORDER BY alpha_2") == of_the_file
    # The source is there, once, and every country names it.
    assert read(store, "SELECT id, name FROM source") == [(1, "iso-codes")]
    assert read(store, "SELECT DISTINCT source_id FROM country") == [(1,)]
    assert read(store, "SELECT count(*) FROM review_item") == [(0,)]


def test_run_again_the_command_adds_nothing_writes_nothing_and_says_so(
    loaded: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = loaded.read_bytes()

    assert main(["countries"]) == 0

    captured = capsys.readouterr()
    assert captured.out == first_line(loaded, "none was", "249 were")
    assert captured.err == ""
    assert loaded.read_bytes() == before
    assert list(loaded.parent.iterdir()) == [loaded]


@pytest.mark.parametrize(
    ("gone", "added", "there"),
    [
        (("NZ",), "1 was", "248 were"),
        (("AD", "NZ", "ZW"), "3 were", "246 were"),
    ],
    ids=["one", "three"],
)
def test_the_countries_the_store_does_not_have_are_added_and_the_others_counted(
    loaded: Path, capsys: pytest.CaptureFixture[str], gone: tuple[str, ...], added: str, there: str
) -> None:
    by_hand(loaded, *((GONE, (code,)) for code in gone))
    assert read(loaded, "SELECT count(*) FROM country") == [(249 - len(gone),)]

    assert main(["countries"]) == 0

    captured = capsys.readouterr()
    assert captured.out == first_line(loaded, added, there)
    assert captured.err == ""
    assert read(loaded, "SELECT count(*) FROM country") == [(249,)]
    assert read(loaded, "SELECT count(*) FROM source") == [(1,)]


def test_what_the_store_says_otherwise_of_is_named_left_and_waits_in_the_review_queue(
    loaded: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    by_hand(
        loaded,
        "UPDATE country SET name = 'Turkey' WHERE alpha_2 = 'TR'",
        "UPDATE country SET alpha_3 = 'FRX' WHERE alpha_2 = 'FR'",
    )
    as_changed = "SELECT alpha_2, alpha_3, name FROM country WHERE alpha_2 IN ('FR', 'TR')"
    assert read(loaded, as_changed) == [("FR", "FRX", "France"), ("TR", "TUR", "Turkey")]

    assert main(["countries"]) == 0

    captured = capsys.readouterr()
    assert captured.out == (
        first_line(loaded, "none was", "247 were")
        + "The data store says something else of 2 of them than the release does: FR, TR. "
        f"They were left as they are, {IN_THE_QUEUE}\n"
    )
    assert captured.err == ""
    assert read(loaded, as_changed) == [("FR", "FRX", "France"), ("TR", "TUR", "Turkey")]
    name_in_the_file = next(
        country.name for country in countries_of_the_project() if country.alpha_2 == "TR"
    )
    assert read(loaded, "SELECT field, source_value, state FROM review_item ORDER BY id") == [
        ("alpha_3", "FRA", "open"),
        ("name", name_in_the_file, "open"),
    ]

    # Run again, the command says the same and writes nothing.
    before = loaded.read_bytes()
    assert main(["countries"]) == 0
    assert capsys.readouterr().out == captured.out
    assert loaded.read_bytes() == before


def test_one_country_the_store_says_otherwise_of_is_said_as_one(
    loaded: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    by_hand(loaded, "UPDATE country SET name = 'Turkey' WHERE alpha_2 = 'TR'")

    assert main(["countries"]) == 0

    assert capsys.readouterr().out == (
        first_line(loaded, "none was", "248 were")
        + "The data store says something else of 1 of them than the release does: TR. "
        f"It was left as it is, {IN_THE_QUEUE}\n"
    )
    assert read(loaded, "SELECT count(*) FROM review_item") == [(1,)]


@pytest.mark.parametrize(
    ("more", "line"),
    [
        (
            (("XK", "XKX", "Kosovo"),),
            "The data store has 1 country that the release does not have: XK. "
            "It was left as it is.\n",
        ),
        (
            (("XK", "XKX", "Kosovo"), ("XA", "XAA", "Atlantis")),
            "The data store has 2 countries that the release does not have: XA, XK. "
            "They were left as they are.\n",
        ),
    ],
    ids=["one", "two"],
)
def test_a_country_the_release_does_not_have_is_named_and_left_as_it_is(
    loaded: Path,
    capsys: pytest.CaptureFixture[str],
    more: tuple[tuple[str, str, str], ...],
    line: str,
) -> None:
    by_hand(loaded, *((ONE_MORE, country) for country in more))
    before = loaded.read_bytes()

    assert main(["countries"]) == 0

    captured = capsys.readouterr()
    assert captured.out == first_line(loaded, "none was", "249 were") + line
    assert captured.err == ""
    # It is no doubt, and nothing was written.
    assert loaded.read_bytes() == before


def test_what_was_found_is_said_in_three_lines_in_their_order(
    loaded: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    by_hand(
        loaded,
        "UPDATE country SET name = 'Turkey' WHERE alpha_2 = 'TR'",
        "DELETE FROM country WHERE alpha_2 = 'NZ'",
    )
    by_hand(loaded, (ONE_MORE, ("XK", "XKX", "Kosovo")))

    assert main(["countries"]) == 0

    captured = capsys.readouterr()
    assert captured.out == (
        first_line(loaded, "1 was", "247 were")
        + "The data store says something else of 1 of them than the release does: TR. "
        f"It was left as it is, {IN_THE_QUEUE}\n"
        "The data store has 1 country that the release does not have: XK. "
        "It was left as it is.\n"
    )
    assert captured.err == ""
    assert read(loaded, "SELECT count(*) FROM country") == [(250,)]


def test_where_there_is_no_store_the_command_says_what_to_do_and_makes_none(
    place: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["countries"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"There is no data store: {place} does not exist. "
        "Run `python -m motosphere migrate` first.\n"
    )
    assert not place.exists()
    assert not place.parent.exists()


def test_a_store_that_lacks_a_migration_is_refused_and_left_as_it_is(
    place: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.MonkeyPatch.context() as for_now:
        for_now.setattr(migrations, "MIGRATIONS", MIGRATIONS[:-1])
        assert main(["migrate"]) == 0
    capsys.readouterr()
    before = place.read_bytes()
    newest = len(MIGRATIONS)

    assert main(["countries"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"The data store lacks 1 migration: {place} is at schema version {newest - 1}, "
        f"and the newest is version {newest}. Run `python -m motosphere migrate` first.\n"
    )
    assert place.read_bytes() == before
    assert list(place.parent.iterdir()) == [place]


def test_a_file_migrate_would_refuse_is_refused_in_the_same_words(
    place: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    place.parent.mkdir(parents=True)
    by_hand(place, "CREATE TABLE theirs (id INTEGER PRIMARY KEY)")
    before = place.read_bytes()
    assert main(["migrate"]) == 1
    of_migrate = capsys.readouterr().err
    assert of_migrate.count("\n") == 1

    assert main(["countries"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == of_migrate
    assert place.read_bytes() == before


def test_a_damaged_countries_file_is_refused_and_the_store_is_as_it_was(
    store: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Another file of the same folder stands in for a damaged one.
    monkeypatch.setattr(reference_file, "COUNTRIES_FILE", "README.md")
    with pytest.raises(CountriesFileError) as refused:
        countries_of_the_project()
    before = store.read_bytes()

    assert main(["countries"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{refused.value}\n"
    assert captured.err.count("\n") == 1
    assert store.read_bytes() == before
    assert list(store.parent.iterdir()) == [store]


def test_a_source_that_is_described_otherwise_is_refused_and_the_store_is_as_it_was(
    loaded: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    by_hand(
        loaded,
        "UPDATE source SET licence = 'MIT' WHERE name = 'iso-codes'",
        "DELETE FROM country WHERE alpha_2 = 'NZ'",
    )
    engine = open_store(loaded)
    with pytest.raises(CountriesSourceError) as refused, unit_of_work(engine) as work:
        source_of_the_countries(work)
    engine.dispose()
    before = loaded.read_bytes()

    assert main(["countries"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{refused.value}\n"
    assert "It differs in its licence." in captured.err
    assert loaded.read_bytes() == before
    assert read(loaded, "SELECT count(*) FROM country") == [(248,)]


def test_a_loading_that_fails_in_the_middle_leaves_nothing_of_it(
    store: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The store itself refuses the last country of the file, after 248 were taken.
    by_hand(
        store,
        "CREATE TRIGGER not_this_one BEFORE INSERT ON country WHEN NEW.alpha_2 = 'ZW' "
        "BEGIN SELECT RAISE(ABORT, 'the store refuses this country'); END",
    )

    with pytest.raises(IntegrityError, match="the store refuses this country"):
        main(["countries"])

    assert capsys.readouterr().out == ""
    assert read(store, "SELECT count(*) FROM country") == [(0,)]
    assert read(store, "SELECT count(*) FROM source") == [(0,)]


def test_nothing_is_fetched(
    store: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_connection(*_arguments: object, **_named: object) -> None:
        raise AssertionError("the command opened a network connection")

    monkeypatch.setattr(socket, "socket", no_connection)
    monkeypatch.setattr(socket, "create_connection", no_connection)

    assert main(["countries"]) == 0

    assert capsys.readouterr().out == first_line(store, "249 were", "none was")


def test_a_relative_store_path_is_taken_from_the_current_folder_and_named_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MOTOSPHERE_STORE_PATH", "data/store.sqlite3")
    whole = (tmp_path / "data" / "store.sqlite3").resolve()
    assert main(["migrate"]) == 0
    capsys.readouterr()

    assert main(["countries"]) == 0

    assert capsys.readouterr().out == first_line(whole, "249 were", "none was")
    assert read(whole, "SELECT count(*) FROM country") == [(249,)]
