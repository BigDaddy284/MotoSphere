"""Tests of a region that is a part of another region, against a real SQLite file.

A country is divided into parts, and some of those into parts again: a
county is a part of a state. A region can say which region it is a part
of. That region is one that is there, of its own country, and not the
region itself, and it cannot be deleted or moved to another country
while regions are parts of it.

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
from sqlalchemy.exc import IntegrityError

from motosphere.db.changes import change
from motosphere.db.models import Country, Region, Source
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 28, 9, 0, tzinfo=UTC)
# The three countries of the tests, by their keys.
FRANCE = 1
SPAIN = 2
ITALY = 3
COUNTRIES = [("FR", "FRA", "France"), ("ES", "ESP", "Spain"), ("IT", "ITA", "Italy")]
# Regions of the list of ISO 3166-2 that comes with release 4.20.1 of
# iso-codes, and what each is a part of there. Two of the 5046 regions of
# that list lie two deep, both in France: the departments Bas-Rhin and
# Haut-Rhin are parts of Alsace, which is a part of Grand-Est. In Spain a
# province and the community it is a part of have one name.
GRAND_EST = ("Grand-Est", "FR-GES")
ALSACE = ("Alsace", "FR-6AE")
BAS_RHIN = ("Bas-Rhin", "FR-67")
HAUT_RHIN = ("Haut-Rhin", "FR-68")
BRETAGNE = ("Bretagne", "FR-BRE")
THE_COMMUNITY = ("Cantabria", "ES-CB")
THE_PROVINCE = ("Cantabria", "ES-S")
LOMBARDIA = ("Lombardia", "IT-25")
POINTS_NOWHERE = "FOREIGN KEY constraint failed"
A_PART_OF_ITSELF = "CHECK constraint failed: ck_region_parent_id_not_itself"
OF_ITS_COUNTRY = "The code of a region (region) begins with the code of its country (country)."
# A region as plain SQL: its country, the region it is a part of, its
# name and its code are given, and its key where the statement names it.
A_REGION = (
    "INTO region ({}country_id, parent_id, name, iso_3166_2, source_id, source_address, "
    "collected_at, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) VALUES ({}?, ?, ?, ?, 1, 'https://standards.example/regions.csv', "
    "'2026-11-28T09:00:00.000000+00:00', '2026-11-28T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-28T09:00:05.000000+00:00', '2026-11-28T09:00:05.000000+00:00')"
)
NEW = "INSERT " + A_REGION.format("", "")
NEW_WITH_ITS_KEY = "INSERT " + A_REGION.format("id, ", "?, ")
IN_THE_PLACE_OF_ANOTHER = "REPLACE " + A_REGION.format("id, ", "?, ")


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


@pytest.fixture
def mapped(newest: Engine) -> Engine:
    """The test's own store with the newest schema, one source and three countries in it.

    The key of the source is 1. The keys of the countries are 1 to 3:
    France, Spain and Italy.
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
    return newest


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


def nothing_points_nowhere(store: Engine) -> bool:
    """Whether SQLite, asked to look at every row, finds none that points nowhere."""
    with store.connect() as connection:
        return connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


@pytest.fixture
def france(mapped: Engine) -> Engine:
    """The store with four regions of France: Grand-Est, Alsace in it, and the two in Alsace.

    Their keys are 1 to 4: Grand-Est, Alsace, Bas-Rhin and Haut-Rhin.
    """
    keep(mapped, FRANCE, GRAND_EST)
    keep(mapped, FRANCE, ALSACE, 1)
    keep(mapped, FRANCE, BAS_RHIN, 2)
    keep(mapped, FRANCE, HAUT_RHIN, 2)
    return mapped


IN_FRANCE = [
    (1, FRANCE, None, "Grand-Est"),
    (2, FRANCE, 1, "Alsace"),
    (3, FRANCE, 2, "Bas-Rhin"),
    (4, FRANCE, 2, "Haut-Rhin"),
]


# ------------------------------------------------------- a region and its parts


