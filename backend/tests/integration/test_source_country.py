"""Tests of the country a source is of, against a real SQLite file.

The store of every test is built the way a real store is built: by the
migrations. What is stored through the model is also read as SQLite holds
it, and what the table must refuse is also written past the model.

A source can say which country it is of, and a country says which source
it came from. So the two tables point to each other, and the tests hold
what follows from that: which of the two can be deleted, and when.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Engine, delete, select, update
from sqlalchemy.exc import IntegrityError

from motosphere.db.models import Country, Source
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 27, 9, 0, tzinfo=UTC)
# The keys the fixture gives: its one source, and its two countries.
STANDARDS = 1
NEW_ZEALAND = 1
BRITAIN = 2
# A key no country has.
NO_COUNTRY = 99


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def a_country(alpha_2: str, alpha_3: str, name: str) -> Country:
    """A country as the one source of the fixture says it."""
    return Country(
        alpha_2=alpha_2,
        alpha_3=alpha_3,
        name=name,
        source_id=STANDARDS,
        source_address="https://standards.example/countries.csv",
        collected_at=COLLECTED,
        last_verified_at=COLLECTED,
        extraction_method=CollectionMethod.DATASET,
        confidence=Confidence.HIGH,
        verification_status=VerificationStatus.OFFICIAL,
    )


@pytest.fixture
def listed(newest: Engine) -> Engine:
    """The newest store with one source, of no country, and the two countries that came from it."""
    with unit_of_work(newest) as work:
        work.add(
            Source(
                name="Example Standards Body",
                website="https://standards.example",
                category=SourceCategory.GOVERNING_BODY,
                collection_method=CollectionMethod.DATASET,
            )
        )
    with unit_of_work(newest) as work:
        work.add(a_country("NZ", "NZL", "New Zealand"))
    with unit_of_work(newest) as work:
        work.add(a_country("GB", "GBR", "United Kingdom of Great Britain and Northern Ireland"))
    return newest


def a_source(**said: Any) -> Source:
    """A federation with what a source cannot be without, and what the test says of it."""
    described: dict[str, Any] = {
        "name": "Example Federation",
        "website": "https://federation.example",
        "category": SourceCategory.GOVERNING_BODY,
        "collection_method": CollectionMethod.RSS,
    }
    return Source(**(described | said))


def keep(store: Engine, source: Source) -> int:
    """Store a source in a unit of work of its own, and give its key."""
    with unit_of_work(store) as work:
        work.add(source)
    return source.id


def write(store: Engine, country_id: object, name: str = "Example Federation") -> None:
    """Write a source past the model, as plain SQL, with this in the column of its country."""
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "country_id, created_at, updated_at) VALUES (?, 'https://federation.example', "
            "'governing body', 'rss feed', 0, ?, '2026-11-27T10:00:00.000000+00:00', "
            "'2026-11-27T10:00:00.000000+00:00')",
            (name, country_id),
        )


def countries_of_the_sources(store: Engine) -> list[tuple[str, object]]:
    """The name of every source and the country SQLite holds for it, by the source's key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name, country_id FROM source ORDER BY id")
        return [(str(name), country) for name, country in found]


def codes(store: Engine) -> list[str]:
    """The code of two letters of every country, by its key."""
    with store.connect() as connection:
        return [
            str(code)
            for (code,) in connection.exec_driver_sql("SELECT alpha_2 FROM country ORDER BY id")
        ]


THE_SOURCE_OF_THE_FIXTURE = ("Example Standards Body", None)


def test_a_source_says_its_country_and_is_read_back_with_it(listed: Engine) -> None:
    key = keep(listed, a_source(country_id=NEW_ZEALAND))

    with unit_of_work(listed) as work:
        found = work.execute(select(Source).where(Source.id == key)).scalar_one()
        country = work.get_one(Country, found.country_id)

        assert found.country_id == NEW_ZEALAND
        assert (country.alpha_2, country.name) == ("NZ", "New Zealand")
    assert countries_of_the_sources(listed) == [
        THE_SOURCE_OF_THE_FIXTURE,
        ("Example Federation", NEW_ZEALAND),
    ]


def test_a_source_of_which_no_country_is_said_has_none(listed: Engine) -> None:
    key = keep(listed, a_source())

    with unit_of_work(listed) as work:
        assert work.get_one(Source, key).country_id is None
    assert countries_of_the_sources(listed) == [
        THE_SOURCE_OF_THE_FIXTURE,
        ("Example Federation", None),
    ]


def test_a_row_written_past_the_model_is_read_with_its_country(listed: Engine) -> None:
    write(listed, BRITAIN)
    write(listed, None, name="Example World Body")

    with unit_of_work(listed) as work:
        found = work.scalars(select(Source).order_by(Source.id)).all()

        assert [(source.name, source.country_id) for source in found] == [
            THE_SOURCE_OF_THE_FIXTURE,
            ("Example Federation", BRITAIN),
            ("Example World Body", None),
        ]


