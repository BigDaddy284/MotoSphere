"""Tests of the names of the parts of a region, against a real SQLite file.

A region can be a part of another, and there are counties of one name in
many states. Among the regions that say no code, a name is there once
among the parts of one region, and once among the regions of a country
that are parts of none. Two regions that are parts of different regions
can have one name, and so can a region and a part of it.

The store of every test is built the way a real store is built: by the
migrations. What must be refused is written through the model and past
it, and each refusal is held to the sentence SQLite gives.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Engine, delete
from sqlalchemy.exc import IntegrityError, OperationalError

from motosphere.db.changes import change
from motosphere.db.models import Country, Region, Source
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 28, 9, 0, tzinfo=UTC)
# The three countries of the tests, by their keys.
UNITED_STATES = 1
CANADA = 2
FRANCE = 3
COUNTRIES = [("US", "USA", "United States"), ("CA", "CAN", "Canada"), ("FR", "FRA", "France")]
# The regions the store of most tests begins with, by their keys: two
# states of the United States, a province of Canada, and two regions of
# France, the second a part of the first. Each says its code of ISO 3166-2.
OHIO = 1
PENNSYLVANIA = 2
ONTARIO = 3
GRAND_EST = 4
ALSACE = 5
AT_FIRST = [
    (OHIO, UNITED_STATES, None, "Ohio", "US-OH"),
    (PENNSYLVANIA, UNITED_STATES, None, "Pennsylvania", "US-PA"),
    (ONTARIO, CANADA, None, "Ontario", "CA-ON"),
    (GRAND_EST, FRANCE, None, "Grand-Est", "FR-GES"),
    (ALSACE, FRANCE, GRAND_EST, "Alsace", "FR-6AE"),
]
# A county of this name is in Ohio and in Pennsylvania, and in many more
# states. The standard gives no county of the United States a code.
A_COUNTY = "Washington County"
TWICE_IN_A_REGION = "UNIQUE constraint failed: region.parent_id, region.name"
TWICE_IN_A_COUNTRY = "UNIQUE constraint failed: region.country_id, region.name"
# A region as plain SQL: its country, the region it is a part of, its
# name and its code are given.
NEW = (
    "INSERT INTO region (country_id, parent_id, name, iso_3166_2, source_id, source_address, "
    "collected_at, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) VALUES (?, ?, ?, ?, 1, 'https://standards.example/regions.csv', "
    "'2026-11-28T09:00:00.000000+00:00', '2026-11-28T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-28T09:00:05.000000+00:00', '2026-11-28T09:00:05.000000+00:00')"
)


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def a_region(country: int, name: str, code: str | None, part_of: int | None) -> Region:
    """A region as the one source of the tests says it: its name, its code, what it is a part of."""
    described: dict[str, Any] = {
        "country_id": country,
        "parent_id": part_of,
        "name": name,
        "iso_3166_2": code,
        "source_id": 1,
        "source_address": "https://standards.example/regions.csv",
        "collected_at": COLLECTED,
        "last_verified_at": COLLECTED,
        "extraction_method": CollectionMethod.DATASET,
        "confidence": Confidence.HIGH,
        "verification_status": VerificationStatus.OFFICIAL,
    }
    return Region(**described)


def keep(
    store: Engine, country: int, name: str, code: str | None = None, part_of: int | None = None
) -> int:
    """Store a region through the model in a unit of work of its own, and give its key."""
    region = a_region(country, name, code, part_of)
    with unit_of_work(store) as work:
        work.add(region)
    return region.id


def write(store: Engine, statement: str, *given: object) -> None:
    """Write one statement past the model, as plain SQL, in a transaction of its own."""
    with store.begin() as connection:
        connection.exec_driver_sql(statement, given)


def regions(store: Engine) -> list[tuple[object, ...]]:
    """The key, the country, the region it is a part of, the name and the code of every region."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT id, country_id, parent_id, name, iso_3166_2 FROM region ORDER BY id"
        )
        return [tuple(row) for row in found]


def history(store: Engine) -> list[tuple[object, ...]]:
    """What the store has noted of the changes to its records."""
    with store.connect() as connection:
        noted = connection.exec_driver_sql(
            "SELECT record_table, record_id, field, old_value, new_value FROM record_change"
        )
        return [tuple(row) for row in noted]


