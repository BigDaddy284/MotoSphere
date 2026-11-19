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
  becomes INTEGER, a ``str`` TEXT, a ``float`` REAL and ``bytes`` BLOB, and
  a ``datetime`` becomes the store's own type for a time
  (:class:`motosphere.db.times.UtcDateTime`), which is TEXT in the table;
- has its constraints and indexes named by one rule, :data:`NAMING`, so
  that a migration can name what it changes and the names are the same on
  every machine. The key has no name: SQLite writes it with its column.

:func:`broken_rules` says in plain words which tables of a schema break a
rule. A test holds the real schema to it.
"""

from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import REAL, Constraint, Index, Integer, MetaData, PrimaryKeyConstraint, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.schema import conv
from sqlalchemy.types import TypeEngine

from motosphere.db import times
from motosphere.db.times import UtcDateTime

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
    type_annotation_map: ClassVar[dict[type, type[TypeEngine[Any]]]] = {
        str: Text,
        float: REAL,
        datetime: UtcDateTime,
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
        them whatever else it says of its table.
        """
        super().__init_subclass__(**kwargs)
        table = cls.__dict__.get("__table__")
        if table is not None:
            table.dialect_options["sqlite"]["strict"] = True
            # AUTOINCREMENT: without it SQLite gives the key of a deleted last
            # row to the next new row, and what pointed to the old row by its
            # key (its history, where it came from) would point to the new one.
            table.dialect_options["sqlite"]["autoincrement"] = True


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


def broken_rules(schema: MetaData) -> list[str]:
    """Say which tables of ``schema`` break a rule, one plain sentence for each break.

    A table must be strict, its key must be the one every table has, and
    every other constraint and every index of it must have its name from
    the naming rule, not one given by hand. A schema that keeps the rules
    gives an empty list.
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
    return breaks