def test_a_region_is_a_part_of_its_country_only_unless_it_says_more(mapped: Engine) -> None:
    through_the_model = keep(mapped, FRANCE, GRAND_EST)
    write(mapped, NEW, FRANCE, None, *BRETAGNE)
    # Past the model the column need not be named at all.
    write(
        mapped,
        "INSERT INTO region (country_id, name, source_id, source_address, collected_at, "
        "last_verified_at, extraction_method, confidence, verification_status, created_at, "
        "updated_at) SELECT country_id, 'Normandie', source_id, source_address, collected_at, "
        "last_verified_at, extraction_method, confidence, verification_status, created_at, "
        "updated_at FROM region WHERE id = 1",
    )

    with unit_of_work(mapped) as work:
        assert work.get_one(Region, through_the_model).parent_id is None
    assert regions(mapped) == [
        (1, FRANCE, None, "Grand-Est"),
        (2, FRANCE, None, "Bretagne"),
        (3, FRANCE, None, "Normandie"),
    ]


def test_a_region_is_stored_as_a_part_of_another_through_the_model(mapped: Engine) -> None:
    whole = keep(mapped, FRANCE, GRAND_EST)
    part = keep(mapped, FRANCE, ALSACE, whole)

    with unit_of_work(mapped) as work:
        assert work.get_one(Region, part).parent_id == whole
    assert regions(mapped) == [(1, FRANCE, None, "Grand-Est"), (2, FRANCE, 1, "Alsace")]


def test_a_region_is_stored_as_a_part_of_another_past_the_model(mapped: Engine) -> None:
    write(mapped, NEW, FRANCE, None, *GRAND_EST)
    write(mapped, NEW, FRANCE, 1, *ALSACE)

    assert regions(mapped) == [(1, FRANCE, None, "Grand-Est"), (2, FRANCE, 1, "Alsace")]


def test_a_part_of_a_region_can_have_parts_of_its_own_and_a_region_many(france: Engine) -> None:
    # Two of the regions of the standard's list lie two deep, and these
    # are the two: each a part of Alsace, which is a part of Grand-Est.
    assert regions(france) == IN_FRANCE
    assert nothing_points_nowhere(france)


def test_a_region_and_a_part_of_it_can_have_one_name(mapped: Engine) -> None:
    community = keep(mapped, SPAIN, THE_COMMUNITY)
    keep(mapped, SPAIN, THE_PROVINCE, community)

    assert regions(mapped) == [(1, SPAIN, None, "Cantabria"), (2, SPAIN, 1, "Cantabria")]


def test_a_region_without_a_code_can_be_a_part_and_can_have_parts(mapped: Engine) -> None:
    whole = keep(mapped, FRANCE, ("Grand-Est", None))
    part = keep(mapped, FRANCE, ("Alsace", None), whole)
    keep(mapped, FRANCE, BAS_RHIN, part)

    assert regions(mapped) == [
        (1, FRANCE, None, "Grand-Est"),
        (2, FRANCE, 1, "Alsace"),
        (3, FRANCE, 2, "Bas-Rhin"),
    ]


def test_a_region_is_made_a_part_of_another_later_and_of_none_again(mapped: Engine) -> None:
    whole = keep(mapped, FRANCE, GRAND_EST)
    part = keep(mapped, FRANCE, ALSACE)

    with unit_of_work(mapped) as work:
        work.get_one(Region, part).parent_id = whole
    assert regions(mapped)[1] == (part, FRANCE, whole, "Alsace")

    with unit_of_work(mapped) as work:
        work.get_one(Region, part).parent_id = None
    assert regions(mapped)[1] == (part, FRANCE, None, "Alsace")

    write(mapped, "UPDATE region SET parent_id = ? WHERE id = ?", whole, part)
    assert regions(mapped)[1] == (part, FRANCE, whole, "Alsace")


def test_a_region_is_moved_from_one_region_to_another_with_its_history(france: Engine) -> None:
    other = keep(france, FRANCE, BRETAGNE)

    with unit_of_work(france) as work:
        change(work, work.get_one(Region, 2), {"parent_id": other}, decided_by="Jo Example")

    assert regions(france)[1] == (2, FRANCE, other, "Alsace")
    # Its own parts went with it: they are parts of Alsace as before.
    assert regions(france)[2:4] == IN_FRANCE[2:4]
    with france.connect() as connection:
        noted = connection.exec_driver_sql(
            "SELECT record_table, record_id, field, old_value, new_value FROM record_change"
        ).all()
    assert [tuple(row) for row in noted] == [("region", 2, "parent_id", "1", str(other))]


# ------------------------------------------- the region it names is one that is there


