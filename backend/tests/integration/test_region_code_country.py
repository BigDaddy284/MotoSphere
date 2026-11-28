"""Tests that the code of a region agrees with its country, against a real SQLite file.

The code of ISO 3166-2 of a region begins with the code of two letters of
its country: "NZ-CAN" is a region of New Zealand, "NZ". The letters of a
country are a column of another table, so the store holds the two
together with triggers, on the regions and on the countries.

The store of every test is built the way a real store is built: by the
migrations. What must be refused is written through the model and past
it, and each refusal is held to the sentence SQLite gives.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, delete, select
from sqlalchemy.exc import IntegrityError

from motosphere.db.base import Base
from motosphere.db.changes import change
from motosphere.db.history import MIGRATIONS
from motosphere.db.migrations import migrate, schema_version
from motosphere.db.models import Country, Region, Source
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 27, 9, 0, tzinfo=UTC)
# The four countries of the tests, by their keys.
NEW_ZEALAND = 1
AUSTRALIA = 2
AUSTRIA = 3
FRANCE = 4
OF_ITS_COUNTRY = "The code of a region (region) begins with the code of its country (country)."
OF_ITS_REGIONS = "The codes of the regions of a country (region) begin with its code (country)."
ONE_NAME_TWICE = "UNIQUE constraint failed: region.country_id, region.name"
# A region as plain SQL, what follows INSERT INTO: its key, its country,
# its name and its code are given.
A_REGION = (
    "region (id, country_id, name, iso_3166_2, source_id, source_address, collected_at, "
    "last_verified_at, extraction_method, confidence, verification_status, created_at, "
    "updated_at) VALUES (?, ?, ?, ?, 1, 'https://standards.example/regions.csv', "
    "'2026-11-27T09:00:00.000000+00:00', '2026-11-27T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-27T09:00:05.000000+00:00', '2026-11-27T09:00:05.000000+00:00')"
)
# A country as plain SQL, what follows INSERT INTO: its key, its two codes
# and its name are given.
A_COUNTRY = (
    "country (id, alpha_2, alpha_3, name, source_id, source_address, collected_at, "
    "last_verified_at, extraction_method, confidence, verification_status, created_at, "
    "updated_at) VALUES (?, ?, ?, ?, 1, 'https://standards.example/countries.csv', "
    "'2026-11-27T09:00:00.000000+00:00', '2026-11-27T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-27T09:00:05.000000+00:00', '2026-11-27T09:00:05.000000+00:00')"
)
COUNTRIES = [
    (NEW_ZEALAND, "NZ", "NZL", "New Zealand"),
    (AUSTRALIA, "AU", "AUS", "Australia"),
    (AUSTRIA, "AT", "AUT", "Austria"),
    (FRANCE, "FR", "FRA", "France"),
]
# Regions of the standard, each with its country and its own code.
OF_THE_STANDARD = [
    (NEW_ZEALAND, "Canterbury", "NZ-CAN"),
    (AUSTRALIA, "New South Wales", "AU-NSW"),
    (AUSTRIA, "Burgenland", "AT-1"),
    (FRANCE, "Paris", "FR-75C"),
]
# A country, a name and a code whose letters are not those of the country:
# of another country of the store, of a country the store does not have,
# and of the country but for one letter.
OF_ANOTHER_COUNTRY = [
    (NEW_ZEALAND, "Styria", "AT-6"),
    (NEW_ZEALAND, "Victoria", "AU-VIC"),
    (AUSTRIA, "Otago", "NZ-OTA"),
    (AUSTRALIA, "Styria", "AT-6"),
    (FRANCE, "Lower Saxony", "DE-NI"),
    (NEW_ZEALAND, "Example Region", "NA-CA"),
    (AUSTRALIA, "Example Region", "AT-NSW"),
    (AUSTRIA, "Example Region", "IT-25"),
]
SAID_OF_ANOTHER_COUNTRY = [
    "Austria's in New Zealand",
    "Australia's in New Zealand",
    "New Zealand's in Austria",
    "Austria's in Australia",
    "of a country that is not in the store",
    "the first letter alone agrees",
    "the first letter alone agrees, the second is of another country",
    "the second letter alone agrees",
]


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def fill(store: Engine) -> None:
    """Give a store one source and the four countries, with the keys 1 to 4."""
    with unit_of_work(store) as work:
        work.add(
            Source(
                name="Example Standards Body",
                website="https://standards.example",
                category=SourceCategory.GOVERNING_BODY,
                collection_method=CollectionMethod.DATASET,
            )
        )
    for _, two, three, name in COUNTRIES:
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


@pytest.fixture
def mapped(newest: Engine) -> Engine:
    """The test's own store with the newest schema, one source and four countries in it.

    The key of the source is 1. The keys of the countries are 1 to 4: New
    Zealand, Australia, Austria and France.
    """
    fill(newest)
    return newest


def a_region(**said: Any) -> Region:
    """Canterbury in New Zealand as the one source of the tests says it, and what the test says."""
    described: dict[str, Any] = {
        "country_id": NEW_ZEALAND,
        "name": "Canterbury",
        "source_id": 1,
        "source_address": "https://standards.example/regions.csv",
        "collected_at": COLLECTED,
        "last_verified_at": COLLECTED,
        "extraction_method": CollectionMethod.DATASET,
        "confidence": Confidence.HIGH,
        "verification_status": VerificationStatus.OFFICIAL,
    }
    return Region(**(described | said))


def keep(store: Engine, region: Region) -> int:
    """Store a region in a unit of work of its own, and give its key."""
    with unit_of_work(store) as work:
        work.add(region)
    return region.id


def write(store: Engine, statement: str, *given: object) -> None:
    """Write one statement past the model, as plain SQL, in a transaction of its own."""
    with store.begin() as connection:
        connection.exec_driver_sql(statement, given)


def regions(store: Engine) -> list[tuple[object, ...]]:
    """Every region as SQLite holds it: its key, its country, its name and its code, by the key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT id, country_id, name, iso_3166_2 FROM region ORDER BY id"
        )
        return [tuple(row) for row in found]


