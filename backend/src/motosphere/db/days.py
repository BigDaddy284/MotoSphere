"""Calendar days in the data store.

Much of what the store holds is said by the day and not by the moment: the
day a race is held, the day a rider was born, the day a page says it was
published. A day has no time of day and no offset, and none is made up for
it: a day stored as the moment its midnight struck somewhere would say
more than its source did.

A strict table has no type for a day, so the store keeps a day as text, in
one form:

    2026-11-24

It always has the four digits of its year, the two of its month and the
two of its day. So every such text has the same length, the order of the
texts is the order of the days, and the text can be read without this
code: by a person, and by SQLite's own date functions.

A model says of such a column that it is a ``date``:

    held_on: Mapped[date]

The column is then TEXT with a check in its table, and SQLite itself
refuses text that is not a day in that form, whoever writes the row: also
a day that no calendar has, such as the 30th of February. To Python the
column is a ``date``, and only a ``date`` is stored. A time is refused,
although Python counts a ``datetime`` as a ``date``: its time of day would
be dropped without a word, and which day a moment falls on depends on
where one stands.

A column that may be without a value says ``Mapped[date | None]``: it holds
no value or a day. No value means that the day is not known.
"""

from contextlib import suppress
from datetime import date, datetime
from typing import override

from sqlalchemy import CheckConstraint, ColumnClause, Dialect, Text, and_, column, func
from sqlalchemy.types import TypeDecorator

from motosphere.db.checks import WithItsCheck

__all__ = ["CalendarDay", "calendar_day", "from_text", "to_text"]

# The form of a day, as SQLite's GLOB is told it: four digits, two and two,
# with a hyphen between them.
_FORM = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"
# The first day there is. SQLite knows a year 0, and Python does not.
_FIRST = "0001-01-01"


def to_text(day: date) -> str:
    """Say a day in the store's form. What is not a day is refused, a time among it."""
    if not isinstance(day, date):
        raise TypeError(
            f"Only a day (a date) is stored as a day, not {type(day).__name__}: {day!r}."
        )
    if isinstance(day, datetime):
        raise TypeError(
            f"A time is not stored as a day: {day!r}. Say the day itself: which day a moment "
            "falls on depends on where one stands."
        )
    return day.isoformat()


def from_text(text: str) -> date:
    """Read a day that is in the store's form.

    Text in any other form is refused, also when it could be read as a day:
    the store holds one form only.
    """
    with suppress(TypeError, ValueError):
        day = date.fromisoformat(text)
        if to_text(day) == text:
            return day
    raise ValueError(f"The store holds a day that is not in the store's form: {text!r}.")


class CalendarDay(WithItsCheck, TypeDecorator[date]):
    """The type of a column that holds a calendar day. In the table it is TEXT."""

    impl = Text
    cache_ok = True
    refuses = "text that is not a calendar day"
    given_by = "calendar_day"

    def check_for(self, name: str) -> CheckConstraint:
        """Give the check of :func:`calendar_day` for the column called ``name``."""
        return calendar_day(name)

    @override
    def process_bind_param(self, value: date | None, dialect: Dialect) -> str | None:
        """Turn a day into the text that is stored."""
        return None if value is None else to_text(value)

    @override
    def process_result_value(self, value: str | None, dialect: Dialect) -> date | None:
        """Turn the text that is stored into a day."""
        return None if value is None else from_text(value)


def calendar_day(name: str) -> CheckConstraint:
    """Give the check that refuses text that is not a calendar day in the column ``name``.

    The check asks three things of the text. It has the form of a day. It
    is a day SQLite's own calendar has: SQLite reads it as a day and says
    the same text back, which it does not for the 30th of February. And it
    is not before the first day there is, the first of January of the year
    1.

    The check is called ``<name>_calendar_day``, which the naming rule makes
    ``ck_<table>_<name>_calendar_day`` once the check is given to a table.
    It belongs to no table until then. A column without a value passes it,
    as it passes every check.
    """
    day: ColumnClause[str] = column(name)
    has_the_form = day.bool_op("GLOB")(_FORM)
    is_on_the_calendar = func.date(day).is_(day)
    return CheckConstraint(
        and_(has_the_form, is_on_the_calendar, day >= _FIRST),
        name=f"{name}_calendar_day",
    )
