"""Tests for the countries file of the project and for its reader."""

import dataclasses
import hashlib
import json
import re
from importlib import resources
from typing import Any

import pytest

from motosphere.db.texts import WHITE_SPACE
from motosphere.reference.countries import (
    COUNTRIES_FILE,
    LIST_NAME,
    ORIGIN_FOLDER,
    CountriesFileError,
    ReferenceCountry,
    countries_of_the_project,
    read_countries,
)

# The two files as release 4.20.1 of iso-codes has them: who changes one
# of them in the project changes it here, and says so beside the file.
COUNTRIES_SHA256 = "f01b812b57fba9f31ff621bf33e7c7570a01964dbeb5be2167e94decf538c89f"
LICENCE_SHA256 = "5749785c8bdefafcb5d798270ed0a967036fe2ca63dcedade1627565dfef81d2"
LICENCE_FILE = "LGPL-2.1-or-later.txt"

NEW_ZEALAND = {"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand"}
FIJI = {"alpha_2": "FJ", "alpha_3": "FJI", "name": "Fiji"}


def _taken(file: str) -> bytes:
    """Give a file of the folder that holds what was taken from iso-codes."""
    return resources.files("motosphere.reference").joinpath(ORIGIN_FOLDER, file).read_bytes()


def _file(*entries: Any) -> bytes:
    """Give a countries file with these entries, as it would be on the disk."""
    return json.dumps({LIST_NAME: list(entries)}, ensure_ascii=False).encode("utf-8")


def _with(**changes: Any) -> dict[str, Any]:
    """Give the entry of New Zealand, with these values in place of its own."""
    return {**NEW_ZEALAND, **changes}


def _without(name: str) -> dict[str, Any]:
    """Give the entry of New Zealand without one of its values."""
    return {key: value for key, value in NEW_ZEALAND.items() if key != name}


def _refused(content: bytes) -> str:
    """Give the sentence with which the reader refuses this content."""
    with pytest.raises(CountriesFileError) as refusal:
        read_countries(content)
    return str(refusal.value)


# ---------------------------------------------------------------- the file


def test_the_names_of_the_folder_the_file_and_the_list() -> None:
    assert ORIGIN_FOLDER == "iso-codes"
    assert COUNTRIES_FILE == "iso_3166-1.json"
    assert LIST_NAME == "3166-1"


def test_the_countries_file_is_the_one_of_the_release_byte_for_byte() -> None:
    assert hashlib.sha256(_taken(COUNTRIES_FILE)).hexdigest() == COUNTRIES_SHA256


def test_the_licence_beside_it_is_the_one_of_the_release_byte_for_byte() -> None:
    assert hashlib.sha256(_taken(LICENCE_FILE)).hexdigest() == LICENCE_SHA256


def test_neither_file_has_a_line_ending_a_checkout_could_change() -> None:
    assert b"\r" not in _taken(COUNTRIES_FILE)
    assert b"\r" not in _taken(LICENCE_FILE)


def test_what_is_written_beside_the_files_names_each_as_it_is() -> None:
    written = _taken("README.md").decode("utf-8")

    assert f"| `{COUNTRIES_FILE}` | `data/{COUNTRIES_FILE}` | `{COUNTRIES_SHA256}` |" in written
    assert f"| `{LICENCE_FILE}` | `LICENSES/{LICENCE_FILE}` | `{LICENCE_SHA256}` |" in written
    assert "the file of release **4.20.1** of\n2026-01-01." in written
    assert "Both are\n**unchanged**" in written
    # The notice of copyright and the licence, as the release states them.
    assert 'SPDX-FileCopyrightText = "2016 Dr. Tobias Quathamer <toddy@debian.org>"' in written
    assert 'SPDX-License-Identifier = "LGPL-2.1-or-later"' in written


def test_the_folder_holds_those_three_files_and_no_other() -> None:
    folder = resources.files("motosphere.reference").joinpath(ORIGIN_FOLDER)

    assert sorted(entry.name for entry in folder.iterdir()) == [
        LICENCE_FILE,
        "README.md",
        COUNTRIES_FILE,
    ]