def everything(store: Engine) -> dict[str, list[tuple[object, ...]]]:
    """Every row of the regions and of the countries with every column, each table by its key."""
    with store.connect() as connection:
        return {
            table: [tuple(row) for row in connection.exec_driver_sql(asked)]
            for table, asked in {
                "region": "SELECT * FROM region ORDER BY id",
                "country": "SELECT * FROM country ORDER BY id",
            }.items()
        }


def countries(store: Engine) -> list[tuple[object, ...]]:
    """Every country as SQLite holds it: its key, its two codes and its name, by the key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT id, alpha_2, alpha_3, name FROM country ORDER BY id"
        )
        return [tuple(row) for row in found]


def history(store: Engine) -> list[tuple[object, ...]]:
    """What the history holds: the record, the field, and what it held and holds."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT record_table, record_id, field, old_value, new_value FROM record_change "
            "ORDER BY id"
        )
        return [tuple(row) for row in found]


def the_standard(store: Engine) -> list[tuple[object, ...]]:
    """Store the four regions of the standard with the keys 1 to 4, and give them as stored."""
    for key, (country, name, code) in enumerate(OF_THE_STANDARD, start=1):
        write(store, f"INSERT INTO {A_REGION}", key, country, name, code)
    return regions(store)


# ---------------------------------------------------------------- a new region


@pytest.mark.parametrize(
    ("country", "name", "code"), OF_THE_STANDARD, ids=[code for _, _, code in OF_THE_STANDARD]
)
def test_a_region_whose_code_begins_with_the_code_of_its_country_is_stored(
    mapped: Engine, country: int, name: str, code: str
) -> None:
    key = keep(mapped, a_region(country_id=country, name=name, iso_3166_2=code))

    assert regions(mapped) == [(key, country, name, code)]


@pytest.mark.parametrize(
    ("country", "name", "code"), OF_ANOTHER_COUNTRY, ids=SAID_OF_ANOTHER_COUNTRY
)
def test_a_region_whose_code_begins_with_other_letters_is_refused(
    mapped: Engine, country: int, name: str, code: str
) -> None:
    with refused(OF_ITS_COUNTRY):
        keep(mapped, a_region(country_id=country, name=name, iso_3166_2=code))

    assert regions(mapped) == []


NEW = [
    f"INSERT INTO {A_REGION}",
    f"INSERT OR REPLACE INTO {A_REGION}",
    f"INSERT OR IGNORE INTO {A_REGION}",
    f"INSERT OR FAIL INTO {A_REGION}",
]
NEW_SAID = ["plainly", "to take the place of what it clashes with", "to be passed over", "to fail"]


@pytest.mark.parametrize("statement", NEW, ids=NEW_SAID)
@pytest.mark.parametrize(
    ("country", "name", "code"), OF_ANOTHER_COUNTRY, ids=SAID_OF_ANOTHER_COUNTRY
)
def test_such_a_region_is_refused_past_the_model_whatever_the_statement_says_of_a_clash(
    mapped: Engine, statement: str, country: int, name: str, code: str
) -> None:
    before = the_standard(mapped)

    with refused(OF_ITS_COUNTRY):
        write(mapped, statement, 9, country, name, code)

    assert regions(mapped) == before


@pytest.mark.parametrize("statement", NEW, ids=NEW_SAID)
def test_a_region_of_its_country_is_stored_past_the_model_by_each_of_these_statements(
    mapped: Engine, statement: str
) -> None:
    write(mapped, statement, 9, NEW_ZEALAND, "Otago", "NZ-OTA")

    assert regions(mapped) == [(9, NEW_ZEALAND, "Otago", "NZ-OTA")]


def test_a_region_that_takes_the_place_of_another_is_held_to_its_country_too(
    mapped: Engine,
) -> None:
    # The region with the key 1 is Canterbury. A statement that says
    # REPLACE takes it out for a new region with its key; the new one is
    # asked about like any other.
    before = the_standard(mapped)

    with refused(OF_ITS_COUNTRY):
        write(mapped, f"INSERT OR REPLACE INTO {A_REGION}", 1, NEW_ZEALAND, "Otago", "AU-OTA")
    assert regions(mapped) == before

    write(mapped, f"INSERT OR REPLACE INTO {A_REGION}", 1, NEW_ZEALAND, "Otago", "NZ-OTA")
    assert regions(mapped)[0] == (1, NEW_ZEALAND, "Otago", "NZ-OTA")


@pytest.mark.parametrize("country", [NEW_ZEALAND, AUSTRALIA, AUSTRIA, FRANCE])
def test_a_region_without_a_code_is_a_part_of_any_country(mapped: Engine, country: int) -> None:
    key = keep(mapped, a_region(country_id=country, name="Example Region"))
    write(mapped, f"INSERT INTO {A_REGION}", 9, country, "Example District", None)

    assert regions(mapped) == [
        (key, country, "Example Region", None),
        (9, country, "Example District", None),
    ]


def test_of_several_regions_stored_by_one_statement_one_of_another_country_stops_them_all(
    mapped: Engine,
) -> None:
    several = (
        "INSERT INTO region (country_id, name, iso_3166_2, source_id, source_address, "
        "collected_at, last_verified_at, extraction_method, confidence, verification_status, "
        "created_at, updated_at) SELECT said.column1, said.column2, said.column3, 1, "
        "'https://standards.example/regions.csv', '2026-11-27T09:00:00.000000+00:00', "
        "'2026-11-27T09:00:00.000000+00:00', 'public dataset', 'high', 'official', "
        "'2026-11-27T09:00:05.000000+00:00', '2026-11-27T09:00:05.000000+00:00' "
        "FROM (VALUES (1, 'Canterbury', 'NZ-CAN'), (1, 'Otago', ?), (2, 'Victoria', 'AU-VIC')) "
        "AS said"
    )

    with refused(OF_ITS_COUNTRY):
        write(mapped, several, "AU-OTA")
    assert regions(mapped) == []

    write(mapped, several, "NZ-OTA")
    assert [region[1:] for region in regions(mapped)] == [
        (NEW_ZEALAND, "Canterbury", "NZ-CAN"),
        (NEW_ZEALAND, "Otago", "NZ-OTA"),
        (AUSTRALIA, "Victoria", "AU-VIC"),
    ]


