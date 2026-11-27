"""Tests of the table of the countries, against a real SQLite file.

The store of every test is built the way a real store is built: by the
migrations. What is stored through the model is also read as SQLite holds
it, and what the table must refuse is also written past the model.

The countries are the first real table of collected records. What every
such table has is proved on tables made for the purpose
(``test_collected.py``, ``test_collected_index.py``); here the real table
is held to it.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import IntegrityError

from motosphere.db.changes import change
from motosphere.db.models import Country, Source
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 27, 9, 0, tzinfo=UTC)
SEEN_AGAIN = datetime(2026, 11, 28, 9, 0, tzinfo=UTC)
ADDRESS = "https://standards.example/countries.csv"
# What a country cannot be without: every column but the day its source
# says it was published.
NEEDED = [
    "alpha_2",
    "alpha_3",
    "name",
    "source_id",
    "source_address",
    "collected_at",
    "last_verified_at",
    "extraction_method",
    "confidence",
    "verification_status",
]
# What is not a code of two letters, and what is not one of three: small
# letters, too few and too many, what is no letter, white space around the
# letters, and letters that are not among the 26, some of which look like
# them. The last three of each have a character with the number 0 in them.
NOT_TWO_CAPITALS = {
    "small letters": "nz",
    "a small letter last": "Nz",
    "a small letter first": "nZ",
    "one letter": "N",
    "three letters": "NZL",
    "nothing": "",
    "a figure": "N2",
    "a hyphen": "N-",
    "a space after one letter": "N ",
    "a space before": " NZ",
    "a space after": "NZ ",
    "a new line after": "NZ\n",
    "a letter with a tilde": "\u00d1Z",
    "Greek capitals": "\u039d\u0396",
    "wide capitals": "\uff2e\uff3a",
    "a nought after": "NZ\x00",
    "a nought and more after": "NZ\x00L",
    "a nought before": "\x00NZ",
}
NOT_THREE_CAPITALS = {
    "small letters": "nzl",
    "a small letter last": "NZl",
    "a small letter first": "nZL",
    "two letters": "NZ",
    "four letters": "NZLD",
    "nothing": "",
    "a figure": "NZ1",
    "a hyphen": "NZ-",
    "a space after two letters": "NZ ",
    "a space before": " NZL",
    "a space after": "NZL ",
    "a new line after": "NZL\n",
    "a letter with a tilde": "\u00d1ZL",
    "Greek capitals": "\u039d\u0396\u039b",
    "wide capitals": "\uff2e\uff3a\uff2c",
    "a nought after": "NZL\x00",
    "a nought and more after": "NZL\x00D",
    "a nought before": "\x00NZL",
}
REFUSED_CODES = [
    *(("alpha_2", "two", text, said) for said, text in NOT_TWO_CAPITALS.items()),
    *(("alpha_3", "three", text, said) for said, text in NOT_THREE_CAPITALS.items()),
]
EACH_REFUSED_CODE = pytest.mark.parametrize(
    ("column", "words", "text"),
    [(column, words, text) for column, words, text, _ in REFUSED_CODES],
    ids=[f"{column}: {said}" for column, _, _, said in REFUSED_CODES],
)


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


@pytest.fixture
def listed(newest: Engine) -> Engine:
    """The test's own store with the newest schema and one source in it, whose key is 1."""
    with unit_of_work(newest) as work:
        work.add(
            Source(
                name="Example Standards Body",
                website="https://standards.example",
                category=SourceCategory.GOVERNING_BODY,
                collection_method=CollectionMethod.DATASET,
            )
        )
    return newest


def a_country(**said: Any) -> Country:
    """New Zealand as the one source of the tests says it, and what the test says of it."""
    described: dict[str, Any] = {
        "alpha_2": "NZ",
        "alpha_3": "NZL",
        "name": "New Zealand",
        "source_id": 1,
        "source_address": ADDRESS,
        "collected_at": COLLECTED,
        "last_verified_at": COLLECTED,
        "extraction_method": CollectionMethod.DATASET,
        "confidence": Confidence.HIGH,
        "verification_status": VerificationStatus.OFFICIAL,
    }
    return Country(**(described | said))


def keep(store: Engine, country: Country) -> int:
    """Store a country in a unit of work of its own, and give its key."""
    with unit_of_work(store) as work:
        work.add(country)
    return country.id


