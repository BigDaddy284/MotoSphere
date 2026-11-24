"""What the store does with its collection runs.

A run is stored as running when it starts, and says itself how it ended.
A run whose job died cannot: it would be running in the table for ever.
:func:`mark_interrupted` is what the next start of collecting calls
before anything else, so that the table says of every run what is true
of it, and whoever takes up the work has a record of what was cut off.
"""

from sqlalchemy import update
from sqlalchemy.orm import Session

from motosphere.db.models.collection_run import CollectionRun, RunOutcome

__all__ = ["mark_interrupted"]


def mark_interrupted(work: Session) -> list[int]:
    """Mark every run that is still running as interrupted, and give their keys in order.

    It is for the moment nothing can be running: the start of collecting,
    before the first new run is stored. A run that is running then was
    left so by a job that died.

    Only the outcome of those runs is changed, and with it when they were
    last changed. They get no end, because nobody knows when they ended,
    and they keep what they had counted. No other run and no other table
    is touched. The marking is part of the unit of work ``work``: it is
    kept or taken back with it.
    """
    marked = work.scalars(
        update(CollectionRun)
        .where(CollectionRun.outcome == RunOutcome.RUNNING)
        .values(outcome=RunOutcome.INTERRUPTED)
        .returning(CollectionRun.id)
    )
    return sorted(marked)
