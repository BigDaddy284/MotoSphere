"""Tests of the form a time has in the data store, without a store.

``tests/integration/test_times.py`` stores times in a real SQLite file.
"""

from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from typing import Any

import pytest
from sqlalchemy.dialects import sqlite

from motosphere.db.times import UtcDateTime, from_text, to_text

A_TIME = datetime(2026, 11, 19, 8, 26, 4, 123456, tzinfo=UTC)
ITS_TEXT = "2026-11-19T08:26:04.123456+00:00"


def offset(hours: int, minutes: int = 0) -> timezone:
    """A zone that is always this far from UTC."""
    return timezone(timedelta(hours=hours, minutes=minutes))


class NoOffset(tzinfo):
    """A zone that does not say how far it is from UTC."""

    def utcoffset(self, _moment: datetime | None) -> timedelta | None:
        return None

    def dst(self, _moment: datetime | None) -> timedelta | None:
        return None

    def tzname(self, _moment: datetime | None) -> str | None:
        return None


def test_a_utc_time_is_said_with_its_offset_and_the_whole_fraction() -> None:
    assert to_text(A_TIME) == ITS_TEXT


@pytest.mark.parametrize(
    "moment",
    [
        datetime(2026, 11, 19, 10, 26, 4, 123456, tzinfo=offset(2)),
        datetime(2026, 11, 19, 2, 56, 4, 123456, tzinfo=offset(-5, -30)),
        datetime(2026, 11, 20, 1, 26, 4, 123456, tzinfo=offset(17)),
        datetime(2026, 11, 18, 22, 26, 4, 123456, tzinfo=offset(-10)),
    ],
    ids=["east of UTC", "west of UTC by hours and minutes", "the day after", "the day before"],
)
def test_a_time_with_another_offset_is_said_as_the_same_moment_in_utc(moment: datetime) -> None:
    assert moment == A_TIME

    assert to_text(moment) == ITS_TEXT


def test_every_text_has_the_same_length() -> None:
    texts = [
        to_text(datetime(2026, 11, 19, 8, 26, 4, tzinfo=UTC)),
        to_text(datetime(2026, 11, 19, 8, 26, tzinfo=UTC)),
        to_text(datetime(2026, 1, 2, 3, 4, 5, 6, tzinfo=UTC)),
        to_text(datetime(987, 6, 5, tzinfo=UTC)),
    ]

    assert texts == [
        "2026-11-19T08:26:04.000000+00:00",
        "2026-11-19T08:26:00.000000+00:00",
        "2026-01-02T03:04:05.000006+00:00",
        "0987-06-05T00:00:00.000000+00:00",
    ]
    assert {len(text) for text in texts} == {len(ITS_TEXT)}


def test_the_order_of_the_texts_is_the_order_of_the_times() -> None:
    in_order = [
        datetime(987, 6, 5, tzinfo=UTC),
        datetime(2026, 11, 19, 23, 0, tzinfo=offset(9)),
        datetime(2026, 11, 19, 8, 26, 4, tzinfo=offset(-8)),
        datetime(2026, 11, 19, 8, 26, 4, 1, tzinfo=offset(-8)),
        datetime(2026, 11, 20, 0, 30, tzinfo=offset(5, 30)),
        datetime(2026, 11, 19, 23, 59, 59, 999999, tzinfo=UTC),
        datetime(2026, 11, 20, tzinfo=UTC),
    ]
    assert sorted(in_order) == in_order

    texts = [to_text(moment) for moment in in_order]

    assert sorted(texts) == texts
    assert len(set(texts)) == len(texts)


def test_a_time_without_an_offset_is_refused() -> None:
    naive = A_TIME.replace(tzinfo=None)

    with pytest.raises(ValueError, match="without an offset") as refused:
        to_text(naive)

    assert str(refused.value) == (
        "A time without an offset is not stored: 2026-11-19T08:26:04.123456. "
        "Say which offset it has, for example with tzinfo=UTC."
    )


def test_a_time_whose_zone_gives_no_offset_is_refused() -> None:
    with pytest.raises(ValueError, match="A time without an offset is not stored"):
        to_text(A_TIME.replace(tzinfo=NoOffset()))


