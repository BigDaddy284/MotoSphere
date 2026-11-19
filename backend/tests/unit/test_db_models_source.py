"""Tests of the two lists an information source is described by. They need no store."""

import re
from enum import StrEnum

import pytest
from sqlalchemy.dialects import sqlite

from motosphere.db.lists import OneOf
from motosphere.db.models.source import CollectionMethod, SourceCategory

# The texts that are stored, written out: a text changed by mistake fails here.
CATEGORIES = [
    "governing body",
    "championship",
    "organiser",
    "promoter",
    "track",
    "club",
    "regional organisation",
    "results database",
    "news publication",
    "community website",
    "social media page",
    "historical archive",
]
METHODS = [
    "official api",
    "structured feed",
    "rss feed",
    "public dataset",
    "html extraction",
    "structured document",
    "json endpoint",
    "sitemap discovery",
    "search engine discovery",
    "human submission",
]
BOTH = pytest.mark.parametrize(
    ("the_list", "texts"),
    [(SourceCategory, CATEGORIES), (CollectionMethod, METHODS)],
    ids=["the kinds of source", "the ways of collecting"],
)


def test_there_are_the_twelve_kinds_of_source_and_the_ten_ways_of_collecting() -> None:
    assert (len(CATEGORIES), len(METHODS)) == (12, 10)
    assert (len(SourceCategory), len(CollectionMethod)) == (12, 10)


@BOTH
def test_a_list_has_exactly_its_texts_in_the_order_of_the_design(
    the_list: type[StrEnum], texts: list[str]
) -> None:
    assert [value.value for value in the_list] == texts


@BOTH
def test_no_text_of_a_list_has_two_names(the_list: type[StrEnum], texts: list[str]) -> None:
    assert len(the_list.__members__) == len(texts)
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("value", [*SourceCategory, *CollectionMethod], ids=lambda value: value)
def test_a_text_is_words_in_small_letters_with_one_space_between_two(value: StrEnum) -> None:
    assert re.fullmatch(r"[a-z]+( [a-z]+)*", value.value)


@BOTH
def test_a_column_can_be_of_the_list_and_its_check_names_the_texts(
    the_list: type[StrEnum], texts: list[str]
) -> None:
    check = OneOf(the_list).check_for("described")
    written = check.sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )

    assert check.name == "described_one_of"
    assert str(written) == "described IN (" + ", ".join(f"'{text}'" for text in texts) + ")"