def test_the_form_of_a_code_and_the_rule_of_one_code_speak_before_the_country(
    mapped: Engine,
) -> None:
    # The triggers ask after the row is written, so what the table itself
    # refuses is refused first, with the table's own words.
    the_standard(mapped)

    with refused("CHECK constraint failed: ck_region_iso_3166_2_form"):
        write(mapped, f"INSERT INTO {A_REGION}", 9, NEW_ZEALAND, "Otago", "at-1")
    with refused("UNIQUE constraint failed: region.iso_3166_2"):
        write(mapped, f"INSERT INTO {A_REGION}", 9, NEW_ZEALAND, "Otago", "AT-1")
    with refused("CHECK constraint failed: ck_region_iso_3166_2_form"):
        write(mapped, "UPDATE region SET iso_3166_2 = 'at-1' WHERE id = 1")
    with refused("UNIQUE constraint failed: region.iso_3166_2"):
        write(mapped, "UPDATE region SET iso_3166_2 = 'AT-1' WHERE id = 1")
    with refused("UNIQUE constraint failed: country.alpha_2"):
        write(mapped, "UPDATE country SET alpha_2 = 'AT' WHERE id = 1")


# ------------------------------------------------- a region that is given a code

GIVEN_A_CODE = [
    "UPDATE region SET iso_3166_2 = ? WHERE id = ?",
    "UPDATE OR REPLACE region SET iso_3166_2 = ? WHERE id = ?",
    "UPDATE OR IGNORE region SET iso_3166_2 = ? WHERE id = ?",
    "UPDATE OR FAIL region SET iso_3166_2 = ? WHERE id = ?",
    "UPDATE region SET name = 'Example Region', iso_3166_2 = ? WHERE id = ?",
    "UPDATE region SET iso_3166_2 = ?, last_verified_at = '2026-11-28T09:00:00.000000+00:00', "
    "updated_at = '2026-11-28T09:00:05.000000+00:00' WHERE id = ?",
    "UPDATE region SET iso_3166_2 = said.code FROM (SELECT ? AS code) AS said WHERE region.id = ?",
]
GIVEN_A_CODE_SAID = [
    "plainly",
    "to take the place of what it clashes with",
    "to be passed over",
    "to fail",
    "with another name",
    "with the day it was seen again",
    "from a query",
]


@pytest.mark.parametrize("statement", GIVEN_A_CODE, ids=GIVEN_A_CODE_SAID)
@pytest.mark.parametrize("had", ["NZ-OTA", None], ids=["had a code", "had none"])
@pytest.mark.parametrize("code", ["AT-1", "AU-OTA", "NA-OTA", "TZ-OTA"])
def test_a_region_is_not_given_a_code_that_begins_with_other_letters(
    mapped: Engine, statement: str, had: str | None, code: str
) -> None:
    the_standard(mapped)
    write(mapped, f"INSERT INTO {A_REGION}", 9, NEW_ZEALAND, "Otago", had)
    write(mapped, "DELETE FROM region WHERE id = 3")
    before = everything(mapped)

    with refused(OF_ITS_COUNTRY):
        write(mapped, statement, code, 9)

    assert everything(mapped) == before


@pytest.mark.parametrize("statement", GIVEN_A_CODE, ids=GIVEN_A_CODE_SAID)
@pytest.mark.parametrize("had", ["NZ-OTA", None], ids=["had a code", "had none"])
@pytest.mark.parametrize("code", ["NZ-STL", None], ids=["a code of its country", "none"])
def test_a_region_is_given_a_code_of_its_country_or_none(
    mapped: Engine, statement: str, had: str | None, code: str | None
) -> None:
    write(mapped, f"INSERT INTO {A_REGION}", 9, NEW_ZEALAND, "Otago", had)

    write(mapped, statement, code, 9)

    assert [(key, country, held) for key, country, _, held in regions(mapped)] == [
        (9, NEW_ZEALAND, code)
    ]


def test_a_region_that_is_stored_again_is_not_given_such_a_code_in_the_same_statement(
    mapped: Engine,
) -> None:
    # A statement that stores a region and says what is to be done where
    # its key is there already changes the region that is there.
    again = (
        f"INSERT INTO {A_REGION} ON CONFLICT (id) DO UPDATE SET iso_3166_2 = excluded.iso_3166_2"
    )
    before = the_standard(mapped)

    with refused(OF_ITS_COUNTRY):
        write(mapped, again, 1, NEW_ZEALAND, "Canterbury", "AU-CAN")
    assert regions(mapped) == before

    write(mapped, again, 1, NEW_ZEALAND, "Canterbury", "NZ-CNT")
    assert regions(mapped)[0] == (1, NEW_ZEALAND, "Canterbury", "NZ-CNT")


def test_of_several_regions_changed_by_one_statement_one_wrong_code_stops_them_all(
    mapped: Engine,
) -> None:
    before = the_standard(mapped)

    with refused(OF_ITS_COUNTRY):
        write(mapped, "UPDATE region SET iso_3166_2 = 'NZ-' || id")

    assert regions(mapped) == before


def test_through_the_stores_code_a_wrong_code_leaves_the_region_and_no_history(
    mapped: Engine,
) -> None:
    key = keep(mapped, a_region(name="Otago", iso_3166_2="NZ-OTA"))

    with refused(OF_ITS_COUNTRY), unit_of_work(mapped) as work:
        change(work, work.get_one(Region, key), {"iso_3166_2": "AU-OTA"}, decided_by="Jo Example")

    assert regions(mapped) == [(key, NEW_ZEALAND, "Otago", "NZ-OTA")]
    assert history(mapped) == []


