"""Tests of the list of how a collection run stands or ended. They need no store."""

import re

import pytest
from sqlalchemy.dialects import sqlite

from motosphere.db.lists import OneOf
from motosphere.db.models.collection_run import RunOutcome

# The texts that are stored, written out: a text changed by mistake fails here.
OUTCOMES = ["running", "succeeded", "failed", "interrupted"]


def test_the_list_has_exactly_the_four_outcomes_in_their_order() -> None:
    assert len(OUTCOMES) == 4
    assert [outcome.value for outcome in RunOutcome] == OUTCOMES


def test_no_outcome_has_two_names() -> None:
    assert len(RunOutcome.__members__) == len(OUTCOMES)
    assert len(set(OUTCOMES)) == len(OUTCOMES)


@pytest.mark.parametrize("outcome", list(RunOutcome), ids=lambda outcome: outcome)
def test_an_outcome_is_one_word_in_small_letters(outcome: RunOutcome) -> None:
    assert re.fullmatch(r"[a-z]+", outcome.value)


def test_a_column_can_be_of_the_list_and_its_check_names_the_outcomes() -> None:
    check = OneOf(RunOutcome).check_for("outcome")
    written = check.sqltext.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )

    assert check.name == "outcome_one_of"
    assert str(written) == "outcome IN ('running', 'succeeded', 'failed', 'interrupted')"
