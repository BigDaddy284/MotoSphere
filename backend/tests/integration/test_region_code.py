"""Tests of the code a region says, against a real SQLite file.

The store of every test is built the way a real store is built: by the
migrations. What is stored through the model is also read as SQLite holds
it, and what the table must refuse is also written past the model.

The code is the one ISO 3166-2 gives a region, as "NZ-CAN" for
Canterbury. The tests hold its form, that a region may be without one,
and that no two regions have one code. Every code of the tests is a code
of the standard, and the code of the region it is given to.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import IntegrityError

from motosphere.db.changes import change
from motosphere.db.models import Country, Region, Source
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 27, 9, 0, tzinfo=UTC)
ADDRESS = "https://standards.example/regions.csv"
# The four countries of the tests, by their keys.
NEW_ZEALAND = 1
AUSTRALIA = 2
AUSTRIA = 3
FRANCE = 4
NO_FORM = "CHECK constraint failed: ck_region_iso_3166_2_form"
ONE_CODE_TWICE = "UNIQUE constraint failed: region.iso_3166_2"


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


@pytest.fixture
def mapped(newest: Engine) -> Engine:
    """The test's own store with the newest schema, one source and four countries in it.

    The key of the source is 1. The keys of the countries are 1 to 4: New
    Zealand, Australia, Austria and France.
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
    for two, three, name in [
        ("NZ", "NZL", "New Zealand"),
        ("AU", "AUS", "Australia"),
        ("AT", "AUT", "Austria"),
        ("FR", "FRA", "France"),
    ]:
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


def a_region(**said: Any) -> Region:
    """Canterbury in New Zealand as the one source of the tests says it, and what the test says."""
    described: dict[str, Any] = {
        "country_id": NEW_ZEALAND,
        "name": "Canterbury",
        "source_id": 1,
        "source_address": ADDRESS,
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


def the_region(store: Engine, key: int) -> Region:
    """Read a region anew from the store."""
    with unit_of_work(store) as work:
        return work.execute(select(Region).where(Region.id == key)).scalar_one()


def write(
    store: Engine, code: object, name: str = "Canterbury", country: int = NEW_ZEALAND
) -> None:
    """Write a region past the model, as plain SQL, with this in the column of its code."""
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO region (country_id, name, iso_3166_2, source_id, source_address, "
            "collected_at, last_verified_at, extraction_method, confidence, "
            "verification_status, created_at, updated_at) VALUES (?, ?, ?, 1, "
            "'https://standards.example/regions.csv', '2026-11-27T09:00:00.000000+00:00', "
            "'2026-11-27T09:00:00.000000+00:00', 'public dataset', 'high', 'official', "
            "'2026-11-27T09:00:05.000000+00:00', '2026-11-27T09:00:05.000000+00:00')",
            (country, name, code),
        )


def codes(store: Engine) -> list[tuple[str, object]]:
    """The name of every region and the code SQLite holds for it, by the region's key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name, iso_3166_2 FROM region ORDER BY id")
        return [(str(name), code) for name, code in found]


def history(store: Engine) -> list[tuple[object, ...]]:
    """What the history holds of the regions: the record, the field, and what it held and holds."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT record_table, record_id, field, old_value, new_value FROM record_change "
            "ORDER BY id"
        )
        return [tuple(row) for row in found]


def test_a_region_says_its_code_and_is_read_back_with_it(mapped: Engine) -> None:
    key = keep(mapped, a_region(iso_3166_2="NZ-CAN"))

    found = the_region(mapped, key)

    assert found.iso_3166_2 == "NZ-CAN"
    assert (found.country_id, found.name) == (NEW_ZEALAND, "Canterbury")
    assert codes(mapped) == [("Canterbury", "NZ-CAN")]


def test_a_region_of_which_no_code_is_said_has_none(mapped: Engine) -> None:
    key = keep(mapped, a_region())

    assert the_region(mapped, key).iso_3166_2 is None
    assert codes(mapped) == [("Canterbury", None)]


def test_a_row_written_past_the_model_is_read_with_its_code(mapped: Engine) -> None:
    write(mapped, "NZ-CAN")
    write(mapped, None, name="Otago")

    assert the_region(mapped, 1).iso_3166_2 == "NZ-CAN"
    assert the_region(mapped, 2).iso_3166_2 is None