def test_a_region_cannot_be_stored_as_a_part_of_a_region_that_is_not_there(
    mapped: Engine,
) -> None:
    keep(mapped, FRANCE, GRAND_EST)

    with refused(POINTS_NOWHERE):
        keep(mapped, FRANCE, ALSACE, 99)
    with refused(POINTS_NOWHERE):
        write(mapped, NEW, FRANCE, 99, *ALSACE)
    # Nor of one whose key is not a key at all.
    with refused(POINTS_NOWHERE):
        write(mapped, NEW, FRANCE, 0, *ALSACE)
    with refused(POINTS_NOWHERE):
        write(mapped, NEW, FRANCE, -1, *ALSACE)

    assert regions(mapped) == [(1, FRANCE, None, "Grand-Est")]


def test_a_region_cannot_be_made_a_part_of_a_region_that_is_not_there(france: Engine) -> None:
    with refused(POINTS_NOWHERE), unit_of_work(france) as work:
        work.get_one(Region, 3).parent_id = 99
    with refused(POINTS_NOWHERE):
        write(france, "UPDATE region SET parent_id = 99 WHERE id = 3")

    assert regions(france) == IN_FRANCE


def test_a_region_cannot_be_a_part_of_a_region_that_was_deleted(mapped: Engine) -> None:
    gone = keep(mapped, FRANCE, GRAND_EST)
    with unit_of_work(mapped) as work:
        work.execute(delete(Region).where(Region.id == gone))

    with refused(POINTS_NOWHERE):
        keep(mapped, FRANCE, ALSACE, gone)

    assert regions(mapped) == []


def test_what_a_region_is_a_part_of_is_a_whole_number(france: Engine) -> None:
    # The table is strict: text that is no number is not taken for a key.
    with pytest.raises(IntegrityError) as refusal:
        write(france, "UPDATE region SET parent_id = 'Alsace' WHERE id = 3")

    assert str(refusal.value.orig) == "cannot store TEXT value in INTEGER column region.parent_id"
    assert regions(france) == IN_FRANCE


# ---------------------------------------------------------------- of its own country


def test_a_region_cannot_be_stored_as_a_part_of_a_region_of_another_country(
    mapped: Engine,
) -> None:
    community = keep(mapped, SPAIN, THE_COMMUNITY)

    with refused(POINTS_NOWHERE):
        keep(mapped, FRANCE, ALSACE, community)
    with refused(POINTS_NOWHERE):
        write(mapped, NEW, FRANCE, community, *ALSACE)
    # Without a code too: it is the country that is asked, not the letters.
    with refused(POINTS_NOWHERE):
        write(mapped, NEW, ITALY, community, "Lombardia", None)

    assert regions(mapped) == [(1, SPAIN, None, "Cantabria")]


def test_a_region_cannot_be_made_a_part_of_a_region_of_another_country(france: Engine) -> None:
    community = keep(france, SPAIN, THE_COMMUNITY)

    with refused(POINTS_NOWHERE), unit_of_work(france) as work:
        work.get_one(Region, 3).parent_id = community
    with refused(POINTS_NOWHERE):
        write(france, "UPDATE region SET parent_id = ? WHERE id = 3", community)

    assert regions(france) == [*IN_FRANCE, (5, SPAIN, None, "Cantabria")]


def test_a_part_of_a_region_cannot_be_moved_to_another_country(mapped: Engine) -> None:
    whole = keep(mapped, FRANCE, ("Grand-Est", None))
    part = keep(mapped, FRANCE, ("Alsace", None), whole)

    with refused(POINTS_NOWHERE), unit_of_work(mapped) as work:
        work.get_one(Region, part).country_id = SPAIN
    with refused(POINTS_NOWHERE):
        write(mapped, "UPDATE region SET country_id = ? WHERE id = ?", SPAIN, part)

    assert regions(mapped) == [(1, FRANCE, None, "Grand-Est"), (2, FRANCE, 1, "Alsace")]
    # Once it is a part of none, it can be.
    write(mapped, "UPDATE region SET parent_id = NULL, country_id = ? WHERE id = ?", SPAIN, part)
    assert regions(mapped) == [(1, FRANCE, None, "Grand-Est"), (2, SPAIN, None, "Alsace")]


