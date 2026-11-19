"""Tests of the rules every table keeps, without a store.

The tables here are made for the tests, each in a schema of its own, so
the real schema never sees them. ``tests/integration/test_base.py`` makes
tables in a real SQLite file.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.schema import SchemaItem

from motosphere.db import times
from motosphere.db.base import NAMING, Base, broken_rules
from motosphere.db.times import UtcDateTime

# What a table made by hand must say of itself to keep the rules. The
# tables of models get both from ``Base``, and the key and the two times
# with them.
KEPT: dict[str, Any] = {"sqlite_strict": True, "sqlite_autoincrement": True}
A_MOMENT = datetime(2026, 11, 19, 8, 0, tzinfo=UTC)
NO_KEY = (
    "The table {} does not have the key every table has: one whole-number column "
    "named id, whose values are never given twice."
)
NO_TIMES = (
    "The table {} does not have the times every table has: created_at and updated_at, "
    "which the store's code sets when a row is first stored and whenever it is changed."
)


def a_schema() -> MetaData:
    """An empty schema with the naming rule of the real one."""
    return MetaData(naming_convention=NAMING)


def the_key() -> Column[int]:
    """The key every table has."""
    return Column("id", Integer, primary_key=True)


def a_time(name: str, **said: Any) -> Column[datetime]:
    """One of the two times, as every table has it unless ``said`` otherwise."""
    how: dict[str, Any] = {"type_": UtcDateTime, "nullable": False, "default": times.now}
    if name == "updated_at":
        how["onupdate"] = times.now
    return Column(name, **(how | said))


def the_times() -> list[Column[datetime]]:
    """The two times every table has."""
    return [a_time("created_at"), a_time("updated_at")]


def test_the_real_schema_breaks_no_rule() -> None:
    assert broken_rules(Base.metadata) == []


def test_tables_that_keep_the_rules_break_none() -> None:
    schema = a_schema()
    Table("owner", schema, the_key(), Column("name", Text, unique=True), *the_times(), **KEPT)
    Table(
        "item",
        schema,
        the_key(),
        Column("owner_id", Integer, ForeignKey("owner.id")),
        Column("number", Integer),
        Column("place", Text, index=True),
        *the_times(),
        UniqueConstraint("owner_id", "number"),
        CheckConstraint("number > 0", name="number_positive"),
        Index(None, "place", "number"),
        **KEPT,
    )

    assert broken_rules(schema) == []


def test_a_table_that_is_not_strict_is_named() -> None:
    schema = a_schema()
    Table("strict_one", schema, the_key(), *the_times(), **KEPT)
    Table("loose_one", schema, the_key(), *the_times(), sqlite_autoincrement=True)

    assert broken_rules(schema) == ["The table loose_one is not strict."]


@pytest.mark.parametrize(
    ("columns", "options"),
    [
        ([Column("id", Integer)], KEPT),
        ([Column("number", Integer, primary_key=True)], KEPT),
        ([the_key(), Column("number", Integer, primary_key=True)], KEPT),
        ([Column("id", Text, primary_key=True)], KEPT),
        ([Column("id", Integer, ForeignKey("other.id"), primary_key=True)], KEPT),
        ([the_key()], {"sqlite_strict": True}),
    ],
    ids=[
        "no key",
        "a key of another name",
        "a key of two columns",
        "a key that is text",
        "a key that is the key of another table",
        "a key that may be given twice",
    ],
)
def test_a_table_without_the_key_every_table_has_is_named(
    columns: list[Column[Any]], options: dict[str, Any]
) -> None:
    schema = a_schema()
    Table("other", schema, the_key(), *the_times(), **KEPT)
    Table("odd_one", schema, *columns, *the_times(), **options)

    assert broken_rules(schema) == [NO_KEY.format("odd_one")]


@pytest.mark.parametrize(
    "columns",
    [
        [],
        [a_time("updated_at")],
        [a_time("created_at")],
        [a_time("created_at", type_=DateTime), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", type_=DateTime)],
        [a_time("created_at", nullable=True), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", nullable=True)],
        [a_time("created_at", server_default=text("CURRENT_TIMESTAMP")), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", server_default=text("CURRENT_TIMESTAMP"))],
        [a_time("created_at", default=None), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", default=None)],
        [a_time("created_at", default=A_MOMENT), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", default=A_MOMENT)],
        [a_time("created_at", default=func.now()), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", default=func.now())],
        [a_time("created_at", onupdate=times.now), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", onupdate=None)],
        [a_time("created_at"), a_time("updated_at", onupdate=A_MOMENT)],
        [a_time("created_at"), a_time("updated_at", onupdate=func.now())],
    ],
    ids=[
        "no times",
        "no time of the first storing",
        "no time of the last change",
        "a first time of another type",
        "a last time of another type",
        "a first time that may be empty",
        "a last time that may be empty",
        "a first time the table sets itself",
        "a last time the table sets itself",
        "a first time the store's code does not set",
        "a last time the store's code does not set",
        "a first time that is one fixed moment",
        "a last time that is one fixed moment",
        "a first time that SQLite is asked for",
        "a last time that SQLite is asked for",
        "a first time that is set anew at a change",
        "a last time that is not set anew at a change",
        "a last time that a change sets to one fixed moment",
        "a last time that a change asks SQLite for",
    ],
)
def test_a_table_without_the_times_every_table_has_is_named(columns: list[Column[Any]]) -> None:
    schema = a_schema()
    Table("odd_one", schema, the_key(), *columns, **KEPT)

    assert broken_rules(schema) == [NO_TIMES.format("odd_one")]


@pytest.mark.parametrize(
    "by_hand",
    [
        UniqueConstraint("number", name="mine"),
        ForeignKeyConstraint(["number"], ["other.id"], name="mine"),
        Index("mine", "number"),
    ],
    ids=["a unique constraint", "a foreign key", "an index"],
)
def test_a_name_given_by_hand_is_named(by_hand: SchemaItem) -> None:
    schema = a_schema()
    Table("other", schema, the_key(), *the_times(), **KEPT)
    Table("named", schema, the_key(), Column("number", Integer), *the_times(), by_hand, **KEPT)

    assert broken_rules(schema) == [
        "The table named has a name given by hand, mine: "
        "constraints and indexes are named by the naming rule."
    ]


def test_the_breaks_are_listed_table_by_table_and_rule_by_rule() -> None:
    schema = a_schema()
    Table(
        "zebra",
        schema,
        the_key(),
        Column("a", Integer),
        Column("b", Integer),
        *the_times(),
        UniqueConstraint("b", name="second"),
        UniqueConstraint("a", name="first"),
        **KEPT,
    )
    Table("aardvark", schema, the_key(), Column("a", Integer), UniqueConstraint("a", name="mine"))

    assert broken_rules(schema) == [
        "The table aardvark is not strict.",
        NO_KEY.format("aardvark"),
        NO_TIMES.format("aardvark"),
        "The table aardvark has a name given by hand, mine: "
        "constraints and indexes are named by the naming rule.",
        "The table zebra has a name given by hand, first: "
        "constraints and indexes are named by the naming rule.",
        "The table zebra has a name given by hand, second: "
        "constraints and indexes are named by the naming rule.",
    ]


def test_a_check_without_a_name_is_refused_when_its_table_is_defined() -> None:
    schema = a_schema()

    with pytest.raises(InvalidRequestError, match="requires that constraint is explicitly named"):
        Table(
            "nameless",
            schema,
            the_key(),
            Column("number", Integer),
            CheckConstraint("number > 0"),
            **KEPT,
        )
