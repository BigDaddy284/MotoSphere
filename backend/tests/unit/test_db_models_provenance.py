"""Tests of the lists that say how far a collected record can be trusted.

They need no store. One list says how sure it is that a record says what
its source says, the other what standing the source's word has.
"""

import re
from enum import StrEnum

import pytest
from sqlalchemy.dialects import sqlite

from motosphere.db.lists import OneOf
from motosphere.db.models.provenance import Confidence, VerificationStatus

# The texts that are stored, written out: a text changed by mistake fails here.
LEVELS = ["high", "medium", "low"]
STATUSES = ["official", "independent", "reconstructed", "unverified"]
EACH = pytest.mark.parametrize(
    ("the_list", "texts"),
    [(Confidence, LEVELS), (VerificationStatus, STATUSES)],
    ids=["how sure", "what standing"],
)
EVERY_VALUE = pytest.mark.parametrize(
    "value", [*Confidence, *VerificationStatus], ids=lambda value: value
)


def test_there_are_the_three_levels_of_confidence_and_the_four_statuses() -> None:
    assert (len(LEVELS), len(STATUSES)) == (3, 4)
    assert (len(Confidence), len(VerificationStatus)) == (3, 4)


@EACH
def test_a_list_has_exactly_its_texts_in_their_order(
    the_list: type[StrEnum], texts: list[str]
) -> None:
    assert [value.value for value in the_list] == texts


@EACH
def test_no_text_of_a_list_has_two_names(the_list: type[StrEnum], texts: list[str]) -> None:
    assert len(the_list.__members__) == len(texts)
    assert len(set(texts)) == len(texts)


@EVERY_VALUE
def test_a_text_is_words_in_small_letters_with_one_space_between_two(value: StrEnum) -> None:
    assert re.fullmatch(r"[a-z]+( [a-z]+)*", value.value)


@EVERY_VALUE
def test_a_value_has_the_name_its_text_spells(value: StrEnum) -> None:
    # Where the code says Confidence.HIGH, the store holds "high" and not
    # another text of the list.
    assert value.name == value.value.upper().replace(" ", "_")


def test_no_text_is_on_both_lists() -> None:
    # A text read from a row says by itself which of the two it speaks of.
    levels = {value.value for value in Confidence}
    statuses = {value.value for value in VerificationStatus}

    assert levels & statuses == set()


@EACH
def test_a_column_can_be_of_the_list_and_its_check_names_the_texts(
    the_list: type[StrEnum], texts: list[str]
) -> None:
    check = OneOf(the_list).check_for("trusted")
    written = check.sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )

    assert check.name == "trusted_one_of"
    assert str(written) == "trusted IN (" + ", ".join(f"'{text}'" for text in texts) + ")"
