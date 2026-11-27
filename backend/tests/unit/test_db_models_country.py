"""Tests of the model of the countries. They need no store."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects import sqlite

from motosphere.db import models
from motosphere.db.base import broken_rules
from motosphere.db.models import SCHEMA, Country
from motosphere.db.models.provenance import Collected
from motosphere.db.models.provenance_rule import NOT_COLLECTED, broken_provenance

# The table as the whole schema has it.
TABLE = SCHEMA.tables["country"]


def as_sqlite_is_given_it(check: CheckConstraint) -> str:
    written = check.sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True, "include_table": False}
    )
    return str(written)


def test_the_countries_are_a_table_of_the_schema_and_a_model_by_name() -> None:
    assert Country.__tablename__ == "country"
    assert Country.__table__ is TABLE
    assert "Country" in models.__all__


def test_a_country_is_a_collected_record() -> None:
    assert issubclass(Country, Collected)
    assert "country" not in NOT_COLLECTED


def test_the_table_has_these_columns_in_this_order() -> None:
    assert [column.name for column in TABLE.columns] == [
        "id",
        "alpha_2",
        "alpha_3",
        "name",
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


def test_only_the_day_it_was_published_may_be_without_a_value() -> None:
    assert [column.name for column in TABLE.columns if column.nullable] == ["published_on"]


def test_no_column_but_the_times_gives_itself_a_value() -> None:
    given = [
        column.name
        for column in TABLE.columns
        if column.default is not None or column.server_default is not None
    ]

    assert given == ["created_at", "updated_at"]


def test_the_checks_of_the_two_codes_say_this() -> None:
    checks = {
        str(check.name): as_sqlite_is_given_it(check)
        for check in TABLE.constraints
        if isinstance(check, CheckConstraint) and "capitals" in str(check.name)
    }

    assert checks == {
        "ck_country_alpha_2_two_capitals": (
            "(alpha_2 GLOB '[A-Z][A-Z]') AND instr(alpha_2, char(0)) = 0"
        ),
        "ck_country_alpha_3_three_capitals": (
            "(alpha_3 GLOB '[A-Z][A-Z][A-Z]') AND instr(alpha_3, char(0)) = 0"
        ),
    }


def test_the_table_has_these_constraints_and_this_index() -> None:
    by_kind = {
        kind: sorted(str(one.name) for one in TABLE.constraints if isinstance(one, kind))
        for kind in (CheckConstraint, UniqueConstraint, ForeignKeyConstraint)
    }

    assert by_kind == {
        CheckConstraint: [
            "ck_country_alpha_2_two_capitals",
            "ck_country_alpha_3_three_capitals",
            "ck_country_confidence_one_of",
            "ck_country_extraction_method_one_of",
            "ck_country_last_verified_at_not_before_collected_at",
            "ck_country_name_not_empty",
            "ck_country_published_on_calendar_day",
            "ck_country_source_address_web_address",
            "ck_country_verification_status_one_of",
        ],
        UniqueConstraint: ["uq_country_alpha_2", "uq_country_alpha_3"],
        ForeignKeyConstraint: ["fk_country_source_id_source"],
    }
    assert [
        (str(index.name), [column.name for column in index.columns]) for index in TABLE.indexes
    ] == [("ix_country_source_id", ["source_id"])]
    for unique in (one for one in TABLE.constraints if isinstance(one, UniqueConstraint)):
        assert len(unique.columns) == 1


def test_the_schema_with_the_countries_keeps_every_rule() -> None:
    assert broken_rules(SCHEMA) == []
    assert broken_provenance(SCHEMA, NOT_COLLECTED) == []
