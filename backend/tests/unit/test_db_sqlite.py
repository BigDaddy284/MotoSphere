"""Tests for what the data store needs from SQLite (`motosphere.db.sqlite`).

A lesser SQLite is stood in for by the real one, in memory, made to behave
like it: it reports another version, refuses statements a lesser build
refuses, or lets through what it should have refused. The tests against the
machine's own SQLite, unchanged, are in `tests/integration`.
"""

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from motosphere.db import sqlite
from motosphere.db.sqlite import FEATURES, LEAST_VERSION, Feature, missing, text_of, version_of

REPOSITORY = Path(__file__).resolve().parents[3]

Connect = Callable[[], sqlite3.Connection]


def lesser(
    *, version: str = "", refuses: tuple[str, ...] = (), drops: tuple[str, ...] = ()
) -> Connect:
    """An SQLite that says it is ``version``, refuses every statement that holds
    one of ``refuses``, and acts as if each of ``drops`` had not been written."""

    class Lesser(sqlite3.Connection):
        def execute(self, sql: str, parameters: Any = (), /) -> sqlite3.Cursor:
            if version and sql == "SELECT sqlite_version()":
                return super().execute("SELECT ?", (version,))
            if any(words in sql for words in refuses):
                raise sqlite3.OperationalError(f"not in this build: {sql}")
            for words in drops:
                sql = sql.replace(words, "")
            return super().execute(sql, parameters)

    return lambda: sqlite3.connect(":memory:", isolation_level=None, factory=Lesser)


def at(version: sqlite.Version) -> Connect:
    """A complete SQLite that says it is ``version``."""
    return lesser(version=text_of(version))


OLD = (
    "SQLite {found} is older than "
    + text_of(LEAST_VERSION)
    + ", the least version the data store works with"
)


def test_a_version_is_written_the_way_people_write_it() -> None:
    assert text_of((3, 45, 0)) == "3.45.0"


def test_reads_the_version_of_the_sqlite_behind_a_connection() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        assert version_of(connection) == sqlite3.sqlite_version_info
    finally:
        connection.close()


def test_reads_the_version_as_numbers() -> None:
    connection = at((3, 9, 12))()
    try:
        assert version_of(connection) == (3, 9, 12)
    finally:
        connection.close()


def test_a_complete_sqlite_of_the_least_version_lacks_nothing() -> None:
    assert missing(at(LEAST_VERSION)) == []


def test_a_newer_sqlite_lacks_nothing() -> None:
    newer = (LEAST_VERSION[0], LEAST_VERSION[1] + 1, 0)

    assert missing(at(newer)) == []


def test_an_sqlite_just_below_the_least_version_is_too_old() -> None:
    below = (LEAST_VERSION[0], LEAST_VERSION[1] - 1, 99)

    assert missing(at(below)) == [OLD.format(found=text_of(below))]


def test_versions_are_compared_as_numbers_not_as_text() -> None:
    # As text, "3.9.0" comes after "3.45.0".
    assert missing(at((3, 9, 0))) == [OLD.format(found="3.9.0")]


@pytest.mark.parametrize("feature", FEATURES, ids=lambda feature: feature.name)
def test_a_feature_whose_last_statement_is_refused_is_missing(feature: Feature) -> None:
    connect = lesser(version=text_of(LEAST_VERSION), refuses=(feature.accepted[-1],))

    assert missing(connect) == [f"this SQLite has no {feature.name}"]


@pytest.mark.parametrize("feature", FEATURES, ids=lambda feature: feature.name)
def test_a_feature_whose_first_statement_is_refused_is_missing(feature: Feature) -> None:
    connect = lesser(version=text_of(LEAST_VERSION), refuses=(feature.accepted[0],))

    assert missing(connect) == [f"this SQLite has no {feature.name}"]


# What a build without each feature refuses, whatever the rest of the statement is.
BUILDS_WITHOUT = {
    "tables with strict column types": ") STRICT",
    "statements that return the rows they wrote (RETURNING)": " RETURNING ",
    "JSON functions": "json_extract(",
    "R*Tree indexes (for finding places inside a part of the map)": " USING rtree ",
    "full-text search (FTS5)": " USING fts5 ",
}


@pytest.mark.parametrize(("name", "words"), BUILDS_WITHOUT.items(), ids=BUILDS_WITHOUT)
def test_a_build_without_a_feature_is_found_out_by_what_it_refuses(name: str, words: str) -> None:
    connect = lesser(version=text_of(LEAST_VERSION), refuses=(words,))

    assert missing(connect) == [f"this SQLite has no {name}"]


def test_foreign_keys_that_are_not_enforced_are_missing() -> None:
    # A build without foreign keys accepts the setting and does nothing.
    connect = lesser(version=text_of(LEAST_VERSION), drops=("PRAGMA foreign_keys = ON",))

    assert missing(connect) == ["this SQLite has no foreign keys that are enforced"]


def test_strict_tables_that_take_any_value_are_missing() -> None:
    connect = lesser(version=text_of(LEAST_VERSION), drops=(" STRICT",))

    assert missing(connect) == ["this SQLite has no tables with strict column types"]


def test_everything_that_is_lacking_is_named_the_version_first() -> None:
    connect = lesser(version="3.31.1", refuses=("USING rtree", "USING fts5"))

    assert missing(connect) == [
        OLD.format(found="3.31.1"),
        "this SQLite has no R*Tree indexes (for finding places inside a part of the map)",
        "this SQLite has no full-text search (FTS5)",
    ]


def test_every_feature_is_tried_in_a_database_of_its_own_and_each_is_closed() -> None:
    opened: list[sqlite3.Connection] = []

    def connect() -> sqlite3.Connection:
        opened.append(at(LEAST_VERSION)())
        return opened[-1]

    assert missing(connect) == []

    # One for the version and one for each feature.
    assert len(opened) == 1 + len(FEATURES)
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")


def test_a_feature_cannot_lean_on_a_table_another_one_made() -> None:
    # Each feature's statements work in an empty database: none uses a name twice.
    for feature in FEATURES:
        connection = sqlite3.connect(":memory:", isolation_level=None)
        try:
            for statement in feature.accepted:
                connection.execute(statement)
        finally:
            connection.close()


def test_the_store_relies_on_these_six_features() -> None:
    assert [feature.name for feature in FEATURES] == [
        "foreign keys that are enforced",
        "tables with strict column types",
        "statements that return the rows they wrote (RETURNING)",
        "JSON functions",
        "R*Tree indexes (for finding places inside a part of the map)",
        "full-text search (FTS5)",
    ]


def test_the_features_that_must_refuse_something_say_what() -> None:
    assert {feature.name: feature.refused for feature in FEATURES if feature.refused} == {
        "foreign keys that are enforced": "INSERT INTO child (parent_id) VALUES (1)",
        "tables with strict column types": (
            "INSERT INTO strict_types (number) VALUES ('not a number')"
        ),
    }


def test_the_least_version_is_the_one_the_decision_record_gives() -> None:
    record = (REPOSITORY / "DATABASE.md").read_text(encoding="utf-8")

    assert f"**SQLite {text_of(LEAST_VERSION)} or newer**" in record
    assert record.count(" or newer**") == 1


def test_the_decision_record_names_every_feature_the_store_relies_on() -> None:
    record = (REPOSITORY / "DATABASE.md").read_text(encoding="utf-8")

    for feature in FEATURES:
        assert f"| {feature.name} |" in record, feature.name
