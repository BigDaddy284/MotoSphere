"""The base of every model: the rules all tables of the data store share.

A model is a class that describes one table. Every model is a subclass of
:class:`Base`, and so every table

- is a strict table: SQLite refuses a value that is not of its column's
  type, where an ordinary table would store whatever it is given;
- has the same key: one whole-number column named ``id``, whose values
  SQLite gives and never gives twice, also not after a row is deleted;
- says when each of its rows was first stored and when it was last
  changed, in its last two columns, ``created_at`` and ``updated_at``,
  which the store's code sets from the store's clock;
- has columns of the few types a strict table takes: a Python ``int``
  becomes INTEGER, a ``str`` TEXT, a ``float`` REAL and ``bytes`` BLOB, a
  ``datetime`` becomes the store's own type for a time
  (:class:`motosphere.db.times.UtcDateTime`), which is TEXT in the table,
  and a ``bool`` the store's own type for yes or no
  (:class:`motosphere.db.yes_no.YesOrNo`), which is INTEGER;
- has the check of every column whose type brings one
  (:class:`motosphere.db.checks.WithItsCheck`). Text that must not be
  empty is such a type (:data:`motosphere.db.texts.NotEmpty`), and so the
  table refuses empty text in every column whose model says so; yes or no
  is another, and so the table refuses every number but 1 and 0 in a
  column that is a ``bool``; a web address is a third
  (:data:`motosphere.db.web.WebAddress`), and so the table refuses text
  that is not one in every column whose model says so;
- has its constraints and indexes named by one rule, :data:`NAMING`, so
  that a migration can name what it changes and the names are the same on
  every machine. The key has no name: SQLite writes it with its column;
- gives each of its constraints and indexes a name of its own. SQLite
  takes a table with two checks of one name, and what it then says when
  it refuses a row does not tell which of the two refused it.

:func:`broken_rules` says in plain words which tables of a schema break a
rule, and which columns are without the check their type brings. A test
holds the real schema to it.
"""

from collections import Counter
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import (
    REAL,
    CheckConstraint,
    Constraint,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
)
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.schema import conv
from sqlalchemy.types import TypeEngine

from motosphere.db import times
from motosphere.db.checks import WithItsCheck
from motosphere.db.texts import NotEmpty, NotEmptyText
from motosphere.db.times import UtcDateTime
from motosphere.db.web import WebAddress, WebAddressText
from motosphere.db.yes_no import YesOrNo

__all__ = ["NAMING", "Base", "broken_rules"]

# How constraints and indexes are named. A check has no columns to be named
# after, so it is given the last part of its name where it is written:
# CheckConstraint("laps > 0", name="laps_positive") is ck_<table>_laps_positive.
# A check without a name is refused when its table is defined.
NAMING = {
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
}


def _this_moment() -> datetime:
    """Ask the store's clock, anew for every row that is stored or changed."""
    return times.now()


def _when_first_stored(context: Any) -> datetime:
    """Give a new row the moment it was first stored as the moment it was last changed.

    The two are then the same moment, not two readings of the clock.
    ``context`` is what SQLAlchemy hands a default: the statement being run.
    In a statement that stores several rows at once, it gives the columns of
    each later row an ending of their own, the same for both columns.
    """
    ending = context.current_column.key.removeprefix("updated_at")
    moment: datetime = context.current_parameters["created_at" + ending]
    return moment


