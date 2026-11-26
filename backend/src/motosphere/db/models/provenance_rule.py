"""The rule that every table of collected records says where its records came from.

A model whose records are collected is a subclass of ``Collected``
(:mod:`motosphere.db.models.provenance`) and its table then has the eight
columns of the set, the index over the source of its records and the
check of its two times. Nothing in that stops a model from being a
subclass of ``Base`` where it should be one of ``Collected``, or from
saying a column of the set again in its own way. :func:`broken_provenance`
says in plain words which tables of a schema do so, and a test holds the
real schema to it.

A table holds collected records unless it is on a list of those that do
not. So a new table that nobody thought about is named, and the list
says of each table on it why it is there. The list of the real schema
is :data:`NOT_COLLECTED`.

The rule says the set a second time, in its own words (``_THE_SET``),
and does not take it from ``Collected``. That is meant: a change to the
set must then be made in both places, and a test fails as long as the
two do not agree.

The rule stands beside :func:`motosphere.db.base.broken_rules` and is not
a part of it. ``Base`` knows nothing of sources, and most of the schemas
that function is asked about hold nothing that was collected.
"""

from collections.abc import Collection, Mapping
from typing import Any, Final

from sqlalchemy import CheckConstraint, Column, Integer, MetaData, Table
from sqlalchemy.types import TypeEngine

from motosphere.db.base import NAMING
from motosphere.db.days import CalendarDay
from motosphere.db.lists import OneOf
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod
from motosphere.db.times import UtcDateTime
from motosphere.db.web import WebAddressText

__all__ = ["NOT_COLLECTED", "broken_provenance"]

# The tables of the store that hold no collected records, each with why.
# A table is put here only with its reason: every other table must say
# where its records came from.
NOT_COLLECTED: Final[Mapping[str, str]] = {
    "collection_run": (
        "A run is the store's own record of its work: it is what collects, "
        "and not what is collected."
    ),
    "record_change": (
        "A change is the store's own record of what it did to a record. Where the new "
        "value came from is said by the record, and by the run that caused the change."
    ),
    "source": (
        "A source is where records come from. A person describes it and reads "
        "its terms: it is not collected from a source itself."
    ),
    "source_offer": (
        "What a source offers is part of the description of the source, which a person gives."
    ),
}

# The columns every table of collected records has, in their order, each
# with its type. They are said here a second time: see the top of the module.
_THE_SET: Final[Mapping[str, TypeEngine[Any]]] = {
    "source_id": Integer(),
    "source_address": WebAddressText(),
    "collected_at": UtcDateTime(),
    "published_on": CalendarDay(),
    "last_verified_at": UtcDateTime(),
    "extraction_method": OneOf(CollectionMethod),
    "confidence": OneOf(Confidence),
    "verification_status": OneOf(VerificationStatus),
}
# The one column of the set that may be without a value.
_MAY_BE_UNKNOWN: Final = "published_on"
# The one column of the set that refers to another table, and what it refers to.
_REFERS: Final = {"source_id": "source.id"}
# The check that holds the two times of a record together: the last part
# of its name, and what it says.
_THE_TWO_TIMES: Final = (
    "last_verified_at_not_before_collected_at",
    "last_verified_at >= collected_at",
)


def _of_the_same_type(found: TypeEngine[Any], wanted: TypeEngine[Any]) -> bool:
    """Say whether a column's type is the one the set has for it, and of the same list."""
    if type(found) is not type(wanted):
        return False
    if isinstance(found, OneOf) and isinstance(wanted, OneOf):
        return found.the_list is wanted.the_list
    return True


def _as_the_set_has_it(column: Column[Any]) -> bool:
    """Say whether a column of a table is as every table of collected records has it.

    It is of the type the set has for it. A row cannot be without it,
    unless it is the day the record was published. The table gives it no
    value, and neither does the store's code. It refers to the source if
    it is the source of the record, and to nothing otherwise, and says
    nothing of what happens when what it refers to is deleted or changed.
    """
    refers_to = {(key.target_fullname, key.ondelete, key.onupdate) for key in column.foreign_keys}
    wanted = {(_REFERS[column.name], None, None)} if column.name in _REFERS else set()
    return (
        _of_the_same_type(column.type, _THE_SET[column.name])
        and column.nullable == (column.name == _MAY_BE_UNKNOWN)
        and column.default is None
        and column.server_default is None
        and column.onupdate is None
        and column.server_onupdate is None
        and refers_to == wanted
    )


def _finds_the_records_of_a_source(table: Table) -> bool:
    """Say whether the table has an index over the source of its records alone.

    The index is over all rows, and two rows can be alike in it.
    """
    return any(
        [column.name for column in index.columns] == ["source_id"]
        and not index.unique
        and index.dialect_options["sqlite"]["where"] is None
        for index in table.indexes
    )


def _holds_its_two_times(table: Table) -> bool:
    """Say whether the table has the check of its two times, as ``Collected`` gives it.

    The check has the name the naming rule gives it and says what the
    check of ``Collected`` says, letter for letter.
    """
    last_part, says = _THE_TWO_TIMES
    name = NAMING["ck"] % {"table_name": table.name, "constraint_name": last_part}
    return any(
        isinstance(check, CheckConstraint)
        and str(check.name) == name
        and str(check.sqltext) == says
        for check in table.constraints
    )


def broken_provenance(schema: MetaData, not_collected: Collection[str]) -> list[str]:
    """Say which tables of ``schema`` do not say where their records came from.

    There is one plain sentence for each break, and a schema that keeps
    the rule gives an empty list. Every table holds collected records
    unless ``not_collected`` names it. Such a table must have the eight
    columns of the set, each as ``Collected`` gives it, an index over the
    source of its records alone, and the check that holds its two times
    together.

    The list is held to the schema as well: a name on it that is no
    table is named, and so is a table on it that has all eight columns.
    A table on the list is not looked at otherwise.
    """
    breaks = [
        f"The list of the tables that hold no collected records names {name}, "
        "which is no table of the schema."
        for name in sorted(set(not_collected) - set(schema.tables))
    ]
    for table in sorted(schema.tables.values(), key=lambda table: table.name):
        without = [name for name in _THE_SET if name not in table.columns]
        if table.name in not_collected:
            if not without:
                breaks.append(
                    f"The table {table.name} has the eight columns of collected records and is "
                    "on the list of the tables that hold none: it must come off the list."
                )
            continue
        if without:
            breaks.append(
                f"The table {table.name} is without {len(without)} of the eight columns every "
                f"table of collected records has ({', '.join(without)}): its model must be a "
                "subclass of Collected, or the table must be on the list of the tables that "
                "hold no collected records, with the reason."
            )
        breaks.extend(
            f"The table {table.name} does not have the column {name} as every table of "
            "collected records has it: a model takes the columns from Collected and does "
            "not say them itself."
            for name in _THE_SET
            if name in table.columns and not _as_the_set_has_it(table.columns[name])
        )
        if "source_id" in table.columns and not _finds_the_records_of_a_source(table):
            breaks.append(
                f"The table {table.name} has no index over source_id alone: every table of "
                "collected records has one, so that the records of one source are found "
                "without reading the whole table."
            )
        if not {"collected_at", "last_verified_at"} & set(without) and not _holds_its_two_times(
            table
        ):
            breaks.append(
                f"The table {table.name} does not refuse a record that was last seen at its "
                "source before it was collected: it must have the check that Collected gives, "
                "named by the naming rule."
            )
    return breaks
