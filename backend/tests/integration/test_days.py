"""Tests of calendar days in the store, with a table made in a real SQLite file.

The model here is made for the tests. It is a subclass of the real
``Base``, so it proves what a model gets when it says that a column is a
``date``, but it is kept in a schema of its own (``Proof.metadata``), so
the real schema never sees it.
"""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import Date, Engine, MetaData, func, select
from sqlalchemy.exc import IntegrityError, OperationalError, StatementError
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base, broken_rules
from motosphere.db.days import CalendarDay
from motosphere.db.times import UtcDateTime
from motosphere.db.work import unit_of_work

A_TIME = "2026-11-19T08:00:00.000000+00:00"
A_DAY = date(2026, 11, 24)
THE_FIRST = date(1957, 8, 4)
REFUSED = "CHECK constraint failed: ck_proof_race_{}_calendar_day"
NOT_A_DAY = "Only a day \\(a date\\) is stored as a day"
A_TIME_IS_NO_DAY = "A time is not stored as a day"
# A row written with plain SQL. Its first three "?" are held_on, announced_on
# and first_held_on; the last two are its two times, which only the store's
# code sets.
PAST_THE_MODEL = (
    "INSERT INTO proof_race (held_on, announced_on, first_held_on, created_at, updated_at) "
    "VALUES (?, ?, ?, ?, ?)"
)
# The day 2026-11-24 with the digits of its year as they are written full width.
IN_ANOTHER_SCRIPT = "".join(chr(0xFF10 + digit) for digit in (2, 0, 2, 6)) + "-11-24"
# Text that is not a day in the store's form, each with what it is.
NOT_DAYS = {
    "the 30th of February": "2026-02-30",
    "the 29th of February of a year that has none": "2025-02-29",
    "the 29th of February 1900": "1900-02-29",
    "the 31st of November": "2026-11-31",
    "a 13th month": "2026-13-01",
    "the day 0": "2026-11-00",
    "the year 0": "0000-01-01",
    "with a time": "2026-11-24T08:00:00",
    "with a space after it": "2026-11-24 ",
    "with a space before it": " 2026-11-24",
    "with one digit for month and day": "2026-1-5",
    "without hyphens": "20261124",
    "day first": "24/11/2026",
    "by week and weekday": "2026-W48-2",
    "with five digits for the year": "10000-01-01",
    "with a character of the number 0 after it": "2026-11-24\x00",
    "with digits of another script": IN_ANOTHER_SCRIPT,
    "the number of a day as astronomers count them": "2460000",
    "the word now": "now",
    "empty text": "",
}


class Proof(Base):
    """A model of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofRace(Proof):
    __tablename__ = "proof_race"

    held_on: Mapped[date]
    # No value or a day.
    announced_on: Mapped[date | None]
    # A model that says more of the column: the value it has when none is given.
    first_held_on: Mapped[date] = mapped_column(default=THE_FIRST)
    # A time, as before: Python counts a datetime as a date, and the base does not.
    started_at: Mapped[datetime | None]


class Named(Base):
    """A schema for a model that names SQLAlchemy's own type for a day."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofHeat(Named):
    __tablename__ = "proof_heat"

    held_on: Mapped[date] = mapped_column(Date)


@pytest.fixture
def made(store: Engine) -> Engine:
    """The store, with the table of the tests made in it."""
    with store.begin() as connection:
        Proof.metadata.create_all(connection)
    return store


def stored(made: Engine) -> list[tuple[Any, ...]]:
    """What the file holds of every race, with what kind of value it is, read without the model."""
    with made.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT held_on, typeof(held_on), announced_on, typeof(announced_on), "
            "first_held_on, typeof(first_held_on) FROM proof_race ORDER BY id"
        ).all()
    return [tuple(row) for row in rows]


