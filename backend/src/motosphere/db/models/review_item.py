"""The review queue: what waits for a person's decision.

Accuracy is more important than quantity (DESIGN.md 8, CLAUDE.md 11).
Where the collecting cannot tell by itself what is right, it does not
guess. Two records that may be the same thing are not merged, a record
is not written over because another source says otherwise, and a value
that the rules of its field refuse is not stored. What is in doubt is
put down as an item of the review queue, and it waits there until a
person decides. This module has the model of the table that keeps the
items, :class:`ReviewItem`, and the two lists an item is said by:
:class:`ReviewKind`, what is in doubt, and :class:`ReviewState`, whether
it was decided and how.

An item is about one record. Like a change in the history, it names the
record by the name of its table and its key there, because it can be
about a record of any table, and SQLite does not hold the two to a row
that exists: a reference is to one table.

What else an item names goes with its kind. A possible duplicate names
the other record, which is of the same table. The two other kinds name
a field of the record, the source that says what the field should hold,
the address at which it says so, and what it says.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base
from motosphere.db.lists import OneOf
from motosphere.db.texts import NotEmpty
from motosphere.db.web import WebAddress

__all__ = ["ReviewItem", "ReviewKind", "ReviewState"]


class ReviewKind(StrEnum):
    """What is in doubt."""

    # Two records of one table may be the same thing.
    POSSIBLE_DUPLICATE = "possible duplicate"
    # A source says that a field of a record holds another value than
    # the record holds.
    SOURCES_DISAGREE = "sources disagree"
    # A source says that a field of a record holds a value which the
    # rules of the field refuse.
    VALUE_OUTSIDE_ITS_RULES = "value outside its rules"


class ReviewState(StrEnum):
    """Whether an item was decided, and how."""

    # Nobody has decided it yet.
    OPEN = "open"
    # What the item puts forward is taken: the two records are one, or
    # the field shall hold what the source says.
    ACCEPTED = "accepted"
    # It is not taken: the two records are two, or the record stays as
    # it is.
    REJECTED = "rejected"


class ReviewItem(Base):
    """One doubt: the record it is about, what is in doubt and why, and what was decided.

    The table itself refuses an item that does not name what goes with
    its kind, or names what does not; a record that is said to be its own
    duplicate; a decision without who made it and when; and who or when
    without a decision.
    """

    __tablename__ = "review_item"
    __table_args__ = (
        CheckConstraint("record_id > 0", name="record_id_positive"),
        # The two records of a possible duplicate are said in one way:
        # the smaller key is the record, the greater the other. So no
        # record is its own duplicate, and a pair is not two pairs.
        CheckConstraint("other_record_id > record_id", name="other_record_id_after_record_id"),
        # What goes with the kind. A possible duplicate names the other
        # record and nothing else; the two other kinds name the field,
        # the source, where it says so and what it says, and no other
        # record.
        CheckConstraint(
            "(other_record_id IS NULL) = (kind != 'possible duplicate')",
            name="other_record_id_when_possible_duplicate",
        ),
        CheckConstraint(
            "(field IS NULL) = (kind = 'possible duplicate')",
            name="field_unless_possible_duplicate",
        ),
        CheckConstraint(
            "(source_id IS NULL) = (kind = 'possible duplicate')",
            name="source_id_unless_possible_duplicate",
        ),
        CheckConstraint(
            "(source_address IS NULL) = (kind = 'possible duplicate')",
            name="source_address_unless_possible_duplicate",
        ),
        CheckConstraint(
            "(source_value IS NULL) = (kind = 'possible duplicate')",
            name="source_value_unless_possible_duplicate",
        ),
        # Who decided and when are known of an item that was decided,
        # and of no other.
        CheckConstraint("(decided_by IS NULL) = (state = 'open')", name="decided_by_when_decided"),
        CheckConstraint("(decided_at IS NULL) = (state = 'open')", name="decided_at_when_decided"),
        # SQLite looks for the items that name a source before it lets
        # the source go, and indexes nothing by itself for a reference.
        Index(None, "source_id"),
    )

    kind: Mapped[ReviewKind] = mapped_column(OneOf(ReviewKind))
    # The record the item is about: the name of its table, and its key there.
    record_table: Mapped[NotEmpty]
    record_id: Mapped[int]
    # The other record of a possible duplicate, by its key in the same table.
    other_record_id: Mapped[int | None]
    # The field that is in doubt, by the name of its column.
    field: Mapped[NotEmpty | None]
    # The source that says what the field should hold, the address at
    # which it says so, and what it says, as text. That text is what a
    # source said and no more: it is kept as it was given, and it is
    # never run or followed.
    source_id: Mapped[int | None] = mapped_column(ForeignKey("source.id"))
    source_address: Mapped[WebAddress | None]
    source_value: Mapped[str | None]
    # Why the item is in doubt, in plain words, for the person who decides.
    reason: Mapped[NotEmpty]
    state: Mapped[ReviewState] = mapped_column(OneOf(ReviewState), default=ReviewState.OPEN)
    # The person who decided, by name, and when.
    decided_by: Mapped[NotEmpty | None]
    decided_at: Mapped[datetime | None]
    # What a person wants kept with the item. It never leaves the store.
    note: Mapped[NotEmpty | None]
