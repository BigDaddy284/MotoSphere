"""Times in the data store.

A strict table has no type for a time, so the store keeps a time as text,
in one form:

    2026-11-19T08:26:04.123456+00:00

It is always in UTC, always has its offset written out, and always has the
six digits of the fraction of its second. So every such text has the same
length, the order of the texts is the order of the times, and the text can
be read without this code: by a person, and by SQLite's own date functions.

A time that does not say which offset it has is refused: nothing can tell
which moment it means.

:func:`now` is the store's clock. What the store's code needs the present
moment for, it asks this one function, so that a test can set the clock.
"""

from contextlib import suppress
from datetime import UTC, datetime
from typing import override

from sqlalchemy import Dialect, Text
from sqlalchemy.types import TypeDecorator

__all__ = ["UtcDateTime", "from_text", "now", "to_text"]


def now() -> datetime:
    """Say which moment it is, in UTC. This is the store's clock."""
    return datetime.now(UTC)


def to_text(moment: datetime) -> str:
    """Say a time in the store's form. A time without an offset is refused."""
    if not isinstance(moment, datetime):
        raise TypeError(
            f"Only a time (a datetime) is stored as a time, not {type(moment).__name__}: "
            f"{moment!r}."
        )
    if moment.utcoffset() is None:
        raise ValueError(
            f"A time without an offset is not stored: {moment.isoformat()}. "
            "Say which offset it has, for example with tzinfo=UTC."
        )
    try:
        in_utc = moment.astimezone(UTC)
    except OverflowError:
        raise ValueError(
            f"A time outside the years 1 to 9999 in UTC is not stored: {moment.isoformat()}."
        ) from None
    return in_utc.isoformat(timespec="microseconds")


def from_text(text: str) -> datetime:
    """Read a time that is in the store's form. It comes back as an aware UTC time.

    Text in any other form is refused, also when it could be read as a time:
    the store holds one form only.
    """
    with suppress(TypeError, ValueError):
        moment = datetime.fromisoformat(text)
        if to_text(moment) == text:
            return moment
    raise ValueError(f"The store holds a time that is not in the store's form: {text!r}.")


class UtcDateTime(TypeDecorator[datetime]):
    """The type of a column that holds a time. In the table it is TEXT."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> str | None:
        """Turn a time into the text that is stored."""
        return None if value is None else to_text(value)

    @override
    def process_result_value(self, value: str | None, dialect: Dialect) -> datetime | None:
        """Turn the text that is stored into a time."""
        return None if value is None else from_text(value)