def plan_of(store: Engine, statement: str) -> list[str]:
    """What SQLite says it does to answer a statement."""
    with store.connect() as connection:
        steps = connection.exec_driver_sql("EXPLAIN QUERY PLAN " + statement).all()
    return [str(detail) for *_, detail in steps]


@pytest.fixture
def mapped(newest: Engine) -> Engine:
    """The test's own store with the newest schema: one source, three countries, five regions.

    The key of the source is 1. The keys of the countries are 1 to 3:
    the United States, Canada and France. The regions are those of
    ``AT_FIRST``.
    """
    with unit_of_work(newest) as work:
        work.add(
            Source(
                name="Example Standards Body",
                website="https://standards.example",
                category=SourceCategory.GOVERNING_BODY,
                collection_method=CollectionMethod.DATASET,
            )
        )
    for two, three, name in COUNTRIES:
        with unit_of_work(newest) as work:
            work.add(
                Country(
                    alpha_2=two,
                    alpha_3=three,
                    name=name,
                    source_id=1,
                    source_address="https://standards.example/countries.csv",
                    collected_at=COLLECTED,
                    last_verified_at=COLLECTED,
                    extraction_method=CollectionMethod.DATASET,
                    confidence=Confidence.HIGH,
                    verification_status=VerificationStatus.OFFICIAL,
                )
            )
    for _, country, part_of, name, code in AT_FIRST:
        keep(newest, country, name, code, part_of)
    assert regions(newest) == AT_FIRST
    return newest


# --------------------------------------------- parts of different regions


def test_two_parts_of_different_regions_have_one_name_through_the_model(mapped: Engine) -> None:
    first = keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    second = keep(mapped, UNITED_STATES, A_COUNTY, part_of=PENNSYLVANIA)

    assert (first, second) == (6, 7)
    assert regions(mapped) == [
        *AT_FIRST,
        (6, UNITED_STATES, OHIO, A_COUNTY, None),
        (7, UNITED_STATES, PENNSYLVANIA, A_COUNTY, None),
    ]


def test_two_parts_of_different_regions_have_one_name_past_the_model(mapped: Engine) -> None:
    write(mapped, NEW, UNITED_STATES, OHIO, A_COUNTY, None)
    write(mapped, NEW, UNITED_STATES, PENNSYLVANIA, A_COUNTY, None)

    assert regions(mapped)[5:] == [
        (6, UNITED_STATES, OHIO, A_COUNTY, None),
        (7, UNITED_STATES, PENNSYLVANIA, A_COUNTY, None),
    ]


def test_a_region_and_a_part_of_it_have_one_name_without_a_code(mapped: Engine) -> None:
    # New York the state and New York the county in it, as a source names
    # them that gives no codes.
    state = keep(mapped, UNITED_STATES, "New York")
    county = keep(mapped, UNITED_STATES, "New York", part_of=state)

    assert regions(mapped)[5:] == [
        (state, UNITED_STATES, None, "New York", None),
        (county, UNITED_STATES, state, "New York", None),
    ]


def test_a_part_and_a_part_of_that_part_have_one_name_without_a_code(mapped: Engine) -> None:
    county = keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    within = keep(mapped, UNITED_STATES, A_COUNTY, part_of=county)

    assert regions(mapped)[5:] == [
        (county, UNITED_STATES, OHIO, A_COUNTY, None),
        (within, UNITED_STATES, county, A_COUNTY, None),
    ]


def test_parts_of_regions_of_two_countries_have_one_name(mapped: Engine) -> None:
    # Huron County is in Ontario, and in Ohio.
    keep(mapped, CANADA, "Huron County", part_of=ONTARIO)
    keep(mapped, UNITED_STATES, "Huron County", part_of=OHIO)

    assert [(country, part_of) for _, country, part_of, _, _ in regions(mapped)[5:]] == [
        (CANADA, ONTARIO),
        (UNITED_STATES, OHIO),
    ]


