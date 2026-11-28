"""Tests of the table of the regions, against a real SQLite file.

The store of every test is built the way a real store is built: by the
migrations. What is stored through the model is also read as SQLite holds
it, and what the table must refuse is also written past the model.

What every table of collected records has is proved on tables made for
the purpose (``test_collected.py``, ``test_collected_index.py``); here
the real table is held to it.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta, timezone
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
SEEN_AGAIN = datetime(2026, 11, 28, 9, 0, tzinfo=UTC)
ADDRESS = "https://standards.example/regions.csv"
# What a region cannot be without: every column but the day its source
# says it was published.
NEEDED = [
    "country_id",
    "name",
    "source_id",
    "source_address",
    "collected_at",
    "last_verified_at",
    "extraction_method",
    "confidence",
    "verification_status",
]
# The two countries of the tests, by their keys.
NEW_ZEALAND = 1
AUSTRALIA = 2


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


@pytest.fixture
def mapped(newest: Engine) -> Engine:
    """The test's own store with the newest schema, one source and two countries in it.

    The key of the source is 1, New Zealand's is 1 and Australia's is 2.
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
    for two, three, name in [("NZ", "NZL", "New Zealand"), ("AU", "AUS", "Australia")]:
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


# A row written past the model, as plain SQL: every column but the key.
A_ROW = (
    "INSERT INTO region (country_id, name, source_id, source_address, collected_at, "
    "published_on, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def write(store: Engine, **said: object) -> None:
    """Write Canterbury past the model, with what the test says of it."""
    row: dict[str, object] = {
        "country_id": NEW_ZEALAND,
        "name": "Canterbury",
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
    assert len(row) == 12
    with store.begin() as connection:
        connection.exec_driver_sql(A_ROW, tuple(row.values()))


def held(store: Engine) -> list[tuple[object, ...]]:
    """The rows of the table as SQLite holds them, by their key."""
    with store.connect() as connection:
        return [
            tuple(row) for row in connection.exec_driver_sql("SELECT * FROM region ORDER BY id")
        ]


def names(store: Engine) -> list[tuple[int, str]]:
    """The country and the name of every region, by their key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT country_id, name FROM region ORDER BY id")
        return [(int(country), str(name)) for country, name in found]


def test_a_region_is_stored_and_read_back_with_everything_said_of_it(
    mapped: Engine, clock: list[datetime]
) -> None:
    in_another_zone = SEEN_AGAIN.astimezone(timezone(timedelta(hours=13)))
    before = len(clock)
    key = keep(
        mapped,
        a_region(published_on=date(2026, 11, 2), last_verified_at=in_another_zone),
    )

    found = the_region(mapped, key)

    assert found.id == key == 1
    assert found.country_id == NEW_ZEALAND
    assert found.name == "Canterbury"
    assert found.source_id == 1
    assert found.source_address == ADDRESS
    assert found.collected_at == COLLECTED
    assert found.published_on == date(2026, 11, 2)
    assert found.last_verified_at == SEEN_AGAIN
    assert found.last_verified_at.utcoffset() == timedelta(0)
    assert found.extraction_method is CollectionMethod.DATASET
    assert found.confidence is Confidence.HIGH
    assert found.verification_status is VerificationStatus.OFFICIAL
    assert found.created_at == found.updated_at == clock[before]
    assert len(clock) == before + 1


def test_what_the_table_holds_is_plain_text_and_whole_numbers(
    mapped: Engine, clock: list[datetime]
) -> None:
    before = len(clock)
    keep(mapped, a_region(published_on=date(2026, 11, 2), last_verified_at=SEEN_AGAIN))

    stored_at = clock[before].isoformat(timespec="microseconds")
    assert held(mapped) == [
        (
            1,
            1,
            None,
            "Canterbury",
            None,
            1,
            ADDRESS,
            "2026-11-27T09:00:00.000000+00:00",
            "2026-11-02",
            "2026-11-28T09:00:00.000000+00:00",
            "public dataset",
            "high",
            "official",
            stored_at,
            stored_at,
        )
    ]
    assert stored_at.endswith("+00:00")
    assert len(clock) == before + 1


def test_a_region_whose_source_gives_no_day_has_no_day(mapped: Engine) -> None:
    key = keep(mapped, a_region())

    assert the_region(mapped, key).published_on is None
    assert held(mapped)[0][8] is None


def test_a_row_written_past_the_model_is_read_as_a_region(mapped: Engine) -> None:
    write(mapped, published_on="2026-11-02")

    found = the_region(mapped, 1)

    assert (found.country_id, found.name) == (NEW_ZEALAND, "Canterbury")
    assert found.collected_at == found.last_verified_at == COLLECTED
    assert found.published_on == date(2026, 11, 2)
    assert found.extraction_method is CollectionMethod.DATASET
    assert found.created_at == COLLECTED + timedelta(seconds=5)


@pytest.mark.parametrize("column", NEEDED)
def test_a_region_without_what_it_cannot_be_without_is_refused(mapped: Engine, column: str) -> None:
    with refused(f"NOT NULL constraint failed: region.{column}"):
        write(mapped, **{column: None})

    assert held(mapped) == []


@pytest.mark.parametrize("column", NEEDED)
def test_the_model_gives_no_value_to_what_a_region_cannot_be_without(
    mapped: Engine, column: str
) -> None:
    with refused(f"NOT NULL constraint failed: region.{column}"):
        keep(mapped, a_region(**{column: None}))

    assert held(mapped) == []


def test_bytes_are_not_a_name(mapped: Engine) -> None:
    with refused("cannot store BLOB value in TEXT column region.name"):
        write(mapped, name=b"Canterbury")

    assert held(mapped) == []


@pytest.mark.parametrize("column", ["country_id", "source_id"])
def test_text_is_not_a_key(mapped: Engine, column: str) -> None:
    with refused(f"cannot store TEXT value in INTEGER column region.{column}"):
        write(mapped, **{column: "the first"})

    assert held(mapped) == []


def test_a_region_is_a_part_of_a_country_that_is_there(mapped: Engine) -> None:
    with refused("FOREIGN KEY constraint failed"):
        keep(mapped, a_region(country_id=3))
    with refused("FOREIGN KEY constraint failed"):
        write(mapped, country_id=3)

    assert held(mapped) == []


def test_a_region_cannot_be_moved_to_a_country_that_is_not_there(mapped: Engine) -> None:
    key = keep(mapped, a_region())

    with refused("FOREIGN KEY constraint failed"), unit_of_work(mapped) as work:
        work.get_one(Region, key).country_id = 3

    assert names(mapped) == [(NEW_ZEALAND, "Canterbury")]


def test_a_country_that_has_regions_cannot_be_deleted(mapped: Engine) -> None:
    keep(mapped, a_region())

    with refused("FOREIGN KEY constraint failed"), unit_of_work(mapped) as work:
        work.execute(delete(Country).where(Country.id == NEW_ZEALAND))

    with unit_of_work(mapped) as work:
        assert work.get_one(Country, NEW_ZEALAND).name == "New Zealand"
    assert names(mapped) == [(NEW_ZEALAND, "Canterbury")]


def test_a_country_without_regions_can_be_deleted_beside_one_that_has_them(
    mapped: Engine,
) -> None:
    keep(mapped, a_region())

    with unit_of_work(mapped) as work:
        work.execute(delete(Country).where(Country.id == AUSTRALIA))

    with unit_of_work(mapped) as work:
        assert [country.name for country in work.scalars(select(Country))] == ["New Zealand"]
    assert names(mapped) == [(NEW_ZEALAND, "Canterbury")]


def test_a_region_can_be_deleted_and_its_country_stays_and_can_then_be_deleted(
    mapped: Engine,
) -> None:
    key = keep(mapped, a_region())

    with unit_of_work(mapped) as work:
        work.execute(delete(Region).where(Region.id == key))

    assert held(mapped) == []
    with unit_of_work(mapped) as work:
        assert work.get_one(Country, NEW_ZEALAND).name == "New Zealand"
        work.execute(delete(Country).where(Country.id == NEW_ZEALAND))
    with unit_of_work(mapped) as work:
        assert [country.name for country in work.scalars(select(Country))] == ["Australia"]


def test_two_regions_of_one_country_cannot_have_one_name(mapped: Engine) -> None:
    keep(mapped, a_region())

    with refused("UNIQUE constraint failed: region.country_id, region.name"):
        keep(mapped, a_region(source_address="https://standards.example/more.csv"))
    with refused("UNIQUE constraint failed: region.country_id, region.name"):
        write(mapped, source_address="https://standards.example/more.csv")

    assert names(mapped) == [(NEW_ZEALAND, "Canterbury")]


def test_two_countries_can_each_have_a_region_of_one_name(mapped: Engine) -> None:
    first = keep(mapped, a_region())
    second = keep(mapped, a_region(country_id=AUSTRALIA))

    assert (first, second) == (1, 2)
    assert names(mapped) == [(NEW_ZEALAND, "Canterbury"), (AUSTRALIA, "Canterbury")]


def test_one_country_can_have_regions_of_several_names(mapped: Engine) -> None:
    keep(mapped, a_region())
    keep(mapped, a_region(name="Otago"))
    write(mapped, name="Southland")

    assert names(mapped) == [
        (NEW_ZEALAND, "Canterbury"),
        (NEW_ZEALAND, "Otago"),
        (NEW_ZEALAND, "Southland"),
    ]


def test_a_region_cannot_be_given_the_name_of_another_of_its_country(mapped: Engine) -> None:
    keep(mapped, a_region())
    key = keep(mapped, a_region(name="Otago"))

    with (
        refused("UNIQUE constraint failed: region.country_id, region.name"),
        unit_of_work(mapped) as work,
    ):
        work.get_one(Region, key).name = "Canterbury"

    assert names(mapped) == [(NEW_ZEALAND, "Canterbury"), (NEW_ZEALAND, "Otago")]


def test_a_region_cannot_be_moved_to_a_country_that_has_a_region_of_its_name(
    mapped: Engine,
) -> None:
    keep(mapped, a_region())
    key = keep(mapped, a_region(country_id=AUSTRALIA))

    with (
        refused("UNIQUE constraint failed: region.country_id, region.name"),
        unit_of_work(mapped) as work,
    ):
        work.get_one(Region, key).country_id = NEW_ZEALAND

    assert names(mapped) == [(NEW_ZEALAND, "Canterbury"), (AUSTRALIA, "Canterbury")]


@pytest.mark.parametrize(
    "other",
    [
        "canterbury",
        "CANTERBURY",
        "Canterbury ",
        " Canterbury",
        "Canterbury Region",
        "Cant\u00e9rbury",
    ],
    ids=repr,
)
def test_two_names_are_one_name_only_if_they_are_the_same_text(mapped: Engine, other: str) -> None:
    # The table does not judge whether two names mean one region. Whether
    # they do is a question for a person (the review queue).
    keep(mapped, a_region())
    keep(mapped, a_region(name=other))

    assert names(mapped) == [(NEW_ZEALAND, "Canterbury"), (NEW_ZEALAND, other)]


@pytest.mark.parametrize("text", ["", " ", " \t\n", "\u00a0"], ids=repr)
def test_the_table_refuses_an_empty_name(mapped: Engine, text: str) -> None:
    with refused("CHECK constraint failed: ck_region_name_not_empty"):
        write(mapped, name=text)
    with refused("CHECK constraint failed: ck_region_name_not_empty"):
        keep(mapped, a_region(name=text))

    assert held(mapped) == []


@pytest.mark.parametrize(
    "name",
    [
        "Manawat\u016b-Whanganui",
        "Hawke's Bay",
        "Provence-Alpes-C\u00f4te d'Azur",
        "\u00cele-de-France",
        "\u5317\u6d77\u9053",
        " Canterbury ",
        "canterbury",
    ],
)
def test_a_name_is_stored_as_it_was_given(mapped: Engine, name: str) -> None:
    key = keep(mapped, a_region(name=name))

    assert the_region(mapped, key).name == name
    assert names(mapped) == [(NEW_ZEALAND, name)]


def test_a_region_comes_from_a_source_that_is_there(mapped: Engine) -> None:
    with refused("FOREIGN KEY constraint failed"):
        keep(mapped, a_region(source_id=2))
    with refused("FOREIGN KEY constraint failed"):
        write(mapped, source_id=2)

    assert held(mapped) == []


def test_a_source_that_regions_came_from_cannot_be_deleted(mapped: Engine) -> None:
    with unit_of_work(mapped) as work:
        work.add(
            Source(
                name="Example Regions",
                website="https://regions.example",
                category=SourceCategory.GOVERNING_BODY,
                collection_method=CollectionMethod.DATASET,
            )
        )
    key = keep(mapped, a_region(source_id=2))

    with refused("FOREIGN KEY constraint failed"), unit_of_work(mapped) as work:
        work.execute(delete(Source).where(Source.id == 2))

    with unit_of_work(mapped) as work:
        assert work.get_one(Source, 2).name == "Example Regions"
    assert names(mapped) == [(NEW_ZEALAND, "Canterbury")]
    # With its regions taken away the source can go.
    with unit_of_work(mapped) as work:
        work.execute(delete(Region).where(Region.id == key))
        work.execute(delete(Source).where(Source.id == 2))
    with unit_of_work(mapped) as work:
        assert [source.name for source in work.scalars(select(Source))] == [
            "Example Standards Body"
        ]


def test_the_key_of_a_deleted_region_is_not_given_again(mapped: Engine) -> None:
    keep(mapped, a_region())
    key = keep(mapped, a_region(name="Otago"))
    with unit_of_work(mapped) as work:
        work.execute(delete(Region).where(Region.id == key))

    again = keep(mapped, a_region(name="Otago"))

    assert (key, again) == (2, 3)


@pytest.mark.parametrize(
    ("column", "text", "check"),
    [
        ("source_address", "standards.example/regions.csv", "source_address_web_address"),
        ("source_address", "ftp://standards.example/regions.csv", "source_address_web_address"),
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
def test_the_table_holds_where_a_region_came_from_to_its_rules(
    mapped: Engine, column: str, text: str, check: str
) -> None:
    with refused(f"CHECK constraint failed: ck_region_{check}"):
        write(mapped, **{column: text})

    assert held(mapped) == []


def test_a_region_was_not_last_seen_at_its_source_before_it_was_collected(
    mapped: Engine,
) -> None:
    check = "CHECK constraint failed: ck_region_last_verified_at_not_before_collected_at"
    with refused(check):
        keep(mapped, a_region(last_verified_at=COLLECTED - timedelta(microseconds=1)))
    with refused(check):
        write(mapped, last_verified_at="2026-11-27T08:59:59.999999+00:00")

    assert held(mapped) == []


@pytest.mark.parametrize("method", list(CollectionMethod))
@pytest.mark.parametrize("confidence", list(Confidence))
def test_a_region_can_be_got_in_every_way_and_be_of_every_confidence(
    mapped: Engine, method: CollectionMethod, confidence: Confidence
) -> None:
    key = keep(mapped, a_region(extraction_method=method, confidence=confidence))

    found = the_region(mapped, key)

    assert found.extraction_method is method
    assert found.confidence is confidence


@pytest.mark.parametrize("status", list(VerificationStatus))
def test_a_region_can_be_of_every_standing(mapped: Engine, status: VerificationStatus) -> None:
    key = keep(mapped, a_region(verification_status=status))

    assert the_region(mapped, key).verification_status is status


def test_the_regions_of_one_source_are_found_by_the_index(mapped: Engine) -> None:
    with mapped.connect() as connection:
        index = connection.exec_driver_sql("PRAGMA index_info(ix_region_source_id)").all()
        plan = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT * FROM region WHERE source_id = 1"
        ).all()
        to_delete_a_source = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN DELETE FROM source WHERE id = 1"
        ).all()

    assert [name for _, _, name in index] == ["source_id"]
    assert [detail for *_, detail in plan] == [
        "SEARCH region USING INDEX ix_region_source_id (source_id=?)"
    ]
    # Before a source is deleted SQLite looks whether regions came from
    # it, and the index alone answers that.
    assert [detail for *_, detail in to_delete_a_source if "region" in str(detail)] == [
        "SEARCH region USING COVERING INDEX ix_region_source_id (source_id=?)"
    ]


def test_the_regions_of_one_country_are_found_by_the_index_of_their_country(
    mapped: Engine,
) -> None:
    with mapped.connect() as connection:
        indexes = connection.exec_driver_sql("PRAGMA index_list(region)").all()
        index = connection.exec_driver_sql("PRAGMA index_info(ix_region_country_id)").all()
        of_a_country = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT * FROM region WHERE country_id = 1"
        ).all()
        by_name = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT * FROM region WHERE country_id = 1 AND name = 'Otago'"
        ).all()
        to_delete_a_country = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN DELETE FROM country WHERE id = 1"
        ).all()

    # Two indexes begin with the country. The one over the country alone is
    # over every region. The one of the rule of the names is over the
    # regions without a code only, so it cannot find the regions of a
    # country. The two indexes SQLite keeps are those of the rules that
    # are written into the table: a key and a country together once, for
    # the region a region is a part of, and the codes.
    assert sorted(
        (str(name), int(unique), int(partial)) for _, name, unique, _, partial in indexes
    ) == [
        ("ix_region_country_id", 0, 0),
        ("ix_region_country_id_name", 1, 1),
        ("ix_region_parent_id", 0, 0),
        ("ix_region_source_id", 0, 0),
        ("sqlite_autoindex_region_1", 1, 0),
        ("sqlite_autoindex_region_2", 1, 0),
    ]
    assert [name for _, _, name in index] == ["country_id"]
    assert [detail for *_, detail in of_a_country] == [
        "SEARCH region USING INDEX ix_region_country_id (country_id=?)"
    ]
    # The regions of one name are looked for among those of their country.
    assert [detail for *_, detail in by_name] == [
        "SEARCH region USING INDEX ix_region_country_id (country_id=?)"
    ]
    # Before a country is deleted SQLite looks whether it has regions, and
    # the index alone answers that.
    assert [detail for *_, detail in to_delete_a_country if "region" in str(detail)] == [
        "SEARCH region USING COVERING INDEX ix_region_country_id (country_id=?)"
    ]


def test_a_region_is_changed_with_its_history(mapped: Engine, clock: list[datetime]) -> None:
    key = keep(mapped, a_region(name="Manawatu-Wanganui"))
    stored = len(clock)

    with unit_of_work(mapped) as work:
        written = change(
            work,
            work.get_one(Region, key),
            {
                "name": "Manawat\u016b-Whanganui",
                "country_id": NEW_ZEALAND,
                "last_verified_at": SEEN_AGAIN,
            },
            decided_by="Jo Example",
        )

    assert [(row.field, row.old_value, row.new_value) for row in written] == [
        ("name", "Manawatu-Wanganui", "Manawat\u016b-Whanganui"),
        (
            "last_verified_at",
            "2026-11-27T09:00:00.000000+00:00",
            "2026-11-28T09:00:00.000000+00:00",
        ),
    ]
    assert {(row.record_table, row.record_id, row.decided_by) for row in written} == {
        ("region", key, "Jo Example")
    }
    found = the_region(mapped, key)
    assert (found.country_id, found.name) == (NEW_ZEALAND, "Manawat\u016b-Whanganui")
    assert found.last_verified_at == SEEN_AGAIN
    assert found.created_at == clock[stored - 1]
    assert found.updated_at == clock[stored]
    assert {row.created_at for row in written} == {clock[stored]}
    assert len(clock) == stored + 1


def test_a_change_the_table_refuses_leaves_the_region_and_no_history(mapped: Engine) -> None:
    keep(mapped, a_region())
    key = keep(mapped, a_region(name="Otago"))

    with (
        refused("UNIQUE constraint failed: region.country_id, region.name"),
        unit_of_work(mapped) as work,
    ):
        change(work, work.get_one(Region, key), {"name": "Canterbury"}, decided_by="Jo Example")

    assert names(mapped) == [(NEW_ZEALAND, "Canterbury"), (NEW_ZEALAND, "Otago")]
    with mapped.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM record_change").scalar_one() == 0
