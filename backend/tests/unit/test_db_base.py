"""Tests of the rules every table keeps, without a store.

The tables here are made for the tests, each in a schema of its own, so
the real schema never sees them. ``tests/integration/test_base.py`` makes
tables in a real SQLite file.
"""

import pytest
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.schema import SchemaItem

from motosphere.db.base import NAMING, Base, broken_rules


def a_schema() -> MetaData:
    """An empty schema with the naming rule of the real one."""
    return MetaData(naming_convention=NAMING)


def test_the_real_schema_breaks_no_rule() -> None:
    assert broken_rules(Base.metadata) == []


def test_tables_that_keep_the_rules_break_none() -> None:
    schema = a_schema()
    Table(
        "owner",
        schema,
        Column("id", Integer, primary_key=True),
        Column("name", Text, unique=True),
        sqlite_strict=True,
    )
    Table(
        "item",
        schema,
        Column("id", Integer, primary_key=True),
        Column("owner_id", Integer, ForeignKey("owner.id")),
        Column("number", Integer),
        Column("place", Text, index=True),
        UniqueConstraint("owner_id", "number"),
        CheckConstraint("number > 0", name="number_positive"),
        Index(None, "place", "number"),
        sqlite_strict=True,
    )

    assert broken_rules(schema) == []


def test_a_table_that_is_not_strict_is_named() -> None:
    schema = a_schema()
    Table("strict_one", schema, Column("id", Integer, primary_key=True), sqlite_strict=True)
    Table("loose_one", schema, Column("id", Integer, primary_key=True))

    assert broken_rules(schema) == ["The table loose_one is not strict."]


@pytest.mark.parametrize(
    "by_hand",
    [
        PrimaryKeyConstraint("id", name="mine"),
        UniqueConstraint("number", name="mine"),
        ForeignKeyConstraint(["number"], ["other.id"], name="mine"),
        Index("mine", "number"),
    ],
    ids=["a key", "a unique constraint", "a foreign key", "an index"],
)
def test_a_name_given_by_hand_is_named(by_hand: SchemaItem) -> None:
    schema = a_schema()
    Table("other", schema, Column("id", Integer, primary_key=True), sqlite_strict=True)
    Table(
        "named",
        schema,
        Column("id", Integer),
        Column("number", Integer),
        by_hand,
        sqlite_strict=True,
    )

    assert broken_rules(schema) == [
        "The table named has a name given by hand, mine: "
        "constraints and indexes are named by the naming rule."
    ]


def test_the_breaks_are_listed_table_by_table_and_name_by_name() -> None:
    schema = a_schema()
    Table(
        "zebra",
        schema,
        Column("id", Integer, primary_key=True),
        Column("a", Integer),
        Column("b", Integer),
        UniqueConstraint("b", name="second"),
        UniqueConstraint("a", name="first"),
        sqlite_strict=True,
    )
    Table("aardvark", schema, Column("id", Integer, primary_key=True))

    assert broken_rules(schema) == [
        "The table aardvark is not strict.",
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
            Column("id", Integer, primary_key=True),
            Column("number", Integer),
            CheckConstraint("number > 0"),
        )
