"""The countries: where in the world everything else is.

A country is known by its two codes of ISO 3166-1, the international
standard for the names of countries: the code of two letters ("NZ") and
the code of three ("NZL"). This module has the model of the table that
knows them, :class:`Country`.

A country is a collected record. Its codes and its name are read from a
source, and every row says which one and when
(:class:`motosphere.db.models.provenance.Collected`).
"""

from sqlalchemy import CheckConstraint, ColumnClause, and_, column, func
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.models.provenance import Collected
from motosphere.db.texts import NotEmpty

__all__ = ["Country"]


def _capitals(name: str, count: int) -> CheckConstraint:
    """Give the check that the column ``name`` holds ``count`` capital letters and no more.

    The letters are the 26 of the English alphabet, "A" to "Z". SQLite's
    GLOB tells small letters from large ones on every machine, and takes
    a letter with an accent, or one of another alphabet, for none of the
    26.
    """
    text: ColumnClause[str] = column(name)
    are_capitals = text.bool_op("GLOB")("[A-Z]" * count)
    # GLOB reads text up to a character with the number 0 and no further,
    # so anything after one would go unseen.
    has_no_nought = func.instr(text, func.char(0)) == 0
    words = {2: "two", 3: "three"}
    return CheckConstraint(
        and_(are_capitals, has_no_nought), name=f"{name}_{words[count]}_capitals"
    )


class Country(Collected):
    """One country: its two codes of ISO 3166-1 and what it is called in English.

    The codes are what a country is known by: no two countries have one
    code of two letters, and no two have one code of three. A code is
    stored in capitals, and the table itself refuses every other form.
    """

    __tablename__ = "country"
    __table_args__ = (_capitals("alpha_2", 2), _capitals("alpha_3", 3))

    # Its code of two letters, as "NZ" for New Zealand.
    alpha_2: Mapped[str] = mapped_column(unique=True)
    # Its code of three letters, as "NZL".
    alpha_3: Mapped[str] = mapped_column(unique=True)
    # What it is called in English: the short name of the standard, as its
    # source writes it. Two rows can hold one name: a country is known by
    # its codes, and a name is not held to be anything but text.
    name: Mapped[NotEmpty]