class Base(DeclarativeBase):
    """The class every model is a subclass of."""

    metadata = MetaData(naming_convention=NAMING)
    # What a column is when its model gives only the Python type. An int and
    # bytes become INTEGER and BLOB without being named here.
    type_annotation_map: ClassVar[dict[Any, type[TypeEngine[Any]]]] = {
        str: Text,
        float: REAL,
        datetime: UtcDateTime,
        bool: YesOrNo,
        NotEmpty: NotEmptyText,
        WebAddress: WebAddressText,
    }

    # The key of every table, and its first column. A model does not name it.
    id: Mapped[int] = mapped_column(primary_key=True, sort_order=-1)
    # When a row was first stored and when it was last changed. They are the
    # last columns of every table, and a model does not name them either.
    created_at: Mapped[datetime] = mapped_column(default=_this_moment)
    updated_at: Mapped[datetime] = mapped_column(default=_when_first_stored, onupdate=_this_moment)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Make the table of a new model strict and its key one that is never given twice.

        Both are done here and not left to the model, so that a model keeps
        them whatever else it says of its table. A column whose type
        brings a check gets its check here too.
        """
        super().__init_subclass__(**kwargs)
        table = cls.__dict__.get("__table__")
        if table is not None:
            table.dialect_options["sqlite"]["strict"] = True
            # AUTOINCREMENT: without it SQLite gives the key of a deleted last
            # row to the next new row, and what pointed to the old row by its
            # key (its history, where it came from) would point to the new one.
            table.dialect_options["sqlite"]["autoincrement"] = True
            for column in table.columns:
                if isinstance(column.type, WithItsCheck):
                    table.append_constraint(column.type.check_for(column.name))


def _has_the_key(table: Table) -> bool:
    """Say whether SQLite will give this table's key and never give one twice.

    SQLite does that for a key that is one whole-number column of the
    table's own, and only if the table asks for it.
    """
    key = list(table.primary_key.columns)
    return (
        [column.name for column in key] == ["id"]
        and isinstance(key[0].type, Integer)
        and not key[0].foreign_keys
        and bool(table.dialect_options["sqlite"]["autoincrement"])
    )


def _has_the_times(table: Table) -> bool:
    """Say whether this table has the two times as every table has them.

    Each is a time as the store keeps one and a row cannot be without it.
    The table gives neither a value of its own: the store's code does, by
    asking for it when a row is first stored, and for ``updated_at`` again
    whenever the row is changed.
    """
    first = table.columns.get("created_at")
    last = table.columns.get("updated_at")
    return (
        first is not None
        and last is not None
        and all(
            isinstance(time.type, UtcDateTime)
            and not time.nullable
            and time.server_default is None
            and time.default is not None
            and time.default.is_callable
            for time in (first, last)
        )
        and first.onupdate is None
        and last.onupdate is not None
        and last.onupdate.is_callable
    )


def _as_sqlite_is_given_it(check: CheckConstraint) -> str:
    """Give the text of a check as it is written when its table is made."""
    written = check.sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True, "include_table": False}
    )
    return str(written)


def _without_their_check(table: Table) -> list[tuple[str, WithItsCheck]]:
    """Name the columns whose type brings a check and whose table lacks it, each with its type.

    The check is the one the column's type gives
    (:class:`motosphere.db.checks.WithItsCheck`): of the name the naming
    rule gives it, and of the same text. A check of another name, and one
    of that name that says something else, do not count. Where a table
    has two checks of that name, one of them with that text is enough,
    whichever comes first: that there are two is another rule's to say.
    """
    checks: dict[str, set[str]] = {}
    for check in table.constraints:
        if isinstance(check, CheckConstraint):
            checks.setdefault(str(check.name), set()).add(_as_sqlite_is_given_it(check))
    without: list[tuple[str, WithItsCheck]] = []
    for column in table.columns:
        if isinstance(column.type, WithItsCheck):
            its_check = column.type.check_for(column.name)
            name = NAMING["ck"] % {"table_name": table.name, "constraint_name": its_check.name}
            if _as_sqlite_is_given_it(its_check) not in checks.get(name, set()):
                without.append((column.name, column.type))
    return without


def broken_rules(schema: MetaData) -> list[str]:
    """Say which tables of ``schema`` break a rule, one plain sentence for each break.

    A table must be strict, its key must be the one every table has, it
    must have the two times every table has, every column of it whose type
    brings a check must have that check, every other constraint and every
    index of it must have its name from the naming rule, not one given by
    hand, and no two of them may have the same name. A schema that keeps
    the rules gives an empty list.
    """
    breaks: list[str] = []
    for table in sorted(schema.tables.values(), key=lambda table: table.name):
        if not table.dialect_options["sqlite"]["strict"]:
            breaks.append(f"The table {table.name} is not strict.")
        if not _has_the_key(table):
            breaks.append(
                f"The table {table.name} does not have the key every table has: one "
                "whole-number column named id, whose values are never given twice."
            )
        if not _has_the_times(table):
            breaks.append(
                f"The table {table.name} does not have the times every table has: "
                "created_at and updated_at, which the store's code sets when a row is "
                "first stored and whenever it is changed."
            )
        breaks.extend(
            f"The table {table.name} does not refuse {its_type.refuses} in its column {name}: "
            f"it must have the check that {its_type.given_by} gives for the column, named by "
            "the naming rule."
            for name, its_type in _without_their_check(table)
        )
        named: list[Constraint | Index] = [
            *(one for one in table.constraints if not isinstance(one, PrimaryKeyConstraint)),
            *table.indexes,
        ]
        by_hand = sorted(str(one.name) for one in named if not isinstance(one.name, conv))
        breaks.extend(
            f"The table {table.name} has a name given by hand, {name}: "
            "constraints and indexes are named by the naming rule."
            for name in by_hand
        )
        times_given = Counter(str(one.name) for one in named)
        breaks.extend(
            f"The table {table.name} gives the name {name} to {count} of its constraints and "
            "indexes: each must have a name of its own."
            for name, count in sorted(times_given.items())
            if count > 1
        )
    return breaks
