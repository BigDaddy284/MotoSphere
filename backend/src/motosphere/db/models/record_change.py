"""The changes: what a record said before it was changed.

Nothing MotoSphere has collected is written over without a trace
(DESIGN.md 8, CLAUDE.md 11). When a field of a record is changed, what
it held before is kept, with what it holds now, when it was changed and
what caused the change. This module has the model of the table that
keeps them, :class:`RecordChange`.

One row is one field of one record that was changed. A change to three
fields of a record is three rows.

The table can keep the changes of any table of the store, so it names
the record by the name of its table and its key there, and SQLite does
not hold the two to a row that exists: a reference is to one table. The
store's code, which writes a change with its history, is what holds
them.
"""

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base
from motosphere.db.texts import NotEmpty

__all__ = ["RecordChange"]


class RecordChange(Base):
    """One field of one record that was changed: what it held, what it holds, and why.

    When it was changed is when the row was stored (``created_at``): a
    change and its history are written together. The table itself refuses
    a change that changed nothing, a change that nothing caused and one
    that two things caused, and a key that no record can have.
    """

    __tablename__ = "record_change"
    __table_args__ = (
        CheckConstraint("record_id > 0", name="record_id_positive"),
        # IS NOT, and not !=: no value is a value here, and a field that
        # had none and has none has not changed either.
        CheckConstraint("old_value IS NOT new_value", name="new_value_not_old_value"),
        # A run caused it or a person did: one of the two, and not both.
        CheckConstraint(
            "(collection_run_id IS NULL) != (decided_by IS NULL)",
            name="caused_by_a_run_or_a_person",
        ),
    )

    # The record that was changed: the name of its table, and its key there.
    record_table: Mapped[NotEmpty]
    record_id: Mapped[int]
    # The field that was changed: the name of its column.
    field: Mapped[NotEmpty]
    # What the field held before and what it holds now, as text, in the
    # form the store keeps the value in. No value: the field had none, or
    # has none now.
    old_value: Mapped[str | None]
    new_value: Mapped[str | None]
    # What caused the change: the collection run that found the record
    # changed at its source, or the person who decided it, by name.
    collection_run_id: Mapped[int | None] = mapped_column(ForeignKey("collection_run.id"))
    decided_by: Mapped[NotEmpty | None]
