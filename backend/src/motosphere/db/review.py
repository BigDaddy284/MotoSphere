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
from motosphere.db.models.provenance_rule import NOT_COLLECTED
from motosphere.db.models.review_item import ReviewItem, ReviewKind

__all__ = ["open_possible_duplicate"]


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
    for one in (record, other):
        state = inspect(one)
        if not state.persistent or state.session is not work:
            raise ValueError(
                "Only records that are stored, and that this unit of work read or stored, "
                "are put to the review queue."
            )
    table = str(type(record).__tablename__)
    table_of_the_other = str(type(other).__tablename__)
    if table_of_the_other != table:
        raise ValueError(
            "A possible duplicate is two records of one table: these are of "
            f"{table} and of {table_of_the_other}."
        )
    if table in NOT_COLLECTED:
        raise ValueError(
            "The review queue is for doubts about collected records, and the table "
            f"{table} holds none."
        )
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