def test_a_region_that_has_parts_cannot_be_moved_to_another_country(mapped: Engine) -> None:
    whole = keep(mapped, FRANCE, ("Grand-Est", None))
    keep(mapped, FRANCE, ("Alsace", None), whole)

    with refused(POINTS_NOWHERE), unit_of_work(mapped) as work:
        work.get_one(Region, whole).country_id = SPAIN
    with refused(POINTS_NOWHERE):
        write(mapped, "UPDATE region SET country_id = ? WHERE id = ?", SPAIN, whole)

    assert regions(mapped) == [(1, FRANCE, None, "Grand-Est"), (2, FRANCE, 1, "Alsace")]


def test_a_region_and_its_parts_can_be_moved_to_another_country_by_one_statement(
    mapped: Engine,
) -> None:
    # SQLite asks where every row points when the statement has ended, and
    # by then the region and its parts are of one country again.
    whole = keep(mapped, FRANCE, ("Grand-Est", None))
    part = keep(mapped, FRANCE, ("Alsace", None), whole)
    keep(mapped, FRANCE, ("Bas-Rhin", None), part)

    write(mapped, "UPDATE region SET country_id = ?", SPAIN)

    assert regions(mapped) == [
        (1, SPAIN, None, "Grand-Est"),
        (2, SPAIN, 1, "Alsace"),
        (3, SPAIN, 2, "Bas-Rhin"),
    ]
    assert nothing_points_nowhere(mapped)


def test_a_part_can_be_moved_to_another_country_and_another_region_at_once(
    mapped: Engine,
) -> None:
    whole = keep(mapped, FRANCE, ("Grand-Est", None))
    part = keep(mapped, FRANCE, ("Alsace", None), whole)
    community = keep(mapped, SPAIN, THE_COMMUNITY)

    write(
        mapped,
        "UPDATE region SET country_id = ?, parent_id = ? WHERE id = ?",
        SPAIN,
        community,
        part,
    )

    assert regions(mapped)[1] == (part, SPAIN, community, "Alsace")


def test_the_code_of_a_part_is_of_its_country_as_that_of_any_region(france: Engine) -> None:
    with refused(OF_ITS_COUNTRY):
        write(france, NEW, FRANCE, 1, "Lorraine", "ES-LO")

    assert regions(france) == IN_FRANCE


# ------------------------------------------------------------------------ not itself


def test_a_region_cannot_be_made_a_part_of_itself(france: Engine) -> None:
    with refused(A_PART_OF_ITSELF), unit_of_work(france) as work:
        work.get_one(Region, 2).parent_id = 2
    with refused(A_PART_OF_ITSELF):
        write(france, "UPDATE region SET parent_id = id WHERE id = 2")
    # One that is a part of no region, too.
    with refused(A_PART_OF_ITSELF):
        write(france, "UPDATE region SET parent_id = 1 WHERE id = 1")

    assert regions(france) == IN_FRANCE


def test_a_region_cannot_be_stored_as_a_part_of_itself(france: Engine) -> None:
    # With its key named, and with the key it will be given: the fifth
    # region of the store would have the key 5.
    with refused(A_PART_OF_ITSELF):
        write(france, NEW_WITH_ITS_KEY, 50, FRANCE, 50, *BRETAGNE)
    with refused(A_PART_OF_ITSELF):
        write(france, NEW, FRANCE, 5, *BRETAGNE)

    assert regions(france) == IN_FRANCE
    # The key 5 was not used up by the refusal that named none.
    assert keep(france, FRANCE, BRETAGNE) == 5


def test_a_region_cannot_take_the_key_of_the_region_it_is_a_part_of(france: Engine) -> None:
    # Bas-Rhin, a part of Alsace, would be put in the place of Alsace.
    with refused(A_PART_OF_ITSELF):
        write(france, "UPDATE OR REPLACE region SET id = 2 WHERE id = 3")

    assert regions(france) == IN_FRANCE


# ------------------------------------------------------- a region that has parts stays


def test_a_region_that_has_parts_cannot_be_deleted(france: Engine) -> None:
    for whole in (1, 2):
        with refused(POINTS_NOWHERE), unit_of_work(france) as work:
            work.execute(delete(Region).where(Region.id == whole))
        with refused(POINTS_NOWHERE):
            write(france, "DELETE FROM region WHERE id = ?", whole)

    assert regions(france) == IN_FRANCE


