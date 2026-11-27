"""Tests of the table of the information sources, against a real SQLite file.

The store of every test is built the way a real store is built: by the
migrations. What is stored through the model is also read as SQLite holds
it, and what the table must refuse is also written past the model.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError

from motosphere.db.models import Source
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

READ_AT = datetime(2026, 11, 18, 21, 30, tzinfo=UTC)
# What a source cannot be without.
NEEDED = ["name", "website", "category", "collection_method"]


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def a_source(**said: Any) -> Source:
    """A source with what a source cannot be without, and what the test says of it."""
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


def the_source(store: Engine, key: int) -> Source:
    """Read a source anew from the store."""
    with unit_of_work(store) as work:
        return work.execute(select(Source).where(Source.id == key)).scalar_one()


def write(store: Engine, **said: object) -> None:
    """Write a row past the model, as plain SQL. ``None`` leaves a column out."""
    row: dict[str, object] = {
        "name": "Example Federation",
        "website": "https://federation.example",
        "category": "governing body",
        "collection_method": "rss feed",
        "switched_on": 0,
        "created_at": "2026-11-19T08:00:00.000000+00:00",
        "updated_at": "2026-11-19T08:00:00.000000+00:00",
    } | said
    given = {column: value for column, value in row.items() if value is not None}
    with store.begin() as connection:
        connection.exec_driver_sql(
            f"INSERT INTO source ({', '.join(given)}) VALUES ({', '.join('?' * len(given))})",  # noqa: S608
            tuple(given.values()),
        )


def held(store: Engine) -> list[tuple[object, ...]]:
    """The rows of the table as SQLite holds them, by their key."""
    with store.connect() as connection:
        return [
            tuple(row) for row in connection.exec_driver_sql("SELECT * FROM source ORDER BY id")
        ]


def names(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM source ORDER BY id")
        return [str(name) for (name,) in found]


def test_a_source_is_stored_and_read_back_with_everything_said_of_it(
    newest: Engine, clock: list[datetime]
) -> None:
    in_another_zone = READ_AT.astimezone(timezone(timedelta(hours=1)))
    key = keep(
        newest,
        a_source(
            scan_every_hours=24,
            terms_address="https://federation.example/terms",
            licence="CC BY 4.0",
            usage_restrictions="Name the federation wherever its calendar is shown.",
            terms_read_at=in_another_zone,
            switched_on=True,
        ),
    )

    found = the_source(newest, key)

    assert found.id == key == 1
    assert found.name == "Example Federation"
    assert found.website == "https://federation.example"
    assert found.category is SourceCategory.GOVERNING_BODY
    assert found.collection_method is CollectionMethod.RSS
    assert found.scan_every_hours == 24
    assert found.terms_address == "https://federation.example/terms"
    assert found.licence == "CC BY 4.0"
    assert found.usage_restrictions == "Name the federation wherever its calendar is shown."
    assert found.terms_read_at == READ_AT
    assert found.terms_read_at.utcoffset() == timedelta(0)
    assert found.switched_on is True
    assert found.created_at == found.updated_at == clock[0]


def test_what_the_table_holds_is_plain_text_and_whole_numbers(
    newest: Engine, clock: list[datetime]
) -> None:
    keep(
        newest,
        a_source(
            scan_every_hours=24,
            terms_address="https://federation.example/terms",
            licence="CC BY 4.0",
            usage_restrictions="Name the federation wherever its calendar is shown.",
            terms_read_at=READ_AT,
            switched_on=True,
        ),
    )

    assert held(newest) == [
        (
            1,
            "Example Federation",
            "https://federation.example",
            "governing body",
            "rss feed",
            24,
            "https://federation.example/terms",
            "CC BY 4.0",
            "Name the federation wherever its calendar is shown.",
            "2026-11-18T21:30:00.000000+00:00",
            1,
            None,
            "2026-11-19T08:00:00.000000+00:00",
            "2026-11-19T08:00:00.000000+00:00",
        )
    ]


def test_a_new_source_is_switched_off_and_nothing_more_is_said_of_it(newest: Engine) -> None:
    key = keep(newest, a_source())

    found = the_source(newest, key)

    assert found.switched_on is False
    assert found.scan_every_hours is None
    assert found.terms_address is None
    assert found.licence is None
    assert found.usage_restrictions is None
    assert found.terms_read_at is None
    assert held(newest)[0][5:11] == (None, None, None, None, None, 0)


@pytest.mark.parametrize("column", NEEDED)
def test_a_source_without_what_it_cannot_be_without_is_refused(newest: Engine, column: str) -> None:
    with refused(f"NOT NULL constraint failed: source.{column}"):
        keep(newest, a_source(**{column: None}))

    assert held(newest) == []


def test_a_row_that_does_not_say_whether_it_is_switched_on_is_refused(newest: Engine) -> None:
    with refused("NOT NULL constraint failed: source.switched_on"):
        write(newest, switched_on=None)

    assert held(newest) == []


def test_two_sources_cannot_have_one_name(newest: Engine) -> None:
    keep(newest, a_source())

    with refused("UNIQUE constraint failed: source.name"):
        keep(newest, a_source(website="https://another.example"))

    assert names(newest) == ["Example Federation"]


def test_names_are_told_apart_letter_for_letter(newest: Engine) -> None:
    keep(newest, a_source())
    keep(newest, a_source(name="EXAMPLE FEDERATION"))
    keep(newest, a_source(name="Example Federation "))

    assert names(newest) == ["Example Federation", "EXAMPLE FEDERATION", "Example Federation "]


def test_two_sources_can_have_one_website(newest: Engine) -> None:
    keep(newest, a_source(name="Example Federation, news"))
    keep(
        newest,
        a_source(name="Example Federation, calendar", collection_method=CollectionMethod.HTML),
    )

    assert [row[1:5] for row in held(newest)] == [
        ("Example Federation, news", "https://federation.example", "governing body", "rss feed"),
        (
            "Example Federation, calendar",
            "https://federation.example",
            "governing body",
            "html extraction",
        ),
    ]


@pytest.mark.parametrize(
    ("column", "text"),
    [
        ("category", "blog"),
        ("category", "Governing Body"),
        ("category", "rss feed"),
        ("collection_method", "scraping"),
        ("collection_method", "RSS feed"),
        ("collection_method", "club"),
    ],
)
def test_the_table_refuses_what_is_not_on_the_list(newest: Engine, column: str, text: str) -> None:
    with refused(f"CHECK constraint failed: ck_source_{column}_one_of"):
        write(newest, **{column: text})

    assert held(newest) == []


@pytest.mark.parametrize("category", list(SourceCategory))
def test_a_source_can_be_of_every_kind_on_the_list(
    newest: Engine, category: SourceCategory
) -> None:
    key = keep(newest, a_source(category=category))

    assert the_source(newest, key).category is category


@pytest.mark.parametrize("method", list(CollectionMethod))
def test_a_source_can_be_collected_from_in_every_way_on_the_list(
    newest: Engine, method: CollectionMethod
) -> None:
    key = keep(newest, a_source(collection_method=method))

    assert the_source(newest, key).collection_method is method


@pytest.mark.parametrize("column", ["website", "terms_address"])
@pytest.mark.parametrize(
    "text", ["federation.example", "ftp://federation.example", "https://", "https://a b.example"]
)
def test_the_table_refuses_what_is_not_a_web_address(
    newest: Engine, column: str, text: str
) -> None:
    with refused(f"CHECK constraint failed: ck_source_{column}_web_address"):
        keep(newest, a_source(**{column: text}))

    assert held(newest) == []


@pytest.mark.parametrize("column", ["name", "licence", "usage_restrictions"])
@pytest.mark.parametrize("text", ["", " \t\n"])
def test_the_table_refuses_empty_text(newest: Engine, column: str, text: str) -> None:
    with refused(f"CHECK constraint failed: ck_source_{column}_not_empty"):
        keep(newest, a_source(**{column: text}))

    assert held(newest) == []


@pytest.mark.parametrize("hours", [0, -1, -24])
def test_a_source_is_not_scanned_every_nought_hours_or_fewer(newest: Engine, hours: int) -> None:
    with refused("CHECK constraint failed: ck_source_scan_every_hours_positive"):
        keep(newest, a_source(scan_every_hours=hours))

    assert held(newest) == []


@pytest.mark.parametrize("hours", [1, 24, 24 * 366])
def test_a_source_is_scanned_every_so_many_whole_hours(newest: Engine, hours: int) -> None:
    key = keep(newest, a_source(scan_every_hours=hours))

    assert the_source(newest, key).scan_every_hours == hours


def test_part_of_an_hour_is_refused(newest: Engine) -> None:
    with refused("cannot store REAL value in INTEGER column source.scan_every_hours"):
        write(newest, scan_every_hours=0.5)

    assert held(newest) == []


def test_a_source_whose_terms_were_not_read_is_not_stored_switched_on(newest: Engine) -> None:
    with refused("CHECK constraint failed: ck_source_switched_on_terms_read"):
        keep(newest, a_source(switched_on=True))

    assert held(newest) == []


def test_a_source_whose_terms_were_not_read_cannot_be_switched_on_later(newest: Engine) -> None:
    key = keep(newest, a_source())

    with (
        refused("CHECK constraint failed: ck_source_switched_on_terms_read"),
        unit_of_work(newest) as work,
    ):
        work.get_one(Source, key).switched_on = True

    assert the_source(newest, key).switched_on is False


def test_a_source_is_switched_on_once_its_terms_were_read(newest: Engine) -> None:
    key = keep(newest, a_source())

    with unit_of_work(newest) as work:
        source = work.get_one(Source, key)
        source.terms_read_at = READ_AT
        source.switched_on = True

    found = the_source(newest, key)
    assert found.switched_on is True
    assert found.terms_read_at == READ_AT


def test_a_source_that_is_switched_on_cannot_lose_when_its_terms_were_read(newest: Engine) -> None:
    key = keep(newest, a_source(terms_read_at=READ_AT, switched_on=True))

    with (
        refused("CHECK constraint failed: ck_source_switched_on_terms_read"),
        unit_of_work(newest) as work,
    ):
        work.get_one(Source, key).terms_read_at = None

    assert the_source(newest, key).terms_read_at == READ_AT


def test_a_source_can_be_switched_off_again_and_keeps_when_its_terms_were_read(
    newest: Engine,
) -> None:
    key = keep(newest, a_source(terms_read_at=READ_AT, switched_on=True))

    with unit_of_work(newest) as work:
        work.get_one(Source, key).switched_on = False

    found = the_source(newest, key)
    assert found.switched_on is False
    assert found.terms_read_at == READ_AT


def test_a_source_that_is_changed_says_when(newest: Engine, clock: list[datetime]) -> None:
    key = keep(newest, a_source())

    with unit_of_work(newest) as work:
        work.get_one(Source, key).scan_every_hours = 168

    found = the_source(newest, key)
    assert found.scan_every_hours == 168
    assert found.created_at == clock[0]
    assert found.updated_at == clock[1]
