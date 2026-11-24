"""The collection runs: the record of every time a source was collected from.

A run is one attempt to collect from one source. This module has the
model of the table that records them, :class:`CollectionRun`, and the
list of how a run stands or ended, :class:`RunOutcome`.

A run is stored when it starts, and it is then running. When it ends it
says so itself: it succeeded, or it failed and says why. A run whose job
died says nothing more. It is still running in the table until the next
start finds it and marks it interrupted
(:func:`motosphere.db.runs.mark_interrupted`).
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base
from motosphere.db.lists import OneOf
from motosphere.db.texts import NotEmpty

__all__ = ["CollectionRun", "RunOutcome"]


class RunOutcome(StrEnum):
    """How a collection run stands or ended."""

    # It has started and has not said how it ended.
    RUNNING = "running"
    # It ended, and collected what it set out to collect.
    SUCCEEDED = "succeeded"
    # It ended, and says what went wrong.
    FAILED = "failed"
    # It never said how it ended, because its job died. Nobody knows when.
    INTERRUPTED = "interrupted"


class CollectionRun(Base):
    """One run: which source it collected from, when, how it ended and what it changed.

    A run belongs to a source that exists, and a source that has runs
    cannot be deleted. The table itself refuses a run that ends before it
    started, a run whose end or whose error does not go with its outcome,
    and a count below nothing.
    """

    __tablename__ = "collection_run"
    __table_args__ = (
        CheckConstraint("ended_at >= started_at", name="ended_at_not_before_started_at"),
        # When it ended is known of a run that said so itself, and of no other.
        CheckConstraint(
            "(ended_at IS NULL) = (outcome IN ('running', 'interrupted'))",
            name="ended_at_when_succeeded_or_failed",
        ),
        # A run that failed says why, and no other run has an error.
        CheckConstraint("(error IS NULL) = (outcome != 'failed')", name="error_when_failed"),
        CheckConstraint("records_seen >= 0", name="records_seen_not_negative"),
        CheckConstraint("records_added >= 0", name="records_added_not_negative"),
        CheckConstraint("records_changed >= 0", name="records_changed_not_negative"),
        CheckConstraint("records_unchanged >= 0", name="records_unchanged_not_negative"),
        # The runs of one source, in the order they started: what asks for
        # the newest run of a source goes straight to it, and so does the
        # look for its runs when a source is to be deleted. SQLite ends
        # every entry of an index with the key, so two runs that started
        # together stand in the order they were stored.
        Index(None, "source_id", "started_at"),
    )

    # The source that was collected from.
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    # When the run started. Whoever starts it says so.
    started_at: Mapped[datetime]
    # When it ended. No value: it is running, or it was interrupted and
    # nobody knows when.
    ended_at: Mapped[datetime | None]
    outcome: Mapped[RunOutcome] = mapped_column(OneOf(RunOutcome), default=RunOutcome.RUNNING)
    # How many records the run was given by its source, and how many of
    # them were new to the store, were different from what the store had,
    # and were what the store had already. A run counts as it goes or when
    # it ends; the table does not ask that the three add up to the first,
    # because a record that was refused is none of the three.
    records_seen: Mapped[int] = mapped_column(default=0)
    records_added: Mapped[int] = mapped_column(default=0)
    records_changed: Mapped[int] = mapped_column(default=0)
    records_unchanged: Mapped[int] = mapped_column(default=0)
    # What went wrong, in plain words, when the run failed.
    error: Mapped[NotEmpty | None]