def test_through_the_stores_code_a_code_of_its_country_is_given_with_its_history(
    mapped: Engine,
) -> None:
    key = keep(mapped, a_region(name="Otago"))

    for code in ("NZ-OTA", "NZ-OTG", None):
        with unit_of_work(mapped) as work:
            change(work, work.get_one(Region, key), {"iso_3166_2": code}, decided_by="Jo Example")

    assert regions(mapped) == [(key, NEW_ZEALAND, "Otago", None)]
    assert history(mapped) == [
        ("region", key, "iso_3166_2", None, "NZ-OTA"),
        ("region", key, "iso_3166_2", "NZ-OTA", "NZ-OTG"),
        ("region", key, "iso_3166_2", "NZ-OTG", None),
    ]


# --------------------------------------- a region that is moved to another country

MOVED = [
    "UPDATE region SET country_id = ? WHERE id = ?",
    "UPDATE OR REPLACE region SET country_id = ? WHERE id = ?",
    "UPDATE OR IGNORE region SET country_id = ? WHERE id = ?",
    "UPDATE region SET name = 'Example Region', country_id = ? WHERE id = ?",
    "UPDATE region SET country_id = said.country FROM (SELECT ? AS country) AS said "
    "WHERE region.id = ?",
]
MOVED_SAID = [
    "plainly",
    "to take the place of what it clashes with",
    "to be passed over",
    "with another name",
    "from a query",
]


@pytest.mark.parametrize("statement", MOVED, ids=MOVED_SAID)
@pytest.mark.parametrize("to", [AUSTRALIA, AUSTRIA, FRANCE])
def test_a_region_with_a_code_is_not_moved_to_another_country(
    mapped: Engine, statement: str, to: int
) -> None:
    the_standard(mapped)
    before = everything(mapped)

    with refused(OF_ITS_COUNTRY):
        write(mapped, statement, to, 1)

    assert everything(mapped) == before


@pytest.mark.parametrize("statement", MOVED, ids=MOVED_SAID)
def test_a_region_without_a_code_is_moved_to_another_country(
    mapped: Engine, statement: str
) -> None:
    write(mapped, f"INSERT INTO {A_REGION}", 9, NEW_ZEALAND, "Otago", None)

    write(mapped, statement, AUSTRIA, 9)

    assert [(key, country, code) for key, country, _, code in regions(mapped)] == [
        (9, AUSTRIA, None)
    ]


@pytest.mark.parametrize(
    ("statement", "code"),
    [
        ("UPDATE region SET country_id = 3, iso_3166_2 = 'AT-9' WHERE id = 1", "AT-9"),
        ("UPDATE region SET iso_3166_2 = 'AT-9', country_id = 3 WHERE id = 1", "AT-9"),
        ("UPDATE region SET country_id = 3, iso_3166_2 = NULL WHERE id = 1", None),
    ],
    ids=["the country first", "the code first", "and its code taken away"],
)
def test_a_region_is_moved_together_with_its_code(
    mapped: Engine, statement: str, code: str | None
) -> None:
    the_standard(mapped)

    write(mapped, statement)

    assert regions(mapped) == [
        (1, AUSTRIA, "Canterbury", code),
        (2, AUSTRALIA, "New South Wales", "AU-NSW"),
        (3, AUSTRIA, "Burgenland", "AT-1"),
        (4, FRANCE, "Paris", "FR-75C"),
    ]


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE region SET country_id = 3, iso_3166_2 = 'AU-9' WHERE id = 1",
        "UPDATE region SET iso_3166_2 = 'AT-9', country_id = 2 WHERE id = 1",
        "UPDATE region SET country_id = 3, iso_3166_2 = 'NZ-CNT' WHERE id = 1",
    ],
    ids=[
        "to one country with the code of another",
        "the same, the code first",
        "with a new code of the old country",
    ],
)
def test_a_region_is_not_moved_with_a_code_that_is_not_of_the_new_country(
    mapped: Engine, statement: str
) -> None:
    before = the_standard(mapped)

    with refused(OF_ITS_COUNTRY):
        write(mapped, statement)

    assert regions(mapped) == before


def test_through_the_model_a_region_with_a_code_is_not_moved_and_one_without_is(
    mapped: Engine,
) -> None:
    coded = keep(mapped, a_region(iso_3166_2="NZ-CAN"))
    plain = keep(mapped, a_region(name="Otago"))

    with refused(OF_ITS_COUNTRY), unit_of_work(mapped) as work:
        work.get_one(Region, coded).country_id = AUSTRALIA
    with unit_of_work(mapped) as work:
        work.get_one(Region, plain).country_id = AUSTRALIA

    assert regions(mapped) == [
        (coded, NEW_ZEALAND, "Canterbury", "NZ-CAN"),
        (plain, AUSTRALIA, "Otago", None),
    ]


def test_all_the_regions_of_one_country_are_not_moved_to_another_by_one_statement(
    mapped: Engine,
) -> None:
    the_standard(mapped)
    write(mapped, f"INSERT INTO {A_REGION}", 9, NEW_ZEALAND, "Otago", None)
    before = regions(mapped)

    with refused(OF_ITS_COUNTRY):
        write(mapped, "UPDATE region SET country_id = 4 WHERE country_id = 1")

    assert regions(mapped) == before


THE_OTHER_THREE: list[tuple[object, ...]] = [
    (2, AUSTRALIA, "New South Wales", "AU-NSW"),
    (3, AUSTRIA, "Burgenland", "AT-1"),
    (4, FRANCE, "Paris", "FR-75C"),
]


