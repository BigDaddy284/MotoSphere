"""Tests of text that must not be empty, without a store.

``tests/integration/test_texts.py`` asks a real SQLite file what it refuses.
"""

import sys

from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import conv

from motosphere.db.base import NAMING
from motosphere.db.checks import WithItsCheck
from motosphere.db.texts import WHITE_SPACE, NotEmptyText, not_empty

THE_CHECK = (
    "trim({}, char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, "
    "8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)) != ''"
)


def said(name: str) -> str:
    """The check of a column of this name, as SQLite is given it."""
    written = not_empty(name).sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )
    return str(written)


def test_the_white_space_is_what_python_calls_white_space() -> None:
    pythons = tuple(number for number in range(sys.maxunicode + 1) if chr(number).isspace())

    assert pythons == WHITE_SPACE
    assert len(WHITE_SPACE) == 29


def test_the_white_space_is_what_pythons_strip_takes_off() -> None:
    kept = [number for number in WHITE_SPACE if (chr(number) + "a" + chr(number)).strip() != "a"]

    assert kept == []
    assert "".join(chr(number) for number in WHITE_SPACE).strip() == ""


def test_the_check_takes_the_white_space_off_and_refuses_what_is_then_empty() -> None:
    assert said("name") == THE_CHECK.format("name")


def test_the_check_of_a_column_named_with_a_word_of_sql_names_it_in_quotes() -> None:
    assert said("group") == THE_CHECK.format('"group"')


def test_the_check_is_named_after_its_column_and_by_the_naming_rule() -> None:
    check = not_empty("name")

    assert check.name == "name_not_empty"

    owner = Table(
        "owner",
        MetaData(naming_convention=NAMING),
        Column("id", Integer),
        Column("name", NotEmptyText),
    )

    assert check not in owner.constraints

    owner.append_constraint(check)

    assert check.name == "ck_owner_name_not_empty"
    assert isinstance(check.name, conv)


def test_the_type_brings_the_check_that_not_empty_gives() -> None:
    its_type = NotEmptyText()
    brought = its_type.check_for("name")

    assert isinstance(its_type, WithItsCheck)
    assert brought.name == "name_not_empty"
    assert str(
        brought.sqltext.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    ) == said("name")
    assert its_type.refuses == "empty text"
    assert its_type.given_by == not_empty.__name__


def test_in_the_table_the_type_is_text() -> None:
    assert NotEmptyText().compile(dialect=sqlite.dialect()) == "TEXT"
