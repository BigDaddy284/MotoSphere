"""Tests of the two lists of the review queue. They need no store.

One list says what is in doubt, and the other whether an item was
decided and how.
"""

import re
from enum import StrEnum

import pytest
from sqlalchemy.dialects import sqlite

from motosphere.db.lists import OneOf
from motosphere.db.models.review_item import ReviewKind, ReviewState

# The texts that are stored, written out: a text changed by mistake fails here.
KINDS = ["possible duplicate", "sources disagree", "value outside its rules"]
STATES = ["open", "accepted", "rejected"]
EACH = pytest.mark.parametrize(
    ("the_list", "texts"),
    [(ReviewKind, KINDS), (ReviewState, STATES)],
    ids=["what is in doubt", "whether it was decided"],
)


def test_there_are_the_three_kinds_of_doubt_and_the_three_states() -> None:
    assert (len(KINDS), len(STATES)) == (3, 3)
    assert (len(ReviewKind), len(ReviewState)) == (3, 3)


@EACH
def test_a_list_has_exactly_its_texts_in_their_order(
    the_list: type[StrEnum], texts: list[str]
) -> None:
    assert [value.value for value in the_list] == texts


@EACH
def test_no_text_of_a_list_has_two_names(the_list: type[StrEnum], texts: list[str]) -> None:
    assert len(the_list.__members__) == len(texts)
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("value", [*ReviewKind, *ReviewState], ids=lambda value: value)
def test_a_text_is_words_in_small_letters_with_one_space_between_two(value: StrEnum) -> None:
    assert re.fullmatch(r"[a-z]+( [a-z]+)*", value.value)


def test_an_item_that_is_new_is_open_and_open_is_first_on_its_list() -> None:
    assert next(iter(ReviewState)) is ReviewState.OPEN


@EACH
def test_a_column_can_be_of_the_list_and_its_check_names_the_texts(
    the_list: type[StrEnum], texts: list[str]
) -> None:
    check = OneOf(the_list).check_for("said")
    written = check.sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )

    assert check.name == "said_one_of"
    assert str(written) == "said IN (" + ", ".join(f"'{text}'" for text in texts) + ")"