@pytest.mark.parametrize(
    ("statement", "then"),
    [
        (
            "UPDATE region SET name = 'Waitaha' WHERE id = 1",
            [(1, NEW_ZEALAND, "Waitaha", "NZ-CAN"), *THE_OTHER_THREE],
        ),
        (
            "UPDATE region SET last_verified_at = '2026-11-28T09:00:00.000000+00:00', "
            "updated_at = '2026-11-28T09:00:05.000000+00:00' WHERE id = 1",
            [(1, NEW_ZEALAND, "Canterbury", "NZ-CAN"), *THE_OTHER_THREE],
        ),
        (
            "UPDATE region SET rowid = 50 WHERE id = 1",
            [*THE_OTHER_THREE, (50, NEW_ZEALAND, "Canterbury", "NZ-CAN")],
        ),
        (
            "UPDATE region SET iso_3166_2 = iso_3166_2, country_id = country_id",
            [(1, NEW_ZEALAND, "Canterbury", "NZ-CAN"), *THE_OTHER_THREE],
        ),
        ("DELETE FROM region WHERE id = 1", THE_OTHER_THREE),
    ],
    ids=["another name", "seen again", "another key", "the same code and country", "deleted"],
)
def test_a_region_whose_code_is_of_its_country_is_changed_in_every_other_way(
    mapped: Engine, statement: str, then: list[tuple[object, ...]]
) -> None:
    the_standard(mapped)

    write(mapped, statement)

    assert regions(mapped) == then


# ------------------------------------------------- a country that is changed

OTHER_LETTERS = [
    "UPDATE country SET alpha_2 = ? WHERE id = ?",
    "UPDATE OR REPLACE country SET alpha_2 = ? WHERE id = ?",
    "UPDATE OR IGNORE country SET alpha_2 = ? WHERE id = ?",
    "UPDATE country SET name = 'Example Country', alpha_2 = ? WHERE id = ?",
    "UPDATE country SET alpha_2 = said.code FROM (SELECT ? AS code) AS said WHERE country.id = ?",
]
OTHER_LETTERS_SAID = [
    "plainly",
    "to take the place of what it clashes with",
    "to be passed over",
    "with another name",
    "from a query",
]


@pytest.mark.parametrize("statement", OTHER_LETTERS, ids=OTHER_LETTERS_SAID)
@pytest.mark.parametrize("letters", ["NX", "ZN", "DE", "TZ"])
def test_a_country_whose_regions_have_codes_is_not_given_other_letters(
    mapped: Engine, statement: str, letters: str
) -> None:
    the_standard(mapped)
    before = everything(mapped)

    with refused(OF_ITS_REGIONS):
        write(mapped, statement, letters, NEW_ZEALAND)

    assert everything(mapped) == before


@pytest.mark.parametrize("statement", OTHER_LETTERS, ids=OTHER_LETTERS_SAID)
@pytest.mark.parametrize(
    "its_regions", [[], [None], [None, None]], ids=["no regions", "one region", "two regions"]
)
def test_a_country_whose_regions_have_no_codes_is_given_other_letters(
    mapped: Engine, statement: str, its_regions: list[None]
) -> None:
    the_standard(mapped)
    write(mapped, "DELETE FROM region WHERE id = 1")
    for number, code in enumerate(its_regions):
        write(mapped, f"INSERT INTO {A_REGION}", 20 + number, NEW_ZEALAND, f"Region {number}", code)

    write(mapped, statement, "NX", NEW_ZEALAND)

    assert countries(mapped)[0][:2] == (NEW_ZEALAND, "NX")


def test_one_region_with_a_code_among_many_without_holds_the_letters_of_its_country(
    mapped: Engine,
) -> None:
    for number in range(5):
        write(mapped, f"INSERT INTO {A_REGION}", 20 + number, NEW_ZEALAND, f"Region {number}", None)
    write(mapped, f"INSERT INTO {A_REGION}", 30, NEW_ZEALAND, "Otago", "NZ-OTA")
    before = countries(mapped)

    with refused(OF_ITS_REGIONS):
        write(mapped, "UPDATE country SET alpha_2 = 'NX' WHERE id = 1")
    assert countries(mapped) == before

    # Once the region has no code, or is gone, the country is given them.
    write(mapped, "UPDATE region SET iso_3166_2 = NULL WHERE id = 30")
    write(mapped, "UPDATE country SET alpha_2 = 'NX' WHERE id = 1")
    assert countries(mapped)[0][:2] == (NEW_ZEALAND, "NX")


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE country SET name = 'Aotearoa New Zealand' WHERE id = 1",
        "UPDATE country SET alpha_3 = 'NZX' WHERE id = 1",
        "UPDATE country SET last_verified_at = '2026-11-28T09:00:00.000000+00:00', "
        "updated_at = '2026-11-28T09:00:05.000000+00:00'",
        "UPDATE country SET alpha_2 = alpha_2",
    ],
    ids=["another name", "another code of three letters", "seen again", "the same letters"],
)
def test_a_country_whose_regions_have_codes_is_changed_in_every_other_way(
    mapped: Engine, statement: str
) -> None:
    before = the_standard(mapped)

    write(mapped, statement)

    assert regions(mapped) == before
    assert [country[1] for country in countries(mapped)] == ["NZ", "AU", "AT", "FR"]


def test_through_the_model_a_country_is_not_given_other_letters_than_its_regions_have(
    mapped: Engine,
) -> None:
    keep(mapped, a_region(iso_3166_2="NZ-CAN"))

    with refused(OF_ITS_REGIONS), unit_of_work(mapped) as work:
        work.get_one(Country, NEW_ZEALAND).alpha_2 = "NX"
    with unit_of_work(mapped) as work:
        work.get_one(Country, AUSTRALIA).alpha_2 = "AX"

    assert [country[:2] for country in countries(mapped)] == [
        (NEW_ZEALAND, "NZ"),
        (AUSTRALIA, "AX"),
        (AUSTRIA, "AT"),
        (FRANCE, "FR"),
    ]