def test_a_part_is_given_the_name_of_a_part_of_another_region_with_its_history(
    mapped: Engine,
) -> None:
    keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    other = keep(mapped, UNITED_STATES, "Greene County", part_of=PENNSYLVANIA)

    with unit_of_work(mapped) as work:
        change(work, work.get_one(Region, other), {"name": A_COUNTY}, decided_by="Jo Example")

    assert regions(mapped)[6] == (other, UNITED_STATES, PENNSYLVANIA, A_COUNTY, None)
    assert history(mapped) == [("region", other, "name", "Greene County", A_COUNTY)]


# ------------------------------------------------- parts of one region


def test_two_parts_of_one_region_that_say_no_code_cannot_have_one_name_through_the_model(
    mapped: Engine,
) -> None:
    keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    before = regions(mapped)

    with refused(TWICE_IN_A_REGION):
        keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)

    assert regions(mapped) == before


def test_two_parts_of_one_region_that_say_no_code_cannot_have_one_name_past_the_model(
    mapped: Engine,
) -> None:
    write(mapped, NEW, UNITED_STATES, OHIO, A_COUNTY, None)
    before = regions(mapped)

    with refused(TWICE_IN_A_REGION):
        write(mapped, NEW, UNITED_STATES, OHIO, A_COUNTY, None)

    assert regions(mapped) == before


def test_a_part_cannot_be_given_the_name_of_another_part_of_its_region(mapped: Engine) -> None:
    keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    other = keep(mapped, UNITED_STATES, "Athens County", part_of=OHIO)
    before = regions(mapped)

    with refused(TWICE_IN_A_REGION):
        write(mapped, "UPDATE region SET name = ? WHERE id = ?", A_COUNTY, other)

    assert regions(mapped) == before


def test_a_part_cannot_be_moved_to_a_region_that_has_a_part_of_its_name(mapped: Engine) -> None:
    keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    other = keep(mapped, UNITED_STATES, A_COUNTY, part_of=PENNSYLVANIA)
    before = regions(mapped)

    with refused(TWICE_IN_A_REGION):
        write(mapped, "UPDATE region SET parent_id = ? WHERE id = ?", OHIO, other)

    assert regions(mapped) == before


def test_a_refused_name_leaves_the_part_and_no_history(mapped: Engine) -> None:
    keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    other = keep(mapped, UNITED_STATES, "Athens County", part_of=OHIO)
    before = regions(mapped)

    with refused(TWICE_IN_A_REGION), unit_of_work(mapped) as work:
        change(work, work.get_one(Region, other), {"name": A_COUNTY}, decided_by="Jo Example")

    assert regions(mapped) == before
    assert history(mapped) == []


def test_the_name_of_a_deleted_part_is_free_again_in_its_region(mapped: Engine) -> None:
    first = keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    with unit_of_work(mapped) as work:
        work.execute(delete(Region).where(Region.id == first))

    second = keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)

    assert regions(mapped)[5:] == [(second, UNITED_STATES, OHIO, A_COUNTY, None)]
    assert second == first + 1


def test_the_name_of_a_part_that_moved_away_is_free_again_in_its_region(mapped: Engine) -> None:
    first = keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    write(mapped, "UPDATE region SET parent_id = ? WHERE id = ?", PENNSYLVANIA, first)

    second = keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)

    assert regions(mapped)[5:] == [
        (first, UNITED_STATES, PENNSYLVANIA, A_COUNTY, None),
        (second, UNITED_STATES, OHIO, A_COUNTY, None),
    ]


def test_the_name_of_a_part_that_was_given_another_is_free_again_in_its_region(
    mapped: Engine,
) -> None:
    first = keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    write(mapped, "UPDATE region SET name = 'Greene County' WHERE id = ?", first)

    second = keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)

    assert regions(mapped)[5:] == [
        (first, UNITED_STATES, OHIO, "Greene County", None),
        (second, UNITED_STATES, OHIO, A_COUNTY, None),
    ]


# ------------------------------------- regions that are parts of no region


def test_two_regions_of_a_country_that_are_parts_of_none_still_cannot_have_one_name(
    mapped: Engine,
) -> None:
    keep(mapped, UNITED_STATES, "Georgia")
    before = regions(mapped)

    with refused(TWICE_IN_A_COUNTRY):
        keep(mapped, UNITED_STATES, "Georgia")
    with refused(TWICE_IN_A_COUNTRY):
        write(mapped, NEW, UNITED_STATES, None, "Georgia", None)

    assert regions(mapped) == before


