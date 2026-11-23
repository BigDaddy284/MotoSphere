"""Tests of the table of what the sources offer, against a real SQLite file.

The store of every test is built by the migrations, as a real store is.
What the table must refuse is also written past the model.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import IntegrityError

from motosphere.db.models import Source, SourceOffer
from motosphere.db.models.source import CollectionMethod, InformationType, SourceCategory
from motosphere.db.work import unit_of_work

MOMENT = "2026-11-19T08:00:00.000000+00:00"
BROKEN_KEY = "FOREIGN KEY constraint failed"
TWICE = "UNIQUE constraint failed: source_offer.source_id, source_offer.information_type"


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def a_source(store: Engine, name: str = "Example Federation") -> int:
    """Store a source, and give its key."""
    source = Source(
        name=name,
        website="https://federation.example",
        category=SourceCategory.GOVERNING_BODY,
        collection_method=CollectionMethod.RSS,
    )
    with unit_of_work(store) as work:
        work.add(source)
    return source.id


def offer(store: Engine, source: int, *types: InformationType) -> None:
    """Store that the source offers these kinds of information, in one unit of work."""
    with unit_of_work(store) as work:
        work.add_all(SourceOffer(source_id=source, information_type=one) for one in types)


def write(store: Engine, source: object, information_type: object) -> None:
    """Write an offer past the model, as plain SQL."""
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source_offer (source_id, information_type, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (source, information_type, MOMENT, MOMENT),
        )


def held(store: Engine) -> list[tuple[object, ...]]:
    """What the table holds, as SQLite holds it: the source and the kind, by their key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT source_id, information_type FROM source_offer ORDER BY id"
        )
        return [tuple(row) for row in found]


def sources(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM source ORDER BY id")
        return [str(name) for (name,) in found]


def test_an_offer_is_stored_and_read_back(newest: Engine) -> None:
    source = a_source(newest)
    offer(newest, source, InformationType.EVENTS)

    with unit_of_work(newest) as work:
        found = work.execute(select(SourceOffer)).scalar_one()

    assert found.id == 1
    assert found.source_id == source
    assert found.information_type is InformationType.EVENTS
    assert found.created_at == found.updated_at
    assert held(newest) == [(source, "events")]


def test_a_source_can_offer_several_kinds_of_information(newest: Engine) -> None:
    source = a_source(newest)

    offer(newest, source, InformationType.EVENTS, InformationType.RESULTS, InformationType.NEWS)

    assert held(newest) == [(source, "events"), (source, "results"), (source, "news")]


@pytest.mark.parametrize("information_type", list(InformationType))
def test_a_source_can_offer_every_kind_on_the_list(
    newest: Engine, information_type: InformationType
) -> None:
    source = a_source(newest)

    offer(newest, source, information_type)

    with unit_of_work(newest) as work:
        assert work.execute(select(SourceOffer.information_type)).scalar_one() is information_type


def test_a_source_does_not_offer_one_kind_twice(newest: Engine) -> None:
    source = a_source(newest)
    offer(newest, source, InformationType.EVENTS)

    with refused(TWICE):
        offer(newest, source, InformationType.EVENTS)

    assert held(newest) == [(source, "events")]


def test_offers_stored_together_are_kept_together_or_not_at_all(newest: Engine) -> None:
    source = a_source(newest)

    with refused(TWICE):
        offer(newest, source, InformationType.TRACKS, InformationType.NEWS, InformationType.TRACKS)

    assert held(newest) == []


def test_two_sources_can_offer_the_same_kind(newest: Engine) -> None:
    first = a_source(newest)
    second = a_source(newest, "Example Club")

    offer(newest, first, InformationType.EVENTS)
    offer(newest, second, InformationType.EVENTS)

    assert held(newest) == [(first, "events"), (second, "events")]


@pytest.mark.parametrize("text", ["weather", "Events", "event", "rss feed", ""])
def test_the_table_refuses_a_kind_that_is_not_on_the_list(newest: Engine, text: str) -> None:
    source = a_source(newest)

    with refused("CHECK constraint failed: ck_source_offer_information_type_one_of"):
        write(newest, source, text)

    assert held(newest) == []


def test_an_offer_belongs_to_a_source_that_exists(newest: Engine) -> None:
    source = a_source(newest)

    with refused(BROKEN_KEY):
        offer(newest, source + 1, InformationType.EVENTS)

    assert held(newest) == []


@pytest.mark.parametrize(
    ("source", "information_type", "column"),
    [(None, "events", "source_id"), (1, None, "information_type")],
)
def test_an_offer_names_its_source_and_its_kind(
    newest: Engine, source: object, information_type: object, column: str
) -> None:
    a_source(newest)

    with refused(f"NOT NULL constraint failed: source_offer.{column}"):
        write(newest, source, information_type)

    assert held(newest) == []


def test_a_source_that_has_offers_cannot_be_deleted(newest: Engine) -> None:
    source = a_source(newest)
    offer(newest, source, InformationType.EVENTS, InformationType.RESULTS)

    with refused(BROKEN_KEY), unit_of_work(newest) as work:
        work.execute(delete(Source).where(Source.id == source))

    assert sources(newest) == ["Example Federation"]
    assert held(newest) == [(source, "events"), (source, "results")]


def test_a_source_whose_offers_were_taken_away_can_be_deleted(newest: Engine) -> None:
    source = a_source(newest)
    other = a_source(newest, "Example Club")
    offer(newest, source, InformationType.EVENTS, InformationType.RESULTS)
    offer(newest, other, InformationType.EVENTS)

    with unit_of_work(newest) as work:
        work.execute(delete(SourceOffer).where(SourceOffer.source_id == source))
        work.execute(delete(Source).where(Source.id == source))

    assert sources(newest) == ["Example Club"]
    assert held(newest) == [(other, "events")]


def test_an_offer_cannot_be_moved_to_a_source_that_does_not_exist(newest: Engine) -> None:
    source = a_source(newest)
    offer(newest, source, InformationType.EVENTS)

    with refused(BROKEN_KEY), unit_of_work(newest) as work:
        work.execute(select(SourceOffer)).scalar_one().source_id = source + 1

    assert held(newest) == [(source, "events")]