def test_a_day_is_text_in_a_strict_table_and_a_time_is_still_a_time(made: Engine) -> None:
    columns = ProofRace.__table__.c

    assert [column.name for column in columns if isinstance(column.type, CalendarDay)] == [
        "held_on",
        "announced_on",
        "first_held_on",
    ]
    assert [column.name for column in columns if isinstance(column.type, UtcDateTime)] == [
        "started_at",
        "created_at",
        "updated_at",
    ]
    assert broken_rules(Proof.metadata) == []

    with made.connect() as connection:
        in_the_file = {
            name: (declared, bool(required))
            for _, name, declared, required, _, _ in connection.exec_driver_sql(
                "PRAGMA table_info(proof_race)"
            )
        }

    assert in_the_file == {
        "id": ("INTEGER", True),
        "held_on": ("TEXT", True),
        "announced_on": ("TEXT", False),
        "first_held_on": ("TEXT", True),
        "started_at": ("TEXT", False),
        "created_at": ("TEXT", True),
        "updated_at": ("TEXT", True),
    }


def test_the_file_has_a_check_named_by_the_rule_for_each_such_column_and_for_no_other(
    made: Engine,
) -> None:
    with made.connect() as connection:
        written = str(
            connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'proof_race'"
            ).scalar_one()
        )

    def check(name: str) -> str:
        return (
            f"CONSTRAINT ck_proof_race_{name}_calendar_day CHECK "
            f"(({name} GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]') "
            f"AND date({name}) IS {name} AND {name} >= '0001-01-01')"
        )

    assert [line.strip().rstrip(",") for line in written.splitlines() if "CHECK" in line] == [
        check("held_on"),
        check("announced_on"),
        check("first_held_on"),
    ]


@pytest.mark.parametrize(
    ("day", "text"),
    [
        (date(2026, 11, 24), "2026-11-24"),
        (date(2026, 1, 5), "2026-01-05"),
        (date(2024, 2, 29), "2024-02-29"),
        (date(2000, 2, 29), "2000-02-29"),
        (date(987, 6, 5), "0987-06-05"),
        (date(1, 1, 1), "0001-01-01"),
        (date(9999, 12, 31), "9999-12-31"),
    ],
    ids=[
        "a day",
        "a day of one digit in a month of one",
        "the 29th of February",
        "the 29th of February 2000",
        "a year of three digits",
        "the first day there is",
        "the last day there is",
    ],
)
def test_a_day_is_stored_as_text_in_one_form_and_comes_back_as_the_day(
    made: Engine, day: date, text: str
) -> None:
    with unit_of_work(made) as work:
        work.add(ProofRace(held_on=day, announced_on=day, first_held_on=day))

    assert stored(made) == [(text, "text", text, "text", text, "text")]
    with unit_of_work(made) as work:
        race = work.scalars(select(ProofRace)).one()
        assert (race.held_on, race.announced_on, race.first_held_on) == (day, day, day)
        # A day and nothing more: not a time at its midnight.
        assert type(race.held_on) is date