def test_a_region_can_be_deleted_once_its_parts_are(france: Engine) -> None:
    write(france, "DELETE FROM region WHERE id IN (3, 4)")
    write(france, "DELETE FROM region WHERE id = 2")
    write(france, "DELETE FROM region WHERE id = 1")

    assert regions(france) == []


def test_a_region_can_be_deleted_once_its_parts_are_parts_of_another(france: Engine) -> None:
    with unit_of_work(france) as work:
        work.get_one(Region, 3).parent_id = 1
        work.get_one(Region, 4).parent_id = None
    with unit_of_work(france) as work:
        work.execute(delete(Region).where(Region.id == 2))

    assert regions(france) == [
        (1, FRANCE, None, "Grand-Est"),
        (3, FRANCE, 1, "Bas-Rhin"),
        (4, FRANCE, None, "Haut-Rhin"),
    ]


def test_a_region_and_all_its_parts_can_be_deleted_by_one_statement(france: Engine) -> None:
    keep(france, FRANCE, BRETAGNE)

    write(france, "DELETE FROM region WHERE id IN (1, 2, 3, 4)")

    assert regions(france) == [(5, FRANCE, None, "Bretagne")]
    assert nothing_points_nowhere(france)


def test_one_statement_cannot_delete_a_region_and_leave_a_part_of_it(france: Engine) -> None:
    with refused(POINTS_NOWHERE):
        write(france, "DELETE FROM region WHERE id IN (1, 2, 3)")

    # The statement is taken back whole.
    assert regions(france) == IN_FRANCE


def test_each_statement_is_asked_where_its_rows_point_when_it_ends(france: Engine) -> None:
    # The statement, not the work it is a part of: a region cannot be
    # deleted first and its parts after it, nor a part stored first and
    # the region it names after it.
    with refused(POINTS_NOWHERE), france.begin() as connection:
        connection.exec_driver_sql("DELETE FROM region WHERE id = 2")
        connection.exec_driver_sql("DELETE FROM region WHERE id IN (3, 4)")
    with refused(POINTS_NOWHERE), france.begin() as connection:
        connection.exec_driver_sql(NEW, (FRANCE, 6, "Finistere", "FR-29"))
        connection.exec_driver_sql(NEW_WITH_ITS_KEY, (6, FRANCE, None, *BRETAGNE))

    assert regions(france) == IN_FRANCE


def test_the_key_of_a_region_that_has_parts_cannot_be_changed(france: Engine) -> None:
    with refused(POINTS_NOWHERE):
        write(france, "UPDATE region SET id = 20 WHERE id = 2")

    assert regions(france) == IN_FRANCE
    # The key of one that has none can, as before.
    write(france, "UPDATE region SET id = 30 WHERE id = 3")
    assert regions(france) == [*IN_FRANCE[:2], IN_FRANCE[3], (30, FRANCE, 2, "Bas-Rhin")]


def test_a_country_cannot_be_deleted_while_it_has_regions_with_parts_or_without(
    france: Engine,
) -> None:
    with refused(POINTS_NOWHERE):
        write(france, "DELETE FROM country WHERE id = ?", FRANCE)

    assert regions(france) == IN_FRANCE


# ------------------------------------------- a statement that says REPLACE


def test_a_region_put_in_the_place_of_one_that_has_parts_keeps_them(france: Engine) -> None:
    # REPLACE takes the region away and stores the new one under its key.
    # The parts point to the key and the country, and both are there
    # again when the statement has ended.
    write(france, IN_THE_PLACE_OF_ANOTHER, 2, FRANCE, 1, "Elsass", "FR-6AE")

    assert regions(france) == [IN_FRANCE[0], (2, FRANCE, 1, "Elsass"), *IN_FRANCE[2:]]
    assert nothing_points_nowhere(france)


def test_a_region_of_another_country_cannot_be_put_in_the_place_of_one_that_has_parts(
    france: Engine,
) -> None:
    with refused(POINTS_NOWHERE):
        write(france, IN_THE_PLACE_OF_ANOTHER, 2, SPAIN, None, "Alsacia", None)

    assert regions(france) == IN_FRANCE