# A code of each form the standard has: one, two and three characters
# after the hyphen, of letters, of digits and of both.
OF_THE_STANDARD = [
    (AUSTRIA, "Burgenland", "AT-1"),
    (AUSTRALIA, "Western Australia", "AU-WA"),
    (FRANCE, "Ain", "FR-01"),
    (FRANCE, "Corse-du-Sud", "FR-2A"),
    (NEW_ZEALAND, "Canterbury", "NZ-CAN"),
    (FRANCE, "Paris", "FR-75C"),
]


@pytest.mark.parametrize(
    ("country", "name", "code"), OF_THE_STANDARD, ids=[code for *_, code in OF_THE_STANDARD]
)
def test_a_code_of_each_form_of_the_standard_is_taken(
    mapped: Engine, country: int, name: str, code: str
) -> None:
    key = keep(mapped, a_region(country_id=country, name=name, iso_3166_2=code))
    write(mapped, None, name="Example Region", country=country)
    with mapped.begin() as connection:
        connection.exec_driver_sql("DELETE FROM region WHERE id = ?", (key,))
    write(mapped, code, name=name, country=country)

    assert the_region(mapped, 3).iso_3166_2 == code
    assert codes(mapped) == [("Example Region", None), (name, code)]


# Text that is not a code of the standard's form, and what is wrong with it.
NOT_OF_THE_FORM = {
    "no text at all": "",
    "small letters": "nz-can",
    "small letters after the hyphen": "NZ-can",
    "one small letter before the hyphen": "Nz-CAN",
    "one small letter after the hyphen": "NZ-CAn",
    "no hyphen": "NZCAN",
    "a space for the hyphen": "NZ CAN",
    "an underscore for the hyphen": "NZ_CAN",
    "a longer dash for the hyphen": "NZ\u2013CAN",
    "nothing after the hyphen": "NZ-",
    "four after the hyphen": "NZ-CANT",
    "nothing before the hyphen": "-CAN",
    "one letter before the hyphen": "N-CAN",
    "three letters before the hyphen": "NZL-CAN",
    "digits before the hyphen": "12-CAN",
    "a digit before the hyphen": "N2-CAN",
    "only the country": "NZ",
    "two hyphens": "NZ--CA",
    "a hyphen after the hyphen": "NZ-C-N",
    "a space before": " NZ-CAN",
    "a space after": "NZ-CAN ",
    "a space within": "NZ-C N",
    "a new line after": "NZ-CAN\n",
    "a tab after": "NZ-CAN\t",
    "a space that does not break after": "NZ-CAN\u00a0",
    "two codes": "NZ-CAN,NZ-OTA",
    "a letter with an accent": "NZ-C\u00c4N",
    "letters of full width": "\uff2e\uff3a-CAN",
    "a Greek capital": "NZ-C\u0391N",
    "a digit of another script": "FR-\u0660\u0661",
    "a star": "NZ-*",
    "a question mark": "NZ-?",
    "the pattern itself": "[A-Z][A-Z]-[A-Z0-9]",
    "a full stop": "NZ-CA.",
    "a character with the number 0 after": "NZ-CAN\x00",
    "a character with the number 0 and more after": "NZ-CAN\x00, or so",
    "a character with the number 0 within": "NZ-C\x00N",
    "a character with the number 0 before": "\x00NZ-CAN",
}


@pytest.mark.parametrize("code", list(NOT_OF_THE_FORM.values()), ids=list(NOT_OF_THE_FORM))
def test_text_that_is_not_of_the_form_is_refused(mapped: Engine, code: str) -> None:
    with refused(NO_FORM):
        keep(mapped, a_region(iso_3166_2=code))
    with refused(NO_FORM):
        write(mapped, code)

    assert codes(mapped) == []


@pytest.mark.parametrize("code", list(NOT_OF_THE_FORM.values()), ids=list(NOT_OF_THE_FORM))
def test_a_region_cannot_be_given_text_that_is_not_of_the_form_later(
    mapped: Engine, code: str
) -> None:
    keep(mapped, a_region(iso_3166_2="NZ-CAN"))
    keep(mapped, a_region(name="Otago"))

    for key in (1, 2):
        with refused(NO_FORM), mapped.begin() as connection:
            connection.exec_driver_sql("UPDATE region SET iso_3166_2 = ? WHERE id = ?", (code, key))

    assert codes(mapped) == [("Canterbury", "NZ-CAN"), ("Otago", None)]