def test_a_column_that_may_be_without_a_value_holds_none_or_a_day(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all([ProofRace(held_on=A_DAY, announced_on=day) for day in (None, THE_FIRST)])

    assert [(announced, kind) for _, _, announced, kind, _, _ in stored(made)] == [
        (None, "null"),
        ("1957-08-04", "text"),
    ]
    with unit_of_work(made) as work:
        races = work.scalars(select(ProofRace).order_by(ProofRace.id)).all()
        assert [race.announced_on for race in races] == [None, THE_FIRST]


def test_a_column_given_no_value_gets_the_one_its_model_says(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofRace(held_on=A_DAY))

    assert stored(made) == [("2026-11-24", "text", None, "null", "1957-08-04", "text")]
    with unit_of_work(made) as work:
        assert work.scalars(select(ProofRace)).one().first_held_on == THE_FIRST


def test_a_change_of_the_day_is_stored(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofRace(held_on=A_DAY, announced_on=THE_FIRST))
    with unit_of_work(made) as work:
        race = work.scalars(select(ProofRace)).one()
        race.held_on = date(2026, 11, 25)
        race.announced_on = None

    assert stored(made) == [("2026-11-25", "text", None, "null", "1957-08-04", "text")]


@pytest.mark.parametrize(
    ("value", "sentence"),
    [
        (datetime(2026, 11, 24, 8, 0, tzinfo=UTC), A_TIME_IS_NO_DAY),
        (datetime(2026, 11, 24, tzinfo=UTC).replace(tzinfo=None), A_TIME_IS_NO_DAY),
        ("2026-11-24", NOT_A_DAY),
        (20261124, NOT_A_DAY),
    ],
    ids=["a time", "midnight without an offset", "text", "a number"],
)
def test_what_is_not_a_day_is_refused_and_nothing_is_stored(
    made: Engine, value: Any, sentence: str
) -> None:
    races = [ProofRace(held_on=A_DAY), ProofRace(held_on=value)]

    with pytest.raises(StatementError, match=sentence) as refused, unit_of_work(made) as work:
        work.add_all(races)

    assert isinstance(refused.value.orig, TypeError)
    assert stored(made) == []


@pytest.mark.parametrize("text", list(NOT_DAYS.values()), ids=list(NOT_DAYS))
def test_text_that_is_not_a_day_written_past_the_model_is_refused(made: Engine, text: str) -> None:
    with made.begin() as connection:
        connection.exec_driver_sql(
            PAST_THE_MODEL, ("2026-11-24", None, "1957-08-04", A_TIME, A_TIME)
        )

    refusal = REFUSED.format("held_on")
    with pytest.raises(IntegrityError) as refused, made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (text, None, "1957-08-04", A_TIME, A_TIME))

    assert str(refused.value.orig) == refusal
    assert stored(made) == [("2026-11-24", "text", None, "null", "1957-08-04", "text")]


@pytest.mark.parametrize(
    ("values", "refused_by"),
    [
        (("2026-11-24", "2026-02-30", "1957-08-04"), "announced_on"),
        (("2026-11-24", "", "1957-08-04"), "announced_on"),
        (("2026-11-24", None, "1957-8-4"), "first_held_on"),
    ],
    ids=[
        "in a column that may be without a value",
        "empty text in a column that may be without a value",
        "in a column with a value of its own",
    ],
)
def test_every_such_column_refuses_what_is_not_a_day(
    made: Engine, values: tuple[Any, ...], refused_by: str
) -> None:
    with pytest.raises(IntegrityError) as refused, made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (*values, A_TIME, A_TIME))

    assert str(refused.value.orig) == REFUSED.format(refused_by)
    assert stored(made) == []


@pytest.mark.parametrize(
    ("written", "refusal"),
    [
        (20261124, REFUSED.format("held_on")),
        (2460000.5, REFUSED.format("held_on")),
        (b"2026-11-24", "cannot store BLOB value in TEXT column proof_race.held_on"),
    ],
    ids=["a whole number", "a number with a fraction", "bytes that spell a day"],
)
def test_what_is_not_text_is_refused_by_the_check_or_because_the_table_is_strict(
    made: Engine, written: Any, refusal: str
) -> None:
    with pytest.raises(IntegrityError) as refused, made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (written, None, "1957-08-04", A_TIME, A_TIME))

    assert str(refused.value.orig) == refusal
    assert stored(made) == []


def test_a_change_to_what_is_not_a_day_is_refused_and_the_row_stays_as_it_was(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofRace(held_on=A_DAY, announced_on=THE_FIRST))

    with pytest.raises(IntegrityError) as first, made.begin() as connection:
        connection.exec_driver_sql("UPDATE proof_race SET held_on = '2026-11-31'")
    with pytest.raises(IntegrityError) as second, made.begin() as connection:
        connection.exec_driver_sql("UPDATE proof_race SET announced_on = 'unknown'")

    assert str(first.value.orig) == REFUSED.format("held_on")
    assert str(second.value.orig) == REFUSED.format("announced_on")
    assert stored(made) == [("2026-11-24", "text", "1957-08-04", "text", "1957-08-04", "text")]