def test_a_part_cannot_be_made_a_part_of_none_beside_a_region_of_its_name(mapped: Engine) -> None:
    state = keep(mapped, UNITED_STATES, "New York")
    county = keep(mapped, UNITED_STATES, "New York", part_of=state)
    before = regions(mapped)

    with refused(TWICE_IN_A_COUNTRY):
        write(mapped, "UPDATE region SET parent_id = NULL WHERE id = ?", county)

    assert regions(mapped) == before


def test_a_region_cannot_be_made_a_part_of_a_region_that_has_a_part_of_its_name(
    mapped: Engine,
) -> None:
    keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)
    alone = keep(mapped, UNITED_STATES, A_COUNTY)
    before = regions(mapped)

    with refused(TWICE_IN_A_REGION):
        write(mapped, "UPDATE region SET parent_id = ? WHERE id = ?", OHIO, alone)

    assert regions(mapped) == before


def test_a_part_is_made_a_part_of_none_where_no_region_of_the_country_has_its_name(
    mapped: Engine,
) -> None:
    county = keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)

    write(mapped, "UPDATE region SET parent_id = NULL WHERE id = ?", county)
    # And its name is free in Ohio again.
    again = keep(mapped, UNITED_STATES, A_COUNTY, part_of=OHIO)

    assert regions(mapped)[5:] == [
        (county, UNITED_STATES, None, A_COUNTY, None),
        (again, UNITED_STATES, OHIO, A_COUNTY, None),
    ]


# ------------------------------------------------- with a code and without


def test_a_part_with_a_code_and_one_without_have_one_name_in_one_region(mapped: Engine) -> None:
    # Alsace is there with its code, a part of Grand-Est. A source that
    # gives no codes names it too.
    second = keep(mapped, FRANCE, "Alsace", part_of=GRAND_EST)

    assert regions(mapped)[4:] == [
        (ALSACE, FRANCE, GRAND_EST, "Alsace", "FR-6AE"),
        (second, FRANCE, GRAND_EST, "Alsace", None),
    ]


def test_a_part_cannot_lose_its_code_beside_a_part_of_its_name_that_says_none(
    mapped: Engine,
) -> None:
    keep(mapped, FRANCE, "Alsace", part_of=GRAND_EST)
    before = regions(mapped)

    with refused(TWICE_IN_A_REGION):
        write(mapped, "UPDATE region SET iso_3166_2 = NULL WHERE id = ?", ALSACE)

    assert regions(mapped) == before


def test_a_part_can_lose_its_code_beside_one_of_its_name_in_another_region(mapped: Engine) -> None:
    keep(mapped, FRANCE, "Alsace")

    write(mapped, "UPDATE region SET iso_3166_2 = NULL WHERE id = ?", ALSACE)

    assert regions(mapped)[4:] == [
        (ALSACE, FRANCE, GRAND_EST, "Alsace", None),
        (6, FRANCE, None, "Alsace", None),
    ]


def test_a_part_that_is_given_its_code_leaves_its_name_free_for_one_without(mapped: Engine) -> None:
    # Bas-Rhin is a part of Alsace, and its code is "FR-67".
    first = keep(mapped, FRANCE, "Bas-Rhin", part_of=ALSACE)
    with refused(TWICE_IN_A_REGION):
        keep(mapped, FRANCE, "Bas-Rhin", part_of=ALSACE)

    write(mapped, "UPDATE region SET iso_3166_2 = 'FR-67' WHERE id = ?", first)
    second = keep(mapped, FRANCE, "Bas-Rhin", part_of=ALSACE)

    assert regions(mapped)[5:] == [
        (first, FRANCE, ALSACE, "Bas-Rhin", "FR-67"),
        (second, FRANCE, ALSACE, "Bas-Rhin", None),
    ]


# ------------------------------------------------- how the store holds it