# ------------------------------------------------- the countries of the file


def test_the_file_of_the_project_has_249_countries() -> None:
    assert len(countries_of_the_project()) == 249


def test_they_are_read_from_the_file_of_the_project() -> None:
    assert countries_of_the_project() == read_countries(_taken(COUNTRIES_FILE))


def test_they_are_in_the_order_of_the_file() -> None:
    countries = countries_of_the_project()

    assert countries[0] == ReferenceCountry("AW", "ABW", "Aruba")
    assert countries[1] == ReferenceCountry("AF", "AFG", "Afghanistan")
    assert countries[-1] == ReferenceCountry("ZW", "ZWE", "Zimbabwe")


@pytest.mark.parametrize(
    "country",
    [
        ReferenceCountry("NZ", "NZL", "New Zealand"),
        ReferenceCountry("GB", "GBR", "United Kingdom"),
        ReferenceCountry("US", "USA", "United States"),
        ReferenceCountry("TR", "TUR", "T\u00fcrkiye"),
        ReferenceCountry("CI", "CIV", "C\u00f4te d'Ivoire"),
        ReferenceCountry("AX", "ALA", "\u00c5land Islands"),
        ReferenceCountry("KR", "KOR", "Korea, Republic of"),
        ReferenceCountry("SH", "SHN", "Saint Helena, Ascension and Tristan da Cunha"),
    ],
    ids=lambda country: country.alpha_2,
)
def test_a_country_is_given_as_the_file_writes_it(country: ReferenceCountry) -> None:
    assert country in countries_of_the_project()


def test_no_two_have_one_code() -> None:
    countries = countries_of_the_project()

    assert len({country.alpha_2 for country in countries}) == 249
    assert len({country.alpha_3 for country in countries}) == 249


def test_every_code_is_in_capitals_of_the_26_letters() -> None:
    for country in countries_of_the_project():
        assert re.fullmatch("[A-Z][A-Z]", country.alpha_2, re.ASCII), country
        assert re.fullmatch("[A-Z][A-Z][A-Z]", country.alpha_3, re.ASCII), country


def test_every_name_is_text_without_white_space_around_it() -> None:
    white_space = "".join(chr(number) for number in WHITE_SPACE)

    for country in countries_of_the_project():
        assert country.name != ""
        assert country.name == country.name.strip(white_space), country


def test_the_file_is_read_anew_each_time_and_gives_the_same() -> None:
    assert countries_of_the_project() == countries_of_the_project()


# ------------------------------------------------------------- what is read


def test_a_file_with_one_country_gives_that_country() -> None:
    assert read_countries(_file(NEW_ZEALAND)) == (ReferenceCountry("NZ", "NZL", "New Zealand"),)


def test_the_countries_are_given_in_the_order_of_the_file() -> None:
    assert read_countries(_file(NEW_ZEALAND, FIJI)) == (
        ReferenceCountry("NZ", "NZL", "New Zealand"),
        ReferenceCountry("FJ", "FJI", "Fiji"),
    )
    assert read_countries(_file(FIJI, NEW_ZEALAND)) == (
        ReferenceCountry("FJ", "FJI", "Fiji"),
        ReferenceCountry("NZ", "NZL", "New Zealand"),
    )


def test_what_more_an_entry_holds_is_left_unread() -> None:
    entry = _with(numeric=554, flag=None, official_name=["x"], something_new={"a": 1})

    assert read_countries(_file(entry)) == (ReferenceCountry("NZ", "NZL", "New Zealand"),)


def test_a_name_is_given_as_it_is_written() -> None:
    names = [
        "T\u00fcrkiye",
        "C\u00f4te d'Ivoire",
        "Korea, Republic of",
        "Virgin Islands, U.S.",
        "\u65e5\u672c",
    ]
    entries = [
        {"alpha_2": f"A{letter}", "alpha_3": f"AA{letter}", "name": name}
        for letter, name in zip("ABCDE", names, strict=True)
    ]

    assert [country.name for country in read_countries(_file(*entries))] == names