@pytest.mark.parametrize("letters", ["NX", "TZ", "DE"])
def test_a_country_that_takes_the_place_of_another_is_held_to_the_regions_it_gets(
    mapped: Engine, letters: str
) -> None:
    # A statement that says REPLACE takes the country with the key out for
    # a new one of that key, and the regions of the old are the regions
    # of the new. SQLite fires no trigger for the row it takes out.
    kept = the_standard(mapped)
    before = everything(mapped)

    with refused(OF_ITS_REGIONS):
        write(mapped, f"INSERT OR REPLACE INTO {A_COUNTRY}", NEW_ZEALAND, letters, "NZL", "Example")
    assert everything(mapped) == before

    write(mapped, f"INSERT OR REPLACE INTO {A_COUNTRY}", NEW_ZEALAND, "NZ", "NZL", "Aotearoa")
    assert countries(mapped)[0] == (NEW_ZEALAND, "NZ", "NZL", "Aotearoa")
    assert regions(mapped) == kept


@pytest.mark.parametrize(
    "its_regions", [[], [None], [None, None]], ids=["no regions", "one region", "two regions"]
)
def test_a_country_that_takes_the_place_of_one_whose_regions_have_no_codes_has_any_letters(
    mapped: Engine, its_regions: list[None]
) -> None:
    the_standard(mapped)
    write(mapped, "DELETE FROM region WHERE id = 1")
    for number, code in enumerate(its_regions):
        write(mapped, f"INSERT INTO {A_REGION}", 20 + number, NEW_ZEALAND, f"Region {number}", code)
    kept = regions(mapped)

    write(mapped, f"INSERT OR REPLACE INTO {A_COUNTRY}", NEW_ZEALAND, "NX", "NZL", "Example")

    assert countries(mapped)[0] == (NEW_ZEALAND, "NX", "NZL", "Example")
    assert regions(mapped) == kept


def test_a_new_country_is_stored_whatever_its_letters(mapped: Engine) -> None:
    the_standard(mapped)

    write(mapped, f"INSERT INTO {A_COUNTRY}", 9, "DE", "DEU", "Germany")
    keep(mapped, a_region(country_id=9, name="Lower Saxony", iso_3166_2="DE-NI"))

    assert countries(mapped)[-1] == (9, "DE", "DEU", "Germany")
    assert regions(mapped)[-1][1:] == (9, "Lower Saxony", "DE-NI")


def test_two_countries_do_not_change_letters_with_each_other_while_their_regions_have_codes(
    mapped: Engine,
) -> None:
    the_standard(mapped)
    before = everything(mapped)

    # The letters of one have to go out of the way first, and cannot.
    with refused("UNIQUE constraint failed: country.alpha_2"):
        write(mapped, "UPDATE country SET alpha_2 = 'NZ' WHERE id = 2")
    with refused(OF_ITS_REGIONS):
        write(mapped, "UPDATE country SET alpha_2 = 'XX' WHERE id = 1")
    with refused(OF_ITS_REGIONS):
        write(mapped, "UPDATE country SET alpha_2 = 'XX' WHERE id = 2")

    assert everything(mapped) == before


# ------------------------------------------------------ what a refusal does


def test_a_refusal_stops_the_statement_and_not_the_work_before_it(mapped: Engine) -> None:
    the_standard(mapped)

    with mapped.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET name = 'Waitaha' WHERE id = 1")
        with pytest.raises(IntegrityError) as refusal:
            connection.exec_driver_sql(
                "UPDATE region SET name = 'Example Region', country_id = 2 WHERE id IN (1, 4)"
            )
        assert str(refusal.value.orig) == OF_ITS_COUNTRY
        with pytest.raises(IntegrityError) as refusal:
            connection.exec_driver_sql("UPDATE country SET name = 'Example', alpha_2 = 'NX'")
        assert str(refusal.value.orig) == OF_ITS_REGIONS
        with pytest.raises(IntegrityError) as refusal:
            connection.exec_driver_sql(
                f"INSERT INTO {A_REGION}", (9, NEW_ZEALAND, "Otago", "AU-OTA")
            )
        assert str(refusal.value.orig) == OF_ITS_COUNTRY
        with pytest.raises(IntegrityError) as refusal:
            connection.exec_driver_sql(
                f"INSERT OR REPLACE INTO {A_COUNTRY}", (FRANCE, "FX", "FRA", "France")
            )
        assert str(refusal.value.orig) == OF_ITS_REGIONS
        connection.exec_driver_sql("UPDATE region SET name = 'Wien' WHERE id = 3")

    assert [(key, name) for key, _, name, _ in regions(mapped)] == [
        (1, "Waitaha"),
        (2, "New South Wales"),
        (3, "Wien"),
        (4, "Paris"),
    ]
    assert [country[3] for country in countries(mapped)] == [name for _, _, _, name in COUNTRIES]


def test_in_a_unit_of_work_a_refusal_takes_the_work_back(mapped: Engine) -> None:
    key = keep(mapped, a_region(iso_3166_2="NZ-CAN"))

    with refused(OF_ITS_COUNTRY), unit_of_work(mapped) as work:
        work.add(a_region(name="Otago", iso_3166_2="NZ-OTA"))
        work.flush()
        work.add(a_region(name="Southland", iso_3166_2="AU-STL"))

    assert regions(mapped) == [(key, NEW_ZEALAND, "Canterbury", "NZ-CAN")]


def test_the_refusals_hold_on_a_connection_the_stores_code_did_not_open(
    mapped: Engine, tmp_path: Path
) -> None:
    # The rule stands in the file. A connection that does not ask SQLite
    # to hold rows to what they point to is held to it all the same.
    the_standard(mapped)
    before = everything(mapped)
    mapped.dispose()
    plain = sqlite3.connect(tmp_path / "store.sqlite3", isolation_level=None)
    try:
        assert plain.execute("PRAGMA foreign_keys").fetchone() == (0,)
        for statement, why in [
            (f"INSERT INTO {A_REGION}", OF_ITS_COUNTRY),
            ("UPDATE region SET iso_3166_2 = 'AU-CAN' WHERE id = 1", OF_ITS_COUNTRY),
            ("UPDATE region SET country_id = 2 WHERE id = 1", OF_ITS_COUNTRY),
            ("UPDATE country SET alpha_2 = 'NX' WHERE id = 1", OF_ITS_REGIONS),
        ]:
            given = (9, NEW_ZEALAND, "Otago", "AU-OTA") if statement.startswith("INSERT") else ()
            with pytest.raises(sqlite3.IntegrityError) as refusal:
                plain.execute(statement, given)
            assert str(refusal.value) == why
    finally:
        plain.close()

    assert everything(mapped) == before


