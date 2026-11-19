"""Tests of a column whose value is one of a list, without a store.

``tests/integration/test_lists.py`` asks a real SQLite file what it refuses.
"""

from enum import Enum, StrEnum
from typing import Any

import pytest
from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import conv

from motosphere.db import times
from motosphere.db.base import NAMING, broken_rules
from motosphere.db.checks import WithItsCheck
from motosphere.db.lists import OneOf, one_of
from motosphere.db.times import UtcDateTime


class Kind(StrEnum):
    TRACK = "track"
    CLUB = "club"


class Surface(StrEnum):
    """A second list. One of its texts is a text of the first list too."""

    SAND = "sand"
    HARD_PACK = "hard pack"
    TRACK = "track"


class Odd(StrEnum):
    """Texts with the characters a statement of SQL has a use for, and one in large letters."""

    QUOTE = "o'brien"
    TWO_QUOTES = 'say "go"'
    PERCENT = "50%"
    COLON = "a:b"
    QUESTION = "what?"
    BACKSLASH = "a\\b"
    LARGE = "MXoN"


class Twice(StrEnum):
    """A list with two names for one value."""

    DIRT = "dirt"
    SOIL = "dirt"
    GRASS = "grass"


class Colour(Enum):
    """Not a list of the store's kind: its values are not texts."""

    RED = 1


NOT_ON_IT = "The store holds what is not on the list Kind: {!r}."
NO_CHECK = (
    "The table owner does not refuse text that is not on its list in its column kind: "
    "it must have the check that one_of gives for the column, named by the naming rule."
)


def said(name: str, the_list: type[StrEnum]) -> str:
    """The check of a column of this name and list, as SQLite is given it."""
    written = one_of(name, the_list).sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )
    return str(written)


def test_a_value_of_the_list_is_stored_as_its_text() -> None:
    stored = OneOf(Kind).process_bind_param(Kind.CLUB, sqlite.dialect())

    assert stored == "club"
    # Plain text, not the value of the list under another name.
    assert type(stored) is str


@pytest.mark.parametrize(
    ("value", "sentence"),
    [
        ("track", "not str: 'track'."),
        ("shop", "not str: 'shop'."),
        (Surface.TRACK, "not Surface: <Surface.TRACK: 'track'>."),
        (1, "not int: 1."),
    ],
    ids=[
        "text that is spelled like a value",
        "text that is not on the list",
        "a value of another list with the same text",
        "a number",
    ],
)
def test_what_is_not_a_value_of_the_list_is_refused(value: Any, sentence: str) -> None:
    with pytest.raises(TypeError, match="Only a value of the list") as refused:
        OneOf(Kind).process_bind_param(value, sqlite.dialect())

    assert str(refused.value) == (
        f"Only a value of the list Kind is stored in this column, {sentence}"
    )


def test_the_text_is_read_as_the_value_of_the_list() -> None:
    column_type = OneOf(Kind)
    dialect = sqlite.dialect()

    assert column_type.process_result_value("track", dialect) is Kind.TRACK
    assert column_type.process_result_value("club", dialect) is Kind.CLUB
    assert OneOf(Surface).process_result_value("track", dialect) is Surface.TRACK


@pytest.mark.parametrize(
    "text",
    ["shop", "TRACK", "track ", "", "sand", 1],
    ids=[
        "another word",
        "in large letters",
        "with a space after it",
        "nothing",
        "a text of another list",
        "a number",
    ],
)
def test_text_that_is_not_on_the_list_is_refused_when_it_is_read(text: Any) -> None:
    with pytest.raises(ValueError, match="not on the list") as refused:
        OneOf(Kind).process_result_value(text, sqlite.dialect())

    assert str(refused.value) == NOT_ON_IT.format(text)
    # The sentence is the whole of it: Python's own refusal is not shown behind it.
    assert refused.value.__suppress_context__


def test_the_column_type_leaves_no_value_as_no_value() -> None:
    column_type = OneOf(Kind)
    dialect = sqlite.dialect()

    assert column_type.process_bind_param(None, dialect) is None
    assert column_type.process_result_value(None, dialect) is None


def test_in_the_table_the_type_is_text() -> None:
    assert str(OneOf(Kind).compile(dialect=sqlite.dialect())) == "TEXT"


def test_the_check_names_the_texts_in_the_order_of_the_list() -> None:
    assert said("kind", Kind) == "kind IN ('track', 'club')"
    assert said("surface", Surface) == "surface IN ('sand', 'hard pack', 'track')"