def test_the_country_of_a_source_is_one_that_is_there(listed: Engine) -> None:
    with refused("FOREIGN KEY constraint failed"):
        keep(listed, a_source(country_id=NO_COUNTRY))
    with refused("FOREIGN KEY constraint failed"):
        write(listed, NO_COUNTRY)
    with refused("FOREIGN KEY constraint failed"):
        write(listed, 0)

    assert countries_of_the_sources(listed) == [THE_SOURCE_OF_THE_FIXTURE]


def test_a_source_cannot_be_moved_to_a_country_that_is_not_there(listed: Engine) -> None:
    key = keep(listed, a_source(country_id=NEW_ZEALAND))

    with refused("FOREIGN KEY constraint failed"), unit_of_work(listed) as work:
        work.execute(update(Source).where(Source.id == key).values(country_id=NO_COUNTRY))

    assert countries_of_the_sources(listed)[1] == ("Example Federation", NEW_ZEALAND)


@pytest.mark.parametrize(
    ("value", "kind"),
    [("NZ", "TEXT"), ("1.5", "REAL"), (1.5, "REAL"), (b"\x01", "BLOB")],
    ids=["a code", "part of a number as text", "part of a number", "bytes"],
)
def test_the_country_of_a_source_is_a_key_and_nothing_else(
    listed: Engine, value: object, kind: str
) -> None:
    with refused(f"cannot store {kind} value in INTEGER column source.country_id"):
        write(listed, value)

    assert countries_of_the_sources(listed) == [THE_SOURCE_OF_THE_FIXTURE]


def test_a_source_is_given_a_country_later_and_another_and_none(listed: Engine) -> None:
    key = keep(listed, a_source())
    said: list[object] = []

    for country in (NEW_ZEALAND, BRITAIN, None):
        with unit_of_work(listed) as work:
            work.get_one(Source, key).country_id = country
        said.append(countries_of_the_sources(listed)[1][1])

    assert said == [NEW_ZEALAND, BRITAIN, None]


def test_two_sources_can_be_of_one_country(listed: Engine) -> None:
    keep(listed, a_source(country_id=NEW_ZEALAND))
    keep(listed, a_source(name="Example Club", country_id=NEW_ZEALAND))

    assert countries_of_the_sources(listed) == [
        THE_SOURCE_OF_THE_FIXTURE,
        ("Example Federation", NEW_ZEALAND),
        ("Example Club", NEW_ZEALAND),
    ]


def test_a_country_that_a_source_is_of_cannot_be_deleted(listed: Engine) -> None:
    keep(listed, a_source(country_id=BRITAIN))

    with refused("FOREIGN KEY constraint failed"), unit_of_work(listed) as work:
        work.execute(delete(Country).where(Country.id == BRITAIN))
    with refused("FOREIGN KEY constraint failed"), listed.begin() as connection:
        connection.exec_driver_sql("DELETE FROM country WHERE alpha_2 = 'GB'")

    assert codes(listed) == ["NZ", "GB"]
    assert countries_of_the_sources(listed)[1] == ("Example Federation", BRITAIN)


def test_a_country_that_no_source_is_of_can_be_deleted(listed: Engine) -> None:
    keep(listed, a_source(country_id=BRITAIN))

    with unit_of_work(listed) as work:
        work.execute(delete(Country).where(Country.id == NEW_ZEALAND))

    assert codes(listed) == ["GB"]
    assert countries_of_the_sources(listed)[1] == ("Example Federation", BRITAIN)


@pytest.mark.parametrize("then", ["of no country", "of another country", "deleted"])
def test_a_country_can_be_deleted_once_no_source_is_of_it_any_more(
    listed: Engine, then: str
) -> None:
    key = keep(listed, a_source(country_id=BRITAIN))

    with unit_of_work(listed) as work:
        if then == "of no country":
            work.get_one(Source, key).country_id = None
        elif then == "of another country":
            work.get_one(Source, key).country_id = NEW_ZEALAND
        else:
            work.execute(delete(Source).where(Source.id == key))
    with unit_of_work(listed) as work:
        work.execute(delete(Country).where(Country.id == BRITAIN))

    assert codes(listed) == ["NZ"]


def test_a_source_can_be_of_a_country_that_came_from_it(listed: Engine) -> None:
    # The body that publishes the list of the countries is itself of one
    # of them. The source is stored first, of no country; its countries
    # follow; and then it is said which of them it is of.
    with unit_of_work(listed) as work:
        work.get_one(Source, STANDARDS).country_id = BRITAIN

    with unit_of_work(listed) as work:
        source = work.get_one(Source, STANDARDS)
        country = work.get_one(Country, BRITAIN)

        assert (source.country_id, country.source_id) == (BRITAIN, STANDARDS)


def test_a_source_and_a_country_that_point_to_each_other_keep_each_other(
    listed: Engine,
) -> None:
    with unit_of_work(listed) as work:
        work.get_one(Source, STANDARDS).country_id = BRITAIN

    with refused("FOREIGN KEY constraint failed"), unit_of_work(listed) as work:
        work.execute(delete(Country).where(Country.id == BRITAIN))
    with refused("FOREIGN KEY constraint failed"), unit_of_work(listed) as work:
        work.execute(delete(Source).where(Source.id == STANDARDS))

    assert codes(listed) == ["NZ", "GB"]
    assert countries_of_the_sources(listed) == [("Example Standards Body", BRITAIN)]


