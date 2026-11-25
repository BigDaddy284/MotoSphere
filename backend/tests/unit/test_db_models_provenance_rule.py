"""Tests of the rule that every table of collected records says where its records came from.

The tables here are made for the tests, by hand and each in a schema of
its own, so the real schema never sees them. Two models of the tests'
own, subclasses of the real ``Collected``, hold the rule to what a model
of collected records really gets.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import pytest
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped
from sqlalchemy.schema import SchemaItem

from motosphere.db import times
from motosphere.db.base import NAMING, broken_rules
from motosphere.db.checks import WithItsCheck
from motosphere.db.days import CalendarDay
from motosphere.db.lists import OneOf
from motosphere.db.models import SCHEMA
from motosphere.db.models.provenance import Collected, Confidence, VerificationStatus
from motosphere.db.models.provenance_rule import NOT_COLLECTED, broken_provenance
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.texts import NotEmpty
from motosphere.db.times import UtcDateTime
from motosphere.db.web import WebAddressText

KEPT: dict[str, Any] = {"sqlite_strict": True, "sqlite_autoincrement": True}
A_MOMENT = datetime(2026, 11, 25, 9, 30, tzinfo=UTC)
THE_EIGHT = (
    "source_id, source_address, collected_at, published_on, last_verified_at, "
    "extraction_method, confidence, verification_status"
)
WITHOUT = (
    "The table {} is without {} of the eight columns every table of collected records has "
    "({}): its model must be a subclass of Collected, or the table must be on the list of "
    "the tables that hold no collected records, with the reason."
)
NOT_AS_THE_SET = (
    "The table {} does not have the column {} as every table of collected records has it: "
    "a model takes the columns from Collected and does not say them itself."
)
NO_INDEX = (
    "The table {} has no index over source_id alone: every table of collected records has "
    "one, so that the records of one source are found without reading the whole table."
)
NO_CHECK = (
    "The table {} does not refuse a record that was last seen at its source before it was "
    "collected: it must have the check that Collected gives, named by the naming rule."
)
NO_TABLE = (
    "The list of the tables that hold no collected records names {}, which is no table of "
    "the schema."
)
LISTED_WITH_THE_SET = (
    "The table {} has the eight columns of collected records and is on the list of the "
    "tables that hold none: it must come off the list."
)
THE_TWO_TIMES = "last_verified_at >= collected_at"


class Standing(StrEnum):
    """A list of the tests' own, with the texts of the levels of confidence."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Proof(Collected):
    """A model of collected records of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=NAMING)


# A record refers to its source, so the schema of the tests knows that table too.
SCHEMA.tables["source"].to_metadata(Proof.metadata)


class ProofResult(Proof):
    """A model that says nothing of its own."""

    __tablename__ = "proof_result"


class ProofVenue(Proof):
    """A model that says more of its table, and has a second index that begins with the source."""

    __tablename__ = "proof_venue"
    __table_args__ = (
        UniqueConstraint("source_id", "name"),
        CheckConstraint("length_in_metres > 0", name="length_in_metres_positive"),
        Index(None, "source_id", "last_verified_at"),
    )

    name: Mapped[NotEmpty]
    length_in_metres: Mapped[int | None]


def a_schema() -> MetaData:
    """A schema with the naming rule of the real one, and a table of sources in it."""
    schema = MetaData(naming_convention=NAMING)
    Table("source", schema, the_key(), *the_times(), **KEPT)
    return schema


def the_key() -> Column[int]:
    return Column("id", Integer, primary_key=True)


def the_times() -> list[Column[datetime]]:
    return [
        Column("created_at", UtcDateTime, nullable=False, default=times.now),
        Column("updated_at", UtcDateTime, nullable=False, default=times.now, onupdate=times.now),
    ]


def the_set(**said: Column[Any] | None) -> list[Column[Any]]:
    """The eight columns as every table of collected records has them.

    ``said`` gives a column in another way, by its name, or leaves it
    out with ``None``.
    """
    as_it_is: dict[str, Column[Any] | None] = {
        "source_id": Column("source_id", Integer, ForeignKey("source.id"), nullable=False),
        "source_address": Column("source_address", WebAddressText, nullable=False),
        "collected_at": Column("collected_at", UtcDateTime, nullable=False),
        "published_on": Column("published_on", CalendarDay),
        "last_verified_at": Column("last_verified_at", UtcDateTime, nullable=False),
        "extraction_method": Column("extraction_method", OneOf(CollectionMethod), nullable=False),
        "confidence": Column("confidence", OneOf(Confidence), nullable=False),
        "verification_status": Column(
            "verification_status", OneOf(VerificationStatus), nullable=False
        ),
    }
    assert set(said) <= set(as_it_is)
    return [column for column in (as_it_is | said).values() if column is not None]


def the_index() -> Index:
    return Index(None, "source_id")


def the_check() -> CheckConstraint:
    return CheckConstraint(THE_TWO_TIMES, name="last_verified_at_not_before_collected_at")


def records(schema: MetaData, name: str, *more: SchemaItem, **said: Column[Any] | None) -> Table:
    """A table of collected records made by hand, with what ``more`` gives it besides.

    It has no index over its source and no check of its two times unless
    ``more`` gives them. As ``Base`` does for the table of a model, it is
    given the check of every column whose type brings one.
    """
    table = Table(name, schema, the_key(), *the_set(**said), *the_times(), *more, **KEPT)
    for column in table.columns:
        if isinstance(column.type, WithItsCheck):
            table.append_constraint(column.type.check_for(column.name))
    return table


def test_the_real_schema_breaks_no_rule_of_where_records_came_from() -> None:
    assert broken_provenance(SCHEMA, NOT_COLLECTED) == []


@pytest.mark.parametrize(
    ("name", "breaks"),
    [
        (
            "collection_run",
            [
                WITHOUT.format("collection_run", 7, THE_EIGHT.removeprefix("source_id, ")),
                NO_INDEX.format("collection_run"),
            ],
        ),
        ("source", [WITHOUT.format("source", 8, THE_EIGHT)]),
        (
            "source_offer",
            [
                WITHOUT.format("source_offer", 7, THE_EIGHT.removeprefix("source_id, ")),
                NO_INDEX.format("source_offer"),
            ],
        ),
    ],
    ids=["collection_run", "source", "source_offer"],
)
def test_every_table_of_the_real_schema_is_named_as_soon_as_it_is_off_the_list(
    name: str, breaks: list[str]
) -> None:
    # What makes the test above worth something: the rule looks at the real tables.
    assert name in NOT_COLLECTED
    the_others = [other for other in NOT_COLLECTED if other != name]

    assert broken_provenance(SCHEMA, the_others) == breaks


def test_every_table_on_the_list_of_the_real_schema_has_its_reason() -> None:
    assert list(NOT_COLLECTED) == sorted(NOT_COLLECTED)
    for reason in NOT_COLLECTED.values():
        assert reason == reason.strip()
        assert len(reason.split()) >= 8
        assert reason[0].isupper()
        assert reason.endswith(".")
    assert len(set(NOT_COLLECTED.values())) == len(NOT_COLLECTED)


def test_the_tables_of_models_of_collected_records_break_none() -> None:
    assert sorted(Proof.metadata.tables) == ["proof_result", "proof_venue", "source"]

    assert broken_provenance(Proof.metadata, ["source"]) == []


def test_a_table_made_by_hand_as_the_set_says_breaks_none() -> None:
    schema = a_schema()
    records(schema, "record", the_index(), the_check())

    assert broken_provenance(schema, ["source"]) == []
    assert broken_rules(schema) == []


def test_a_table_with_none_of_the_columns_is_named() -> None:
    schema = a_schema()
    Table("track", schema, the_key(), Column("name", Text), *the_times(), **KEPT)

    assert broken_provenance(schema, ["source"]) == [WITHOUT.format("track", 8, THE_EIGHT)]


@pytest.mark.parametrize(
    ("missing", "named"),
    [
        (["confidence"], "confidence"),
        (["published_on"], "published_on"),
        (["verification_status", "source_address"], "source_address, verification_status"),
        (
            ["extraction_method", "confidence", "verification_status", "source_address"],
            "source_address, extraction_method, confidence, verification_status",
        ),
    ],
    ids=["the confidence", "the day it was published", "two of them", "four of them"],
)
def test_a_table_without_some_of_the_columns_is_named_once_with_them_in_the_order_of_the_set(
    missing: list[str], named: str
) -> None:
    schema = a_schema()
    records(schema, "record", the_index(), the_check(), **dict.fromkeys(missing))

    assert broken_provenance(schema, ["source"]) == [WITHOUT.format("record", len(missing), named)]


@pytest.mark.parametrize(
    "column",
    [
        Column("source_id", BigInteger, ForeignKey("source.id"), nullable=False),
        Column("source_id", Text, ForeignKey("source.id"), nullable=False),
        Column("source_address", Text, nullable=False),
        Column("collected_at", DateTime(timezone=True), nullable=False),
        Column("collected_at", CalendarDay, nullable=False),
        Column("published_on", UtcDateTime),
        Column("published_on", Text),
        Column("last_verified_at", Text, nullable=False),
        Column("extraction_method", Text, nullable=False),
        Column("extraction_method", OneOf(SourceCategory), nullable=False),
        Column("confidence", Text, nullable=False),
        Column("confidence", OneOf(VerificationStatus), nullable=False),
        Column("confidence", OneOf(Standing), nullable=False),
        Column("verification_status", OneOf(Confidence), nullable=False),
    ],
    ids=[
        "the source as a larger whole number",
        "the source as text",
        "the address as any text",
        "the moment it was collected as a time of another kind",
        "the moment it was collected as a day",
        "the day it was published as a time",
        "the day it was published as any text",
        "the moment it was last seen as any text",
        "how it was got as any text",
        "how it was got as a kind of source",
        "the confidence as any text",
        "the confidence as a status",
        "the confidence of a list with the same texts",
        "the status as a level of confidence",
    ],
)
def test_a_column_of_another_type_or_of_another_list_is_named(column: Column[Any]) -> None:
    schema = a_schema()
    records(schema, "record", the_index(), the_check(), **{column.name: column})

    assert broken_provenance(schema, ["source"]) == [NOT_AS_THE_SET.format("record", column.name)]


@pytest.mark.parametrize(
    "column",
    [
        Column("source_id", Integer, ForeignKey("source.id")),
        Column("source_address", WebAddressText),
        Column("collected_at", UtcDateTime),
        Column("published_on", CalendarDay, nullable=False),
        Column("last_verified_at", UtcDateTime),
        Column("extraction_method", OneOf(CollectionMethod)),
        Column("confidence", OneOf(Confidence)),
        Column("verification_status", OneOf(VerificationStatus)),
    ],
    ids=lambda column: column.name,
)
def test_a_column_that_may_be_without_a_value_where_the_set_says_otherwise_is_named(
    column: Column[Any],
) -> None:
    schema = a_schema()
    records(schema, "record", the_index(), the_check(), **{column.name: column})

    assert broken_provenance(schema, ["source"]) == [NOT_AS_THE_SET.format("record", column.name)]


@pytest.mark.parametrize(
    "column",
    [
        Column("collected_at", UtcDateTime, nullable=False, default=times.now),
        Column("collected_at", UtcDateTime, nullable=False, default=A_MOMENT),
        Column("last_verified_at", UtcDateTime, nullable=False, onupdate=times.now),
        Column("last_verified_at", UtcDateTime, nullable=False, server_onupdate=text("''")),
        Column("confidence", OneOf(Confidence), nullable=False, default=Confidence.LOW),
        Column("confidence", OneOf(Confidence), nullable=False, server_default="low"),
        Column("published_on", CalendarDay, server_default=text("(date('now'))")),
        Column("source_id", Integer, ForeignKey("source.id"), nullable=False, default=1),
    ],
    ids=[
        "the moment it was collected from the clock",
        "the moment it was collected as one fixed moment",
        "the moment it was last seen from the clock at every change",
        "the moment it was last seen from the table at every change",
        "low confidence from the code",
        "low confidence from the table",
        "the day it was published as today",
        "the first source",
    ],
)
def test_a_column_that_is_given_a_value_nobody_said_is_named(column: Column[Any]) -> None:
    schema = a_schema()
    records(schema, "record", the_index(), the_check(), **{column.name: column})

    assert broken_provenance(schema, ["source"]) == [NOT_AS_THE_SET.format("record", column.name)]


@pytest.mark.parametrize(
    "column",
    [
        Column("source_id", Integer, nullable=False),
        Column("source_id", Integer, ForeignKey("source.created_at"), nullable=False),
        Column("source_id", Integer, ForeignKey("record.id"), nullable=False),
        Column("source_id", Integer, ForeignKey("source.id", ondelete="CASCADE"), nullable=False),
        Column("source_id", Integer, ForeignKey("source.id", ondelete="SET NULL"), nullable=False),
        Column("source_id", Integer, ForeignKey("source.id", onupdate="CASCADE"), nullable=False),
        Column(
            "source_id",
            Integer,
            ForeignKey("source.id"),
            ForeignKey("record.id"),
            nullable=False,
        ),
        Column("source_address", WebAddressText, ForeignKey("source.id"), nullable=False),
        Column("published_on", CalendarDay, ForeignKey("record.id")),
    ],
    ids=[
        "the source refers to nothing",
        "the source refers to another column of the sources",
        "the source refers to another table",
        "the records go with their source",
        "the source is forgotten when it goes",
        "the source follows a change of its key",
        "the source refers to two tables",
        "the address refers to the sources",
        "the day it was published refers to a table",
    ],
)
def test_a_column_that_does_not_refer_as_the_set_says_is_named(column: Column[Any]) -> None:
    schema = a_schema()
    records(schema, "record", the_index(), the_check(), **{column.name: column})

    assert broken_provenance(schema, ["source"]) == [NOT_AS_THE_SET.format("record", column.name)]


@pytest.mark.parametrize(
    "indexes",
    [
        [],
        [Index(None, "source_id", "last_verified_at")],
        [Index(None, "last_verified_at", "source_id")],
        [Index(None, "source_address")],
        [Index(None, "source_id", unique=True)],
        [Index(None, "source_id", sqlite_where=text("source_id > 1"))],
        [
            Index(None, "source_id", "collected_at"),
            Index(None, "source_id", unique=True),
            Index(None, "source_address"),
        ],
    ],
    ids=[
        "no index",
        "over the source and a time",
        "over a time and the source",
        "over the address",
        "one record for a source",
        "over some of the rows",
        "three that are not it",
    ],
)
def test_a_table_without_the_index_over_the_source_alone_is_named(indexes: list[Index]) -> None:
    schema = a_schema()
    records(schema, "record", the_check(), *indexes)

    assert broken_provenance(schema, ["source"]) == [NO_INDEX.format("record")]


def test_the_index_over_the_source_counts_among_others_and_whatever_it_is_called() -> None:
    schema = a_schema()
    records(
        schema,
        "record",
        the_check(),
        Index(None, "source_id", "last_verified_at"),
        Index("by_source", "source_id"),
        Index(None, "source_address"),
    )

    # That an index has a name given by hand is for the rules every table keeps to say.
    assert broken_provenance(schema, ["source"]) == []
    assert broken_rules(schema) == [
        "The table record has a name given by hand, by_source: "
        "constraints and indexes are named by the naming rule."
    ]


@pytest.mark.parametrize(
    "checks",
    [
        [],
        [CheckConstraint(THE_TWO_TIMES, name="the_two_times")],
        [CheckConstraint(THE_TWO_TIMES, name="last_verified_at_not_before_collected_at_")],
        [CheckConstraint(THE_TWO_TIMES, name="its_last_verified_at_not_before_collected_at")],
        [
            CheckConstraint(
                "last_verified_at > collected_at", name="last_verified_at_not_before_collected_at"
            )
        ],
        [
            CheckConstraint(
                "collected_at >= last_verified_at", name="last_verified_at_not_before_collected_at"
            )
        ],
        [
            CheckConstraint(
                "date(last_verified_at) >= date(collected_at)",
                name="last_verified_at_not_before_collected_at",
            )
        ],
        [
            CheckConstraint("last_verified_at > collected_at", name="later"),
            CheckConstraint("collected_at != ''", name="collected_at_not_empty"),
        ],
    ],
    ids=[
        "no check",
        "of another name",
        "of a longer name",
        "of a name that only ends as it should",
        "that asks for a later moment",
        "the other way round",
        "that compares days",
        "two that are not it",
    ],
)
def test_a_table_without_the_check_of_its_two_times_is_named(
    checks: list[CheckConstraint],
) -> None:
    schema = a_schema()
    records(schema, "record", the_index(), *checks)

    assert broken_provenance(schema, ["source"]) == [NO_CHECK.format("record")]


def test_the_check_of_another_table_does_not_count() -> None:
    schema = a_schema()
    records(schema, "record", the_index(), the_check())
    records(schema, "result", the_index())

    assert broken_provenance(schema, ["source"]) == [NO_CHECK.format("result")]


def test_what_cannot_be_there_without_a_missing_column_is_not_asked_for() -> None:
    schema = a_schema()
    # Without its source a table has no index over it, and without one of
    # its two times it has no check of them: the missing column says it all.
    records(schema, "record", the_check(), source_id=None)
    records(schema, "result", the_index(), collected_at=None)
    records(schema, "track", the_index(), last_verified_at=None)

    assert broken_provenance(schema, ["source"]) == [
        WITHOUT.format("record", 1, "source_id"),
        WITHOUT.format("result", 1, "collected_at"),
        WITHOUT.format("track", 1, "last_verified_at"),
    ]


def test_a_table_on_the_list_is_not_looked_at() -> None:
    schema = a_schema()
    Table("country", schema, the_key(), Column("name", Text), *the_times(), **KEPT)
    records(
        schema,
        "run",
        confidence=Column("confidence", Text),
        source_id=Column("source_id", Integer),
        published_on=None,
    )

    assert broken_provenance(schema, ["country", "run", "source"]) == []
    assert broken_provenance(schema, ["source"]) == [
        WITHOUT.format("country", 8, THE_EIGHT),
        WITHOUT.format("run", 1, "published_on"),
        NOT_AS_THE_SET.format("run", "source_id"),
        NOT_AS_THE_SET.format("run", "confidence"),
        NO_INDEX.format("run"),
        NO_CHECK.format("run"),
    ]


def test_a_name_on_the_list_that_is_no_table_is_named() -> None:
    schema = a_schema()
    records(schema, "record", the_index(), the_check())

    assert broken_provenance(schema, ["source", "team", "country", "team"]) == [
        NO_TABLE.format("country"),
        NO_TABLE.format("team"),
    ]


def test_a_table_on_the_list_that_has_the_whole_set_is_named() -> None:
    schema = a_schema()
    # However it has the set: what counts is that it holds collected records.
    records(schema, "record", confidence=Column("confidence", Text))
    records(schema, "result", the_index(), the_check())
    records(schema, "run", published_on=None)

    assert broken_provenance(schema, ["record", "result", "run", "source"]) == [
        LISTED_WITH_THE_SET.format("record"),
        LISTED_WITH_THE_SET.format("result"),
    ]


def test_the_breaks_are_listed_the_list_first_then_table_by_table_and_rule_by_rule() -> None:
    schema = a_schema()
    records(
        schema,
        "venue",
        verification_status=Column("verification_status", Text, nullable=False),
        source_address=Column("source_address", WebAddressText),
        extraction_method=None,
    )
    Table("rider", schema, the_key(), *the_times(), **KEPT)
    records(schema, "event", the_index(), the_check())
    records(schema, "result", the_check(), confidence=None, source_id=None)
    records(schema, "country", the_index(), the_check())

    assert broken_provenance(schema, ["source", "zone", "country", "area"]) == [
        NO_TABLE.format("area"),
        NO_TABLE.format("zone"),
        LISTED_WITH_THE_SET.format("country"),
        WITHOUT.format("result", 2, "source_id, confidence"),
        WITHOUT.format("rider", 8, THE_EIGHT),
        WITHOUT.format("venue", 1, "extraction_method"),
        NOT_AS_THE_SET.format("venue", "source_address"),
        NOT_AS_THE_SET.format("venue", "verification_status"),
        NO_INDEX.format("venue"),
        NO_CHECK.format("venue"),
    ]


def test_a_schema_with_no_tables_breaks_none_and_the_list_is_not_changed() -> None:
    listed = ["source"]

    assert broken_provenance(MetaData(), []) == []
    assert broken_provenance(MetaData(), listed) == [NO_TABLE.format("source")]
    assert listed == ["source"]
