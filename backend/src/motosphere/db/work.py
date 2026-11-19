"""Units of work: how the pipeline writes to its data store.

``unit_of_work`` gives a session on the opened store for one piece of work.
The work is kept as a whole when it ends and taken back as a whole when it
fails, and its connection is closed either way.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session

__all__ = ["unit_of_work"]


class _Work(Session):
    """The session of one unit of work. Only the end of the unit commits it."""

    def commit(self) -> None:
        raise RuntimeError(
            "A unit of work is kept as a whole when it ends; it cannot be committed part-way."
        )


@contextmanager
def unit_of_work(store: Engine) -> Iterator[Session]:
    """Give a session for one unit of work on the store ``open_store`` returned.

    Use it in a ``with`` statement. When the block ends, everything the work
    did is committed together. When the block raises, everything it did is
    taken back, a new table included, and the error reaches the caller as it
    was raised. The connection is closed either way.

    What the work read or wrote can still be read after the unit has ended,
    as it was at that moment. The session itself cannot be used again.
    """
    with (
        _Work(
            store,
            # What was loaded stays readable after the commit: the unit is over
            # then, and nothing could load it again.
            expire_on_commit=False,
            # Closed means closed. Used again, the session would open a
            # connection that nothing commits and nothing closes.
            close_resets_only=False,
        ) as work,
        work.begin(),
    ):
        yield work
