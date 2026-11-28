"""Tests that no region is a part of itself through other regions, against a real SQLite file.

A region is not a part of itself: the table refuses that. Two regions
that are each a part of the other, or three in a ring, each name a
region that is there, of their country, and not themselves. Two triggers
refuse them: for a new region and for one that is changed.

The store of every test is built the way a real store is built: by the
migrations. What must be refused is written through the model and past
it, and each refusal is held to the sentence the store gives.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import IntegrityError

from motosphere.db.base import Base
from motosphere.db.changes import change
from motosphere.db.models import Country, Region, Source
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 28, 9, 0, tzinfo=UTC)
# The two countries of the tests, by their keys.
FRANCE = 1
SPAIN = 2
COUNTRIES = [("FR", "FRA", "France"), ("ES", "ESP", "Spain")]
# Regions of the list of ISO 3166-2 that comes with release 4.20.1 of
# iso-codes, and what each is a part of there: the departments Bas-Rhin
# and Haut-Rhin are parts of Alsace, which is a part of Grand-Est. In
# Spain a province and the community it is a part of have one name.
GRAND_EST = ("Grand-Est", "FR-GES")
ALSACE = ("Alsace", "FR-6AE")
BAS_RHIN = ("Bas-Rhin", "FR-67")
HAUT_RHIN = ("Haut-Rhin", "FR-68")
THE_COMMUNITY = ("Cantabria", "ES-CB")
THE_PROVINCE = ("Cantabria", "ES-S")
# A city in Bas-Rhin. The standard gives no city of France a code.
STRASBOURG = ("Strasbourg", None)
A_RING = "A region (region) is not a part of itself through other regions."
A_PART_OF_ITSELF = "CHECK constraint failed: ck_region_parent_id_not_itself"
# A region as plain SQL: its key, its country, the region it is a part
# of, its name and its code are given.
A_REGION = (
    "INTO region (id, country_id, parent_id, name, iso_3166_2, source_id, source_address, "
    "collected_at, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, 'https://standards.example/regions.csv', "
    "'2026-11-28T09:00:00.000000+00:00', '2026-11-28T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-28T09:00:05.000000+00:00', '2026-11-28T09:00:05.000000+00:00')"
)
NEW = "INSERT " + A_REGION
IN_THE_PLACE_OF_ANOTHER = "REPLACE " + A_REGION


@contextmanager
def refused(why: str) -> Iterator[None]:
    """The store refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def fill(store: Engine) -> None:
    """Give a store one source, with the key 1, and France and Spain, with the keys 1 and 2."""
    with unit_of_work(store) as work:
        work.add(
            Source(
                name="Example Standards Body",
                website="https://standards.example",
                category=SourceCategory.GOVERNING_BODY,
                collection_method=CollectionMethod.DATASET,
            )
        )
    for two, three, name in COUNTRIES:
        with unit_of_work(store) as work:
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


def a_region(country: int, named: tuple[str, str | None], part_of: int | None) -> Region:
    """A region as the one source of the tests says it: its name, its code, what it is a part of."""
    described: dict[str, Any] = {
        "country_id": country,
        "parent_id": part_of,
        "name": named[0],
        "iso_3166_2": named[1],
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
    store: Engine, country: int, named: tuple[str, str | None], part_of: int | None = None
) -> int:
    """Store a region through the model in a unit of work of its own, and give its key."""
    region = a_region(country, named, part_of)
    with unit_of_work(store) as work:
        work.add(region)
    return region.id


def write(store: Engine, statement: str, *given: object) -> None:
    """Write one statement past the model, as plain SQL, in a transaction of its own."""
    with store.begin() as connection:
        connection.exec_driver_sql(statement, given)


def regions(store: Engine) -> list[tuple[object, ...]]:
    """The key, the country, the region it is a part of and the name of every region, by the key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT id, country_id, parent_id, name FROM region ORDER BY id"
        )
        return [tuple(row) for row in found]


def history(store: Engine) -> list[tuple[object, ...]]:
    """What the store has noted of the changes to its records."""
    with store.connect() as connection:
        noted = connection.exec_driver_sql(
            "SELECT record_table, record_id, field, old_value, new_value FROM record_change"
        )
        return [tuple(row) for row in noted]


def the_four_of_france(store: Engine) -> None:
    """Store Grand-Est, Alsace in it, and Bas-Rhin and Haut-Rhin in Alsace, with the keys 1 to 4."""
    keep(store, FRANCE, GRAND_EST)
    keep(store, FRANCE, ALSACE, 1)
    keep(store, FRANCE, BAS_RHIN, 2)
    keep(store, FRANCE, HAUT_RHIN, 2)


@pytest.fixture
def mapped(newest: Engine) -> Engine:
    """The test's own store with the newest schema, one source and two countries in it."""
    fill(newest)
    return newest


