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

The code of a region begins with the code of its country. The letters of
a country are a column of another table, which a check of this one
cannot read, so the rule stands in the file as triggers: on the regions,
for a region that is stored or changed, and on the countries, for a
country that is stored in the place of another or changed.
"""

from sqlalchemy import (
    CheckConstraint,
    ColumnClause,
    Connection,
    ForeignKey,
    UniqueConstraint,
    and_,
    column,
    event,
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


# The four triggers by which the code of a region begins with the code of
# its country: two on the regions, for a new region and for one that is
# changed, and two on the countries, for a new country and for one that
# is changed. A new country can have regions already: a statement that
# says REPLACE puts it in the place of the country that had its key.
#
# Each fires after the row is written and SQLite takes the row back with
# the statement. None names a column: a trigger that fires for a change
# of one column is not fired by a statement that sets the key by another
# of its names (DAT-068). So each fires for every change, and a region
# whose code was wrong before the rule was there can be put right or
# deleted and nothing else. A region without a code is asked nothing:
# nothing compares with what is not there.
_THE_CODE_IS_OF_THE_COUNTRY = (
    "CREATE TRIGGER tr_region_code_of_its_country AFTER INSERT ON region "
    "WHEN substr(NEW.iso_3166_2, 1, 2) != "
    "(SELECT alpha_2 FROM country WHERE id = NEW.country_id) "
    "BEGIN SELECT RAISE(ABORT, "
    "'The code of a region (region) begins with the code of its country (country).'); END",
    "CREATE TRIGGER tr_region_code_stays_of_its_country AFTER UPDATE ON region "
    "WHEN substr(NEW.iso_3166_2, 1, 2) != "
    "(SELECT alpha_2 FROM country WHERE id = NEW.country_id) "
    "BEGIN SELECT RAISE(ABORT, "
    "'The code of a region (region) begins with the code of its country (country).'); END",
    "CREATE TRIGGER tr_country_code_of_its_regions AFTER INSERT ON country "
    "WHEN EXISTS (SELECT 1 FROM region WHERE country_id = NEW.id "
    "AND substr(iso_3166_2, 1, 2) != NEW.alpha_2) "
    "BEGIN SELECT RAISE(ABORT, "
    "'The codes of the regions of a country (region) begin with its code (country).'); END",
    "CREATE TRIGGER tr_country_code_stays_of_its_regions AFTER UPDATE ON country "
    "WHEN EXISTS (SELECT 1 FROM region WHERE country_id = NEW.id "
    "AND substr(iso_3166_2, 1, 2) != NEW.alpha_2) "
    "BEGIN SELECT RAISE(ABORT, "
    "'The codes of the regions of a country (region) begin with its code (country).'); END",
)


def _make_its_triggers(table: object, connection: Connection, **said: object) -> None:
    """Make the four triggers, with the connection that has just made the table.

    The table of the countries is there by then: a region points to its
    country, so the countries are made first.
    """
    for trigger in _THE_CODE_IS_OF_THE_COUNTRY:
        connection.exec_driver_sql(trigger)


# Wherever the table is made from the model, the triggers are made with it.
event.listen(Region.__table__, "after_create", _make_its_triggers)
