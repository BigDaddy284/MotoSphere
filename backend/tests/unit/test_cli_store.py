"""Tests of what a person is told to do about a store that is not ready."""

from motosphere.cli.app import PROGRAM
from motosphere.cli.store import MIGRATE_FIRST


def test_the_advice_names_the_command_as_a_person_types_it() -> None:
    advice = MIGRATE_FIRST

    assert advice == f"Run `{PROGRAM} migrate` first."
