"""Tests of the names two regions of one country can share, against a real SQLite file.

The standard's own list, ISO 3166-2, has regions of one country that
have one name: Maputo the city and Maputo the province of Mozambique.
Their codes tell them apart. So the rule of the names is over the
regions that say no code: no two of them have one name in a country. A
region that says its code can have the name of any other.

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
# The four countries of the tests, by their keys.
MOZAMBIQUE = 1
ESTONIA = 2
SPAIN = 3
BANGLADESH = 4
COUNTRIES = [
    ("MZ", "MOZ", "Mozambique"),
    ("EE", "EST", "Estonia"),
    ("ES", "ESP", "Spain"),
    ("BD", "BGD", "Bangladesh"),
]
# Four of the 36 pairs of regions that have one name in one country in the
# list of ISO 3166-2 that comes with release 4.20.1 of iso-codes: the
# country, the name and the two codes. A province and a city, neither
# inside another region; a town and the parish around it, both inside one
# county; an autonomous community and the one province inside it; and a
# district inside the division of its name.
PAIRS = [
    (MOZAMBIQUE, "Maputo", "MZ-L", "MZ-MPM"),
    (ESTONIA, "Tartu", "EE-793", "EE-796"),
    (SPAIN, "Cantabria", "ES-CB", "ES-S"),
    (BANGLADESH, "Dhaka", "BD-13", "BD-C"),
]
OF_THE_PAIRS = [name for _, name, _, _ in PAIRS]
ONE_NAME_TWICE = "UNIQUE constraint failed: region.country_id, region.name"
# A region as plain SQL: its country, its name and its code are given.
A_REGION = (
    "INSERT INTO region (country_id, name, iso_3166_2, source_id, source_address, "
    "collected_at, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) VALUES (?, ?, ?, 1, 'https://standards.example/regions.csv', "
    "'2026-11-28T09:00:00.000000+00:00', '2026-11-28T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-28T09:00:05.000000+00:00', '2026-11-28T09:00:05.000000+00:00')"
)


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


@pytest.fixture
def mapped(newest: Engine) -> Engine:
    """The test's own store with the newest schema, one source and four countries in it.

    The key of the source is 1. The keys of the countries are 1 to 4:
    Mozambique, Estonia, Spain and Bangladesh.
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