def test_the_rule_is_two_indexes_each_over_some_of_the_regions(mapped: Engine) -> None:
    with mapped.connect() as connection:
        written = {
            str(row[0]): str(row[1])
            for row in connection.exec_driver_sql(
                "SELECT name, sql FROM sqlite_master WHERE type = 'index' "
                "AND name IN ('ix_region_country_id_name', 'ix_region_parent_id_name')"
            )
        }
        over = {
            name: [
                column for _, _, column in connection.exec_driver_sql(f"PRAGMA index_info({name})")
            ]
            for name in written
        }
        of_the_table = {
            name: (unique, partial)
            for _, name, unique, _, partial in connection.exec_driver_sql(
                "PRAGMA index_list(region)"
            )
        }

    assert written == {
        "ix_region_country_id_name": (
            "CREATE UNIQUE INDEX ix_region_country_id_name ON region (country_id, name) "
            "WHERE iso_3166_2 IS NULL AND parent_id IS NULL"
        ),
        "ix_region_parent_id_name": (
            "CREATE UNIQUE INDEX ix_region_parent_id_name ON region (parent_id, name) "
            "WHERE iso_3166_2 IS NULL AND parent_id IS NOT NULL"
        ),
    }
    assert over == {
        "ix_region_country_id_name": ["country_id", "name"],
        "ix_region_parent_id_name": ["parent_id", "name"],
    }
    # Each holds no two rows alike, and each is over some of the rows.
    assert of_the_table["ix_region_country_id_name"] == (1, 1)
    assert of_the_table["ix_region_parent_id_name"] == (1, 1)
    # No other index of the table that the code makes is over some rows only.
    assert sorted(name for name, (_, partial) in of_the_table.items() if partial == 1) == [
        "ix_region_country_id_name",
        "ix_region_parent_id_name",
    ]


def test_a_region_without_a_code_is_found_by_its_place_and_name_with_the_index_of_its_rule(
    mapped: Engine,
) -> None:
    assert plan_of(
        mapped,
        "SELECT id FROM region WHERE parent_id = 1 AND name = 'Washington County' "
        "AND iso_3166_2 IS NULL",
    ) == ["SEARCH region USING INDEX ix_region_parent_id_name (parent_id=? AND name=?)"]
    assert plan_of(
        mapped,
        "SELECT id FROM region WHERE country_id = 1 AND name = 'Georgia' "
        "AND iso_3166_2 IS NULL AND parent_id IS NULL",
    ) == ["SEARCH region USING INDEX ix_region_country_id_name (country_id=? AND name=?)"]
    # A question that does not say whether the region is a part of one
    # is not answered from either index of the rule: neither holds all
    # the regions of a country that say no code.
    in_any_place = plan_of(
        mapped,
        "SELECT id FROM region WHERE country_id = 1 AND name = 'Georgia' AND iso_3166_2 IS NULL",
    )
    assert len(in_any_place) == 1
    assert "ix_region_country_id_name" not in in_any_place[0]
    assert "ix_region_parent_id_name" not in in_any_place[0]


def test_a_statement_that_stores_a_part_or_does_nothing_names_the_parts_of_the_rule(
    mapped: Engine,
) -> None:
    or_nothing = NEW + " ON CONFLICT (parent_id, name) {}DO NOTHING"
    of_the_rule = "WHERE iso_3166_2 IS NULL AND parent_id IS NOT NULL "

    write(mapped, or_nothing.format(of_the_rule), UNITED_STATES, OHIO, A_COUNTY, None)
    write(mapped, or_nothing.format(of_the_rule), UNITED_STATES, OHIO, A_COUNTY, None)
    write(mapped, or_nothing.format(of_the_rule), UNITED_STATES, PENNSYLVANIA, A_COUNTY, None)

    # The statement that did nothing was given the key 7 before it was
    # found to be one too many, and a key is not given twice.
    assert regions(mapped)[5:] == [
        (6, UNITED_STATES, OHIO, A_COUNTY, None),
        (8, UNITED_STATES, PENNSYLVANIA, A_COUNTY, None),
    ]
    # A statement that names the two columns and not which regions the
    # rule is over names no rule of the table, and SQLite says so. So
    # does one that names the regions of the other rule.
    for named in ("", "WHERE iso_3166_2 IS NULL AND parent_id IS NULL "):
        with pytest.raises(OperationalError) as no_rule:
            write(mapped, or_nothing.format(named), UNITED_STATES, OHIO, A_COUNTY, None)
        assert str(no_rule.value.orig) == (
            "ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint"
        )