def test_two_countries_can_have_one_name() -> None:
    countries = read_countries(_file(NEW_ZEALAND, {**FIJI, "name": "New Zealand"}))

    assert [country.name for country in countries] == ["New Zealand", "New Zealand"]


def test_a_file_that_writes_its_letters_as_numbers_is_read_the_same() -> None:
    plain = json.dumps({LIST_NAME: [_with(name="T\u00fcrkiye")]}, ensure_ascii=True).encode("ascii")

    assert b"T\\u00fcrkiye" in plain
    assert read_countries(plain) == (ReferenceCountry("NZ", "NZL", "T\u00fcrkiye"),)


def test_a_country_cannot_be_changed_once_it_is_read() -> None:
    country = read_countries(_file(NEW_ZEALAND))[0]

    for name in ("alpha_2", "alpha_3", "name"):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(country, name, "Elsewhere")
    assert country == ReferenceCountry("NZ", "NZL", "New Zealand")


# ---------------------------------------------------------- what is refused


def test_content_that_is_not_utf_8_is_refused() -> None:
    assert _refused("T\u00fcrkiye".encode("latin-1")) == "The countries file is not text in UTF-8."
    assert _refused(_file(NEW_ZEALAND).decode("utf-8").encode("utf-16")) == (
        "The countries file is not text in UTF-8."
    )


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"   ",
        b"{",
        b'{"3166-1": [',
        b'{"3166-1": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand"},]}',
        b"{'3166-1': []}",
        b'{"3166-1": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand"}]} more',
        b'\xef\xbb\xbf{"3166-1": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand"}]}',
        b'{"3166-1": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New\nZealand"}]}',
        b'{"3166-1": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand", "numeric": '
        + b"9" * 5000
        + b"}]}",
    ],
    ids=[
        "nothing",
        "white space",
        "cut off at once",
        "cut off in the list",
        "a comma too many",
        "the wrong quotation marks",
        "something after the end",
        "a mark of byte order before the beginning",
        "a line break inside a text",
        "a number too long to be read",
    ],
)
def test_content_that_cannot_be_read_as_json_is_refused(content: bytes) -> None:
    assert _refused(content).startswith("The countries file cannot be read as JSON: ")


@pytest.mark.parametrize("word", ["NaN", "Infinity", "-Infinity"])
def test_a_word_python_reads_as_a_number_and_json_does_not_have_is_refused(word: str) -> None:
    content = b'{"3166-1": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand", "numeric": '
    content += word.encode("ascii") + b"}]}"

    assert _refused(content) == f"The countries file has {word}, which JSON does not have."


def test_content_nested_too_deeply_to_be_read_is_refused() -> None:
    content = b'{"3166-1": ' + b"[" * 100_000 + b"]" * 100_000 + b"}"

    assert _refused(content) == "The countries file is nested too deeply to be read."


@pytest.mark.parametrize(
    ("content", "name"),
    [
        (b'{"3166-1": [], "3166-1": []}', "3166-1"),
        (
            b'{"3166-1": [{"alpha_2": "NZ", "alpha_2": "FJ", "alpha_3": "NZL", '
            b'"name": "New Zealand"}]}',
            "alpha_2",
        ),
        (
            b'{"3166-1": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand", '
            b'"name": "New Zealand"}]}',
            "name",
        ),
        (
            b'{"3166-1": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand", '
            b'"more": {"a": 1, "a": 1}}]}',
            "a",
        ),
    ],
    ids=["the list", "a code", "the same name again", "in what is left unread"],
)
def test_a_name_twice_in_one_place_is_refused(content: bytes, name: str) -> None:
    assert _refused(content) == f'The countries file has "{name}" twice in one place.'


@pytest.mark.parametrize(
    "content",
    [
        b"[]",
        b'[{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand"}]',
        b"null",
        b'"3166-1"',
        b"3166",
        b"{}",
        b'{"3166-2": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand"}]}',
        b'{"3166-1": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand"}], "more": 1}',
        b'{"more": 1, "3166-1": [{"alpha_2": "NZ", "alpha_3": "NZL", "name": "New Zealand"}]}',
    ],
    ids=[
        "an empty list",
        "the list by itself",
        "no value",
        "a text",
        "a number",
        "no list at all",
        "a list of another name",
        "something after the list",
        "something before the list",
    ],
)
def test_content_that_is_not_the_one_list_is_refused(content: bytes) -> None:
    assert _refused(content) == (
        'The countries file is not one list under the name "3166-1" and nothing else.'
    )


