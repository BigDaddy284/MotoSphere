"""Putting a doubt into the review queue.

Where the collecting cannot tell by itself what is right, it does not
guess (DESIGN.md 8, CLAUDE.md 11): it puts the doubt down as an item of
the review queue, and a person decides. The functions here are how an
item is opened. Each is given the records themselves and takes the name
of their table and their keys from them, so that an item is about
records that are stored.

A doubt is one item. Whoever opens a doubt that the queue holds already
is given the item that is there, as it is, whether it is still open or
was decided: a question a person has answered is not put to them again.
"""

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from motosphere.db.base import Base
from motosphere.db.changes import THE_STORES_OWN
from motosphere.db.models.provenance_rule import NOT_COLLECTED
from motosphere.db.models.review_item import ReviewItem, ReviewKind

__all__ = ["open_field_doubt", "open_possible_duplicate"]


def _must_be_stored(work: Session, *records: Base) -> None:
    """Refuse a record that is not stored, or that this unit of work did not read or store."""
    for one in records:
        state = inspect(one)
        if not state.persistent or state.session is not work:
            raise ValueError(
                "Only records that are stored, and that this unit of work read or stored, "
                "are put to the review queue."
            )


def _must_hold_collected_records(table: str) -> None:
    """Refuse a table that holds no collected records."""
    if table in NOT_COLLECTED:
        raise ValueError(
            "The review queue is for doubts about collected records, and the table "
            f"{table} holds none."
        )


def open_possible_duplicate(work: Session, record: Base, other: Base, *, reason: str) -> ReviewItem:
    """Put down that two stored records of one table may be the same thing, and give the item.

    The two records can be given in either order: the item names the one
    with the smaller key as its record and the one with the greater as
    the other, which is the one way the table says a pair. ``reason``
    says why they may be the same, in plain words, for the person who
    decides.

    When the queue holds an item for these two records already, that
    item is given back as it is and nothing is written: its state, its
    reason and its note stay what they were, and the reason given here
    is not read. Otherwise one open item is stored and given back.

    Neither record is touched. Nothing is merged, and nothing is written
    to the history of the changes: an item is a question, and what
    follows from its answer belongs to the code that decides and merges.

    The item is part of the unit of work ``work`` and is written to it
    before the function returns, so what the store refuses is refused
    here, which is a reason that is empty. Whatever is refused, the unit
    of work fails as a whole, and no item is kept.

    The function looks for the doubt and then writes it. No other
    connection can store the same doubt between the two: SQLite keeps
    nothing another connection writes while a unit of work that has read
    is open. Past this function, the store's own index refuses the same
    doubt a second time (DAT-050).

    Refused before anything is written, each in one sentence: a record
    that this unit of work did not read or store, or that is not stored
    yet; two records of two tables; records of a table that holds no
    collected records; and a record given as its own duplicate.
    """
    _must_be_stored(work, record, other)
    table = str(type(record).__tablename__)
    table_of_the_other = str(type(other).__tablename__)
    if table_of_the_other != table:
        raise ValueError(
            "A possible duplicate is two records of one table: these are of "
            f"{table} and of {table_of_the_other}."
        )
    _must_hold_collected_records(table)
    if record.id == other.id:
        raise ValueError("A record is not its own duplicate.")

    first, second = sorted((record.id, other.id))
    there = work.scalars(
        select(ReviewItem).where(
            ReviewItem.record_table == table,
            ReviewItem.record_id == first,
            ReviewItem.other_record_id == second,
        )
    ).one_or_none()
    if there is not None:
        return there

    item = ReviewItem(
        kind=ReviewKind.POSSIBLE_DUPLICATE,
        record_table=table,
        record_id=first,
        other_record_id=second,
        reason=reason,
    )
    work.add(item)
    work.flush()
    return item


def open_field_doubt(
    work: Session,
    record: Base,
    field: str,
    *,
    kind: ReviewKind,
    source: int,
    address: str,
    says: str,
    reason: str,
) -> ReviewItem:
    """Put down what a source says of a field of a stored record, and give the item.

    ``field`` is the name of a column of the record's table. ``source``
    is the key of the source, ``address`` where it says so, and ``says``
    what it says the field holds, as the text the source gave. That text
    is kept as it is, letter for letter, and empty text is text. It is
    never run, followed or taken for an instruction. ``kind`` says which
    of the two doubts about a field this is: the source says another
    value than the record holds, or a value that the rules of the field
    refuse. ``reason`` says why, in plain words, for the person who
    decides.

    When the queue holds an item in which this source says this of this
    field of this record, that item is given back as it is and nothing
    is written: its kind, its address, its state, its reason and its
    note stay what they were, and the kind, the address and the reason
    given here are not read. Otherwise one open item is stored and given
    back.

    The record is not touched, and nothing is written to the history of
    the changes. The function does not look at what the record holds: a
    source says a thing in its own words, and whether that is what the
    record holds is for the code that collects to say before it calls.

    The item is part of the unit of work ``work`` and is written to it
    before the function returns, so what the store refuses is refused
    here: a source that is not there, an address that is no web address,
    and a reason that is empty. Whatever is refused, the unit of work
    fails as a whole, and no item is kept.

    The function looks for the doubt and then writes it, as
    :func:`open_possible_duplicate` does, and no other connection can
    store the same doubt between the two.

    Refused before anything is written, each in one sentence: a record
    that this unit of work did not read or store, or that is not stored
    yet; a record of a table that holds no collected records; a possible
    duplicate, which is two records and has its own function; a field
    its table does not have; the three columns that are the store's own
    in every table; and something said that is not text.
    """
    _must_be_stored(work, record)
    table = str(type(record).__tablename__)
    _must_hold_collected_records(table)
    if kind is ReviewKind.POSSIBLE_DUPLICATE:
        raise ValueError(
            "A possible duplicate is two records and no field: it is opened with "
            "open_possible_duplicate."
        )
    if field in THE_STORES_OWN:
        raise ValueError(
            f"The column {field} is the store's own in every table: no source says what it holds."
        )
    if field not in inspect(record).mapper.columns:
        raise ValueError(f"The table {table} has no column {field}.")
    # Exactly text: the table keeps text here, and what is merely like it
    # would not be kept as it was given.
    if type(says) is not str:
        raise TypeError(f"What a source says is given as the text it said, which {says!r} is not.")

    there = work.scalars(
        select(ReviewItem).where(
            ReviewItem.record_table == table,
            ReviewItem.record_id == record.id,
            ReviewItem.field == field,
            ReviewItem.source_id == source,
            ReviewItem.source_value == says,
        )
    ).one_or_none()
    if there is not None:
        return there

    item = ReviewItem(
        kind=kind,
        record_table=table,
        record_id=record.id,
        field=field,
        source_id=source,
        source_address=address,
        source_value=says,
        reason=reason,
    )
    work.add(item)
    work.flush()
    return item
