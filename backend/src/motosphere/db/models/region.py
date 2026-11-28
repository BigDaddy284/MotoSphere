"""The regions: the parts a country is divided into.

A country can be divided into parts: states, provinces, counties,
islands. A track says with one of them where in its country it lies.
This module has the model of the table that knows them,
:class:`Region`.

A region is a collected record. That it is there, the country it is a
part of and its name are read from a source, and every row says which
one and when (:class:`motosphere.db.models.provenance.Collected`). The
table has no rows of its own: a region comes with the record that needs
it.
"""

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.models.provenance import Collected
from motosphere.db.texts import NotEmpty

__all__ = ["Region"]


class Region(Collected):
    """One part of a country, and what it is called.

    A region is a part of exactly one country, one that is in the store,
    and a country that has regions cannot be deleted: its regions are
    taken away first. No two regions of one country have one name; two
    countries can each have a region of a name.
    """

    __tablename__ = "region"
    # SQLite keeps an index for this rule, which begins with the country.
    # It is what finds the regions of one country: for whoever asks for
    # them, and for SQLite itself when a country is to be deleted and it
    # looks whether the country has regions.
    __table_args__ = (UniqueConstraint("country_id", "name"),)

    # The country it is a part of.
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"))
    # What it is called, as its source writes it. Two names are one name
    # only if they are the same text: the table does not judge whether
    # "Bayern" and "Bavaria" mean one region.
    name: Mapped[NotEmpty]