@pytest.mark.parametrize(
    "content",
    [b'{"3166-1": {}}', b'{"3166-1": null}', b'{"3166-1": "NZ"}', b'{"3166-1": 249}'],
    ids=["names and values", "no value", "a text", "a number"],
)
def test_something_else_than_a_list_under_the_name_is_refused(content: bytes) -> None:
    assert _refused(content) == 'The countries file has no list under the name "3166-1".'


def test_a_list_without_countries_is_refused() -> None:
    assert _refused(_file()) == "The countries file has no countries."


@pytest.mark.parametrize(
    "entry",
    [None, "NZ", 554, ["NZ", "NZL", "New Zealand"], True],
    ids=["no value", "a text", "a number", "a list", "yes"],
)
def test_an_entry_that_is_not_names_and_values_is_refused(entry: Any) -> None:
    assert _refused(_file(NEW_ZEALAND, entry)) == (
        "Entry 2 of the countries file is not a country."
    )


@pytest.mark.parametrize("name", ["alpha_2", "alpha_3", "name"])
def test_an_entry_without_one_of_the_three_is_refused(name: str) -> None:
    assert _refused(_file(FIJI, NEW_ZEALAND, _without(name))) == (
        f'Entry 3 of the countries file has no text under "{name}".'
    )


@pytest.mark.parametrize("name", ["alpha_2", "alpha_3", "name"])
@pytest.mark.parametrize(
    "value",
    [None, 12, 1.5, True, ["NZ"], {"en": "NZ"}],
    ids=["no value", "a number", "a fraction", "yes", "a list", "names and values"],
)
def test_one_of_the_three_that_is_not_text_is_refused(name: str, value: Any) -> None:
    assert _refused(_file(_with(**{name: value}))) == (
        f'Entry 1 of the countries file has no text under "{name}".'
    )


@pytest.mark.parametrize(
    "code",
    [
        "",
        "N",
        "NZL",
        "nz",
        "Nz",
        "N1",
        "N Z",
        "NZ ",
        " NZ",
        "NZ\n",
        "\u00c5L",
        "\u039d\u0396",
        "\uff2e\uff3a",
        "N\x00",
    ],
    ids=[
        "empty",
        "one letter",
        "three letters",
        "small letters",
        "one small letter",
        "a figure",
        "a space between",
        "a space after",
        "a space before",
        "a line break after",
        "a letter with a ring",
        "Greek letters that look the same",
        "wide letters",
        "a nought character",
    ],
)
def test_a_code_of_two_letters_in_another_form_is_refused(code: str) -> None:
    assert _refused(_file(FIJI, _with(alpha_2=code))) == (
        f"Entry 2 of the countries file has {code!r} where a code of two capital letters belongs."
    )


@pytest.mark.parametrize(
    "code",
    [
        "",
        "NZ",
        "NZLD",
        "nzl",
        "NzL",
        "NZ1",
        "N ZL",
        "NZL ",
        " NZL",
        "NZL\n",
        "\u00c5LA",
        "\u039d\u0396L",
        "NZ\x00",
    ],
    ids=[
        "empty",
        "two letters",
        "four letters",
        "small letters",
        "one small letter",
        "a figure",
        "a space between",
        "a space after",
        "a space before",
        "a line break after",
        "a letter with a ring",
        "Greek letters that look the same",
        "a nought character",
    ],
)
def test_a_code_of_three_letters_in_another_form_is_refused(code: str) -> None:
    assert _refused(_file(FIJI, _with(alpha_3=code))) == (
        f"Entry 2 of the countries file (NZ) has {code!r} "
        "where a code of three capital letters belongs."
    )