def test_a_region_put_in_the_place_of_another_is_held_to_the_rules_of_a_part(
    france: Engine,
) -> None:
    community = keep(france, SPAIN, THE_COMMUNITY)

    for part_of, why in [(99, POINTS_NOWHERE), (community, POINTS_NOWHERE), (3, A_PART_OF_ITSELF)]:
        with refused(why):
            write(france, IN_THE_PLACE_OF_ANOTHER, 3, FRANCE, part_of, *BAS_RHIN)

    assert regions(france) == [*IN_FRANCE, (5, SPAIN, None, "Cantabria")]


# ------------------------------------------------------ how the store holds the rules


def test_the_table_points_to_itself_with_the_region_and_the_country_together(
    mapped: Engine,
) -> None:
    with mapped.connect() as connection:
        the_table = str(
            connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'region'"
            ).scalar_one()
        )
        points = connection.exec_driver_sql(
            'SELECT "table", "from", "to", on_update, on_delete, "match" '
            "FROM pragma_foreign_key_list('region') ORDER BY \"table\", seq"
        ).all()
        column = connection.exec_driver_sql(
            "SELECT name, type, \"notnull\", dflt_value, pk FROM pragma_table_info('region') "
            "WHERE name = 'parent_id'"
        ).all()

    written = " ".join(the_table.split())
    assert "CONSTRAINT uq_region_id_country_id UNIQUE (id, country_id)" in written
    assert (
        "CONSTRAINT fk_region_parent_id_country_id_region "
        "FOREIGN KEY(parent_id, country_id) REFERENCES region (id, country_id)"
    ) in written
    assert "CONSTRAINT ck_region_parent_id_not_itself CHECK (parent_id != id)" in written
    assert [tuple(row) for row in points] == [
        ("country", "country_id", "id", "NO ACTION", "NO ACTION", "NONE"),
        ("region", "parent_id", "id", "NO ACTION", "NO ACTION", "NONE"),
        ("region", "country_id", "country_id", "NO ACTION", "NO ACTION", "NONE"),
        ("source", "source_id", "id", "NO ACTION", "NO ACTION", "NONE"),
    ]
    assert [tuple(row) for row in column] == [("parent_id", "INTEGER", 0, None, 0)]


def test_a_key_and_a_country_together_are_there_once_and_sqlite_keeps_the_index(
    mapped: Engine,
) -> None:
    with mapped.connect() as connection:
        kept = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'region' "
            "AND sql IS NULL ORDER BY name"
        ).all()
        first = connection.exec_driver_sql("PRAGMA index_info(sqlite_autoindex_region_1)").all()
        second = connection.exec_driver_sql("PRAGMA index_info(sqlite_autoindex_region_2)").all()

    # The region a region points to is found by its key and its country
    # together, and SQLite asks that the two together be there once.
    assert [str(name) for (name,) in kept] == [
        "sqlite_autoindex_region_1",
        "sqlite_autoindex_region_2",
    ]
    assert [name for _, _, name in first] == ["id", "country_id"]
    assert [name for _, _, name in second] == ["iso_3166_2"]


def test_the_parts_of_a_region_are_found_by_the_index_of_what_they_are_parts_of(
    mapped: Engine,
) -> None:
    with mapped.connect() as connection:
        written = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE name = 'ix_region_parent_id'"
        ).scalar_one()
        of_a_region = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT * FROM region WHERE parent_id = 1"
        ).all()
        of_no_region = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT * FROM region WHERE parent_id IS NULL"
        ).all()
        to_delete_a_region = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN DELETE FROM region WHERE id = 1"
        ).all()

    assert written == "CREATE INDEX ix_region_parent_id ON region (parent_id)"
    assert [detail for *_, detail in of_a_region] == [
        "SEARCH region USING INDEX ix_region_parent_id (parent_id=?)"
    ]
    # The regions that are parts of their country only are found by it too.
    assert [detail for *_, detail in of_no_region] == [
        "SEARCH region USING INDEX ix_region_parent_id (parent_id=?)"
    ]
    # Before a region is deleted SQLite looks whether it has parts, and
    # looks them up by the index: it does not read every region.
    asked = [str(detail) for *_, detail in to_delete_a_region]
    assert asked[0] == "SEARCH region USING INTEGER PRIMARY KEY (rowid=?)"
    assert [detail for detail in asked[1:] if "region" in detail] == [
        "SEARCH region USING INDEX ix_region_parent_id (parent_id=?)"
    ]
