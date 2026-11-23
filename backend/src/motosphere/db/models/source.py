"""The information sources: where everything the store holds comes from.

A source is a website or a dataset that MotoSphere may collect from. This
module has the model of the table that knows them all, :class:`Source`,
and the two lists a source is described by: what kind of source it is,
and how it is collected from.

Each list is said once, here. Its values are the texts that are stored,
and a column of the list (:class:`motosphere.db.lists.OneOf`) refuses
every other text. The texts are in small letters, with one space between
two words. Once a table has a column of a list, a text of that list is
changed or taken away only by a migration, because the table's check names
the texts and rows hold them.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base
from motosphere.db.lists import OneOf
from motosphere.db.texts import NotEmpty
from motosphere.db.web import WebAddress

__all__ = ["CollectionMethod", "Source", "SourceCategory"]


class SourceCategory(StrEnum):
    """What kind of source this is: who publishes it (DESIGN.md 7.1, in its order)."""

    # A body that makes the rules of the sport, for the world or for a country.
    GOVERNING_BODY = "governing body"
    # The website of one championship or series.
    CHAMPIONSHIP = "championship"
    # Whoever runs a championship from year to year.
    ORGANISER = "organiser"
    # Whoever puts on single races and sells them.
    PROMOTER = "promoter"
    # One track, about itself.
    TRACK = "track"
    # A local motorcycle club.
    CLUB = "club"
    # An organisation for the racing of one region of a country.
    REGIONAL_ORGANISATION = "regional organisation"
    # A public collection of race results or of timing.
    RESULTS_DATABASE = "results database"
    # A magazine or a news site about the sport.
    NEWS = "news publication"
    # A website the riders and followers of the sport write themselves.
    COMMUNITY = "community website"
    # A public page on a social network, only where that network permits collecting.
    SOCIAL_MEDIA = "social media page"
    # A public archive of how the sport was.
    ARCHIVE = "historical archive"


class CollectionMethod(StrEnum):
    """How a source is collected from (DESIGN.md 7.2, in its order)."""

    # An interface the source itself offers to programs.
    API = "official api"
    # A feed of records in a form made for programs, such as a calendar file.
    STRUCTURED_FEED = "structured feed"
    # A feed of what is new, as RSS or Atom.
    RSS = "rss feed"
    # A whole set of records published for reuse, under a licence.
    DATASET = "public dataset"
    # Pages made for people, only where the site's terms and its robots.txt permit.
    HTML = "html extraction"
    # A public document with a fixed layout, such as a results sheet.
    DOCUMENT = "structured document"
    # The data behind a public page, only where the source authorises its use.
    JSON = "json endpoint"
    # The list of its pages that a site publishes for programs.
    SITEMAP = "sitemap discovery"
    # What a search engine finds, only where the engine permits it.
    SEARCH = "search engine discovery"
    # A reference a person has sent in.
    SUBMITTED = "human submission"


class Source(Base):
    """One source of information: who it is, how it is collected from and how it may be used.

    A new source is switched off. It is switched on only after a person
    has read its terms, and the table itself refuses a row that is
    switched on and does not say when they were read.
    """

    __tablename__ = "source"
    __table_args__ = (
        CheckConstraint("scan_every_hours > 0", name="scan_every_hours_positive"),
        CheckConstraint(
            "switched_on = 0 OR terms_read_at IS NOT NULL", name="switched_on_terms_read"
        ),
    )

    # What the source is called. No two sources have one name.
    name: Mapped[NotEmpty] = mapped_column(unique=True)
    # The address of the site it is: its front page, not the page or feed
    # that is read. Two sources can have one website: a site that is
    # collected from in two ways is two sources.
    website: Mapped[WebAddress]
    category: Mapped[SourceCategory] = mapped_column(OneOf(SourceCategory))
    collection_method: Mapped[CollectionMethod] = mapped_column(OneOf(CollectionMethod))
    # After how many hours it is to be looked at again. No value: it is
    # not looked at by the clock, only when somebody loads it.
    scan_every_hours: Mapped[int | None]
    # Where its terms of use are, if it has any.
    terms_address: Mapped[WebAddress | None]
    # The licence under which what it publishes may be used, as the source names it.
    licence: Mapped[NotEmpty | None]
    # What its terms ask for or forbid, in plain words.
    usage_restrictions: Mapped[NotEmpty | None]
    # When a person last read its terms. No value: nobody has yet.
    terms_read_at: Mapped[datetime | None]
    # Whether MotoSphere collects from it.
    switched_on: Mapped[bool] = mapped_column(default=False)