def test_a_region_of_no_country_is_left_to_the_rule_of_what_a_row_points_to(
    mapped: Engine, tmp_path: Path
) -> None:
    # Where the country of a region is not in the store, there are no
    # letters to hold its code to, and this rule says nothing. The store's
    # own connections refuse such a region by another rule: a row points
    # to a row that is there.
    with refused("FOREIGN KEY constraint failed"):
        write(mapped, f"INSERT INTO {A_REGION}", 9, 77, "Otago", "NZ-OTA")
    assert regions(mapped) == []

    mapped.dispose()
    plain = sqlite3.connect(tmp_path / "store.sqlite3", isolation_level=None)
    try:
        plain.execute(f"INSERT INTO {A_REGION}", (9, 77, "Otago", "NZ-OTA"))
        # A country that is given the key such a region points to is held
        # to the code of the region, whether it is new or was there. What
        # the table of the countries refuses, it refuses first.
        for statement, given, why in [
            (f"INSERT INTO {A_COUNTRY}", (77, "DE", "DEU", "Germany"), OF_ITS_REGIONS),
            ("UPDATE country SET id = 77 WHERE id = 4", (), OF_ITS_REGIONS),
            ("UPDATE country SET rowid = 77 WHERE id = 4", (), OF_ITS_REGIONS),
            (
                f"INSERT INTO {A_COUNTRY}",
                (77, "FR", "FXX", "Example"),
                "UNIQUE constraint failed: country.alpha_2",
            ),
        ]:
            with pytest.raises(sqlite3.IntegrityError) as refusal:
                plain.execute(statement, given)
            assert str(refusal.value) == why
        plain.execute("UPDATE country SET rowid = 77 WHERE id = 1")
    finally:
        plain.close()
    assert regions(mapped) == [(9, 77, "Otago", "NZ-OTA")]
    assert [country[:2] for country in countries(mapped)] == [
        (AUSTRALIA, "AU"),
        (AUSTRIA, "AT"),
        (FRANCE, "FR"),
        (77, "NZ"),
    ]


def test_a_store_made_from_the_models_holds_the_code_to_the_country_too(tmp_path: Path) -> None:
    made = create_engine(f"sqlite:///{tmp_path / 'made.sqlite3'}")
    Base.metadata.create_all(made)
    try:
        fill(made)
        the_standard(made)
        before = everything(made)

        for statement, given, why in [
            (f"INSERT INTO {A_REGION}", (9, NEW_ZEALAND, "Otago", "AU-OTA"), OF_ITS_COUNTRY),
            ("UPDATE region SET iso_3166_2 = 'AU-CAN' WHERE id = 1", (), OF_ITS_COUNTRY),
            ("UPDATE region SET country_id = 2 WHERE id = 1", (), OF_ITS_COUNTRY),
            ("UPDATE country SET alpha_2 = 'NX' WHERE id = 1", (), OF_ITS_REGIONS),
            (
                f"INSERT OR REPLACE INTO {A_COUNTRY}",
                (NEW_ZEALAND, "NX", "NZL", "Example"),
                OF_ITS_REGIONS,
            ),
        ]:
            with refused(why):
                write(made, statement, *given)
        assert everything(made) == before
    finally:
        made.dispose()


# -------------------------------------------------------- how the rule stands

THE_FOUR = [
    ("tr_country_code_of_its_regions", "country"),
    ("tr_country_code_stays_of_its_regions", "country"),
    ("tr_region_code_of_its_country", "region"),
    ("tr_region_code_stays_of_its_country", "region"),
]


def test_the_rule_is_four_triggers_two_on_the_regions_and_two_on_the_countries(
    mapped: Engine,
) -> None:
    with mapped.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name, tbl_name, sql FROM sqlite_master WHERE type = 'trigger' "
            "AND tbl_name IN ('region', 'country') ORDER BY name"
        ).all()

    assert [(str(name), str(table)) for name, table, _ in found] == THE_FOUR
    written = {str(name): " ".join(str(statement).split()) for name, _, statement in found}
    assert "AFTER INSERT ON country WHEN" in written["tr_country_code_of_its_regions"]
    assert "AFTER UPDATE ON country WHEN" in written["tr_country_code_stays_of_its_regions"]
    assert "AFTER INSERT ON region WHEN" in written["tr_region_code_of_its_country"]
    assert "AFTER UPDATE ON region WHEN" in written["tr_region_code_stays_of_its_country"]
    # None fires for the change of one column alone (DAT-068).
    assert [name for name, statement in written.items() if "UPDATE OF" in statement.upper()] == []


def test_the_regions_of_a_country_are_found_for_the_rule_by_the_index_of_the_country(
    mapped: Engine,
) -> None:
    # What the triggers of the countries ask, as a query of its own.
    asked = (
        "EXPLAIN QUERY PLAN SELECT 1 FROM region WHERE country_id = 1 "
        "AND substr(iso_3166_2, 1, 2) != 'NZ'"
    )
    with mapped.connect() as connection:
        plan = [str(row[3]) for row in connection.exec_driver_sql(asked)]

    assert plan == ["SEARCH region USING INDEX ix_region_country_id (country_id=?)"]


# ----------------------------------------- a store that had regions before the rule


def a_store_at_version_18_with_a_region_of_another_country(store: Engine) -> None:
    """Bring a store to version 18 and fill it: the four regions and one that is wrong.

    The region with the key 9 is "Otago" in New Zealand with the code
    "AU-OTA". Until the nineteenth migration nothing refuses it.
    """
    migrate(store, MIGRATIONS[:18])
    fill(store)
    the_standard(store)
    write(store, f"INSERT INTO {A_REGION}", 9, NEW_ZEALAND, "Otago", "AU-OTA")