@pytest.fixture
def france(mapped: Engine) -> Engine:
    """The store with four regions of France: Grand-Est, Alsace in it, and the two in Alsace."""
    the_four_of_france(mapped)
    return mapped


IN_FRANCE: list[tuple[object, ...]] = [
    (1, FRANCE, None, "Grand-Est"),
    (2, FRANCE, 1, "Alsace"),
    (3, FRANCE, 2, "Bas-Rhin"),
    (4, FRANCE, 2, "Haut-Rhin"),
]
# A region and a region below it, by their keys: to make the first a
# part of the second would close a ring, of two regions or of three.
BELOW_IT = [(1, 2), (2, 3), (2, 4), (1, 3), (1, 4)]


# ------------------------------------------------- a region that is changed


@pytest.mark.parametrize(("region", "below"), BELOW_IT)
def test_a_region_cannot_be_made_a_part_of_a_region_below_it(
    france: Engine, region: int, below: int
) -> None:
    with refused(A_RING):
        write(france, "UPDATE region SET parent_id = ? WHERE id = ?", below, region)

    assert regions(france) == IN_FRANCE


@pytest.mark.parametrize(("region", "below"), BELOW_IT)
def test_through_the_model_a_region_cannot_be_made_a_part_of_a_region_below_it(
    france: Engine, region: int, below: int
) -> None:
    with refused(A_RING), unit_of_work(france) as work:
        work.get_one(Region, region).parent_id = below

    assert regions(france) == IN_FRANCE


def test_a_refused_change_leaves_the_region_and_no_history(france: Engine) -> None:
    with refused(A_RING), unit_of_work(france) as work:
        change(work, work.get_one(Region, 1), {"parent_id": 3}, decided_by="Jo Example")

    assert regions(france) == IN_FRANCE
    assert history(france) == []


def test_a_ring_four_deep_is_refused_too(france: Engine) -> None:
    city = keep(france, FRANCE, STRASBOURG, 3)

    with refused(A_RING):
        write(france, "UPDATE region SET parent_id = ? WHERE id = 1", city)

    assert regions(france) == [*IN_FRANCE, (city, FRANCE, 3, "Strasbourg")]


def test_a_region_is_still_not_a_part_of_itself_and_the_table_says_so(france: Engine) -> None:
    # What the table refuses, it refuses first, in its own words.
    with refused(A_PART_OF_ITSELF):
        write(france, "UPDATE region SET parent_id = 2 WHERE id = 2")

    assert regions(france) == IN_FRANCE


def test_one_statement_that_would_close_a_ring_with_one_of_its_rows_is_taken_back_whole(
    france: Engine,
) -> None:
    # Haut-Rhin could be made a part of Bas-Rhin; Grand-Est cannot.
    with refused(A_RING):
        write(france, "UPDATE region SET parent_id = 3 WHERE id IN (4, 1)")

    assert regions(france) == IN_FRANCE


# ------------------------------------------------- what the rule leaves free


def test_a_region_is_moved_up_and_down_among_the_regions_above_it(france: Engine) -> None:
    # Bas-Rhin lies in Grand-Est too. Neither change closes a ring.
    write(france, "UPDATE region SET parent_id = 1 WHERE id = 3")
    assert regions(france)[2] == (3, FRANCE, 1, "Bas-Rhin")

    write(france, "UPDATE region SET parent_id = 2 WHERE id = 3")
    assert regions(france) == IN_FRANCE


def test_a_region_that_has_parts_and_is_a_part_is_changed_in_every_other_way(
    france: Engine,
) -> None:
    with unit_of_work(france) as work:
        change(work, work.get_one(Region, 2), {"name": "Elsass"}, decided_by="Jo Example")
    write(france, "UPDATE region SET iso_3166_2 = NULL WHERE id = 2")
    write(france, "UPDATE region SET parent_id = NULL WHERE id = 2")
    write(france, "UPDATE region SET parent_id = 1 WHERE id = 2")

    assert regions(france) == [
        (1, FRANCE, None, "Grand-Est"),
        (2, FRANCE, 1, "Elsass"),
        (3, FRANCE, 2, "Bas-Rhin"),
        (4, FRANCE, 2, "Haut-Rhin"),
    ]
    assert history(france) == [("region", 2, "name", "Alsace", "Elsass")]


def test_a_new_part_is_stored_at_every_depth(france: Engine) -> None:
    city = keep(france, FRANCE, STRASBOURG, 3)
    write(france, NEW, 9, FRANCE, 1, "Lorraine", None)

    assert regions(france) == [
        *IN_FRANCE,
        (city, FRANCE, 3, "Strasbourg"),
        (9, FRANCE, 1, "Lorraine"),
    ]