def test_bytes_are_not_a_code(mapped: Engine) -> None:
    with refused("cannot store BLOB value in TEXT column region.iso_3166_2"):
        write(mapped, b"NZ-CAN")

    assert codes(mapped) == []


@pytest.mark.parametrize("number", [12, 1.5, 0], ids=["whole", "with a point", "nought"])
def test_a_number_is_not_a_code(mapped: Engine, number: object) -> None:
    # SQLite makes text of a number that is written to a column of text,
    # and that text has not the form.
    with refused(NO_FORM):
        write(mapped, number)

    assert codes(mapped) == []


def test_no_two_regions_have_one_code(mapped: Engine) -> None:
    keep(mapped, a_region(iso_3166_2="NZ-CAN"))

    with refused(ONE_CODE_TWICE):
        keep(mapped, a_region(name="Otago", iso_3166_2="NZ-CAN"))
    with refused(ONE_CODE_TWICE):
        write(mapped, "NZ-CAN", name="Otago")

    assert codes(mapped) == [("Canterbury", "NZ-CAN")]


def test_any_number_of_regions_can_be_without_a_code(mapped: Engine) -> None:
    keep(mapped, a_region())
    keep(mapped, a_region(name="Otago"))
    write(mapped, None, name="Southland")
    keep(mapped, a_region(country_id=AUSTRALIA, name="Western Australia"))

    assert codes(mapped) == [
        ("Canterbury", None),
        ("Otago", None),
        ("Southland", None),
        ("Western Australia", None),
    ]


def test_the_regions_of_one_country_each_say_their_own_code(mapped: Engine) -> None:
    keep(mapped, a_region(iso_3166_2="NZ-CAN"))
    keep(mapped, a_region(name="Otago", iso_3166_2="NZ-OTA"))
    keep(mapped, a_region(name="Southland"))
    keep(mapped, a_region(country_id=AUSTRALIA, name="Western Australia", iso_3166_2="AU-WA"))

    assert codes(mapped) == [
        ("Canterbury", "NZ-CAN"),
        ("Otago", "NZ-OTA"),
        ("Southland", None),
        ("Western Australia", "AU-WA"),
    ]


def test_a_region_cannot_be_given_the_code_of_another_later(mapped: Engine) -> None:
    keep(mapped, a_region(iso_3166_2="NZ-CAN"))
    with_another = keep(mapped, a_region(name="Otago", iso_3166_2="NZ-OTA"))
    without = keep(mapped, a_region(name="Southland"))

    for key in (with_another, without):
        with refused(ONE_CODE_TWICE), mapped.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE region SET iso_3166_2 = 'NZ-CAN' WHERE id = ?", (key,)
            )

    assert codes(mapped) == [("Canterbury", "NZ-CAN"), ("Otago", "NZ-OTA"), ("Southland", None)]


def test_a_code_is_given_later_and_another_and_none_with_its_history(mapped: Engine) -> None:
    key = keep(mapped, a_region(name="Otago"))

    for code in ("NZ-CAN", "NZ-OTA", None):
        with unit_of_work(mapped) as work:
            change(
                work,
                work.get_one(Region, key),
                {"iso_3166_2": code},
                decided_by="Jo Example",
            )

    assert the_region(mapped, key).iso_3166_2 is None
    assert codes(mapped) == [("Otago", None)]
    assert history(mapped) == [
        ("region", key, "iso_3166_2", None, "NZ-CAN"),
        ("region", key, "iso_3166_2", "NZ-CAN", "NZ-OTA"),
        ("region", key, "iso_3166_2", "NZ-OTA", None),
    ]


def test_a_code_that_is_said_again_is_no_change(mapped: Engine) -> None:
    key = keep(mapped, a_region(iso_3166_2="NZ-CAN"))

    with unit_of_work(mapped) as work:
        written = change(
            work, work.get_one(Region, key), {"iso_3166_2": "NZ-CAN"}, decided_by="Jo Example"
        )

    assert written == []
    assert history(mapped) == []


