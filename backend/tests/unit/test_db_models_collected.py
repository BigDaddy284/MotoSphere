"""Tests of the columns every collected record has, without a store.

The models here are made for the tests. They are subclasses of the real
``Collected``, so they prove what a model of collected records gets, but
they are kept in a schema of their own (``Proof.metadata``), so the real
schema never sees them. ``tests/integration/test_collected.py`` asks a
real SQLite file what it refuses.
"""

from enum import StrEnum
from typing import Any

import pytest
from sqlalchemy import CheckConstraint, Integer, MetaData, Table, UniqueConstraint
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import Mapped
from sqlalchemy.schema import conv
from sqlalchemy.types import TypeEngine

from motosphere.db.base import NAMING, Base, broken_rules
from motosphere.db.days import CalendarDay
from motosphere.db.lists import OneOf
from motosphere.db.models import SCHEMA
from motosphere.db.models.provenance import Collected, Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod
from motosphere.db.texts import NotEmpty
from motosphere.db.times import UtcDateTime
from motosphere.db.web import WebAddressText

# The columns every collected record has, in their order: the type of
# each, the list it is of where it is of one, and whether it may be
# without a value.
THE_SET: dict[str, tuple[type[TypeEngine[Any]], type[StrEnum] | None, bool]] = {
    "source_id": (Integer, None, False),
    "source_address": (WebAddressText, None, False),
    "collected_at": (UtcDateTime, None, False),
    "published_on": (CalendarDay, None, True),
    "last_verified_at": (UtcDateTime, None, False),
    "extraction_method": (OneOf, CollectionMethod, False),
    "confidence": (OneOf, Confidence, False),
    "verification_status": (OneOf, VerificationStatus, False),
}
EACH_COLUMN = pytest.mark.parametrize("name", list(THE_SET))
THE_TWO_TIMES = "last_verified_at >= collected_at"


class Proof(Collected):
    """A model of collected records of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=NAMING)


# A record refers to its source, so the schema of the tests knows that table too.
SCHEMA.tables["source"].to_metadata(Proof.metadata)


class ProofRecord(Proof):
    """A model that says nothing of its own: its table is the key, the set and the two times."""

    __tablename__ = "proof_record"


class ProofTrack(Proof):
    """A model that says more of its table: columns, a rule of its own and a check."""

    __tablename__ = "proof_track"
    __table_args__ = (
        UniqueConstraint("name"),
        CheckConstraint("length_in_metres > 0", name="length_in_metres_positive"),
    )

    name: Mapped[NotEmpty]
    length_in_metres: Mapped[int | None]


def table_of(model: type[Proof]) -> Table:
    """The table of a model of the tests."""
    return Proof.metadata.tables[model.__tablename__]


def checks_of(model: type[Proof]) -> dict[str, str]:
    """The checks of a model's table: the name of each and its text as SQLite is given it."""
    return {
        str(check.name): str(
            check.sqltext.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
        )
        for check in table_of(model).constraints
        if isinstance(check, CheckConstraint)
    }


def test_the_table_of_a_model_that_says_nothing_else_is_the_key_the_set_and_the_two_times() -> None:
    assert [column.name for column in table_of(ProofRecord).columns] == [
        "id",
        "source_id",
        "source_address",
        "collected_at",
        "published_on",
        "last_verified_at",
        "extraction_method",
        "confidence",
        "verification_status",
        "created_at",
        "updated_at",
    ]


def test_the_set_comes_after_the_columns_a_model_names_and_before_the_two_times() -> None:
    assert [column.name for column in table_of(ProofTrack).columns] == [
        "id",
        "name",
        "length_in_metres",
        *THE_SET,
        "created_at",
        "updated_at",
    ]


@EACH_COLUMN
def test_each_column_of_the_set_is_of_its_type_and_of_its_list(name: str) -> None:
    its_type, its_list, _ = THE_SET[name]

    for model in (ProofRecord, ProofTrack):
        column = table_of(model).columns[name]

        assert type(column.type) is its_type
        assert getattr(column.type, "the_list", None) is its_list


@EACH_COLUMN
def test_only_the_day_a_record_was_published_may_be_without_a_value(name: str) -> None:
    _, _, may_be_without = THE_SET[name]

    assert may_be_without is (name == "published_on")
    for model in (ProofRecord, ProofTrack):
        assert table_of(model).columns[name].nullable is may_be_without


@EACH_COLUMN
def test_no_column_of_the_set_gives_itself_a_value(name: str) -> None:
    for model in (ProofRecord, ProofTrack):
        column = table_of(model).columns[name]

        assert column.default is None
        assert column.server_default is None
        assert column.onupdate is None
        assert column.server_onupdate is None


