"""Changing a record, with its history.

Nothing the store holds of a record is written over without a trace
(DESIGN.md 8, CLAUDE.md 11). :func:`change` is how a record that is
stored is changed. It gives the record its new values and adds one row
to the table of the changes for every field that then holds another
value, in the same unit of work. So a change and its history are kept
together or taken back together, and neither is there without the other.

A value is compared, and written to the history, as the text of what the
store keeps for it: a whole number as its digits, a time, a day and a
word of a list as the text the store's own types make of them, and yes
or no as 1 or 0.
"""

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Column, Dialect, Integer, String, inspect
from sqlalchemy.orm import Session
from sqlalchemy.types import TypeDecorator

from motosphere.db import times
from motosphere.db.base import Base
from motosphere.db.models.record_change import RecordChange

__all__ = ["THE_STORES_OWN", "change"]

# The columns of every table that only the store's code sets.
THE_STORES_OWN = ("id", "created_at", "updated_at")


def _as_the_store_keeps_it(
    table: str, column: Column[Any], value: object, dialect: Dialect
) -> str | None:
    """Give the text of what the store keeps for ``value`` in this column, or none for no value.

    The type of the column says what is kept: it is asked as it is asked
    when a row is written, so the text is the one the row holds. A column
    of text takes text and a column of whole numbers a whole number, and
    nothing that is merely like one. A column of numbers with a fraction
    or of bytes has no text here yet: no real table has one, and the
    task that brings the first says which text its values have.
    """
    kind = column.type.impl_instance if isinstance(column.type, TypeDecorator) else column.type
    wanted: type[int] | type[str]
    if isinstance(kind, Integer):
        wanted, what = int, "a whole number"
    elif isinstance(kind, String):
        wanted, what = str, "text"
    else:
        raise TypeError(
            f"The history has no text for what the column {table}.{column.name} keeps: it "
            "has one for text and for whole numbers, and for what the store's own types "
            "make of a time, a day, a word of a list and yes or no."
        )
    to_the_store = column.type.bind_processor(dialect)
    kept = value if to_the_store is None else to_the_store(value)
    if kept is None:
        return None
    # Exactly that, and not a subclass: yes is a whole number to Python,
    # and its text would be "True".
    if type(kept) is not wanted:
        raise TypeError(f"The column {table}.{column.name} keeps {what}, which {value!r} is not.")
    return str(kept)


def change(
    work: Session,
    record: Base,
    to: Mapping[str, object],
    *,
    run: int | None = None,
    decided_by: str | None = None,
) -> list[RecordChange]:
    """Give a stored record new values, and write what it held before to its history.

    ``to`` names the fields and what each shall hold now. A field that
    holds that already is left alone and gets no row. For every other
    field the record is changed and one row is added to the table of the
    changes, in the order the fields are given. The rows are given back,
    and there are none when nothing changed.

    What caused the change is said with it, and it is one of two: the key
    of the collection run that found the record changed at its source
    (``run``), or the name of the person who decided it (``decided_by``).

    The rows of one call are stored at one moment, and the record says
    it was last changed at that same moment. When nothing changed the
    record is not touched at all.

    Everything is part of the unit of work ``work`` and is written to it
    before the function returns, so what the store refuses is refused
    here. Whatever is refused, the unit of work fails as a whole, and
    neither the change nor its history is kept.

    Refused before anything is changed: a call that names no cause or
    both; a record that this unit of work did not read or store, or
    that is not stored yet, since a record that is stored for the first
    time has no history; a row of the history itself; a field its table
    does not have; and the three columns that are the store's own in
    every table.
    """
    if (run is None) == (decided_by is None):
        raise ValueError(
            "A change is caused by a collection run or decided by a person: "
            "say one of the two, and not both."
        )
    if isinstance(record, RecordChange):
        raise ValueError("The history is added to and never changed: its rows are not records.")
    state = inspect(record)
    if not state.persistent or state.session is not work:
        raise ValueError(
            "Only a record that is stored, and that this unit of work read or stored, is "
            "changed with its history. A record that is stored for the first time has none yet."
        )
    table = str(type(record).__tablename__)
    columns = state.mapper.columns
    for field in to:
        if field in THE_STORES_OWN:
            raise ValueError(
                f"The column {field} is the store's own in every table: only the store's "
                "code sets it."
            )
        if field not in columns:
            raise ValueError(f"The table {table} has no column {field}.")

    dialect = work.get_bind().dialect
    different: list[tuple[str, object, str | None, str | None]] = []
    for field, value in to.items():
        before = _as_the_store_keeps_it(table, columns[field], getattr(record, field), dialect)
        after = _as_the_store_keeps_it(table, columns[field], value, dialect)
        if before != after:
            different.append((field, value, before, after))
    if not different:
        return []

    # One reading of the clock for the whole change.
    moment = times.now()
    written: list[RecordChange] = []
    for field, value, before, after in different:
        setattr(record, field, value)
        written.append(
            RecordChange(
                record_table=table,
                record_id=record.id,
                field=field,
                old_value=before,
                new_value=after,
                collection_run_id=run,
                decided_by=decided_by,
                created_at=moment,
            )
        )
    record.updated_at = moment
    work.add_all(written)
    work.flush()
    return written
