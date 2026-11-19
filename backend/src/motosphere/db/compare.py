"""Comparing two stores: the schema the models describe and the one the migrations build.

The models say what the store's tables are, and the migrations build them
in every store there is. :func:`differences` says in plain words where the
two differ, so that a test can hold them together: a model cannot change
without a migration, nor a migration without its model.

It compares the statements by which SQLite itself says each table and
index is made, which SQLite keeps in the file. Two statements are the same
when they are the same words in the same order. How the words are spaced,
whether they are written large or small, quotes around a name and comments
make no difference; text in single quotes is compared letter for letter.
"""

import re
from itertools import zip_longest

from sqlalchemy import Engine

__all__ = ["differences"]

# The parts of a statement: white space and comments, which are left out;
# text in single quotes; a name in quotes of one of three kinds; a word;
# and any other sign, one at a time, but the signs of a comparison together.
_PART = re.compile(
    r"""
      (?P<nothing> \s+ | --[^\n]* | /\*.*?\*/ )
    | (?P<text> '(?:[^']|'')*' )
    | (?P<name> "(?:[^"]|"")*" | `(?:[^`]|``)*` | \[[^\]]*\] )
    | (?P<word> \w+ )
    | (?P<sign> [<>=!]+ | . )
    """,
    re.DOTALL | re.VERBOSE,
)
# How many words are shown after the first one that differs.
_SHOWN_AFTER = 5


def _statements(store: Engine) -> dict[tuple[str, str], str]:
    """Give the statement that makes each thing in the store, by its kind and name.

    The tables SQLite keeps for itself are left out: their names begin
    with ``sqlite_``, which no other name may.
    """
    with store.connect() as connection:
        held = connection.exec_driver_sql(
            "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite~_%' ESCAPE '~'"
        ).all()
    return {(str(kind), str(name)): str(statement) for kind, name, statement in held}


def _words(statement: str) -> list[str]:
    """Give the words of a statement, in the one form in which they are compared."""
    words: list[str] = []
    for part in _PART.finditer(statement):
        found = part.group()
        if part.lastgroup == "name":
            words.append(found[1:-1].lower())
        elif part.lastgroup == "word":
            words.append(found.lower())
        elif part.lastgroup != "nothing":
            words.append(found)
    return words


def _from_where_they_differ(one: list[str], other: list[str]) -> tuple[str, str]:
    """Give the words of two statements that differ, around the first place where they do.

    The words begin after the last comma or opening bracket before that
    place, which is where the column or constraint begins that differs.
    Where one statement ends before the other, that place is its end.
    """
    first = next(place for place, (a, b) in enumerate(zip_longest(one, other)) if a != b)
    begins = max((place + 1 for place in range(first) if one[place] in {",", "("}), default=0)

    def shown(words: list[str]) -> str:
        more = " ..." if len(words) > first + _SHOWN_AFTER + 1 else ""
        return " ".join(words[begins : first + _SHOWN_AFTER + 1]) + more

    return shown(one), shown(other)


def differences(*, models: Engine, migrated: Engine) -> list[str]:
    """Say where the schemas of two stores differ, one plain sentence for each thing.

    ``models`` is a store whose tables were made from the models, and
    ``migrated`` one that the migrations built. The sentences come kind by
    kind (indexes, tables, triggers, views) and name by name. Stores with
    the same schema give an empty list. Nothing is written to either.
    """
    said = _statements(models)
    built = _statements(migrated)
    found: list[str] = []
    for kind, name in sorted(said.keys() | built.keys()):
        if (kind, name) not in built:
            found.append(f"Only the models have the {kind} {name}.")
        elif (kind, name) not in said:
            found.append(f"Only the migrations have the {kind} {name}.")
        else:
            one, other = _words(said[kind, name]), _words(built[kind, name])
            if one != other:
                here, there = _from_where_they_differ(one, other)
                found.append(
                    f"The {kind} {name} is not the same in both. Where they first differ, "
                    f"the models say `{here}` and the migrations say `{there}`."
                )
    return found
