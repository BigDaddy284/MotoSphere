"""Tests of the model of the regions. They need no store."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.dialects import sqlite

from motosphere.db import models
from motosphere.db.base import broken_rules
from motosphere.db.models import SCHEMA, Region
from motosphere.db.models.provenance import Collected
from motosphere.db.models.provenance_rule import NOT_COLLECTED, broken_provenance

# The table as the whole schema has it.
TABLE = SCHEMA.tables["region"]


def as_sqlite_is_given_it(check: CheckConstraint) -> str:
    written = check.sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True, "include_table": False}
    )
    return str(written)


def test_the_regions_are_a_table_of_the_schema_and_a_model_by_name() -> None:
    assert Region.__tablename__ == "region"
    assert Region.__table__ is TABLE
    assert "Region" in models.__all__


def test_a_region_is_a_collected_record() -> None:
    assert issubclass(Region, Collected)
    assert "region" not in NOT_COLLECTED


def test_the_table_has_these_columns_in_this_order() -> None:
    assert [column.name for column in TABLE.columns] == [
        "id",
        "country_id",
        "parent_id",
        "name",
        "iso_3166_2",
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


def test_only_the_parent_the_code_and_the_day_it_was_published_may_be_without_a_value() -> None:
    assert [column.name for column in TABLE.columns if column.nullable] == [
        "parent_id",
        "iso_3166_2",
        "published_on",
    ]


def test_no_column_but_the_times_gives_itself_a_value() -> None:
    given = [
        column.name
        for column in TABLE.columns
        if column.default is not None or column.server_default is not None
    ]

    assert given == ["created_at", "updated_at"]


def test_a_region_points_to_its_country_to_its_source_and_to_the_region_it_is_a_part_of() -> None:
    points = {
        str(key.name): (
            [column.name for column in key.columns],
            [element.target_fullname for element in key.elements],
            key.ondelete,
            key.onupdate,
        )
        for key in TABLE.constraints
        if isinstance(key, ForeignKeyConstraint)
    }

    # Nothing is said of what happens when a country, a source or a
    # region is deleted or its key changed, so SQLite refuses both while
    # a region points there. To the region it is a part of a region
    # points with two columns, so that region is of its own country.
    assert points == {
        "fk_region_country_id_country": (["country_id"], ["country.id"], None, None),
        "fk_region_parent_id_country_id_region": (
            ["parent_id", "country_id"],
            ["region.id", "region.country_id"],
            None,
            None,
        ),
        "fk_region_source_id_source": (["source_id"], ["source.id"], None, None),
    }


def test_no_two_regions_without_a_code_have_one_name_in_a_country_and_no_two_one_code() -> None:
    rules = sorted(
        (str(unique.name), [column.name for column in unique.columns])
        for unique in TABLE.constraints
        if isinstance(unique, UniqueConstraint)
    )
    of_some_rows = [
        (
            str(index.name),
            [column.name for column in index.columns],
            str(index.dialect_options["sqlite"]["where"]),
        )
        for index in TABLE.indexes
        if index.unique
    ]

    # The rule of the codes is written into the table. The rule of the
    # names is an index, because it is over some regions only: those
    # that say no code. The other rule in the table, a key and a country
    # together once, is there for the region a region is a part of.
    assert rules == [
        ("uq_region_id_country_id", ["id", "country_id"]),
        ("uq_region_iso_3166_2", ["iso_3166_2"]),
    ]
    assert of_some_rows == [
        ("ix_region_country_id_name", ["country_id", "name"], "iso_3166_2 IS NULL")
    ]


def test_the_country_of_a_region_has_an_index_of_its_own() -> None:
    country = TABLE.columns["country_id"]
    over_every_region = [
        (str(index.name), [column.name for column in index.columns])
        for index in TABLE.indexes
        if index.dialect_options["sqlite"]["where"] is None
    ]

    # The index of the rule of the names begins with the country too, but
    # it is over the regions without a code only and finds no others.
    assert country.index is True
    assert sorted(over_every_region) == [
        ("ix_region_country_id", ["country_id"]),
        ("ix_region_parent_id", ["parent_id"]),
        ("ix_region_source_id", ["source_id"]),
    ]


def test_what_a_region_is_a_part_of_is_a_whole_number_that_points_to_a_region() -> None:
    parent = TABLE.columns["parent_id"]
    country = TABLE.columns["country_id"]

    assert type(parent.type) is Integer
    assert parent.nullable is True
    assert parent.primary_key is False
    assert parent.unique is None
    assert parent.index is True
    # It points to the key of a region, and the country beside it to the
    # country of that region: the one rule that names both.
    assert {key.target_fullname for key in parent.foreign_keys} == {"region.id"}
    assert {key.target_fullname for key in country.foreign_keys} == {
        "country.id",
        "region.country_id",
    }
    assert {str(key.constraint.name) for key in parent.foreign_keys if key.constraint} == {
        "fk_region_parent_id_country_id_region"
    }


def test_the_check_of_what_a_region_is_a_part_of_says_this() -> None:
    checks = {
        str(check.name): as_sqlite_is_given_it(check)
        for check in TABLE.constraints
        if isinstance(check, CheckConstraint) and "parent_id" in str(check.name)
    }

    assert checks == {"ck_region_parent_id_not_itself": "parent_id != id"}


def test_a_region_is_made_as_a_part_of_no_region_and_as_a_part_of_one() -> None:
    of_none = Region(country_id=1, name="Grand-Est")
    of_one = Region(country_id=1, name="Alsace", parent_id=7)

    assert of_none.parent_id is None
    assert of_one.parent_id == 7


def test_the_code_is_plain_text_that_points_nowhere() -> None:
    code = TABLE.columns["iso_3166_2"]

    assert type(code.type) is Text
    assert code.foreign_keys == set()
    assert code.primary_key is False
    # The rule that no two regions have one code brings its own index,
    # and the model asks for no second one.
    assert code.unique is True
    assert code.index is None


def test_the_check_of_the_code_says_this() -> None:
    checks = {
        str(check.name): as_sqlite_is_given_it(check)
        for check in TABLE.constraints
        if isinstance(check, CheckConstraint) and "iso_3166_2" in str(check.name)
    }

    assert checks == {
        "ck_region_iso_3166_2_form": (
            "((iso_3166_2 GLOB '[A-Z][A-Z]-[A-Z0-9]') "
            "OR (iso_3166_2 GLOB '[A-Z][A-Z]-[A-Z0-9][A-Z0-9]') "
            "OR (iso_3166_2 GLOB '[A-Z][A-Z]-[A-Z0-9][A-Z0-9][A-Z0-9]')) "
            "AND instr(iso_3166_2, char(0)) = 0"
        )
    }


def test_a_region_is_made_without_a_code_and_with_one() -> None:
    without = Region(country_id=1, name="Canterbury")
    with_one = Region(country_id=1, name="Canterbury", iso_3166_2="NZ-CAN")

    assert without.iso_3166_2 is None
    assert with_one.iso_3166_2 == "NZ-CAN"


def test_the_table_has_these_constraints_and_these_indexes() -> None:
    by_kind = {
        kind: sorted(str(one.name) for one in TABLE.constraints if isinstance(one, kind))
        for kind in (CheckConstraint, UniqueConstraint, ForeignKeyConstraint)
    }

    assert by_kind == {
        CheckConstraint: [
            "ck_region_confidence_one_of",
            "ck_region_extraction_method_one_of",
            "ck_region_iso_3166_2_form",
            "ck_region_last_verified_at_not_before_collected_at",
            "ck_region_name_not_empty",
            "ck_region_parent_id_not_itself",
            "ck_region_published_on_calendar_day",
            "ck_region_source_address_web_address",
            "ck_region_verification_status_one_of",
        ],
        UniqueConstraint: ["uq_region_id_country_id", "uq_region_iso_3166_2"],
        ForeignKeyConstraint: [
            "fk_region_country_id_country",
            "fk_region_parent_id_country_id_region",
            "fk_region_source_id_source",
        ],
    }
    assert sorted(
        (str(index.name), [column.name for column in index.columns]) for index in TABLE.indexes
    ) == [
        ("ix_region_country_id", ["country_id"]),
        ("ix_region_country_id_name", ["country_id", "name"]),
        ("ix_region_parent_id", ["parent_id"]),
        ("ix_region_source_id", ["source_id"]),
    ]


def test_the_schema_with_the_regions_keeps_every_rule() -> None:
    assert broken_rules(SCHEMA) == []
    assert broken_provenance(SCHEMA, NOT_COLLECTED) == []
