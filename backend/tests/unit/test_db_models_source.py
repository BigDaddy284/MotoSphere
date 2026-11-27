"""Tests of the lists of the information sources. They need no store.

Two lists describe a source: what kind of source it is and how it is
collected from. The third names the kinds of information a source can
offer.
"""

import re
from enum import StrEnum

import pytest
from sqlalchemy.dialects import sqlite

from motosphere.db.lists import OneOf
from motosphere.db.models.source import CollectionMethod, InformationType, SourceCategory

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
    "reference list",
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
TYPES = [
    "tracks",
    "events",
    "championships",
    "results",
    "standings",
    "riders",
    "teams",
    "news",
    "reference data",
]
EACH = pytest.mark.parametrize(
    ("the_list", "texts"),
    [(SourceCategory, CATEGORIES), (CollectionMethod, METHODS), (InformationType, TYPES)],
    ids=["the kinds of source", "the ways of collecting", "the kinds of information"],
)


def test_there_are_the_thirteen_kinds_of_source_and_the_ten_ways_of_collecting() -> None:
    assert (len(CATEGORIES), len(METHODS)) == (13, 10)
    assert (len(SourceCategory), len(CollectionMethod)) == (13, 10)


def test_the_kind_that_is_this_projects_own_stands_after_the_twelve_of_the_design() -> None:
    # DESIGN.md 7.1 has twelve kinds of source, each a kind of website of
    # the sport. A keeper of reference lists is none of them (DAT-058).
    assert SourceCategory.REFERENCE.value == "reference list"
    assert list(SourceCategory).index(SourceCategory.REFERENCE) == 12
    assert list(SourceCategory)[11] is SourceCategory.ARCHIVE


def test_there_are_the_nine_kinds_of_information() -> None:
    assert len(TYPES) == 9
    assert len(InformationType) == 9


@EACH
def test_a_list_has_exactly_its_texts_in_their_order(
    the_list: type[StrEnum], texts: list[str]
) -> None:
    assert [value.value for value in the_list] == texts


@EACH
def test_no_text_of_a_list_has_two_names(the_list: type[StrEnum], texts: list[str]) -> None:
    assert len(the_list.__members__) == len(texts)
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize(
    "value", [*SourceCategory, *CollectionMethod, *InformationType], ids=lambda value: value
)
def test_a_text_is_words_in_small_letters_with_one_space_between_two(value: StrEnum) -> None:
    assert re.fullmatch(r"[a-z]+( [a-z]+)*", value.value)


@EACH
def test_a_column_can_be_of_the_list_and_its_check_names_the_texts(
    the_list: type[StrEnum], texts: list[str]
) -> None:
    check = OneOf(the_list).check_for("described")
    written = check.sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )

    assert check.name == "described_one_of"
    assert str(written) == "described IN (" + ", ".join(f"'{text}'" for text in texts) + ")"
