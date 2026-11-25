"""Where a collected record came from, and how far it can be trusted.

Everything MotoSphere collects keeps with it where it came from and how
far it can be trusted (DESIGN.md 8). This module has the columns that say
so, which are the same in every table of collected records
(:class:`Collected`), and the two lists that two of those columns are of.

Two different questions are asked of how far a record can be trusted,
and each has a list of its own:

- how sure it is that the record says what its source says. That is its
  confidence, :class:`Confidence`, and it is about the reading: a value
  taken from a field made for it is surer than one worked out from a
  sentence;
- what standing the source's word has. That is its verification status,
  :class:`VerificationStatus`, and it is about the publishing: what the
  organiser of a race published about it is official, whoever read it
  and however surely.

Neither answers the other. A result read without doubt from a fan's
website is of high confidence and independent; a date worked out from an
official notice is official and of low confidence.

Each list is said once, here. Its values are the texts that are stored,
and a column of the list (:class:`motosphere.db.lists.OneOf`) refuses
every other text. The texts are in small letters, with one space between
two words. Both lists go from what can be trusted most to what can be
trusted least. Once a table has a column of a list, a text of that list
is changed or taken away only by a migration, because the table's check
names the texts and rows hold them.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base
from motosphere.db.lists import OneOf
from motosphere.db.models.source import CollectionMethod
from motosphere.db.web import WebAddress

__all__ = ["Collected", "Confidence", "VerificationStatus"]


class Confidence(StrEnum):
    """How sure it is that a record says what its source says (DESIGN.md 8)."""

    # The source gives the value in a place made for it, such as a field of
    # a feed or a cell under its heading, and it was taken as it stands.
    HIGH = "high"
    # The value was read out of a page or a document made for people, by a
    # rule written for that source. It is wrong where the page is not as
    # the rule expects it.
    MEDIUM = "medium"
    # The value was worked out from what stands around it, or the source is
    # unclear about it or says two things.
    LOW = "low"


class VerificationStatus(StrEnum):
    """What standing the word of a record's source has (DESIGN.md 6, in its order)."""

    # Published by whoever is answerable for what the record says: the body
    # that ran the race or the championship, or the track about itself.
    OFFICIAL = "official"
    # Published by somebody else, such as a news publication, a results
    # database or a community website.
    INDEPENDENT = "independent"
    # Put together afterwards from what is left, where nothing published at
    # the time is at hand. It is never shown as an official record.
    RECONSTRUCTED = "reconstructed"
    # A mention that has not been checked against anything.
    UNVERIFIED = "unverified"


class Collected(Base):
    """A model of collected records: every row says where it came from.

    A model whose records are collected is a subclass of this class, and
    not of ``Base`` itself:

        class Track(Collected):
            __tablename__ = "track"

            name: Mapped[NotEmpty]

    Its table then has the eight columns below, after the columns the
    model names and before the two times every table ends with. A record
    belongs to a source that exists, and a source that records came from
    cannot be deleted. The table itself refuses a record that was last
    seen at its source before it was collected.

    Only the day a record was published may be without a value, because
    not every source says it. Everything else is known of every record
    when it is collected, and whoever stores the record says it: no
    column here gives itself a value.
    """

    __abstract__ = True

    # The source it was collected from.
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    # The address at which it was found: the page, the feed or the file
    # that says it, not the front page of the site.
    source_address: Mapped[WebAddress]
    # When what the row says was taken from its source.
    collected_at: Mapped[datetime]
    # The day its source says it was published. No value: the source does
    # not say, and no day is made up for it.
    published_on: Mapped[date | None]
    # When the source was last seen to say what the row says. That is the
    # moment it was collected, until the source is looked at again.
    last_verified_at: Mapped[datetime]
    # How this record was got. A source is collected from in one way at a
    # time, and that way can change; the record keeps the way it was got.
    extraction_method: Mapped[CollectionMethod] = mapped_column(OneOf(CollectionMethod))
    confidence: Mapped[Confidence] = mapped_column(OneOf(Confidence))
    verification_status: Mapped[VerificationStatus] = mapped_column(OneOf(VerificationStatus))

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Give the table of a new model the check that holds its two times together.

        It is given here and not left to the model, so that a model keeps
        it whatever else it says of its table.
        """
        super().__init_subclass__(**kwargs)
        table = cls.__dict__.get("__table__")
        if table is not None:
            table.append_constraint(
                CheckConstraint(
                    "last_verified_at >= collected_at",
                    name="last_verified_at_not_before_collected_at",
                )
            )