@pytest.mark.parametrize(
    "name",
    ["", " ", "   ", "\t", "\n", "\u00a0", "\u3000", " \u00a0\t "],
    ids=[
        "no characters",
        "a space",
        "spaces",
        "a tab",
        "a line break",
        "a space that cannot be broken",
        "a wide space",
        "white space of several kinds",
    ],
)
def test_an_empty_name_is_refused(name: str) -> None:
    assert _refused(_file(_with(name=name))) == (
        "Entry 1 of the countries file (NZ) has a name that is empty."
    )


@pytest.mark.parametrize(
    "name",
    [" New Zealand", "New Zealand ", "New Zealand\n", "\tNew Zealand", "New Zealand\u00a0"],
    ids=[
        "a space before",
        "a space after",
        "a line break after",
        "a tab before",
        "a space that cannot be broken after",
    ],
)
def test_a_name_with_white_space_around_it_is_refused(name: str) -> None:
    assert _refused(_file(_with(name=name))) == (
        "Entry 1 of the countries file (NZ) has a name that begins or ends with white space."
    )


@pytest.mark.parametrize(
    "name",
    ["New\tZealand", "New\nZealand", "New\r\nZealand", "New\u00a0Zealand", "New\u2028Zealand"],
    ids=[
        "a tab",
        "a line break",
        "a line break of Windows",
        "a space that cannot be broken",
        "a line separator",
    ],
)
def test_a_name_with_white_space_inside_that_is_no_plain_space_is_refused(name: str) -> None:
    assert _refused(_file(_with(name=name))) == (
        "Entry 1 of the countries file (NZ) has a name "
        "that holds white space that is not a plain space."
    )


@pytest.mark.parametrize(
    "name",
    ["New\x00Zealand", "New Zealand\x00", "\x1bNew Zealand", "New\x7fZealand", "New\u009bZealand"],
    ids=["a nought character", "one at the end", "escape", "delete", "one of the second set"],
)
def test_a_name_with_a_control_character_is_refused(name: str) -> None:
    assert _refused(_file(_with(name=name))) == (
        "Entry 1 of the countries file (NZ) has a name that holds a control character."
    )


def test_a_code_of_two_letters_twice_is_refused() -> None:
    again = {"alpha_2": "NZ", "alpha_3": "NZZ", "name": "Elsewhere"}

    assert _refused(_file(NEW_ZEALAND, FIJI, again)) == (
        "Entries 1 and 3 of the countries file have one code, NZ."
    )


def test_a_code_of_three_letters_twice_is_refused() -> None:
    again = {"alpha_2": "ZN", "alpha_3": "FJI", "name": "Elsewhere"}

    assert _refused(_file(NEW_ZEALAND, FIJI, again)) == (
        "Entries 2 and 3 of the countries file have one code, FJI."
    )


def test_an_entry_twice_is_refused() -> None:
    assert _refused(_file(NEW_ZEALAND, NEW_ZEALAND)) == (
        "Entries 1 and 2 of the countries file have one code, NZ."
    )


def test_a_file_with_one_wrong_entry_gives_no_country_at_all() -> None:
    good = [
        {"alpha_2": f"A{letter}", "alpha_3": f"AA{letter}", "name": f"Country {letter}"}
        for letter in "ABCDEFGH"
    ]

    assert len(read_countries(_file(*good))) == 8
    for place in range(9):
        entries = [*good[:place], _with(alpha_3="nzl"), *good[place:]]
        with pytest.raises(CountriesFileError, match=f"^Entry {place + 1} of the countries file"):
            read_countries(_file(*entries))


def test_the_file_of_the_project_with_one_entry_damaged_is_refused() -> None:
    whole = json.loads(_taken(COUNTRIES_FILE))
    whole[LIST_NAME][100]["alpha_2"] = whole[LIST_NAME][7]["alpha_2"]
    damaged = json.dumps(whole, ensure_ascii=False).encode("utf-8")

    assert _refused(damaged).startswith("Entries 8 and 101 of the countries file have one code, ")


def test_the_refusal_is_an_error_of_its_own_kind_and_a_value_error() -> None:
    assert issubclass(CountriesFileError, ValueError)
    assert CountriesFileError is not ValueError
