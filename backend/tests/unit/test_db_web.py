"""Tests of a web address, without a store.

``tests/integration/test_web.py`` asks a real SQLite file what it refuses.
"""

from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import conv

from motosphere.db import times
from motosphere.db.base import NAMING, Base, broken_rules
from motosphere.db.checks import WithItsCheck
from motosphere.db.texts import WHITE_SPACE
from motosphere.db.times import UtcDateTime
from motosphere.db.web import WebAddress, WebAddressText, web_address

THE_CHECK = (
    "(({0} GLOB '[Hh][Tt][Tt][Pp][Ss]://[^/?#]*') OR ({0} GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*')) "
    "AND NOT ({0} GLOB '*[' || char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, "
    "8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, "
    "12288) || ']*') AND instr({0}, char(0)) = 0"
)


def said(name: str) -> str:
    """The check of a column of this name, as SQLite is given it."""
    written = web_address(name).sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )
    return str(written)


def a_table(schema: MetaData) -> Table:
    """A table made by hand that keeps every rule but one: two of its columns have no check."""
    return Table(
        "source",
        schema,
        Column("id", Integer, primary_key=True),
        Column("website", WebAddressText, nullable=False),
        Column("feed", WebAddressText),
        Column("created_at", UtcDateTime, nullable=False, default=times.now),
        Column("updated_at", UtcDateTime, nullable=False, default=times.now, onupdate=times.now),
        sqlite_strict=True,
        sqlite_autoincrement=True,
    )


def test_the_check_says_how_an_address_begins_and_what_it_must_not_have() -> None:
    assert said("website") == THE_CHECK.format("website")


def test_the_check_of_a_column_named_with_a_word_of_sql_names_it_in_quotes() -> None:
    assert said("group") == THE_CHECK.format('"group"')


def test_the_white_space_of_the_check_is_the_stores_own_list() -> None:
    the_list = "char(" + ", ".join(str(number) for number in WHITE_SPACE) + ")"

    assert f"GLOB '*[' || {the_list} || ']*'" in said("website")


def test_the_check_is_named_after_its_column_and_by_the_naming_rule() -> None:
    check = web_address("website")

    assert check.name == "website_web_address"

    owner = Table(
        "owner",
        MetaData(naming_convention=NAMING),
        Column("id", Integer),
        Column("website", WebAddressText),
    )

    assert check not in owner.constraints

    owner.append_constraint(check)

    assert check.name == "ck_owner_website_web_address"
    assert isinstance(check.name, conv)


def test_the_type_brings_the_check_that_web_address_gives() -> None:
    its_type = WebAddressText()
    brought = its_type.check_for("website")

    assert isinstance(its_type, WithItsCheck)
    assert brought.name == "website_web_address"
    assert str(
        brought.sqltext.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    ) == said("website")
    assert its_type.refuses == "text that is not a web address"
    assert its_type.given_by == web_address.__name__


def test_in_the_table_the_type_is_text() -> None:
    assert WebAddressText().compile(dialect=sqlite.dialect()) == "TEXT"


def test_a_model_says_a_web_address_by_the_columns_python_type() -> None:
    assert Base.type_annotation_map[WebAddress] is WebAddressText


def test_such_a_column_is_named_until_its_table_has_the_check() -> None:
    sentence = (
        "The table source does not refuse text that is not a web address in its column {}: it "
        "must have the check that web_address gives for the column, named by the naming rule."
    )
    schema = MetaData(naming_convention=NAMING)
    source = a_table(schema)

    assert broken_rules(schema) == [sentence.format("website"), sentence.format("feed")]

    source.append_constraint(web_address("website"))

    assert broken_rules(schema) == [sentence.format("feed")]

    source.append_constraint(web_address("feed"))

    assert broken_rules(schema) == []