def test_two_regions_that_were_stored_the_wrong_way_round_are_turned_around_in_two_statements(
    mapped: Engine,
) -> None:
    # A source had the community as a part of the province of its name.
    province = keep(mapped, SPAIN, THE_PROVINCE)
    community = keep(mapped, SPAIN, THE_COMMUNITY, province)

    # The store asks after each row. One statement that turns the two
    # around comes to the province first, and at that moment each is a
    # part of the other.
    with refused(A_RING):
        write(
            mapped,
            "UPDATE region SET parent_id = CASE id WHEN ? THEN ? END WHERE id IN (?, ?)",
            province,
            community,
            province,
            community,
        )
    assert regions(mapped) == [
        (province, SPAIN, None, "Cantabria"),
        (community, SPAIN, province, "Cantabria"),
    ]

    # The lower region first, then the upper.
    write(mapped, "UPDATE region SET parent_id = NULL WHERE id = ?", community)
    write(mapped, "UPDATE region SET parent_id = ? WHERE id = ?", community, province)

    assert regions(mapped) == [
        (province, SPAIN, community, "Cantabria"),
        (community, SPAIN, None, "Cantabria"),
    ]


# ------------------------------------------- a region that takes another's key


@pytest.mark.parametrize(
    "takes_the_key",
    [
        "UPDATE OR REPLACE region SET id = 1 WHERE id = 3",
        "UPDATE OR REPLACE region SET rowid = 1 WHERE id = 3",
        "UPDATE OR REPLACE region SET _rowid_ = 1 WHERE id = 3",
        "UPDATE OR REPLACE region SET oid = 1 WHERE id = 3",
    ],
    ids=["id", "rowid", "_rowid_", "oid"],
)
def test_a_part_cannot_take_the_key_of_a_region_above_its_region(
    france: Engine, takes_the_key: str
) -> None:
    # Bas-Rhin in the place of Grand-Est, under each name SQLite has for
    # the key: Alsace would be a part of the region with the key 1
    # still, and that region a part of Alsace.
    with refused(A_RING):
        write(france, takes_the_key)

    assert regions(france) == IN_FRANCE


def test_a_region_can_take_the_key_of_a_region_that_is_not_above_it(france: Engine) -> None:
    # Haut-Rhin in the place of Bas-Rhin, which has no parts.
    write(france, "UPDATE OR REPLACE region SET id = 3 WHERE id = 4")

    assert regions(france) == [*IN_FRANCE[:2], (3, FRANCE, 2, "Haut-Rhin")]


@pytest.mark.parametrize(
    ("place", "below"), [(1, 2), (1, 3), (2, 3)], ids=["1 in 2", "1 in 3", "2 in 3"]
)
def test_a_region_put_in_the_place_of_another_is_not_a_part_of_a_region_below_that_place(
    france: Engine, place: int, below: int
) -> None:
    with refused(A_RING):
        write(france, IN_THE_PLACE_OF_ANOTHER, place, FRANCE, below, "Lorraine", "FR-LOR")

    assert regions(france) == IN_FRANCE


def test_a_region_put_in_the_place_of_another_keeps_its_parts_where_no_ring_closes(
    france: Engine,
) -> None:
    write(france, IN_THE_PLACE_OF_ANOTHER, 2, FRANCE, 1, "Elsass", None)

    assert regions(france) == [
        (1, FRANCE, None, "Grand-Est"),
        (2, FRANCE, 1, "Elsass"),
        (3, FRANCE, 2, "Bas-Rhin"),
        (4, FRANCE, 2, "Haut-Rhin"),
    ]


# ------------------------------------------------------- how a refusal behaves


def test_a_refusal_stops_the_statement_and_not_the_work_before_it(france: Engine) -> None:
    with france.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET name = 'Elsass' WHERE id = 2")
        with pytest.raises(IntegrityError) as refusal:
            connection.exec_driver_sql(
                "UPDATE region SET name = 'Example', parent_id = 3 WHERE id = 1"
            )
        assert str(refusal.value.orig) == A_RING
        with pytest.raises(IntegrityError) as refusal:
            connection.exec_driver_sql(IN_THE_PLACE_OF_ANOTHER, (1, FRANCE, 4, "Example", None))
        assert str(refusal.value.orig) == A_RING
        connection.exec_driver_sql("UPDATE region SET parent_id = 1 WHERE id = 4")

    assert regions(france) == [
        (1, FRANCE, None, "Grand-Est"),
        (2, FRANCE, 1, "Elsass"),
        (3, FRANCE, 2, "Bas-Rhin"),
        (4, FRANCE, 1, "Haut-Rhin"),
    ]


def test_in_a_unit_of_work_a_refusal_takes_the_work_back(france: Engine) -> None:
    with refused(A_RING), unit_of_work(france) as work:
        work.add(a_region(FRANCE, STRASBOURG, 3))
        work.flush()
        work.get_one(Region, 1).parent_id = 4

    assert regions(france) == IN_FRANCE


