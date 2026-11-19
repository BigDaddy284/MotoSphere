"""Tests of the rules every table keeps, without a store.

The tables here are made for the tests, each in a schema of its own, so
the real schema never sees them. ``tests/integration/test_base.py`` makes
tables in a real SQLite file.
"""

from typing import Any

import pytest
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.schema import SchemaItem

from motosphere.db.base import NAMING, Base, broken_rules

# What a table made by hand must say of itself to keep the rules. The
# tables of models get both from ``Base``.
KEPT: dict[str, Any] = {"sqlite_strict": True, "sqlite_autoincrement": True}
NO_KEY = (
    "The table {} does not have the key every table has: one whole-number column "
    "named id, whose values are never given twice."
)


def a_schema() -> MetaData:
    """An empty schema with the naming rule of the real one."""
    return MetaData(naming_convention=NAMING)


def the_key() -> Column[int]:
    """The key every table has."""
    return Column("id", Integer, primary_key=True)


def test_the_real_schema_breaks_no_rule() -> None:
    assert broken_rules(Base.metadata) == []


def test_tables_that_keep_the_rules_break_none() -> None:
    schema = a_schema()
    Table("owner", schema, the_key(), Column("name", Text, unique=True), **KEPT)
    Table(
        "item",
        schema,
        the_key(),
        Column("owner_id", Integer, ForeignKey("owner.id")),
        Column("number", Integer),
        Column("place", Text, index=True),
        UniqueConstraint("owner_id", "number"),
        CheckConstraint("number > 0", name="number_positive"),
        Index(None, "place", "number"),
        **KEPT,
    )

    assert broken_rules(schema) == []


def test_a_table_that_is_not_strict_is_named() -> None:
    schema = a_schema()
    Table("strict_one", schema, the_key(), **KEPT)
    Table("loose_one", schema, the_key(), sqlite_autoincrement=True)

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
    Table("other", schema, the_key(), **KEPT)
    Table("odd_one", schema, *columns, **options)

    assert broken_rules(schema) == [NO_KEY.format("odd_one")]


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
    Table("other", schema, the_key(), **KEPT)
    Table("named", schema, the_key(), Column("number", Integer), by_hand, **KEPT)

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
        UniqueConstraint("b", name="second"),
        UniqueConstraint("a", name="first"),
        **KEPT,
    )
    Table("aardvark", schema, the_key())

    assert broken_rules(schema) == [
        "The table aardvark is not strict.",
        NO_KEY.format("aardvark"),
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