def test_the_nineteenth_migration_puts_no_region_right_and_changes_no_row(store: Engine) -> None:
    a_store_at_version_18_with_a_region_of_another_country(store)
    before = everything(store)

    assert migrate(store, MIGRATIONS[:19]) == [19]

    assert schema_version(store) == 19
    assert everything(store) == before
    assert regions(store)[-1] == (9, NEW_ZEALAND, "Otago", "AU-OTA")


@pytest.mark.parametrize(
    ("statement", "then"),
    [
        (
            "UPDATE region SET iso_3166_2 = 'NZ-OTA' WHERE id = 9",
            [(9, NEW_ZEALAND, "Otago", "NZ-OTA")],
        ),
        ("UPDATE region SET iso_3166_2 = NULL WHERE id = 9", [(9, NEW_ZEALAND, "Otago", None)]),
        ("UPDATE region SET country_id = 2 WHERE id = 9", [(9, AUSTRALIA, "Otago", "AU-OTA")]),
        ("DELETE FROM region WHERE id = 9", []),
    ],
    ids=["a code of its country", "no code", "the country of its code", "deleted"],
)
def test_a_region_that_was_wrong_before_the_rule_is_put_right_or_deleted(
    store: Engine, statement: str, then: list[tuple[object, ...]]
) -> None:
    a_store_at_version_18_with_a_region_of_another_country(store)
    migrate(store)

    write(store, statement)

    assert regions(store)[4:] == then
    # From then on the country of the region is changed like any other.
    write(store, "UPDATE country SET name = 'Aotearoa New Zealand' WHERE id = 1")
    assert countries(store)[0] == (NEW_ZEALAND, "NZ", "NZL", "Aotearoa New Zealand")


@pytest.mark.parametrize(
    ("statement", "why"),
    [
        ("UPDATE region SET name = 'Otakou' WHERE id = 9", OF_ITS_COUNTRY),
        ("UPDATE region SET iso_3166_2 = 'AT-OTA' WHERE id = 9", OF_ITS_COUNTRY),
        ("UPDATE region SET country_id = 3 WHERE id = 9", OF_ITS_COUNTRY),
        ("UPDATE country SET name = 'Aotearoa New Zealand' WHERE id = 1", OF_ITS_REGIONS),
        ("UPDATE country SET alpha_2 = 'NX' WHERE id = 1", OF_ITS_REGIONS),
    ],
    ids=[
        "another name",
        "another wrong code",
        "another wrong country",
        "its country, another name",
        "its country, other letters",
    ],
)
def test_until_then_every_other_change_of_it_and_of_its_country_is_refused(
    store: Engine, statement: str, why: str
) -> None:
    a_store_at_version_18_with_a_region_of_another_country(store)
    migrate(store)
    before = everything(store)

    with refused(why):
        write(store, statement)

    assert everything(store) == before


def test_its_country_can_be_given_the_letters_of_its_code_where_no_other_region_minds(
    store: Engine,
) -> None:
    # The letters of the wrong code would put the region right. Australia
    # has them, and no two countries have one code. Once Australia has
    # others, New Zealand still has two regions with codes, "NZ-CAN" and
    # the wrong "AU-OTA", and no letters fit both. Without Canterbury the
    # country is given them.
    a_store_at_version_18_with_a_region_of_another_country(store)
    migrate(store)

    with refused("UNIQUE constraint failed: country.alpha_2"):
        write(store, "UPDATE country SET alpha_2 = 'AU' WHERE id = 1")
    write(store, "DELETE FROM region WHERE id = 2")
    write(store, "UPDATE country SET alpha_2 = 'AX' WHERE id = 2")
    with refused(OF_ITS_REGIONS):
        write(store, "UPDATE country SET alpha_2 = 'AU' WHERE id = 1")
    write(store, "DELETE FROM region WHERE id = 1")
    write(store, "UPDATE country SET alpha_2 = 'AU' WHERE id = 1")

    assert countries(store)[0][:2] == (NEW_ZEALAND, "AU")
    assert regions(store)[-1] == (9, NEW_ZEALAND, "Otago", "AU-OTA")


def test_before_the_nineteenth_migration_the_store_took_what_it_refuses_after(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:18])
    fill(store)
    the_standard(store)
    write(store, f"INSERT INTO {A_REGION}", 9, NEW_ZEALAND, "Otago", "AU-OTA")
    write(store, "UPDATE region SET country_id = 2 WHERE id = 4")
    write(store, "UPDATE country SET alpha_2 = 'XX' WHERE id = 3")
    before = everything(store)

    migrate(store)

    for statement, given, why in [
        (f"INSERT INTO {A_REGION}", (10, NEW_ZEALAND, "Southland", "AU-STL"), OF_ITS_COUNTRY),
        ("UPDATE region SET country_id = 4 WHERE id = 2", (), OF_ITS_COUNTRY),
        ("UPDATE country SET alpha_2 = 'YY' WHERE id = 1", (), OF_ITS_REGIONS),
    ]:
        with refused(why):
            write(store, statement, *given)
    # Every row has what it had. A region has one column more since: the
    # region it is a part of, after its country, and every region that
    # was there is a part of none (DAT-065).
    assert everything(store) == {
        "region": [(*region[:2], None, *region[2:]) for region in before["region"]],
        "country": before["country"],
    }


def test_a_region_is_deleted_whatever_its_code_and_a_country_without_regions_too(
    mapped: Engine,
) -> None:
    the_standard(mapped)

    with unit_of_work(mapped) as work:
        work.execute(delete(Region).where(Region.country_id == NEW_ZEALAND))
    with unit_of_work(mapped) as work:
        work.execute(delete(Country).where(Country.id == NEW_ZEALAND))

    with unit_of_work(mapped) as work:
        left = work.execute(select(Country.alpha_2).order_by(Country.id)).scalars().all()
    assert left == ["AU", "AT", "FR"]
    assert [region[3] for region in regions(mapped)] == ["AU-NSW", "AT-1", "FR-75C"]