@pytest.mark.parametrize(
    ("moment", "sentence"),
    [
        (
            datetime.min.replace(tzinfo=offset(1)),
            "A time outside the years 1 to 9999 in UTC is not stored: 0001-01-01T00:00:00+01:00.",
        ),
        (
            datetime.max.replace(tzinfo=offset(-1)),
            "A time outside the years 1 to 9999 in UTC is not stored: "
            "9999-12-31T23:59:59.999999-01:00.",
        ),
    ],
    ids=["before the year 1", "after the year 9999"],
)
def test_a_time_that_utc_cannot_say_is_refused(moment: datetime, sentence: str) -> None:
    with pytest.raises(ValueError, match="outside the years") as refused:
        to_text(moment)

    assert str(refused.value) == sentence


@pytest.mark.parametrize(
    ("value", "sentence"),
    [
        (
            date(2026, 11, 19),
            "Only a time (a datetime) is stored as a time, not date: datetime.date(2026, 11, 19).",
        ),
        (ITS_TEXT, f"Only a time (a datetime) is stored as a time, not str: '{ITS_TEXT}'."),
        (1795076764, "Only a time (a datetime) is stored as a time, not int: 1795076764."),
    ],
    ids=["a date", "text", "a number"],
)
def test_what_is_not_a_time_is_refused(value: Any, sentence: str) -> None:
    with pytest.raises(TypeError, match="Only a time") as refused:
        to_text(value)

    assert str(refused.value) == sentence


def test_text_in_the_stores_form_is_read_as_an_aware_utc_time() -> None:
    moment = from_text(ITS_TEXT)

    assert moment == A_TIME
    assert moment.tzinfo == UTC
    assert moment.utcoffset() == timedelta(0)


def test_the_first_and_the_last_time_are_stored_and_read() -> None:
    first = datetime.min.replace(tzinfo=UTC)
    last = datetime.max.replace(tzinfo=UTC)

    assert to_text(first) == "0001-01-01T00:00:00.000000+00:00"
    assert to_text(last) == "9999-12-31T23:59:59.999999+00:00"
    assert from_text(to_text(first)) == first
    assert from_text(to_text(last)) == last


@pytest.mark.parametrize(
    "text",
    [
        "2026-11-19T08:26:04.123456",
        "2026-11-19T10:26:04.123456+02:00",
        "2026-11-19T08:26:04.123456Z",
        "2026-11-19T08:26:04.123456-00:00",
        "2026-11-19 08:26:04.123456+00:00",
        "2026-11-19T08:26:04+00:00",
        "2026-11-19T08:26:04.123+00:00",
        "2026-11-19T08:26:04.123456+00:00 ",
        "2026-11-19",
        "0001-01-01T00:00:00.000000+01:00",
        "yesterday",
        "",
    ],
    ids=[
        "no offset",
        "another offset",
        "Z for the offset",
        "the offset with a minus",
        "a space for the T",
        "no fraction",
        "three digits of the fraction",
        "a space after it",
        "a date",
        "a time UTC cannot say",
        "a word",
        "nothing",
    ],
)
def test_text_in_another_form_is_refused(text: str) -> None:
    with pytest.raises(ValueError, match="not in the store's form") as refused:
        from_text(text)

    assert str(refused.value) == (
        f"The store holds a time that is not in the store's form: {text!r}."
    )


def test_what_is_not_text_is_refused_as_a_time_of_the_store() -> None:
    a_number: Any = 1795076764

    with pytest.raises(ValueError, match="not in the store's form") as refused:
        from_text(a_number)

    assert str(refused.value) == (
        "The store holds a time that is not in the store's form: 1795076764."
    )


def test_the_column_type_stores_the_text_and_reads_the_time() -> None:
    column_type = UtcDateTime()
    dialect = sqlite.dialect()

    stored = column_type.process_bind_param(A_TIME.astimezone(offset(2)), dialect)

    assert stored == ITS_TEXT
    assert column_type.process_result_value(stored, dialect) == A_TIME


def test_the_column_type_leaves_no_time_as_no_time() -> None:
    column_type = UtcDateTime()
    dialect = sqlite.dialect()

    assert column_type.process_bind_param(None, dialect) is None
    assert column_type.process_result_value(None, dialect) is None


def test_the_column_type_is_text_in_the_table() -> None:
    assert str(UtcDateTime().compile(dialect=sqlite.dialect())) == "TEXT"
