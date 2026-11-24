"""Tests of calendar days in the store, without a store.

``tests/integration/test_days.py`` asks a real SQLite file what it refuses.
"""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import conv

from motosphere.db import times
from motosphere.db.base import NAMING, Base, broken_rules
from motosphere.db.checks import WithItsCheck
from motosphere.db.days import CalendarDay, calendar_day, from_text, to_text
from motosphere.db.times import UtcDateTime

# A day and its text, from the first day there is to the last.
DAYS = [
    (date(1, 1, 1), "0001-01-01"),
    (date(987, 6, 5), "0987-06-05"),
    (date(1957, 8, 4), "1957-08-04"),
    (date(2024, 2, 29), "2024-02-29"),
    (date(2026, 1, 5), "2026-01-05"),
    (date(2026, 11, 24), "2026-11-24"),
    (date(9999, 12, 31), "9999-12-31"),
]
EACH_DAY = pytest.mark.parametrize(("day", "text"), DAYS, ids=[text for _, text in DAYS])
# The moment a day begins in UTC: the time that looks most like a day.
MIDNIGHT = datetime(2026, 11, 24, tzinfo=UTC)


def said(name: str) -> str:
    """The check of a column of this name, as SQLite is given it."""
    written = calendar_day(name).sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )
    return str(written)


@EACH_DAY
def test_a_day_is_said_as_its_year_its_month_and_its_day(day: date, text: str) -> None:
    assert to_text(day) == text


@pytest.mark.parametrize(
    ("value", "sentence"),
    [
        ("2026-11-24", "Only a day (a date) is stored as a day, not str: '2026-11-24'."),
        (20261124, "Only a day (a date) is stored as a day, not int: 20261124."),
        (None, "Only a day (a date) is stored as a day, not NoneType: None."),
    ],
    ids=["text", "a number", "no value"],
)
def test_what_is_not_a_day_is_refused(value: Any, sentence: str) -> None:
    with pytest.raises(TypeError, match="Only a day") as refused:
        to_text(value)

    assert str(refused.value) == sentence


@pytest.mark.parametrize(
    ("moment", "written"),
    [
        (
            datetime(2026, 11, 24, 8, 0, tzinfo=UTC),
            "datetime.datetime(2026, 11, 24, 8, 0, tzinfo=datetime.timezone.utc)",
        ),
        (MIDNIGHT, "datetime.datetime(2026, 11, 24, 0, 0, tzinfo=datetime.timezone.utc)"),
        (MIDNIGHT.replace(tzinfo=None), "datetime.datetime(2026, 11, 24, 0, 0)"),
    ],
    ids=["a time", "midnight in UTC", "midnight without an offset"],
)
def test_a_time_is_refused_although_python_counts_it_as_a_day(
    moment: datetime, written: str
) -> None:
    assert isinstance(moment, date)

    with pytest.raises(TypeError, match="A time is not stored as a day") as refused:
        to_text(moment)

    assert str(refused.value) == (
        f"A time is not stored as a day: {written}. Say the day itself: which day a moment "
        "falls on depends on where one stands."
    )


@EACH_DAY
def test_a_day_in_the_stores_form_is_read(day: date, text: str) -> None:
    read = from_text(text)

    assert read == day
    # A day and nothing more: not a time at its midnight.
    assert type(read) is date


@pytest.mark.parametrize(
    "text",
    [
        "20261124",
        "2026-W48-2",
        "2026-11-24T00:00:00",
        "2026-11-24 ",
        " 2026-11-24",
        "2026-11-24\n",
        "2026-1-5",
        "24/11/2026",
        "2026-02-30",
        "0000-01-01",
        "",
        "now",
        20261124,
        None,
        date(2026, 11, 24),
    ],
    ids=[
        "without hyphens",
        "by week and weekday",
        "with a time",
        "with a space after it",
        "with a space before it",
        "with a new line after it",
        "with one digit for month and day",
        "day first",
        "a day no calendar has",
        "the year 0",
        "empty text",
        "a word",
        "a number",
        "no value",
        "a day that is not text",
    ],
)
def test_what_is_not_in_the_stores_form_is_refused_also_when_it_could_be_read(text: Any) -> None:
    with pytest.raises(ValueError, match="not in the store's form") as refused:
        from_text(text)

    assert str(refused.value) == (
        f"The store holds a day that is not in the store's form: {text!r}."
    )


