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

The table is only added to. What a row said once it says for good: the
store itself refuses to edit a row, to delete one and to put a new row
in the place of one. The refusal stands in the file, as triggers, so it
holds whoever writes to the file, through the models or past them.
"""

from sqlalchemy import CheckConstraint, Connection, ForeignKey, event
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


# The four triggers by which the table is only added to. SQLite stops the
# statement that fires one, and the sentence is what it says.
#
# The third is there for REPLACE, which takes a row out to put another in
# its place and fires no trigger for the row it takes out. A row is
# replaced by its key, so the trigger asks before every new row whether
# its key is taken. A row that names no key has none yet when it asks:
# SQLite shows -1 then, and the row is given the next key afterwards.
# The fourth is there for the third: no row has a key below 1, so the -1
# of a row without a key is never the key of a row that is there.
_ONLY_ADDED_TO = (
    "CREATE TRIGGER tr_record_change_never_edited BEFORE UPDATE ON record_change "
    "BEGIN SELECT RAISE(ABORT, 'A row of the history (record_change) is never edited.'); END",
    "CREATE TRIGGER tr_record_change_never_deleted BEFORE DELETE ON record_change "
    "BEGIN SELECT RAISE(ABORT, 'A row of the history (record_change) is never deleted.'); END",
    "CREATE TRIGGER tr_record_change_never_replaced BEFORE INSERT ON record_change "
    "WHEN EXISTS (SELECT 1 FROM record_change WHERE id = NEW.id) "
    "BEGIN SELECT RAISE(ABORT, 'A row of the history (record_change) is never replaced.'); END",
    "CREATE TRIGGER tr_record_change_key_positive AFTER INSERT ON record_change "
    "WHEN NEW.id < 1 "
    "BEGIN SELECT RAISE(ABORT, 'A key of the history (record_change) is 1 or more.'); END",
)


def _let_it_only_be_added_to(table: object, connection: Connection, **said: object) -> None:
    """Make the four triggers, with the connection that has just made the table."""
    for trigger in _ONLY_ADDED_TO:
        connection.exec_driver_sql(trigger)


# Wherever the table is made from the model, its triggers are made with it.
event.listen(RecordChange.__table__, "after_create", _let_it_only_be_added_to)
