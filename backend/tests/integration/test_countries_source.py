"""Tests of the source of the countries in the store, against a real SQLite file.

The store of every test is built the way a real store is built: by the
migrations. What the function stores is read as SQLite holds it, and a
source it must refuse or leave alone is written the way a person or
another program would have written it.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Engine, select

from motosphere.db.models import Country, Source, SourceOffer
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, InformationType, SourceCategory
from motosphere.db.work import unit_of_work
from motosphere.reference.countries_source import (
    LICENCE,
    NAME,
    USAGE_RESTRICTIONS,
    WEBSITE,
    CountriesSourceError,
    source_of_the_countries,
)

# What the set clock says first, as the store keeps it.
MOMENT = "2026-11-19T08:00:00.000000+00:00"
READ = datetime(2026, 11, 28, 10, 30, tzinfo=UTC)
READ_AS_KEPT = "2026-11-28T10:30:00.000000+00:00"
RESTRICTIONS = (
    "Every copy keeps the notice of copyright and comes with the licence. "
    "A changed copy says that it was changed, and when. "
    "A work that takes over the list, or part of it, is passed on under the same licence, "
    "free of charge."
)
# The row of the source as the function stores it in an empty store.
AS_STORED = (
    1,
    "iso-codes",
    "https://salsa.debian.org/iso-codes-team/iso-codes",
    "reference list",
    "public dataset",
    None,
    None,
    "LGPL-2.1-or-later",
    RESTRICTIONS,
    None,
    0,
    None,
    MOMENT,
    MOMENT,
)


def sources(store: Engine) -> list[tuple[object, ...]]:
    """Every row of the table of the sources, as SQLite holds it, by its key."""
    with store.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT id, name, website, category, collection_method, scan_every_hours, "
            "terms_address, licence, usage_restrictions, terms_read_at, switched_on, "
            "country_id, created_at, updated_at FROM source ORDER BY id"
        )
        return [tuple(row) for row in rows]


def offers(store: Engine) -> list[tuple[object, ...]]:
    """Every offer SQLite holds: its source and its kind, by its key."""
    with store.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT source_id, information_type FROM source_offer ORDER BY id"
        )
        return [tuple(row) for row in rows]


def the_source(**said: Any) -> Source:
    """The source of the countries as the pipeline describes it, and what the test says of it."""
    described: dict[str, Any] = {
        "name": NAME,
        "website": WEBSITE,
        "category": SourceCategory.REFERENCE,
        "collection_method": CollectionMethod.DATASET,
        "licence": LICENCE,
        "usage_restrictions": USAGE_RESTRICTIONS,
    }
    return Source(**(described | said))


def keep(store: Engine, source: Source, *kinds: InformationType) -> int:
    """Store a source with these offers, each in a unit of work of its own, and give its key."""
    with unit_of_work(store) as work:
        work.add(source)
    with unit_of_work(store) as work:
        work.add_all(SourceOffer(source_id=source.id, information_type=kind) for kind in kinds)
    return source.id


@pytest.mark.usefixtures("clock")
def test_the_source_is_stored_as_the_pipeline_describes_it(newest: Engine) -> None:
    with unit_of_work(newest) as work:
        source = source_of_the_countries(work)

    assert source.id == 1
    assert sources(newest) == [AS_STORED]
    assert offers(newest) == [(1, "reference data")]


def test_what_the_module_says_is_what_the_tests_expect() -> None:
    # The texts are written out a second time here, so that a change to
    # what the store is told is made in two places and seen.
    assert (AS_STORED[1], AS_STORED[2], AS_STORED[7]) == (NAME, WEBSITE, LICENCE)
    assert RESTRICTIONS == USAGE_RESTRICTIONS


@pytest.mark.usefixtures("clock")
def test_a_new_source_is_switched_off_and_nobody_has_read_its_terms(newest: Engine) -> None:
    with unit_of_work(newest) as work:
        source = source_of_the_countries(work)

    assert source.switched_on is False
    assert source.terms_read_at is None
    assert source.scan_every_hours is None
    assert source.country_id is None


@pytest.mark.usefixtures("clock")
def test_the_source_is_stored_once_however_often_it_is_asked_for(newest: Engine) -> None:
    with unit_of_work(newest) as work:
        first = source_of_the_countries(work)
        again = source_of_the_countries(work)
        assert again is first
    with unit_of_work(newest) as work:
        later = source_of_the_countries(work)
        assert source_of_the_countries(work) is later

    assert later.id == first.id == 1
    # Nothing was written the other three times: not even when it was last changed.
    assert sources(newest) == [AS_STORED]
    assert offers(newest) == [(1, "reference data")]


@pytest.mark.usefixtures("clock")
def test_the_source_takes_the_next_key_and_other_sources_are_left_alone(newest: Engine) -> None:
    federation = Source(
        name="Example Federation",
        website="https://federation.example",
        category=SourceCategory.GOVERNING_BODY,
        collection_method=CollectionMethod.RSS,
    )
    keep(newest, federation, InformationType.EVENTS, InformationType.REFERENCE)
    before = sources(newest)

    with unit_of_work(newest) as work:
        source = source_of_the_countries(work)

    assert source.id == 2
    assert sources(newest)[:1] == before
    assert [row[1] for row in sources(newest)] == ["Example Federation", "iso-codes"]
    assert offers(newest) == [(1, "events"), (1, "reference data"), (2, "reference data")]


@pytest.mark.parametrize("name", ["ISO-codes", "iso-codes 4", "iso codes"])
def test_a_source_of_another_name_is_another_source(newest: Engine, name: str) -> None:
    keep(newest, the_source(name=name), InformationType.REFERENCE)

    with unit_of_work(newest) as work:
        source = source_of_the_countries(work)

    assert source.id == 2
    assert [row[1] for row in sources(newest)] == [name, "iso-codes"]


def test_a_source_that_is_there_as_described_is_given_and_nothing_is_written(
    newest: Engine,
) -> None:
    key = keep(newest, the_source(), InformationType.REFERENCE)
    before = sources(newest)

    with unit_of_work(newest) as work:
        source = source_of_the_countries(work)

    assert source.id == key
    assert sources(newest) == before
    assert offers(newest) == [(key, "reference data")]


def test_what_people_have_said_of_the_source_is_left_as_it_is(newest: Engine) -> None:
    key = keep(newest, the_source(), InformationType.REFERENCE)
    with unit_of_work(newest) as work:
        work.add(
            Country(
                alpha_2="NZ",
                alpha_3="NZL",
                name="New Zealand",
                source_id=key,
                source_address="https://standards.example/countries.csv",
                collected_at=READ,
                last_verified_at=READ,
                extraction_method=CollectionMethod.DATASET,
                confidence=Confidence.HIGH,
                verification_status=VerificationStatus.INDEPENDENT,
            )
        )
    with unit_of_work(newest) as work:
        stored = work.get_one(Source, key)
        stored.terms_read_at = READ
        stored.switched_on = True
        stored.scan_every_hours = 720
        stored.country_id = 1
    before = sources(newest)
    assert before[0][5] == 720
    assert before[0][9:12] == (READ_AS_KEPT, 1, 1)

    with unit_of_work(newest) as work:
        source = source_of_the_countries(work)

    assert source.id == key
    assert source.switched_on is True
    assert source.terms_read_at == READ
    assert sources(newest) == before


def test_the_source_may_offer_more_than_the_pipeline_says(newest: Engine) -> None:
    key = keep(newest, the_source(), InformationType.NEWS, InformationType.REFERENCE)

    with unit_of_work(newest) as work:
        source = source_of_the_countries(work)

    assert source.id == key
    assert offers(newest) == [(key, "news"), (key, "reference data")]


@pytest.mark.parametrize(
    ("said", "word"),
    [
        ({"website": "https://iso-codes.example"}, "website"),
        ({"website": WEBSITE + "/"}, "website"),
        ({"category": SourceCategory.ARCHIVE}, "kind"),
        ({"collection_method": CollectionMethod.STRUCTURED_FEED}, "way of collecting"),
        ({"terms_address": "https://iso-codes.example/terms"}, "address of its terms"),
        ({"licence": "LGPL-2.1-only"}, "licence"),
        ({"licence": None}, "licence"),
        ({"usage_restrictions": "None."}, "restrictions of use"),
        ({"usage_restrictions": None}, "restrictions of use"),
    ],
)
def test_a_source_of_the_name_that_is_described_otherwise_is_refused(
    newest: Engine, said: dict[str, Any], word: str
) -> None:
    keep(newest, the_source(**said), InformationType.REFERENCE)
    before = sources(newest)

    with pytest.raises(CountriesSourceError) as refusal, unit_of_work(newest) as work:
        source_of_the_countries(work)

    assert str(refusal.value) == (
        'The store has a source called "iso-codes" that is not the source of the countries '
        f"as the pipeline describes it. It differs in its {word}. Nothing was changed."
    )
    assert sources(newest) == before
    assert offers(newest) == [(1, "reference data")]


@pytest.mark.parametrize("kinds", [(), (InformationType.NEWS,)])
def test_a_source_of_the_name_that_does_not_offer_reference_data_is_refused(
    newest: Engine, kinds: tuple[InformationType, ...]
) -> None:
    keep(newest, the_source(), *kinds)
    before = sources(newest)

    with pytest.raises(CountriesSourceError) as refusal, unit_of_work(newest) as work:
        source_of_the_countries(work)

    assert str(refusal.value) == (
        'The store has a source called "iso-codes" that is not the source of the countries '
        'as the pipeline describes it. It differs in its offer of "reference data". '
        "Nothing was changed."
    )
    assert sources(newest) == before
    assert offers(newest) == [(1, str(kind)) for kind in kinds]


def test_what_another_source_offers_does_not_count_for_this_one(newest: Engine) -> None:
    federation = Source(
        name="Example Federation",
        website="https://federation.example",
        category=SourceCategory.GOVERNING_BODY,
        collection_method=CollectionMethod.RSS,
    )
    keep(newest, federation, InformationType.REFERENCE)
    keep(newest, the_source(), InformationType.NEWS)

    with (
        pytest.raises(CountriesSourceError, match='It differs in its offer of "reference data"'),
        unit_of_work(newest) as work,
    ):
        source_of_the_countries(work)

    assert offers(newest) == [(1, "reference data"), (2, "news")]


def test_a_refusal_names_everything_that_differs_in_the_order_of_the_table(
    newest: Engine,
) -> None:
    keep(
        newest,
        the_source(
            licence="LGPL-2.1-only",
            website="https://iso-codes.example",
            collection_method=CollectionMethod.STRUCTURED_FEED,
        ),
    )

    with pytest.raises(CountriesSourceError) as refusal, unit_of_work(newest) as work:
        source_of_the_countries(work)

    assert str(refusal.value) == (
        'The store has a source called "iso-codes" that is not the source of the countries '
        "as the pipeline describes it. It differs in its website, way of collecting, licence "
        'and offer of "reference data". Nothing was changed.'
    )


def test_a_refusal_names_two_things_that_differ(newest: Engine) -> None:
    keep(newest, the_source(category=SourceCategory.ARCHIVE, licence="LGPL-2.1-only"))

    def the_work() -> None:
        with unit_of_work(newest) as work:
            work.add(SourceOffer(source_id=1, information_type=InformationType.REFERENCE))
            source_of_the_countries(work)

    with pytest.raises(CountriesSourceError, match="It differs in its kind and licence\\. "):
        the_work()

    # The offer the unit of work added before the refusal went with it.
    assert offers(newest) == []


def test_the_source_is_kept_or_taken_back_with_its_unit_of_work(newest: Engine) -> None:
    def the_work() -> None:
        with unit_of_work(newest) as work:
            source = source_of_the_countries(work)
            # It is written when the function returns, with its offer, and
            # is in the store for the rest of the unit of work.
            assert not work.new
            assert work.scalars(select(Source.name)).all() == ["iso-codes"]
            assert source.id == 1
            raise RuntimeError("the job died")

    with pytest.raises(RuntimeError, match="the job died"):
        the_work()

    assert sources(newest) == []
    assert offers(newest) == []