def test_the_check_of_a_column_named_with_a_word_of_sql_names_it_in_quotes() -> None:
    assert said("group", Kind) == "\"group\" IN ('track', 'club')"


def test_a_text_is_written_into_the_check_as_text_whatever_characters_it_has() -> None:
    assert said("mark", Odd) == (
        "mark IN ('o''brien', 'say \"go\"', '50%', 'a:b', 'what?', 'a\\b', 'MXoN')"
    )


def test_a_value_with_two_names_is_named_once() -> None:
    assert said("ground", Twice) == "ground IN ('dirt', 'grass')"
    assert OneOf(Twice).process_bind_param(Twice.SOIL, sqlite.dialect()) == "dirt"
    assert OneOf(Twice).process_result_value("dirt", sqlite.dialect()) is Twice.DIRT


def test_the_check_is_named_after_its_column_and_by_the_naming_rule() -> None:
    check = one_of("kind", Kind)

    assert check.name == "kind_one_of"

    owner = Table(
        "owner",
        MetaData(naming_convention=NAMING),
        Column("id", Integer),
        Column("kind", OneOf(Kind)),
    )

    assert check not in owner.constraints

    owner.append_constraint(check)

    assert check.name == "ck_owner_kind_one_of"
    assert isinstance(check.name, conv)


def test_the_type_brings_the_check_that_one_of_gives_for_its_list() -> None:
    its_type = OneOf(Surface)
    brought = its_type.check_for("surface")

    assert isinstance(its_type, WithItsCheck)
    assert brought.name == "surface_one_of"
    assert str(
        brought.sqltext.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    ) == said("surface", Surface)
    assert its_type.refuses == "text that is not on its list"
    assert its_type.given_by == one_of.__name__


@pytest.mark.parametrize(
    ("not_a_list", "shown"),
    [
        (str, "<class 'str'>"),
        (Colour, "<enum 'Colour'>"),
        (["track", "club"], "['track', 'club']"),
        (Kind.TRACK, "<Kind.TRACK: 'track'>"),
        ("Kind", "'Kind'"),
    ],
    ids=[
        "text itself",
        "an enum whose values are not texts",
        "texts in square brackets",
        "a value of a list",
        "the name of a list",
    ],
)
def test_what_is_not_a_list_is_refused(not_a_list: Any, shown: str) -> None:
    with pytest.raises(TypeError, match="A list is a StrEnum") as refused:
        OneOf(not_a_list)

    assert str(refused.value) == f"A list is a StrEnum, with the texts that are stored: {shown}."


def test_a_list_with_nothing_on_it_is_refused() -> None:
    class Nothing(StrEnum):
        pass

    with pytest.raises(ValueError, match="nothing on it") as refused:
        OneOf(Nothing)

    assert str(refused.value) == "The list Nothing has nothing on it."


@pytest.mark.parametrize(
    "empty",
    ["", " ", "\t\n", chr(160)],
    ids=["no characters", "a space", "a tab and a line end", "the space that cannot be broken"],
)
def test_a_list_with_an_empty_value_is_refused(empty: str) -> None:
    class Holed(StrEnum):
        FULL = "full"
        EMPTY = empty

    with pytest.raises(ValueError, match="an empty value") as refused:
        OneOf(Holed)

    assert str(refused.value) == f"The list Holed has an empty value: <Holed.EMPTY: {empty!r}>."


def a_table(schema: MetaData) -> Table:
    """A table made by hand that keeps every rule but one: its column kind has no check."""
    return Table(
        "owner",
        schema,
        Column("id", Integer, primary_key=True),
        Column("kind", OneOf(Kind), nullable=False),
        Column("created_at", UtcDateTime, nullable=False, default=times.now),
        Column("updated_at", UtcDateTime, nullable=False, default=times.now, onupdate=times.now),
        sqlite_strict=True,
        sqlite_autoincrement=True,
    )


def test_such_a_column_is_named_until_its_table_has_the_check() -> None:
    schema = MetaData(naming_convention=NAMING)
    owner = a_table(schema)

    assert broken_rules(schema) == [NO_CHECK]

    owner.append_constraint(one_of("kind", Kind))

    assert broken_rules(schema) == []


def test_the_check_for_another_list_does_not_count() -> None:
    schema = MetaData(naming_convention=NAMING)
    owner = a_table(schema)
    owner.append_constraint(one_of("kind", Surface))

    assert broken_rules(schema) == [NO_CHECK]
