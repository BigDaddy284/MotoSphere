"""Tests of yes or no in the store, without a store.

``tests/integration/test_yes_no.py`` asks a real SQLite file what it refuses.
"""

from typing import Any

import pytest
from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import conv

from motosphere.db import times
from motosphere.db.base import NAMING, broken_rules
from motosphere.db.checks import WithItsCheck
from motosphere.db.times import UtcDateTime
from motosphere.db.yes_no import YesOrNo, from_number, to_number, yes_or_no


def said(name: str) -> str:
    """The check of a column of this name, as SQLite is given it."""
    written = yes_or_no(name).sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )
    return str(written)


def test_yes_is_said_as_1_and_no_as_0() -> None:
    assert to_number(True) == 1
    assert to_number(False) == 0
    # A whole number, not Python's True and False under another name.
    assert [type(to_number(value)) for value in (True, False)] == [int, int]


@pytest.mark.parametrize(
    ("value", "sentence"),
    [
        (1, "Only yes or no (True or False) is stored as yes or no, not int: 1."),
        (0, "Only yes or no (True or False) is stored as yes or no, not int: 0."),
        ("no", "Only yes or no (True or False) is stored as yes or no, not str: 'no'."),
        ("", "Only yes or no (True or False) is stored as yes or no, not str: ''."),
        (1.0, "Only yes or no (True or False) is stored as yes or no, not float: 1.0."),
    ],
    ids=["the number 1", "the number 0", "the word no", "empty text", "a number with a fraction"],
)
def test_what_is_neither_true_nor_false_is_refused(value: Any, sentence: str) -> None:
    with pytest.raises(TypeError, match="Only yes or no") as refused:
        to_number(value)

    assert str(refused.value) == sentence


def test_1_is_read_as_yes_and_0_as_no() -> None:
    assert from_number(1) is True
    assert from_number(0) is False


@pytest.mark.parametrize(
    "number",
    [2, -1, 1.0, "1", True],
    ids=["two", "less than nothing", "a number with a fraction", "text", "Python's True"],
)
def test_what_is_neither_1_nor_0_is_refused_and_not_read_as_yes(number: Any) -> None:
    with pytest.raises(ValueError, match="neither yes") as refused:
        from_number(number)

    assert str(refused.value) == (
        f"The store holds what is neither yes (1) nor no (0): {number!r}."
    )


def test_the_column_type_stores_the_number_and_reads_yes_or_no() -> None:
    column_type = YesOrNo()
    dialect = sqlite.dialect()

    assert column_type.process_bind_param(True, dialect) == 1
    assert column_type.process_bind_param(False, dialect) == 0
    assert column_type.process_result_value(1, dialect) is True
    assert column_type.process_result_value(0, dialect) is False


def test_the_column_type_leaves_no_value_as_no_value() -> None:
    column_type = YesOrNo()
    dialect = sqlite.dialect()

    assert column_type.process_bind_param(None, dialect) is None
    assert column_type.process_result_value(None, dialect) is None


def test_in_the_table_the_type_is_a_whole_number() -> None:
    assert str(YesOrNo().compile(dialect=sqlite.dialect())) == "INTEGER"


def test_the_check_allows_the_two_numbers_and_no_other() -> None:
    assert said("active") == "active IN (0, 1)"


def test_the_check_of_a_column_named_with_a_word_of_sql_names_it_in_quotes() -> None:
    assert said("group") == '"group" IN (0, 1)'


def test_the_check_is_named_after_its_column_and_by_the_naming_rule() -> None:
    check = yes_or_no("active")

    assert check.name == "active_yes_or_no"

    owner = Table(
        "owner",
        MetaData(naming_convention=NAMING),
        Column("id", Integer),
        Column("active", YesOrNo),
    )

    assert check not in owner.constraints

    owner.append_constraint(check)

    assert check.name == "ck_owner_active_yes_or_no"
    assert isinstance(check.name, conv)


def test_the_type_brings_the_check_that_yes_or_no_gives() -> None:
    its_type = YesOrNo()
    brought = its_type.check_for("active")

    assert isinstance(its_type, WithItsCheck)
    assert brought.name == "active_yes_or_no"
    assert str(
        brought.sqltext.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    ) == said("active")
    assert its_type.refuses == "a number other than 0 and 1"
    assert its_type.given_by == yes_or_no.__name__


def test_a_column_that_is_yes_or_no_is_named_until_its_table_has_the_check() -> None:
    schema = MetaData(naming_convention=NAMING)
    owner = Table(
        "owner",
        schema,
        Column("id", Integer, primary_key=True),
        Column("active", YesOrNo, nullable=False),
        Column("created_at", UtcDateTime, nullable=False, default=times.now),
        Column("updated_at", UtcDateTime, nullable=False, default=times.now, onupdate=times.now),
        sqlite_strict=True,
        sqlite_autoincrement=True,
    )

    assert broken_rules(schema) == [
        "The table owner does not refuse a number other than 0 and 1 in its column active: "
        "it must have the check that yes_or_no gives for the column, named by the naming rule."
    ]

    owner.append_constraint(yes_or_no("active"))

    assert broken_rules(schema) == []