def test_every_text_has_the_same_length_and_their_order_is_the_order_of_the_days() -> None:
    texts = [to_text(day) for day, _ in DAYS]

    assert {len(text) for text in texts} == {10}
    assert sorted(texts, reverse=True) == [to_text(day) for day, _ in sorted(DAYS, reverse=True)]


def test_the_column_type_stores_the_text_and_reads_the_day() -> None:
    column_type = CalendarDay()
    dialect = sqlite.dialect()

    assert column_type.process_bind_param(date(2026, 11, 24), dialect) == "2026-11-24"
    assert column_type.process_result_value("2026-11-24", dialect) == date(2026, 11, 24)


def test_the_column_type_leaves_no_value_as_no_value() -> None:
    column_type = CalendarDay()
    dialect = sqlite.dialect()

    assert column_type.process_bind_param(None, dialect) is None
    assert column_type.process_result_value(None, dialect) is None


def test_in_the_table_the_type_is_text() -> None:
    assert str(CalendarDay().compile(dialect=sqlite.dialect())) == "TEXT"


def test_the_check_asks_for_the_form_for_a_day_of_the_calendar_and_for_the_year_1_or_later() -> (
    None
):
    assert said("held_on") == (
        "(held_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]') "
        "AND date(held_on) IS held_on AND held_on >= '0001-01-01'"
    )


def test_the_check_of_a_column_named_with_a_word_of_sql_names_it_in_quotes() -> None:
    assert said("group") == (
        "(\"group\" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]') "
        'AND date("group") IS "group" AND "group" >= \'0001-01-01\''
    )


def test_the_check_is_named_after_its_column_and_by_the_naming_rule() -> None:
    check = calendar_day("held_on")

    assert check.name == "held_on_calendar_day"

    owner = Table(
        "owner",
        MetaData(naming_convention=NAMING),
        Column("id", Integer),
        Column("held_on", CalendarDay),
    )

    assert check not in owner.constraints

    owner.append_constraint(check)

    assert check.name == "ck_owner_held_on_calendar_day"
    assert isinstance(check.name, conv)


def test_the_type_brings_the_check_that_calendar_day_gives() -> None:
    its_type = CalendarDay()
    brought = its_type.check_for("held_on")

    assert isinstance(its_type, WithItsCheck)
    assert brought.name == "held_on_calendar_day"
    assert str(
        brought.sqltext.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    ) == said("held_on")
    assert its_type.refuses == "text that is not a calendar day"
    assert its_type.given_by == calendar_day.__name__


def test_a_column_that_is_a_day_is_named_until_its_table_has_the_check() -> None:
    schema = MetaData(naming_convention=NAMING)
    owner = Table(
        "owner",
        schema,
        Column("id", Integer, primary_key=True),
        Column("held_on", CalendarDay, nullable=False),
        Column("created_at", UtcDateTime, nullable=False, default=times.now),
        Column("updated_at", UtcDateTime, nullable=False, default=times.now, onupdate=times.now),
        sqlite_strict=True,
        sqlite_autoincrement=True,
    )

    assert broken_rules(schema) == [
        "The table owner does not refuse text that is not a calendar day in its column held_on: "
        "it must have the check that calendar_day gives for the column, named by the naming rule."
    ]

    owner.append_constraint(calendar_day("held_on"))

    assert broken_rules(schema) == []


def test_to_the_base_a_date_is_a_day_and_a_datetime_is_still_a_time() -> None:
    # Python counts a datetime as a date. The base does not take one for the other.
    assert Base.type_annotation_map[date] is CalendarDay
    assert Base.type_annotation_map[datetime] is UtcDateTime
