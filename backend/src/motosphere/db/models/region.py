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

A region can be a part of another region of its country, as a county is
of a state, and says so with the key of that region. Most are parts of
their country only.

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
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    and_,
    column,
    event,
    func,
    or_,
    text,
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
    taken away first. A region may be without a code, and any number of
    regions may be; no two regions have one code.

    Two regions of one country can have one name when each says its
    code: the standard itself has such pairs, as Maputo the city and
    Maputo the province of Mozambique, and their codes tell them apart.
    Of the regions that say no code, no two parts of one region have
    one name, and no two regions of one country that are parts of none:
    nothing would tell them apart. Two that are parts of different
    regions can have one name, as there are counties of one name in
    many states, and so can a region and a part of it. A region that
    says its code and one that says none can have one name too. Whether
    they are one region, named by two sources, the table cannot know;
    that is asked in the review queue by whoever stores them. Two
    countries can each have a region of a name.

    A region can be a part of another region: of one that is there, of
    its own country, and not of itself. A region that others are parts
    of cannot be deleted, given another key or moved to another country
    while they are; a statement that deletes or moves it and all of them
    is taken. No region is a part of itself through others either, as
    two that are each a part of the other: two triggers hold that, which
    stand below (DAT-070).
    """

    __tablename__ = "region"
    __table_args__ = (
        # One name among the regions that say no code and are parts of
        # one region, and one among those of a country that are parts of
        # none. Each rule is an index over those regions only. An index
        # over the region a region is a part of holds nothing of the
        # regions that are parts of none: what is not there is never
        # twice the same.
        Index(
            None,
            "country_id",
            "name",
            unique=True,
            sqlite_where=text("iso_3166_2 IS NULL AND parent_id IS NULL"),
        ),
        Index(
            None,
            "parent_id",
            "name",
            unique=True,
            sqlite_where=text("iso_3166_2 IS NULL AND parent_id IS NOT NULL"),
        ),
        _code_of_the_standard("iso_3166_2"),
        # The region it is a part of is one that is there, of its own
        # country: the two columns together point to the key and the
        # country of one region. For that the table says that a key and
        # a country together are there once, which is so of every key.
        UniqueConstraint("id", "country_id"),
        ForeignKeyConstraint(["parent_id", "country_id"], ["region.id", "region.country_id"]),
        CheckConstraint("parent_id != id", name="parent_id_not_itself"),
    )

    # The country it is a part of. The index over it is what finds the
    # regions of one country: for whoever asks for them, and for SQLite
    # itself when a country is to be deleted and it looks whether the
    # country has regions.
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"), index=True)
    # The region it is a part of, as a county is of a state, where it is
    # a part of one. A region without one is a part of its country only.
    # The index over it finds the parts of a region: for whoever asks
    # for them, and for SQLite itself when a region is to be deleted and
    # it looks whether the region has parts.
    parent_id: Mapped[int | None] = mapped_column(index=True)
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

# The two triggers by which no region is a part of itself through other
# regions, as two that are each a part of the other: one for a new
# region, one for a region that is changed. The check of the table
# refuses a region that names itself; it reads one row and cannot see
# further.
#
# Each goes upwards from the region that the row names, from part to
# region, and refuses where it comes to the row itself. It gathers every
# region once, so it ends in a store that holds a ring from before the
# rule too. A new region is asked because a statement that says REPLACE
# puts it in the place of a region that others are parts of. A changed
# region is asked when the region it is a part of is another than
# before, or its key is: a ring cannot come about in another way, and
# every other change is free. Neither names a column, like the four
# above (DAT-068).
#
# SQLite asks after each row and not when the statement has ended. One
# statement that turns two regions around, the part made the region and
# the region its part, is refused where it comes to the upper one first;
# two statements do it, the lower region first.
_ABOVE_IT = (
    "WITH RECURSIVE above(id) AS (SELECT NEW.parent_id UNION "
    "SELECT region.parent_id FROM region JOIN above ON region.id = above.id "
    "WHERE region.parent_id IS NOT NULL) SELECT 1 FROM above WHERE id = NEW.id"
)
_NOT_A_PART_OF_ITSELF_THROUGH_OTHERS = (
    "CREATE TRIGGER tr_region_parent_id_not_below_itself AFTER INSERT ON region "
    f"WHEN NEW.parent_id IS NOT NULL AND EXISTS ({_ABOVE_IT}) "
    "BEGIN SELECT RAISE(ABORT, "
    "'A region (region) is not a part of itself through other regions.'); END",
    "CREATE TRIGGER tr_region_parent_id_stays_not_below_itself AFTER UPDATE ON region "
    "WHEN NEW.parent_id IS NOT NULL "
    "AND (NEW.parent_id IS NOT OLD.parent_id OR NEW.id != OLD.id) "
    f"AND EXISTS ({_ABOVE_IT}) "
    "BEGIN SELECT RAISE(ABORT, "
    "'A region (region) is not a part of itself through other regions.'); END",
)


def _make_its_triggers(table: object, connection: Connection, **said: object) -> None:
    """Make the six triggers, with the connection that has just made the table.

    The table of the countries is there by then: a region points to its
    country, so the countries are made first.
    """
    for trigger in (*_THE_CODE_IS_OF_THE_COUNTRY, *_NOT_A_PART_OF_ITSELF_THROUGH_OTHERS):
        connection.exec_driver_sql(trigger)


# Wherever the table is made from the model, the triggers are made with it.
event.listen(Region.__table__, "after_create", _make_its_triggers)
