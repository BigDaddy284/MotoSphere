"""Tests of what the loading of the countries says of the release, without a store."""

import dataclasses
from datetime import date
from importlib import resources

import pytest

from motosphere.db.texts import WHITE_SPACE
from motosphere.reference.countries import ORIGIN_FOLDER
from motosphere.reference.countries_load import ADDRESS, PUBLISHED_ON, RELEASE, CountriesLoaded

# Where the note beside the file says the release was fetched from.
FETCHED_FROM = "https://archive.ubuntu.com/ubuntu/pool/main/i/iso-codes/"


def _the_note() -> str:
    folder = resources.files("motosphere.reference").joinpath(ORIGIN_FOLDER)
    return folder.joinpath("README.md").read_bytes().decode("utf-8")


def test_the_release_is_named_by_its_number() -> None:
    assert RELEASE == "4.20.1"


def test_the_release_was_published_on_the_first_day_of_2026() -> None:
    assert date(2026, 1, 1) == PUBLISHED_ON
    # A day and no time: the store keeps it as a day.
    assert type(PUBLISHED_ON) is date


def test_the_address_is_the_file_of_the_release_where_it_was_fetched() -> None:
    assert ADDRESS == (
        "https://archive.ubuntu.com/ubuntu/pool/main/i/iso-codes/iso-codes_4.20.1.orig.tar.xz"
    )
    assert f"{FETCHED_FROM}iso-codes_{RELEASE}.orig.tar.xz" == ADDRESS


def test_the_address_is_one_web_address_without_white_space() -> None:
    assert ADDRESS.startswith("https://")
    assert not any(chr(number) in ADDRESS for number in WHITE_SPACE)


def test_the_note_beside_the_file_names_the_same_release_and_day() -> None:
    assert f"the file of release **{RELEASE}** of\n{PUBLISHED_ON.isoformat()}." in _the_note()


def test_the_note_beside_the_file_names_the_same_file_and_where_it_was_fetched() -> None:
    written = _the_note()

    assert f"`iso-codes_{RELEASE}.orig.tar.xz`" in written
    assert f"(<{FETCHED_FROM}>)" in written


def test_what_a_loading_found_is_said_in_four_lists_in_this_order() -> None:
    assert [field.name for field in dataclasses.fields(CountriesLoaded)] == [
        "added",
        "as_they_were",
        "said_otherwise",
        "not_in_the_file",
    ]


def test_what_a_loading_found_cannot_be_changed_afterwards() -> None:
    found = CountriesLoaded(added=("NZ",), as_they_were=(), said_otherwise=(), not_in_the_file=())

    def put(field: str) -> None:
        setattr(found, field, ())

    with pytest.raises(dataclasses.FrozenInstanceError):
        put("added")
    assert found.added == ("NZ",)