@EACH_COLUMN
def test_no_column_of_the_set_is_the_key_or_must_be_the_only_one_of_its_value(name: str) -> None:
    for model in (ProofRecord, ProofTrack):
        column = table_of(model).columns[name]

        assert not column.primary_key
        assert not column.unique
        assert not column.index


def test_a_record_refers_to_its_source_and_the_rule_names_the_reference() -> None:
    for model, name in (
        (ProofRecord, "fk_proof_record_source_id_source"),
        (ProofTrack, "fk_proof_track_source_id_source"),
    ):
        table = table_of(model)
        (reference,) = table.foreign_key_constraints

        assert [column.name for column in reference.columns] == ["source_id"]
        assert [element.target_fullname for element in reference.elements] == ["source.id"]
        assert reference.name == name
        assert isinstance(reference.name, conv)
        # Nothing is said of what happens to the records when their source is
        # deleted or its key changes, and so SQLite refuses both.
        assert reference.ondelete is None
        assert reference.onupdate is None
        assert [
            other.name
            for other in table.columns
            if other.foreign_keys and other.name != "source_id"
        ] == []


def test_the_table_has_the_check_that_holds_its_two_times_together() -> None:
    assert checks_of(ProofRecord)["ck_proof_record_last_verified_at_not_before_collected_at"] == (
        THE_TWO_TIMES
    )


def test_the_table_has_the_check_of_every_column_of_the_set_whose_type_brings_one() -> None:
    assert sorted(checks_of(ProofRecord)) == [
        "ck_proof_record_confidence_one_of",
        "ck_proof_record_extraction_method_one_of",
        "ck_proof_record_last_verified_at_not_before_collected_at",
        "ck_proof_record_published_on_calendar_day",
        "ck_proof_record_source_address_web_address",
        "ck_proof_record_verification_status_one_of",
    ]


def test_the_checks_of_the_lists_name_their_texts_in_their_order() -> None:
    checks = checks_of(ProofRecord)

    assert checks["ck_proof_record_extraction_method_one_of"] == (
        "extraction_method IN ('official api', 'structured feed', 'rss feed', "
        "'public dataset', 'html extraction', 'structured document', 'json endpoint', "
        "'sitemap discovery', 'search engine discovery', 'human submission')"
    )
    assert checks["ck_proof_record_confidence_one_of"] == (
        "confidence IN ('high', 'medium', 'low')"
    )
    assert checks["ck_proof_record_verification_status_one_of"] == (
        "verification_status IN ('official', 'independent', 'reconstructed', 'unverified')"
    )


def test_a_model_that_says_more_of_its_table_keeps_what_it_said_and_the_checks_of_the_set() -> None:
    table = table_of(ProofTrack)
    checks = checks_of(ProofTrack)

    assert sorted(checks) == [
        "ck_proof_track_confidence_one_of",
        "ck_proof_track_extraction_method_one_of",
        "ck_proof_track_last_verified_at_not_before_collected_at",
        "ck_proof_track_length_in_metres_positive",
        "ck_proof_track_name_not_empty",
        "ck_proof_track_published_on_calendar_day",
        "ck_proof_track_source_address_web_address",
        "ck_proof_track_verification_status_one_of",
    ]
    assert checks["ck_proof_track_length_in_metres_positive"] == "length_in_metres > 0"
    assert checks["ck_proof_track_last_verified_at_not_before_collected_at"] == THE_TWO_TIMES
    assert [
        ([column.name for column in rule.columns], rule.name)
        for rule in table.constraints
        if isinstance(rule, UniqueConstraint)
    ] == [(["name"], "uq_proof_track_name")]


def test_every_table_has_a_check_of_its_own_for_its_two_times() -> None:
    of_the_times = [
        check
        for model in (ProofRecord, ProofTrack)
        for check in table_of(model).constraints
        if isinstance(check, CheckConstraint)
        and str(check.name).endswith("_last_verified_at_not_before_collected_at")
    ]

    assert [check.table.name for check in of_the_times] == ["proof_record", "proof_track"]
    assert of_the_times[0] is not of_the_times[1]
    assert all(isinstance(check.name, conv) for check in of_the_times)


def test_the_tables_of_models_of_collected_records_break_no_rule() -> None:
    assert sorted(Proof.metadata.tables) == ["proof_record", "proof_track", "source"]
    assert broken_rules(Proof.metadata) == []


def test_the_set_itself_is_no_table_and_the_real_schema_has_none_of_the_tests() -> None:
    assert Collected.__abstract__ is True
    assert "__table__" not in Collected.__dict__
    assert "__table__" not in Proof.__dict__
    assert issubclass(Collected, Base)
    assert not {"proof_record", "proof_track"} & set(SCHEMA.tables)
    # The source the tests' schema knows is a copy: the real one is where it was.
    assert Proof.metadata.tables["source"] is not SCHEMA.tables["source"]
    assert SCHEMA.tables["source"].metadata is SCHEMA
