"""The countries of ISO 3166-1, read from the reference file of the project.

The file is ``iso_3166-1.json`` of the project iso-codes, unchanged, in
the folder ``iso-codes`` beside this module. ``README.md`` in that folder
says which release it is from and under which licence it is passed on.

:func:`read_countries` reads the content of such a file and gives its
countries, each with its two codes and its name. It reads what MotoSphere
keeps of a country and nothing else: whatever more an entry holds is left
unread. A file that is damaged is refused whole, with a sentence that
says what is wrong: no country is given of a file that is not right
throughout. The content is data from outside the project and is treated
as such. Nothing of it is run.
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from importlib import resources

from motosphere.db.texts import WHITE_SPACE

__all__ = [
    "COUNTRIES_FILE",
    "LIST_NAME",
    "ORIGIN_FOLDER",
    "CountriesFileError",
    "ReferenceCountry",
    "countries_of_the_project",
    "read_countries",
]

# The folder beside this module that holds what was taken from iso-codes.
ORIGIN_FOLDER = "iso-codes"
# The file of the countries in it, under the name its source gives it.
COUNTRIES_FILE = "iso_3166-1.json"
# The name the file gives its one list.
LIST_NAME = "3166-1"

_TWO_CAPITALS = re.compile("[A-Z]{2}")
_THREE_CAPITALS = re.compile("[A-Z]{3}")
_WHITE_SPACE = "".join(chr(number) for number in WHITE_SPACE)


class CountriesFileError(ValueError):
    """The content is not a countries file the reader can go by."""


@dataclass(frozen=True, slots=True)
class ReferenceCountry:
    """One country as the reference file has it."""

    # Its code of two letters, as "NZ".
    alpha_2: str
    # Its code of three letters, as "NZL".
    alpha_3: str
    # What the file calls it in English, as the file writes it.
    name: str


def countries_of_the_project() -> tuple[ReferenceCountry, ...]:
    """Give the countries of the reference file that comes with the project."""
    file = resources.files(__package__).joinpath(ORIGIN_FOLDER, COUNTRIES_FILE)
    return read_countries(file.read_bytes())


def read_countries(content: bytes) -> tuple[ReferenceCountry, ...]:
    """Give the countries of a countries file, in the order the file has them.

    ``content`` is the file as it is on the disk. The file is JSON in
    UTF-8: one list, under the name ``3166-1``, of entries that each have
    text under ``alpha_2``, ``alpha_3`` and ``name``. A
    :class:`CountriesFileError` says what is wrong when the content is
    anything else, when a code is not in capitals of the right number,
    when a name is empty or holds what no name holds, and when two
    entries have one code.
    """
    entries = _entries(_parsed(content))
    countries = tuple(_country(number, entry) for number, entry in enumerate(entries, start=1))
    _refuse_a_code_twice(countries)
    return countries


def _parsed(content: bytes) -> object:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise CountriesFileError("The countries file is not text in UTF-8.") from None
    try:
        return json.loads(text, object_pairs_hook=_names_once, parse_constant=_no_such_value)
    except CountriesFileError:
        raise
    except ValueError as error:
        raise CountriesFileError(f"The countries file cannot be read as JSON: {error}.") from None
    except RecursionError:
        raise CountriesFileError("The countries file is nested too deeply to be read.") from None


def _names_once(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Give what JSON calls an object, and refuse one that has a name twice."""
    found: dict[str, object] = {}
    for name, value in pairs:
        if name in found:
            raise CountriesFileError(f'The countries file has "{name}" twice in one place.')
        found[name] = value
    return found


def _no_such_value(word: str) -> object:
    """Refuse the three words Python reads as numbers and JSON does not have."""
    raise CountriesFileError(f"The countries file has {word}, which JSON does not have.")


def _entries(parsed: object) -> list[object]:
    if not isinstance(parsed, dict) or list(parsed) != [LIST_NAME]:
        raise CountriesFileError(
            f'The countries file is not one list under the name "{LIST_NAME}" and nothing else.'
        )
    entries = parsed[LIST_NAME]
    if not isinstance(entries, list):
        raise CountriesFileError(f'The countries file has no list under the name "{LIST_NAME}".')
    if not entries:
        raise CountriesFileError("The countries file has no countries.")
    return entries


def _country(number: int, entry: object) -> ReferenceCountry:
    if not isinstance(entry, dict):
        raise CountriesFileError(f"Entry {number} of the countries file is not a country.")
    alpha_2 = _text(number, entry, "alpha_2")
    alpha_3 = _text(number, entry, "alpha_3")
    name = _text(number, entry, "name")
    if _TWO_CAPITALS.fullmatch(alpha_2) is None:
        raise CountriesFileError(
            f"Entry {number} of the countries file has {alpha_2!r} "
            "where a code of two capital letters belongs."
        )
    if _THREE_CAPITALS.fullmatch(alpha_3) is None:
        raise CountriesFileError(
            f"Entry {number} of the countries file ({alpha_2}) has {alpha_3!r} "
            "where a code of three capital letters belongs."
        )
    wrong = _wrong_with(name)
    if wrong is not None:
        raise CountriesFileError(
            f"Entry {number} of the countries file ({alpha_2}) has a name that {wrong}."
        )
    return ReferenceCountry(alpha_2=alpha_2, alpha_3=alpha_3, name=name)


def _text(number: int, entry: dict[object, object], name: str) -> str:
    value = entry.get(name)
    if not isinstance(value, str):
        raise CountriesFileError(
            f'Entry {number} of the countries file has no text under "{name}".'
        )
    return value


def _wrong_with(name: str) -> str | None:
    """Say what a name has that no name of a country has, or give nothing."""
    if name.strip(_WHITE_SPACE) == "":
        return "is empty"
    if name != name.strip(_WHITE_SPACE):
        return "begins or ends with white space"
    for character in name:
        if character != " " and character in _WHITE_SPACE:
            return "holds white space that is not a plain space"
        if unicodedata.category(character) == "Cc":
            return "holds a control character"
    return None


def _refuse_a_code_twice(countries: tuple[ReferenceCountry, ...]) -> None:
    for what in ("alpha_2", "alpha_3"):
        first: dict[str, int] = {}
        for number, country in enumerate(countries, start=1):
            code: str = getattr(country, what)
            if code in first:
                raise CountriesFileError(
                    f"Entries {first[code]} and {number} of the countries file "
                    f"have one code, {code}."
                )
            first[code] = number
