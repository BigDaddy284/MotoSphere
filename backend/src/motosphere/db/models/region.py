"""The regions: the parts a country is divided into.

A country can be divided into parts: states, provinces, counties,
islands. A track says with one of them where in its country it lies.
This module has the model of the table that knows them,
:class:`Region`.

A region is a collected record. That it is there, the country it is a
part of, its name and its code are read from a source, and every row
says which one and when
(:class:`motosphere.db.models.provenance.Collected`). The table has no
rows of its own: a region comes with the record that needs it.

A region can say the code that ISO 3166-2 gives it, the international
standard for the parts of countries: the two letters of its country, a
hyphen, and one to three capital letters or digits, as "NZ-CAN" for
Canterbury. Not every region a source names has one.
"""

from sqlalchemy import (
    CheckConstraint,
    ColumnClause,
    ForeignKey,
    UniqueConstraint,
    and_,
    column,
    func,
    or_,
)
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.models.provenance import Collected
from motosphere.db.texts import NotEmpty

__all__ = ["Region"]


def _code_of_the_standard(name: str) -> CheckConstraint:
    """Give the check that the column ``name`` holds a code in the form of ISO 3166-2.

    The form is two capital letters, a hyphen, and one, two or three
    capital letters or digits. The letters are the 26 of the English
    alphabet and the digits the ten from "0" to "9". SQLite's GLOB tells
    small letters from large ones on every machine, and takes a letter
    with an accent, or a letter or digit of another alphabet, for none
    of them.
    """
    text: ColumnClause[str] = column(name)
    has_the_form = or_(
        *(text.bool_op("GLOB")("[A-Z][A-Z]-" + "[A-Z0-9]" * count) for count in (1, 2, 3))
    )
    # GLOB reads text up to a character with the number 0 and no further,
    # so anything after one would go unseen.
    has_no_nought = func.instr(text, func.char(0)) == 0
    return CheckConstraint(and_(has_the_form, has_no_nought), name=f"{name}_form")


class Region(Collected):
    """One part of a country, and what it is called.

    A region is a part of exactly one country, one that is in the store,
    and a country that has regions cannot be deleted: its regions are
    taken away first. No two regions of one country have one name; two
    countries can each have a region of a name. A region may be without
    a code, and any number of regions may be; no two regions have one
    code.
    """

    __tablename__ = "region"
    # SQLite keeps an index for this rule, which begins with the country.
    # It is what finds the regions of one country: for whoever asks for
    # them, and for SQLite itself when a country is to be deleted and it
    # looks whether the country has regions.
    __table_args__ = (
        UniqueConstraint("country_id", "name"),
        _code_of_the_standard("iso_3166_2"),
    )

    # The country it is a part of.
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"))
    # What it is called, as its source writes it. Two names are one name
    # only if they are the same text: the table does not judge whether
    # "Bayern" and "Bavaria" mean one region.
    name: Mapped[NotEmpty]
    # Its code of ISO 3166-2, as "NZ-CAN", where it has one and its
    # source says it.
    iso_3166_2: Mapped[str | None] = mapped_column(unique=True)
