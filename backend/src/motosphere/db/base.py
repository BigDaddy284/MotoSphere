"""The base of every model: the rules all tables of the data store share.

A model is a class that describes one table. Every model is a subclass of
:class:`Base`, and so every table

- is a strict table: SQLite refuses a value that is not of its column's
  type, where an ordinary table would store whatever it is given;
- has columns of the few types a strict table takes: a Python ``int``
  becomes INTEGER, a ``str`` TEXT, a ``float`` REAL and ``bytes`` BLOB;
- has its constraints and indexes named by one rule, :data:`NAMING`, so
  that a migration can name what it changes and the names are the same on
  every machine.

:func:`broken_rules` says in plain words which tables of a schema break a
rule. A test holds the real schema to it.
"""

from typing import Any, ClassVar

from sqlalchemy import REAL, Constraint, Index, MetaData, Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.schema import conv
from sqlalchemy.types import TypeEngine

__all__ = ["NAMING", "Base", "broken_rules"]

# How constraints and indexes are named. A check has no columns to be named
# after, so it is given the last part of its name where it is written:
# CheckConstraint("laps > 0", name="laps_positive") is ck_<table>_laps_positive.
# A check without a name is refused when its table is defined.
NAMING = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
}


class Base(DeclarativeBase):
    """The class every model is a subclass of."""

    metadata = MetaData(naming_convention=NAMING)
    # What a column is when its model gives only the Python type. An int and
    # bytes become INTEGER and BLOB without being named here.
    type_annotation_map: ClassVar[dict[type, type[TypeEngine[Any]]]] = {
        str: Text,
        float: REAL,
    }

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Make the table of a new model strict, whatever else the model says of it."""
        super().__init_subclass__(**kwargs)
        table = cls.__dict__.get("__table__")
        if table is not None:
            table.dialect_options["sqlite"]["strict"] = True


def broken_rules(schema: MetaData) -> list[str]:
    """Say which tables of ``schema`` break a rule, one plain sentence for each break.

    A table must be strict, and every constraint and index of it must have
    its name from the naming rule, not one given by hand. A schema that
    keeps the rules gives an empty list.
    """
    breaks: list[str] = []
    for table in sorted(schema.tables.values(), key=lambda table: table.name):
        if not table.dialect_options["sqlite"]["strict"]:
            breaks.append(f"The table {table.name} is not strict.")
        named: list[Constraint | Index] = [*table.constraints, *table.indexes]
        by_hand = sorted(str(one.name) for one in named if not isinstance(one.name, conv))
        breaks.extend(
            f"The table {table.name} has a name given by hand, {name}: "
            "constraints and indexes are named by the naming rule."
            for name in by_hand
        )
    return breaks