def a_region(country: int, name: str, code: str | None, **said: Any) -> Region:
    """A region as the one source of the tests says it, and what the test says."""
    described: dict[str, Any] = {
        "country_id": country,
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
    return Region(**(described | said))


def keep(store: Engine, country: int, name: str, code: str | None) -> int:
    """Store a region through the model in a unit of work of its own, and give its key."""
    region = a_region(country, name, code)
    with unit_of_work(store) as work:
        work.add(region)
    return region.id


def write(store: Engine, statement: str, *given: object) -> None:
    """Write one statement past the model, as plain SQL, in a transaction of its own."""
    with store.begin() as connection:
        connection.exec_driver_sql(statement, given)


def regions(store: Engine) -> list[tuple[object, ...]]:
    """The key, the country, the name and the code of every region, by their key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT id, country_id, name, iso_3166_2 FROM region ORDER BY id"
        )
        return [tuple(row) for row in found]


# ------------------------------------------------ two regions that say their codes


@pytest.mark.parametrize(("country", "name", "one", "other"), PAIRS, ids=OF_THE_PAIRS)
def test_both_regions_of_a_pair_of_the_standard_are_stored_through_the_model(
    mapped: Engine, country: int, name: str, one: str, other: str
) -> None:
    first = keep(mapped, country, name, one)
    second = keep(mapped, country, name, other)

    assert (first, second) == (1, 2)
    assert regions(mapped) == [(1, country, name, one), (2, country, name, other)]


@pytest.mark.parametrize(("country", "name", "one", "other"), PAIRS, ids=OF_THE_PAIRS)
def test_both_regions_of_a_pair_of_the_standard_are_stored_past_the_model(
    mapped: Engine, country: int, name: str, one: str, other: str
) -> None:
    # The other of the pair first: the order makes no difference.
    write(mapped, A_REGION, country, name, other)
    write(mapped, A_REGION, country, name, one)

    assert regions(mapped) == [(1, country, name, other), (2, country, name, one)]


def test_all_four_pairs_are_in_one_store_together(mapped: Engine) -> None:
    for country, name, one, other in PAIRS:
        keep(mapped, country, name, one)
        keep(mapped, country, name, other)

    assert [(name, code) for _, _, name, code in regions(mapped)] == [
        ("Maputo", "MZ-L"),
        ("Maputo", "MZ-MPM"),
        ("Tartu", "EE-793"),
        ("Tartu", "EE-796"),
        ("Cantabria", "ES-CB"),
        ("Cantabria", "ES-S"),
        ("Dhaka", "BD-13"),
        ("Dhaka", "BD-C"),
    ]


def test_a_region_with_a_code_can_be_given_the_name_of_another_of_its_country(
    mapped: Engine,
) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", "MZ-L")
    city = keep(mapped, MOZAMBIQUE, "Cidade de Maputo", "MZ-MPM")
    keep(mapped, MOZAMBIQUE, "Gaza", None)

    with unit_of_work(mapped) as work:
        work.get_one(Region, city).name = "Maputo"
    assert regions(mapped)[1] == (city, MOZAMBIQUE, "Maputo", "MZ-MPM")
    # The name of a region that says no code, too.
    write(mapped, "UPDATE region SET name = 'Gaza' WHERE id = ?", city)
    assert regions(mapped) == [
        (1, MOZAMBIQUE, "Maputo", "MZ-L"),
        (2, MOZAMBIQUE, "Gaza", "MZ-MPM"),
        (3, MOZAMBIQUE, "Gaza", None),
    ]


def test_a_region_is_changed_to_a_name_it_shares_with_its_history(mapped: Engine) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", "MZ-L")
    city = keep(mapped, MOZAMBIQUE, "Cidade de Maputo", "MZ-MPM")

    with unit_of_work(mapped) as work:
        change(work, work.get_one(Region, city), {"name": "Maputo"}, decided_by="Jo Example")

    assert regions(mapped)[1] == (city, MOZAMBIQUE, "Maputo", "MZ-MPM")
    with mapped.connect() as connection:
        noted = connection.exec_driver_sql(
            "SELECT record_table, record_id, field, old_value, new_value FROM record_change"
        ).all()
    assert [tuple(row) for row in noted] == [("region", city, "name", "Cidade de Maputo", "Maputo")]


# ------------------------------------------------------ two regions that say no code


@pytest.mark.parametrize(("country", "name", "one", "other"), PAIRS, ids=OF_THE_PAIRS)
def test_two_regions_of_one_country_that_say_no_code_cannot_have_one_name(
    mapped: Engine, country: int, name: str, one: str, other: str
) -> None:
    keep(mapped, country, name, None)

    with refused(ONE_NAME_TWICE):
        keep(mapped, country, name, None)
    with refused(ONE_NAME_TWICE):
        write(mapped, A_REGION, country, name, None)

    assert regions(mapped) == [(1, country, name, None)]


def test_two_regions_that_say_no_code_cannot_have_one_name_beside_a_pair_that_does(
    mapped: Engine,
) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", "MZ-L")
    keep(mapped, MOZAMBIQUE, "Maputo", "MZ-MPM")
    keep(mapped, MOZAMBIQUE, "Maputo", None)

    with refused(ONE_NAME_TWICE):
        keep(mapped, MOZAMBIQUE, "Maputo", None)
    with refused(ONE_NAME_TWICE):
        write(mapped, A_REGION, MOZAMBIQUE, "Maputo", None)

    assert regions(mapped) == [
        (1, MOZAMBIQUE, "Maputo", "MZ-L"),
        (2, MOZAMBIQUE, "Maputo", "MZ-MPM"),
        (3, MOZAMBIQUE, "Maputo", None),
    ]


def test_two_countries_can_each_have_a_region_of_one_name_that_says_no_code(
    mapped: Engine,
) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", None)
    keep(mapped, ESTONIA, "Maputo", None)

    assert regions(mapped) == [(1, MOZAMBIQUE, "Maputo", None), (2, ESTONIA, "Maputo", None)]


def test_a_region_without_a_code_cannot_be_given_the_name_of_another_without_one(
    mapped: Engine,
) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", None)
    other = keep(mapped, MOZAMBIQUE, "Gaza", None)

    with refused(ONE_NAME_TWICE), unit_of_work(mapped) as work:
        work.get_one(Region, other).name = "Maputo"
    with refused(ONE_NAME_TWICE):
        write(mapped, "UPDATE region SET name = 'Maputo' WHERE id = ?", other)

    assert regions(mapped) == [(1, MOZAMBIQUE, "Maputo", None), (2, MOZAMBIQUE, "Gaza", None)]


def test_a_region_without_a_code_cannot_be_moved_to_a_country_that_has_one_of_its_name(
    mapped: Engine,
) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", None)
    other = keep(mapped, ESTONIA, "Maputo", None)

    with refused(ONE_NAME_TWICE):
        write(mapped, "UPDATE region SET country_id = ? WHERE id = ?", MOZAMBIQUE, other)

    assert regions(mapped) == [(1, MOZAMBIQUE, "Maputo", None), (2, ESTONIA, "Maputo", None)]


def test_a_refused_name_leaves_the_region_and_no_history(mapped: Engine) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", None)
    other = keep(mapped, MOZAMBIQUE, "Gaza", None)

    with refused(ONE_NAME_TWICE), unit_of_work(mapped) as work:
        change(work, work.get_one(Region, other), {"name": "Maputo"}, decided_by="Jo Example")

    assert regions(mapped) == [(1, MOZAMBIQUE, "Maputo", None), (2, MOZAMBIQUE, "Gaza", None)]
    with mapped.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM record_change").scalar_one() == 0


def test_the_name_of_a_deleted_region_without_a_code_is_free_again(mapped: Engine) -> None:
    first = keep(mapped, MOZAMBIQUE, "Maputo", None)
    with unit_of_work(mapped) as work:
        work.execute(delete(Region).where(Region.id == first))

    second = keep(mapped, MOZAMBIQUE, "Maputo", None)

    assert regions(mapped) == [(second, MOZAMBIQUE, "Maputo", None)]
    assert second == first + 1


# ------------------------------------------- one that says its code and one that says none


@pytest.mark.parametrize(
    ("first", "second"),
    [("MZ-L", None), (None, "MZ-L")],
    ids=["the one with the code first", "the one without a code first"],
)
def test_a_region_with_a_code_and_one_without_can_have_one_name(
    mapped: Engine, first: str | None, second: str | None
) -> None:
    # Whether the two are one region, named by two sources, the table
    # cannot know. It holds both, each with its source.
    keep(mapped, MOZAMBIQUE, "Maputo", first)
    write(mapped, A_REGION, MOZAMBIQUE, "Maputo", second)

    assert regions(mapped) == [
        (1, MOZAMBIQUE, "Maputo", first),
        (2, MOZAMBIQUE, "Maputo", second),
    ]


def test_a_region_without_a_code_can_be_given_the_name_of_one_with_a_code(
    mapped: Engine,
) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", "MZ-L")
    other = keep(mapped, MOZAMBIQUE, "Lourenco Marques", None)

    with unit_of_work(mapped) as work:
        work.get_one(Region, other).name = "Maputo"

    assert regions(mapped) == [
        (1, MOZAMBIQUE, "Maputo", "MZ-L"),
        (2, MOZAMBIQUE, "Maputo", None),
    ]


# -------------------------------------------------- a code that is given or taken away


def test_a_region_cannot_lose_its_code_beside_one_of_its_name_that_says_none(
    mapped: Engine,
) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", None)
    province = keep(mapped, MOZAMBIQUE, "Maputo", "MZ-L")

    with refused(ONE_NAME_TWICE), unit_of_work(mapped) as work:
        work.get_one(Region, province).iso_3166_2 = None
    with refused(ONE_NAME_TWICE):
        write(mapped, "UPDATE region SET iso_3166_2 = NULL WHERE id = ?", province)

    assert regions(mapped) == [
        (1, MOZAMBIQUE, "Maputo", None),
        (2, MOZAMBIQUE, "Maputo", "MZ-L"),
    ]


def test_a_region_can_lose_its_code_beside_one_of_its_name_that_says_its_own(
    mapped: Engine,
) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", "MZ-L")
    city = keep(mapped, MOZAMBIQUE, "Maputo", "MZ-MPM")

    with unit_of_work(mapped) as work:
        work.get_one(Region, city).iso_3166_2 = None

    assert regions(mapped) == [
        (1, MOZAMBIQUE, "Maputo", "MZ-L"),
        (2, MOZAMBIQUE, "Maputo", None),
    ]
    # And then the other cannot lose its own.
    with refused(ONE_NAME_TWICE):
        write(mapped, "UPDATE region SET iso_3166_2 = NULL WHERE id = 1")
    assert regions(mapped)[0] == (1, MOZAMBIQUE, "Maputo", "MZ-L")


def test_a_region_that_is_given_its_code_leaves_its_name_free_for_one_without(
    mapped: Engine,
) -> None:
    first = keep(mapped, MOZAMBIQUE, "Maputo", None)
    with refused(ONE_NAME_TWICE):
        keep(mapped, MOZAMBIQUE, "Maputo", None)

    with unit_of_work(mapped) as work:
        work.get_one(Region, first).iso_3166_2 = "MZ-L"
    second = keep(mapped, MOZAMBIQUE, "Maputo", None)

    assert regions(mapped) == [
        (first, MOZAMBIQUE, "Maputo", "MZ-L"),
        (second, MOZAMBIQUE, "Maputo", None),
    ]


def test_one_statement_cannot_take_the_codes_of_both_regions_of_a_pair_away(
    mapped: Engine,
) -> None:
    keep(mapped, MOZAMBIQUE, "Maputo", "MZ-L")
    keep(mapped, MOZAMBIQUE, "Maputo", "MZ-MPM")

    with refused(ONE_NAME_TWICE):
        write(mapped, "UPDATE region SET iso_3166_2 = NULL WHERE name = 'Maputo'")

    # The statement is taken back whole: the first region has its code too.
    assert regions(mapped) == [
        (1, MOZAMBIQUE, "Maputo", "MZ-L"),
        (2, MOZAMBIQUE, "Maputo", "MZ-MPM"),
    ]


# ----------------------------------------------------- how the store holds the rule


def test_the_rule_is_an_index_over_the_regions_without_a_code_that_are_parts_of_none(
    mapped: Engine,
) -> None:
    with mapped.connect() as connection:
        written = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE name = 'ix_region_country_id_name'"
        ).scalar_one()
        index = connection.exec_driver_sql("PRAGMA index_info(ix_region_country_id_name)").all()
        the_table = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE name = 'region'"
        ).scalar_one()

    # Among the parts of one region the rule is an index of its own
    # (DAT-069; test_region_part_name.py).
    assert written == (
        "CREATE UNIQUE INDEX ix_region_country_id_name ON region (country_id, name) "
        "WHERE iso_3166_2 IS NULL AND parent_id IS NULL"
    )
    assert [name for _, _, name in index] == ["country_id", "name"]
    # The table itself has the rule of the codes and none of the names.
    # Its other rule of that kind is over a key and a country together,
    # for the region a region is a part of (DAT-065).
    assert "UNIQUE (iso_3166_2)" in str(the_table)
    assert "UNIQUE (id, country_id)" in str(the_table)
    assert str(the_table).count("UNIQUE") == 2


def test_a_region_without_a_code_is_found_by_its_name_with_the_index_of_the_rule(
    mapped: Engine,
) -> None:
    asked = (
        "EXPLAIN QUERY PLAN SELECT * FROM region "
        "WHERE country_id = 1 AND name = 'Maputo' AND iso_3166_2 IS NULL AND parent_id IS NULL"
    )
    with mapped.connect() as connection:
        plan = [str(row[3]) for row in connection.exec_driver_sql(asked)]

    assert plan == ["SEARCH region USING INDEX ix_region_country_id_name (country_id=? AND name=?)"]


def test_a_statement_that_stores_a_region_or_does_nothing_names_the_regions_of_the_rule(
    mapped: Engine,
) -> None:
    # Whoever stores a region where none of its name is there, and
    # otherwise does nothing, has to say which regions the rule is over:
    # SQLite takes the statement for the index only when it does. Since
    # DAT-069 those are the regions without a code that are parts of
    # none, and what named them before names no rule any more.
    keep(mapped, MOZAMBIQUE, "Maputo", None)
    or_nothing = A_REGION + " ON CONFLICT (country_id, name) {}DO NOTHING"
    of_the_rule = "WHERE iso_3166_2 IS NULL AND parent_id IS NULL "

    write(mapped, or_nothing.format(of_the_rule), MOZAMBIQUE, "Maputo", None)
    write(mapped, or_nothing.format(of_the_rule), MOZAMBIQUE, "Gaza", None)
    for named in ("", "WHERE iso_3166_2 IS NULL "):
        with pytest.raises(OperationalError) as refusal:
            write(mapped, or_nothing.format(named), MOZAMBIQUE, "Tete", None)
        assert str(refusal.value.orig) == (
            "ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint"
        )
    # The statement that did nothing was given the key 2 before it was
    # found to be one too many, and a key is not given twice.
    assert regions(mapped) == [(1, MOZAMBIQUE, "Maputo", None), (3, MOZAMBIQUE, "Gaza", None)]