def test_a_source_and_its_countries_are_taken_away_in_this_order(listed: Engine) -> None:
    with unit_of_work(listed) as work:
        work.get_one(Source, STANDARDS).country_id = BRITAIN

    # First the source is of no country any more, then its countries go,
    # and the source last.
    with unit_of_work(listed) as work:
        work.get_one(Source, STANDARDS).country_id = None
    with unit_of_work(listed) as work:
        work.execute(delete(Country))
    with unit_of_work(listed) as work:
        work.execute(delete(Source).where(Source.id == STANDARDS))

    assert codes(listed) == []
    assert countries_of_the_sources(listed) == []


def test_what_the_table_holds_of_a_country_is_its_key_as_a_whole_number(listed: Engine) -> None:
    keep(listed, a_source(country_id=BRITAIN))

    with listed.connect() as connection:
        held = connection.exec_driver_sql(
            "SELECT country_id, typeof(country_id) FROM source ORDER BY id"
        ).all()

    assert [tuple(row) for row in held] == [(None, "null"), (BRITAIN, "integer")]


@pytest.mark.parametrize("value", ["2", 2.0], ids=["as text", "with a point"])
def test_a_whole_number_written_another_way_is_stored_as_the_key_it_is(
    listed: Engine, value: object
) -> None:
    # SQLite itself reads such a value as the whole number it stands for
    # before it stores it, and the country must then be there.
    write(listed, value)

    with listed.connect() as connection:
        held = connection.exec_driver_sql(
            "SELECT country_id, typeof(country_id) FROM source WHERE id = 2"
        ).one()
    assert tuple(held) == (BRITAIN, "integer")
    with refused("FOREIGN KEY constraint failed"):
        write(listed, "99", name="Example Club")


def test_the_table_has_the_column_before_its_two_times(listed: Engine) -> None:
    with listed.connect() as connection:
        columns = connection.exec_driver_sql(
            "SELECT name, type, \"notnull\" FROM pragma_table_info('source')"
        ).all()
        points_to = connection.exec_driver_sql(
            'SELECT "table", "from", "to", on_update, on_delete '
            "FROM pragma_foreign_key_list('source')"
        ).all()

    assert [str(name) for name, _, _ in columns] == [
        "id",
        "name",
        "website",
        "category",
        "collection_method",
        "scan_every_hours",
        "terms_address",
        "licence",
        "usage_restrictions",
        "terms_read_at",
        "switched_on",
        "country_id",
        "created_at",
        "updated_at",
    ]
    assert [tuple(column) for column in columns if column[0] == "country_id"] == [
        ("country_id", "INTEGER", 0)
    ]
    # Nothing is done for a source when its country is deleted or its key
    # changed: the country is kept from both.
    assert [tuple(row) for row in points_to] == [
        ("country", "country_id", "id", "NO ACTION", "NO ACTION")
    ]


def test_the_sources_of_one_country_are_found_by_the_index(listed: Engine) -> None:
    with listed.connect() as connection:
        index = connection.exec_driver_sql("PRAGMA index_info(ix_source_country_id)").all()
        made_as = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE name = 'ix_source_country_id'"
        ).scalar_one()
        plan = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT * FROM source WHERE country_id = 1"
        ).all()
        to_delete_a_country = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN DELETE FROM country WHERE id = 1"
        ).all()

    assert [name for _, _, name in index] == ["country_id"]
    assert made_as == "CREATE INDEX ix_source_country_id ON source (country_id)"
    assert [detail for *_, detail in plan] == [
        "SEARCH source USING INDEX ix_source_country_id (country_id=?)"
    ]
    # Before a country is deleted SQLite looks whether a source is of it,
    # and the index alone answers that.
    assert [detail for *_, detail in to_delete_a_country if "source" in str(detail)] == [
        "SEARCH source USING COVERING INDEX ix_source_country_id (country_id=?)"
    ]


def test_the_sources_of_a_country_are_asked_for_through_the_model(listed: Engine) -> None:
    keep(listed, a_source(country_id=NEW_ZEALAND))
    keep(listed, a_source(name="Example Club", country_id=NEW_ZEALAND))
    keep(listed, a_source(name="Example World Body"))
    keep(listed, a_source(name="Example Union", country_id=BRITAIN))

    with unit_of_work(listed) as work:
        of_new_zealand = work.scalars(
            select(Source.name).where(Source.country_id == NEW_ZEALAND).order_by(Source.id)
        ).all()
        of_no_country = work.scalars(
            select(Source.name).where(Source.country_id.is_(None)).order_by(Source.id)
        ).all()

    assert of_new_zealand == ["Example Federation", "Example Club"]
    assert of_no_country == ["Example Standards Body", "Example World Body"]