def test_the_refusals_hold_on_a_connection_the_stores_code_did_not_open(
    france: Engine, tmp_path: Path
) -> None:
    # The rule stands in the file. A connection that does not ask SQLite
    # to hold rows to what they point to is held to it all the same.
    france.dispose()
    plain = sqlite3.connect(tmp_path / "store.sqlite3", isolation_level=None)
    try:
        assert plain.execute("PRAGMA foreign_keys").fetchone() == (0,)
        for statement, given in [
            ("UPDATE region SET parent_id = 3 WHERE id = 1", ()),
            ("UPDATE OR REPLACE region SET rowid = 1 WHERE id = 3", ()),
            (IN_THE_PLACE_OF_ANOTHER, (1, FRANCE, 4, "Example", None)),
        ]:
            with pytest.raises(sqlite3.IntegrityError) as refusal:
                plain.execute(statement, given)
            assert str(refusal.value) == A_RING
    finally:
        plain.close()

    assert regions(france) == IN_FRANCE


def test_a_store_made_from_the_models_refuses_a_ring_too(tmp_path: Path) -> None:
    made = create_engine(f"sqlite:///{tmp_path / 'made.sqlite3'}")
    Base.metadata.create_all(made)
    try:
        fill(made)
        the_four_of_france(made)

        for statement, given in [
            ("UPDATE region SET parent_id = 3 WHERE id = 1", ()),
            ("UPDATE OR REPLACE region SET id = 1 WHERE id = 3", ()),
            (IN_THE_PLACE_OF_ANOTHER, (1, FRANCE, 4, "Example", None)),
        ]:
            with refused(A_RING):
                write(made, statement, *given)
        assert regions(made) == IN_FRANCE
    finally:
        made.dispose()


# -------------------------------------------------------- how the rule stands

ON_THE_REGIONS_AND_THE_COUNTRIES = [
    ("tr_country_code_of_its_regions", "country"),
    ("tr_country_code_stays_of_its_regions", "country"),
    ("tr_region_code_of_its_country", "region"),
    ("tr_region_code_stays_of_its_country", "region"),
    ("tr_region_parent_id_not_below_itself", "region"),
    ("tr_region_parent_id_stays_not_below_itself", "region"),
]
# The question both triggers ask, as SQLite has it written.
ABOVE_IT = (
    "EXISTS ( WITH RECURSIVE above(id) AS ( SELECT NEW.parent_id UNION "
    "SELECT region.parent_id FROM region JOIN above ON region.id = above.id "
    "WHERE region.parent_id IS NOT NULL) SELECT 1 FROM above WHERE id = NEW.id)"
)


def test_the_rule_is_two_triggers_on_the_regions(mapped: Engine) -> None:
    with mapped.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name, tbl_name, sql FROM sqlite_master WHERE type = 'trigger' "
            "AND tbl_name IN ('region', 'country') ORDER BY name"
        ).all()

    assert [(str(name), str(table)) for name, table, _ in found] == ON_THE_REGIONS_AND_THE_COUNTRIES
    written = {str(name): " ".join(str(statement).split()) for name, _, statement in found}
    assert written["tr_region_parent_id_not_below_itself"] == (
        "CREATE TRIGGER tr_region_parent_id_not_below_itself AFTER INSERT ON region "
        f"WHEN NEW.parent_id IS NOT NULL AND {ABOVE_IT} "
        f"BEGIN SELECT RAISE(ABORT, '{A_RING}'); END"
    )
    assert written["tr_region_parent_id_stays_not_below_itself"] == (
        "CREATE TRIGGER tr_region_parent_id_stays_not_below_itself AFTER UPDATE ON region "
        "WHEN NEW.parent_id IS NOT NULL "
        "AND (NEW.parent_id IS NOT OLD.parent_id OR NEW.id != OLD.id) "
        f"AND {ABOVE_IT} "
        f"BEGIN SELECT RAISE(ABORT, '{A_RING}'); END"
    )
    # Neither fires for the change of one column alone (DAT-068).
    assert [name for name, statement in written.items() if "UPDATE OF" in statement.upper()] == []


def test_the_regions_above_a_region_are_found_by_their_keys(mapped: Engine) -> None:
    # The way upwards is from key to key: SQLite reads no region that is
    # not above the one that is asked about.
    with mapped.connect() as connection:
        steps = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN WITH RECURSIVE above(id) AS (SELECT 3 UNION "
            "SELECT region.parent_id FROM region JOIN above ON region.id = above.id "
            "WHERE region.parent_id IS NOT NULL) SELECT 1 FROM above WHERE id = 1"
        ).all()

    plan = [str(detail) for *_, detail in steps]
    assert "SEARCH region USING INTEGER PRIMARY KEY (rowid=?)" in plan
    assert [step for step in plan if step.startswith("SCAN region")] == []