def test_rows_are_found_by_a_day_by_the_days_before_and_after_and_in_their_order(
    made: Engine,
) -> None:
    days = [date(2026, 11, 24), date(987, 6, 5), date(2026, 1, 5), date(9999, 12, 31)]
    with unit_of_work(made) as work:
        work.add_all([ProofRace(held_on=day) for day in days])
        work.add(ProofRace(held_on=A_DAY, announced_on=THE_FIRST))

    def found(*asked: Any) -> list[int]:
        with unit_of_work(made) as work:
            return list(work.scalars(select(ProofRace.id).where(*asked).order_by(ProofRace.id)))

    assert found(ProofRace.held_on == A_DAY) == [1, 5]
    assert found(ProofRace.held_on < A_DAY) == [2, 3]
    assert found(ProofRace.held_on > A_DAY) == [4]
    assert found(ProofRace.held_on.between(date(2026, 1, 1), date(2026, 12, 31))) == [1, 3, 5]
    assert found(ProofRace.held_on.in_([date(987, 6, 5), date(9999, 12, 31)])) == [2, 4]
    assert found(ProofRace.announced_on.is_(None)) == [1, 2, 3, 4]
    with unit_of_work(made) as work:
        in_order = work.scalars(select(ProofRace.held_on).order_by(ProofRace.held_on, ProofRace.id))
        assert list(in_order) == sorted([*days, A_DAY])
        assert work.scalar(select(func.min(ProofRace.held_on))) == date(987, 6, 5)
        assert work.scalar(select(func.max(ProofRace.held_on))) == date(9999, 12, 31)


def test_a_question_with_a_time_is_refused(made: Engine) -> None:
    moment = datetime(2026, 11, 24, 8, 0, tzinfo=UTC)

    with (
        pytest.raises(StatementError, match=A_TIME_IS_NO_DAY) as refused,
        unit_of_work(made) as work,
    ):
        work.scalars(select(ProofRace).where(ProofRace.held_on == moment))

    assert isinstance(refused.value.orig, TypeError)


def test_what_is_read_through_the_type_and_is_no_day_is_refused(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofRace(held_on=A_DAY))

    # Not a row: what SQLite makes of the day when it is asked to, read through the type.
    as_a_year = func.strftime("%Y", ProofRace.held_on, type_=CalendarDay)
    refusal = "The store holds a day that is not in the store's form: '2026'\\."
    with pytest.raises(ValueError, match=refusal), unit_of_work(made) as work:
        work.scalar(select(as_a_year))


def test_sqlites_own_date_functions_read_a_stored_day(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofRace(held_on=date(2024, 2, 28)))

    with made.connect() as connection:
        read = connection.exec_driver_sql(
            "SELECT date(held_on, '+1 day'), date(held_on, '+2 days'), strftime('%Y', held_on), "
            "CAST(julianday(first_held_on) - julianday('1957-08-01') AS INTEGER) FROM proof_race"
        ).one()

    assert tuple(read) == ("2024-02-29", "2024-03-01", "2024", 3)


def test_a_time_next_to_a_day_is_stored_as_a_time(made: Engine) -> None:
    moment = datetime(2026, 11, 24, 8, 0, tzinfo=UTC)
    with unit_of_work(made) as work:
        work.add(ProofRace(held_on=A_DAY, started_at=moment))

    with made.connect() as connection:
        held_on, started_at = connection.exec_driver_sql(
            "SELECT held_on, started_at FROM proof_race"
        ).one()

    assert (held_on, started_at) == ("2026-11-24", "2026-11-24T08:00:00.000000+00:00")
    with unit_of_work(made) as work:
        assert work.scalars(select(ProofRace)).one().started_at == moment


def test_a_model_that_names_sqlalchemys_own_date_gets_a_table_sqlite_refuses_to_make(
    store: Engine,
) -> None:
    refusal = 'unknown datatype for proof_heat.held_on: "DATE"'

    with pytest.raises(OperationalError, match=refusal), store.begin() as connection:
        Named.metadata.create_all(connection)