def the_country(store: Engine, key: int) -> Country:
    """Read a country anew from the store."""
    with unit_of_work(store) as work:
        return work.execute(select(Country).where(Country.id == key)).scalar_one()


# A row written past the model, as plain SQL: every column but the key.
A_ROW = (
    "INSERT INTO country (alpha_2, alpha_3, name, source_id, source_address, collected_at, "
    "published_on, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def write(store: Engine, **said: object) -> None:
    """Write New Zealand past the model, with what the test says of it."""
    row: dict[str, object] = {
        "alpha_2": "NZ",
        "alpha_3": "NZL",
        "name": "New Zealand",
        "source_id": 1,
        "source_address": ADDRESS,
        "collected_at": "2026-11-27T09:00:00.000000+00:00",
        "published_on": None,
        "last_verified_at": "2026-11-27T09:00:00.000000+00:00",
        "extraction_method": "public dataset",
        "confidence": "high",
        "verification_status": "official",
        "created_at": "2026-11-27T09:00:05.000000+00:00",
        "updated_at": "2026-11-27T09:00:05.000000+00:00",
    } | said
    # A column the test names that the table does not have would be one value more.
    assert len(row) == 13
    with store.begin() as connection:
        connection.exec_driver_sql(A_ROW, tuple(row.values()))


def held(store: Engine) -> list[tuple[object, ...]]:
    """The rows of the table as SQLite holds them, by their key."""
    with store.connect() as connection:
        return [
            tuple(row) for row in connection.exec_driver_sql("SELECT * FROM country ORDER BY id")
        ]


def codes(store: Engine) -> list[tuple[str, str, str]]:
    """The two codes and the name of every country, by their key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT alpha_2, alpha_3, name FROM country ORDER BY id")
        return [(str(two), str(three), str(name)) for two, three, name in found]


def test_a_country_is_stored_and_read_back_with_everything_said_of_it(
    listed: Engine, clock: list[datetime]
) -> None:
    in_another_zone = SEEN_AGAIN.astimezone(timezone(timedelta(hours=13)))
    key = keep(
        listed,
        a_country(published_on=date(2026, 11, 2), last_verified_at=in_another_zone),
    )

    found = the_country(listed, key)

    assert found.id == key == 1
    assert found.alpha_2 == "NZ"
    assert found.alpha_3 == "NZL"
    assert found.name == "New Zealand"
    assert found.source_id == 1
    assert found.source_address == ADDRESS
    assert found.collected_at == COLLECTED
    assert found.published_on == date(2026, 11, 2)
    assert found.last_verified_at == SEEN_AGAIN
    assert found.last_verified_at.utcoffset() == timedelta(0)
    assert found.extraction_method is CollectionMethod.DATASET
    assert found.confidence is Confidence.HIGH
    assert found.verification_status is VerificationStatus.OFFICIAL
    assert found.created_at == found.updated_at == clock[0]
    assert len(clock) == 1


def test_what_the_table_holds_is_plain_text_and_whole_numbers(
    listed: Engine, clock: list[datetime]
) -> None:
    keep(listed, a_country(published_on=date(2026, 11, 2), last_verified_at=SEEN_AGAIN))

    assert held(listed) == [
        (
            1,
            "NZ",
            "NZL",
            "New Zealand",
            1,
            ADDRESS,
            "2026-11-27T09:00:00.000000+00:00",
            "2026-11-02",
            "2026-11-28T09:00:00.000000+00:00",
            "public dataset",
            "high",
            "official",
            "2026-11-19T08:00:00.000000+00:00",
            "2026-11-19T08:00:00.000000+00:00",
        )
    ]
    assert len(clock) == 1


def test_a_country_whose_source_gives_no_day_has_no_day(listed: Engine) -> None:
    key = keep(listed, a_country())

    assert the_country(listed, key).published_on is None
    assert held(listed)[0][7] is None


def test_a_row_written_past_the_model_is_read_as_a_country(listed: Engine) -> None:
    write(listed, published_on="2026-11-02")

    found = the_country(listed, 1)

    assert (found.alpha_2, found.alpha_3, found.name) == ("NZ", "NZL", "New Zealand")
    assert found.collected_at == found.last_verified_at == COLLECTED
    assert found.published_on == date(2026, 11, 2)
    assert found.extraction_method is CollectionMethod.DATASET
    assert found.created_at == COLLECTED + timedelta(seconds=5)


@pytest.mark.parametrize("column", NEEDED)
def test_a_country_without_what_it_cannot_be_without_is_refused(
    listed: Engine, column: str
) -> None:
    with refused(f"NOT NULL constraint failed: country.{column}"):
        write(listed, **{column: None})

    assert held(listed) == []


@pytest.mark.parametrize("column", NEEDED)
def test_the_model_gives_no_value_to_what_a_country_cannot_be_without(
    listed: Engine, column: str
) -> None:
    with refused(f"NOT NULL constraint failed: country.{column}"):
        keep(listed, a_country(**{column: None}))

    assert held(listed) == []


@EACH_REFUSED_CODE
def test_the_table_refuses_a_code_that_is_not_capital_letters_of_its_number(
    listed: Engine, column: str, words: str, text: str
) -> None:
    with refused(f"CHECK constraint failed: ck_country_{column}_{words}_capitals"):
        write(listed, **{column: text})

    assert held(listed) == []


@pytest.mark.parametrize(
    ("column", "words", "text"),
    [("alpha_2", "two", "nz"), ("alpha_3", "three", "nzl")],
    ids=["alpha_2", "alpha_3"],
)
def test_the_model_does_not_put_a_code_into_capitals(
    listed: Engine, column: str, words: str, text: str
) -> None:
    # What is given is what is stored, or it is refused: a code that is
    # put right in silence would hide that its source wrote it otherwise.
    with refused(f"CHECK constraint failed: ck_country_{column}_{words}_capitals"):
        keep(listed, a_country(**{column: text}))

    assert held(listed) == []


@pytest.mark.parametrize(
    ("column", "words"), [("alpha_2", "two"), ("alpha_3", "three")], ids=["alpha_2", "alpha_3"]
)
def test_a_number_is_not_a_code(listed: Engine, column: str, words: str) -> None:
    # A strict table makes text of a whole number where the column is text,
    # and the text is then held to the check like any other.
    with refused(f"CHECK constraint failed: ck_country_{column}_{words}_capitals"):
        write(listed, **{column: 64})

    assert held(listed) == []


@pytest.mark.parametrize("column", ["alpha_2", "alpha_3", "name"])
def test_bytes_are_not_text(listed: Engine, column: str) -> None:
    with refused(f"cannot store BLOB value in TEXT column country.{column}"):
        write(listed, **{column: b"NZ"})

    assert held(listed) == []


def test_text_is_not_a_source(listed: Engine) -> None:
    with refused("cannot store TEXT value in INTEGER column country.source_id"):
        write(listed, source_id="the first")

    assert held(listed) == []


@pytest.mark.parametrize(
    ("two", "three"),
    [("AA", "AAA"), ("ZZ", "ZZZ"), ("AZ", "AZA"), ("ZA", "ZAZ"), ("GB", "GBR"), ("XK", "XKX")],
)
def test_every_code_of_capital_letters_is_taken(listed: Engine, two: str, three: str) -> None:
    # The table knows the form of a code and not the standard's list: which
    # codes there are is what the source says.
    write(listed, alpha_2=two, alpha_3=three)

    assert codes(listed) == [(two, three, "New Zealand")]


def test_two_countries_cannot_have_one_code_of_two_letters(listed: Engine) -> None:
    keep(listed, a_country())

    with refused("UNIQUE constraint failed: country.alpha_2"):
        keep(listed, a_country(alpha_3="NIU", name="Niue"))
    with refused("UNIQUE constraint failed: country.alpha_2"):
        write(listed, alpha_3="NIU", name="Niue")

    assert codes(listed) == [("NZ", "NZL", "New Zealand")]


def test_two_countries_cannot_have_one_code_of_three_letters(listed: Engine) -> None:
    keep(listed, a_country())

    with refused("UNIQUE constraint failed: country.alpha_3"):
        keep(listed, a_country(alpha_2="NU", name="Niue"))
    with refused("UNIQUE constraint failed: country.alpha_3"):
        write(listed, alpha_2="NU", name="Niue")

    assert codes(listed) == [("NZ", "NZL", "New Zealand")]


@pytest.mark.parametrize(
    ("column", "taken"), [("alpha_2", "NZ"), ("alpha_3", "NZL")], ids=["alpha_2", "alpha_3"]
)
def test_a_country_cannot_be_given_the_code_of_another(
    listed: Engine, column: str, taken: str
) -> None:
    keep(listed, a_country())
    key = keep(listed, a_country(alpha_2="NU", alpha_3="NIU", name="Niue"))

    with refused(f"UNIQUE constraint failed: country.{column}"), unit_of_work(listed) as work:
        setattr(work.get_one(Country, key), column, taken)

    assert codes(listed) == [("NZ", "NZL", "New Zealand"), ("NU", "NIU", "Niue")]


def test_two_countries_with_codes_of_their_own_are_both_stored(listed: Engine) -> None:
    first = keep(listed, a_country())
    second = keep(listed, a_country(alpha_2="NU", alpha_3="NIU", name="Niue"))

    assert (first, second) == (1, 2)
    assert codes(listed) == [("NZ", "NZL", "New Zealand"), ("NU", "NIU", "Niue")]


def test_two_countries_can_have_one_name(listed: Engine) -> None:
    # A country is known by its codes. A name is text, and the table does
    # not judge whether two rows mean one country.
    keep(listed, a_country())
    keep(listed, a_country(alpha_2="NU", alpha_3="NIU"))

    assert codes(listed) == [("NZ", "NZL", "New Zealand"), ("NU", "NIU", "New Zealand")]


@pytest.mark.parametrize("text", ["", " ", " \t\n", "\u00a0"], ids=repr)
def test_the_table_refuses_an_empty_name(listed: Engine, text: str) -> None:
    with refused("CHECK constraint failed: ck_country_name_not_empty"):
        write(listed, name=text)
    with refused("CHECK constraint failed: ck_country_name_not_empty"):
        keep(listed, a_country(name=text))

    assert held(listed) == []


@pytest.mark.parametrize(
    "name",
    [
        "T\u00fcrkiye",
        "C\u00f4te d'Ivoire",
        "\u00c5land Islands",
        "Korea (the Republic of)",
        " New Zealand ",
        "new zealand",
    ],
)
def test_a_name_is_stored_as_it_was_given(listed: Engine, name: str) -> None:
    key = keep(listed, a_country(name=name))

    assert the_country(listed, key).name == name
    assert codes(listed) == [("NZ", "NZL", name)]


def test_a_country_comes_from_a_source_that_is_there(listed: Engine) -> None:
    with refused("FOREIGN KEY constraint failed"):
        keep(listed, a_country(source_id=2))
    with refused("FOREIGN KEY constraint failed"):
        write(listed, source_id=2)

    assert held(listed) == []


def test_a_source_that_countries_came_from_cannot_be_deleted(listed: Engine) -> None:
    keep(listed, a_country())

    with refused("FOREIGN KEY constraint failed"), unit_of_work(listed) as work:
        work.execute(delete(Source).where(Source.id == 1))

    with unit_of_work(listed) as work:
        assert work.get_one(Source, 1).name == "Example Standards Body"
    assert codes(listed) == [("NZ", "NZL", "New Zealand")]


def test_a_country_can_be_deleted_and_its_source_stays_and_can_then_be_deleted(
    listed: Engine,
) -> None:
    key = keep(listed, a_country())

    with unit_of_work(listed) as work:
        work.execute(delete(Country).where(Country.id == key))

    assert held(listed) == []
    with unit_of_work(listed) as work:
        assert work.get_one(Source, 1).name == "Example Standards Body"
        work.execute(delete(Source).where(Source.id == 1))
    with unit_of_work(listed) as work:
        assert work.scalars(select(Source)).all() == []


def test_the_key_of_a_deleted_country_is_not_given_again(listed: Engine) -> None:
    keep(listed, a_country())
    key = keep(listed, a_country(alpha_2="NU", alpha_3="NIU", name="Niue"))
    with unit_of_work(listed) as work:
        work.execute(delete(Country).where(Country.id == key))

    again = keep(listed, a_country(alpha_2="NU", alpha_3="NIU", name="Niue"))

    assert (key, again) == (2, 3)


@pytest.mark.parametrize(
    ("column", "text", "check"),
    [
        ("source_address", "standards.example/countries.csv", "source_address_web_address"),
        ("source_address", "ftp://standards.example/countries.csv", "source_address_web_address"),
        ("published_on", "2 November 2026", "published_on_calendar_day"),
        ("published_on", "2026-11-31", "published_on_calendar_day"),
        ("extraction_method", "dataset", "extraction_method_one_of"),
        ("extraction_method", "Public dataset", "extraction_method_one_of"),
        ("confidence", "certain", "confidence_one_of"),
        ("confidence", "", "confidence_one_of"),
        ("verification_status", "verified", "verification_status_one_of"),
        ("verification_status", "high", "verification_status_one_of"),
    ],
)
def test_the_table_holds_where_a_country_came_from_to_its_rules(
    listed: Engine, column: str, text: str, check: str
) -> None:
    with refused(f"CHECK constraint failed: ck_country_{check}"):
        write(listed, **{column: text})

    assert held(listed) == []


def test_a_country_was_not_last_seen_at_its_source_before_it_was_collected(
    listed: Engine,
) -> None:
    check = "CHECK constraint failed: ck_country_last_verified_at_not_before_collected_at"
    with refused(check):
        keep(listed, a_country(last_verified_at=COLLECTED - timedelta(microseconds=1)))
    with refused(check):
        write(listed, last_verified_at="2026-11-27T08:59:59.999999+00:00")

    assert held(listed) == []


@pytest.mark.parametrize("method", list(CollectionMethod))
@pytest.mark.parametrize("confidence", list(Confidence))
def test_a_country_can_be_got_in_every_way_and_be_of_every_confidence(
    listed: Engine, method: CollectionMethod, confidence: Confidence
) -> None:
    key = keep(listed, a_country(extraction_method=method, confidence=confidence))

    found = the_country(listed, key)

    assert found.extraction_method is method
    assert found.confidence is confidence


@pytest.mark.parametrize("status", list(VerificationStatus))
def test_a_country_can_be_of_every_standing(listed: Engine, status: VerificationStatus) -> None:
    key = keep(listed, a_country(verification_status=status))

    assert the_country(listed, key).verification_status is status


def test_the_countries_of_one_source_are_found_by_the_index(listed: Engine) -> None:
    with listed.connect() as connection:
        index = connection.exec_driver_sql("PRAGMA index_info(ix_country_source_id)").all()
        plan = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT * FROM country WHERE source_id = 1"
        ).all()
        to_delete_a_source = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN DELETE FROM source WHERE id = 1"
        ).all()

    assert [name for _, _, name in index] == ["source_id"]
    assert [detail for *_, detail in plan] == [
        "SEARCH country USING INDEX ix_country_source_id (source_id=?)"
    ]
    # Before a source is deleted SQLite looks whether countries came from
    # it, and the index alone answers that.
    assert [detail for *_, detail in to_delete_a_source if "country" in str(detail)] == [
        "SEARCH country USING COVERING INDEX ix_country_source_id (source_id=?)"
    ]


def test_a_country_is_changed_with_its_history(listed: Engine, clock: list[datetime]) -> None:
    key = keep(listed, a_country(name="Turkey", alpha_2="TR", alpha_3="TUR"))

    with unit_of_work(listed) as work:
        written = change(
            work,
            work.get_one(Country, key),
            {"name": "T\u00fcrkiye", "alpha_2": "TR", "last_verified_at": SEEN_AGAIN},
            decided_by="Jo Example",
        )

    assert [(row.field, row.old_value, row.new_value) for row in written] == [
        ("name", "Turkey", "T\u00fcrkiye"),
        (
            "last_verified_at",
            "2026-11-27T09:00:00.000000+00:00",
            "2026-11-28T09:00:00.000000+00:00",
        ),
    ]
    assert {(row.record_table, row.record_id, row.decided_by) for row in written} == {
        ("country", key, "Jo Example")
    }
    found = the_country(listed, key)
    assert (found.alpha_2, found.alpha_3, found.name) == ("TR", "TUR", "T\u00fcrkiye")
    assert found.last_verified_at == SEEN_AGAIN
    assert found.created_at == clock[0]
    assert found.updated_at == clock[1]
    assert {row.created_at for row in written} == {clock[1]}
    assert len(clock) == 2


def test_a_change_the_table_refuses_leaves_the_country_and_no_history(listed: Engine) -> None:
    key = keep(listed, a_country())

    with (
        refused("CHECK constraint failed: ck_country_alpha_2_two_capitals"),
        unit_of_work(listed) as work,
    ):
        change(work, work.get_one(Country, key), {"alpha_2": "nz"}, decided_by="Jo Example")

    assert codes(listed) == [("NZ", "NZL", "New Zealand")]
    with listed.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM record_change").scalar_one() == 0