@pytest.mark.parametrize(
    ("code", "why"),
    [("NZ-CAN", ONE_CODE_TWICE), ("nz-ota", NO_FORM)],
    ids=["the code of another", "not of the form"],
)
def test_a_change_the_table_refuses_leaves_the_code_and_no_history(
    mapped: Engine, code: str, why: str
) -> None:
    keep(mapped, a_region(iso_3166_2="NZ-CAN"))
    key = keep(mapped, a_region(name="Otago", iso_3166_2="NZ-OTA"))

    with refused(why), unit_of_work(mapped) as work:
        change(work, work.get_one(Region, key), {"iso_3166_2": code}, decided_by="Jo Example")

    assert codes(mapped) == [("Canterbury", "NZ-CAN"), ("Otago", "NZ-OTA")]
    assert history(mapped) == []


@pytest.mark.parametrize("then", ["without a code", "of another code", "deleted"])
def test_a_code_can_be_given_again_once_no_region_has_it_any_more(
    mapped: Engine, then: str
) -> None:
    first = keep(mapped, a_region(name="Example Region", iso_3166_2="NZ-CAN"))
    with unit_of_work(mapped) as work:
        if then == "deleted":
            work.execute(delete(Region).where(Region.id == first))
        else:
            work.get_one(Region, first).iso_3166_2 = None if then == "without a code" else "NZ-OTA"

    keep(mapped, a_region(iso_3166_2="NZ-CAN"))

    assert codes(mapped)[-1] == ("Canterbury", "NZ-CAN")
    assert [code for _, code in codes(mapped)].count("NZ-CAN") == 1


def test_what_the_table_holds_of_a_code_is_its_text(mapped: Engine) -> None:
    keep(mapped, a_region(iso_3166_2="NZ-CAN"))
    keep(mapped, a_region(name="Otago"))

    with mapped.connect() as connection:
        held = connection.exec_driver_sql(
            "SELECT iso_3166_2, typeof(iso_3166_2), length(iso_3166_2) FROM region ORDER BY id"
        ).all()

    assert [tuple(row) for row in held] == [("NZ-CAN", "text", 6), (None, "null", None)]


def test_the_table_has_the_column_after_the_name(mapped: Engine) -> None:
    with mapped.connect() as connection:
        columns = connection.exec_driver_sql(
            "SELECT name, type, \"notnull\", dflt_value FROM pragma_table_info('region')"
        ).all()
        strict = connection.exec_driver_sql(
            "SELECT strict FROM pragma_table_list('region')"
        ).scalar_one()

    assert [str(name) for name, *_ in columns] == [
        "id",
        "country_id",
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
    assert [tuple(column) for column in columns if column[0] == "iso_3166_2"] == [
        ("iso_3166_2", "TEXT", 0, None)
    ]
    assert strict == 1


def test_the_region_of_a_code_is_found_by_the_index(mapped: Engine) -> None:
    with mapped.connect() as connection:
        index = connection.exec_driver_sql("PRAGMA index_info(sqlite_autoindex_region_2)").all()
        plan = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT * FROM region WHERE iso_3166_2 = 'NZ-CAN'"
        ).all()

    # The index SQLite keeps for the rule that no two regions have one code.
    assert [name for _, _, name in index] == ["iso_3166_2"]
    assert [detail for *_, detail in plan] == [
        "SEARCH region USING INDEX sqlite_autoindex_region_2 (iso_3166_2=?)"
    ]


def test_a_region_is_asked_for_by_its_code_through_the_model(mapped: Engine) -> None:
    keep(mapped, a_region(iso_3166_2="NZ-CAN"))
    keep(mapped, a_region(name="Otago", iso_3166_2="NZ-OTA"))
    keep(mapped, a_region(name="Southland"))
    keep(mapped, a_region(country_id=AUSTRALIA, name="Canterbury"))

    with unit_of_work(mapped) as work:
        of_the_code = work.scalars(select(Region.name).where(Region.iso_3166_2 == "NZ-OTA")).all()
        of_no_such_code = work.scalars(
            select(Region.name).where(Region.iso_3166_2 == "NZ-AUK")
        ).all()
        without_a_code = work.execute(
            select(Region.country_id, Region.name)
            .where(Region.iso_3166_2.is_(None))
            .order_by(Region.id)
        ).all()

    assert of_the_code == ["Otago"]
    assert of_no_such_code == []
    assert [tuple(row) for row in without_a_code] == [
        (NEW_ZEALAND, "Southland"),
        (AUSTRALIA, "Canterbury"),
    ]
