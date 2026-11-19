"""What the data store needs from SQLite, and whether a given SQLite has it.

SQLite is not one program: every Python carries its own, built with its own
choice of features, and the Python on a GitHub machine is not the one on a
developer's computer. So the store relies only on what is named here, and
:func:`missing` says in plain words what a given SQLite lacks. Its tests run
against the real SQLite of the Python that runs them, on Linux and on Windows
(``DATABASE.md`` records what each machine had when this was decided).

Nothing here opens the store itself. The check works in a database of its
own, in memory, which is gone when the check ends.
"""

import contextlib
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

__all__ = ["FEATURES", "LEAST_VERSION", "Feature", "Version", "missing", "text_of", "version_of"]

Version = tuple[int, ...]

# The least SQLite the store works with: 3.45 is the oldest series it has been
# run with. An older one may well have every feature below; nobody has tried.
LEAST_VERSION: Version = (3, 45, 0)


@dataclass(frozen=True)
class Feature:
    """One thing the store relies on, and the statements that prove it is there."""

    # What it is, in plain words, to complete "this SQLite has no ...".
    name: str
    # Every statement must be accepted, in this order.
    accepted: tuple[str, ...]
    # If given, this statement must be refused after the others were accepted.
    refused: str = ""


FEATURES: tuple[Feature, ...] = (
    Feature(
        "foreign keys that are enforced",
        (
            "PRAGMA foreign_keys = ON",
            "CREATE TABLE parent (id INTEGER PRIMARY KEY)",
            "CREATE TABLE child (parent_id INTEGER NOT NULL REFERENCES parent (id))",
        ),
        refused="INSERT INTO child (parent_id) VALUES (1)",
    ),
    Feature(
        "tables with strict column types",
        ("CREATE TABLE strict_types (number INTEGER) STRICT",),
        refused="INSERT INTO strict_types (number) VALUES ('not a number')",
    ),
    Feature(
        "statements that return the rows they wrote (RETURNING)",
        (
            "CREATE TABLE returned (id INTEGER PRIMARY KEY, name TEXT)",
            "INSERT INTO returned (name) VALUES ('a') RETURNING id",
        ),
    ),
    Feature(
        "JSON functions",
        ("""SELECT json_extract('{"a": 1}', '$.a')""",),
    ),
    Feature(
        "R*Tree indexes (for finding places inside a part of the map)",
        ("CREATE VIRTUAL TABLE boxes USING rtree (id, west, east, south, north)",),
    ),
    Feature(
        "full-text search (FTS5)",
        ("CREATE VIRTUAL TABLE words USING fts5 (body)",),
    ),
)

Connect = Callable[[], sqlite3.Connection]


def text_of(version: Version) -> str:
    """A version the way people write it: 3.45.0."""
    return ".".join(str(part) for part in version)


def _in_memory() -> sqlite3.Connection:
    """A new, empty database in memory, in which every statement takes effect at once."""
    return sqlite3.connect(":memory:", isolation_level=None)


def version_of(connection: sqlite3.Connection) -> Version:
    """The version of the SQLite behind a connection."""
    (text,) = connection.execute("SELECT sqlite_version()").fetchone()
    return tuple(int(part) for part in str(text).split("."))


def _has(feature: Feature, connect: Connect) -> bool:
    """Whether a new, empty database accepts and refuses what the feature says."""
    with contextlib.closing(connect()) as connection:
        try:
            for statement in feature.accepted:
                connection.execute(statement).fetchall()
        except sqlite3.Error:
            return False
        if not feature.refused:
            return True
        try:
            connection.execute(feature.refused).fetchall()
        except sqlite3.Error:
            return True
        return False


def missing(connect: Connect = _in_memory) -> list[str]:
    """What this SQLite lacks, one plain sentence each. Empty when it lacks nothing.

    ``connect`` gives a new, empty database every time it is called; each
    feature is tried in one of its own, so no feature can help or hinder
    another.
    """
    problems = []
    with contextlib.closing(connect()) as connection:
        version = version_of(connection)
    if version < LEAST_VERSION:
        problems.append(
            f"SQLite {text_of(version)} is older than {text_of(LEAST_VERSION)}, "
            "the least version the data store works with"
        )
    problems.extend(
        f"this SQLite has no {feature.name}" for feature in FEATURES if not _has(feature, connect)
    )
    return problems
