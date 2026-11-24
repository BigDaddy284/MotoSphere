"""Tests of the list of how a source can be doing. They need no store."""

import re

import pytest

from motosphere.db.source_health import SourceHealth

# The texts, written out: a text changed by mistake fails here.
HEALTH = ["not yet scanned", "healthy", "failing", "interrupted"]


def test_the_list_has_exactly_its_four_texts_in_their_order() -> None:
    assert len(HEALTH) == 4
    assert [health.value for health in SourceHealth] == HEALTH


def test_no_text_of_the_list_has_two_names() -> None:
    assert len(SourceHealth.__members__) == len(HEALTH)
    assert len(set(HEALTH)) == len(HEALTH)


@pytest.mark.parametrize("health", list(SourceHealth), ids=lambda health: health)
def test_a_text_is_words_in_small_letters_with_one_space_between_two(health: SourceHealth) -> None:
    assert re.fullmatch(r"[a-z]+( [a-z]+)*", health.value)
