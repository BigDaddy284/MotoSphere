"""How a source is doing, told by its collection runs.

The registry of the design says of each source when it was last scanned,
when that last worked, what last went wrong and how it is doing. All of
that is what the source's runs say already, so it is not stored a second
time with the source, where the two could come to disagree:
:func:`standing_of` reads it from the runs whenever it is asked, and
writes nothing.

A scan is said by when it started, which is the one time every run has:
a run that was interrupted has no end. The newest run is the one that
started last, and of two that started together the one that was stored
last.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from motosphere.db.models.collection_run import CollectionRun, RunOutcome
from motosphere.db.models.source import Source

__all__ = ["SourceHealth", "SourceStanding", "standing_of"]


class SourceHealth(StrEnum):
    """How a source is doing: what became of the newest of its runs that is over.

    A run that is still running says nothing yet, so it is passed over.
    """

    # No run of it is over yet: it has none, or only one that is running.
    NOT_YET_SCANNED = "not yet scanned"
    # Its newest run that is over succeeded.
    HEALTHY = "healthy"
    # Its newest run that is over failed.
    FAILING = "failing"
    # Its newest run that is over was cut off, because its job died.
    INTERRUPTED = "interrupted"


_HEALTH_AFTER = {
    RunOutcome.SUCCEEDED: SourceHealth.HEALTHY,
    RunOutcome.FAILED: SourceHealth.FAILING,
    RunOutcome.INTERRUPTED: SourceHealth.INTERRUPTED,
}


@dataclass(frozen=True, slots=True)
class SourceStanding:
    """How one source is doing, as its runs say it at the moment it is asked."""

    # When its newest run started, whatever became of it. No value: it has no run.
    last_attempt: datetime | None
    # When its newest run that succeeded started. No value: none has succeeded.
    last_success: datetime | None
    # What went wrong in its newest run that failed, in plain words. No
    # value: none has failed, or one has succeeded since.
    last_error: str | None
    health: SourceHealth


def standing_of(work: Session, source_id: int) -> SourceStanding:
    """Say how the source with this key is doing. Nothing is written.

    A key that no source has is refused with a ``LookupError``: of a
    source that does not exist nothing is true, also not that it was
    never scanned.
    """
    if work.scalar(select(Source.id).where(Source.id == source_id)) is None:
        raise LookupError(f"There is no source with the key {source_id}.")

    def newest(*outcomes: RunOutcome) -> Row[datetime, RunOutcome, str | None] | None:
        """The newest run of the source that has one of these outcomes."""
        return work.execute(
            select(CollectionRun.started_at, CollectionRun.outcome, CollectionRun.error)
            .where(CollectionRun.source_id == source_id, CollectionRun.outcome.in_(outcomes))
            .order_by(CollectionRun.started_at.desc(), CollectionRun.id.desc())
            .limit(1)
        ).first()

    attempted = newest(*RunOutcome)
    over = newest(*_HEALTH_AFTER)
    succeeded = newest(RunOutcome.SUCCEEDED)
    # A run that succeeded takes the error of an older run away: only the
    # newest of the runs that said how they ended has a say.
    said = newest(RunOutcome.SUCCEEDED, RunOutcome.FAILED)
    return SourceStanding(
        last_attempt=None if attempted is None else attempted.started_at,
        last_success=None if succeeded is None else succeeded.started_at,
        last_error=None if said is None else said.error,
        health=SourceHealth.NOT_YET_SCANNED if over is None else _HEALTH_AFTER[over.outcome],
    )
