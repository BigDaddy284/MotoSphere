"""Tests of the rules every table keeps, without a store.

The tables here are made for the tests, each in a schema of its own, so
the real schema never sees them. ``tests/integration/test_base.py`` makes
tables in a real SQLite file.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    column,
    func,
    text,
)
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import SchemaItem

from motosphere.db import times
from motosphere.db.base import NAMING, Base, broken_rules
from motosphere.db.checks import WithItsCheck
from motosphere.db.texts import WHITE_SPACE, NotEmptyText, not_empty
from motosphere.db.times import UtcDateTime

# What a table made by hand must say of itself to keep the rules. The
# tables of models get both from ``Base``, and the key and the two times
# with them.
KEPT: dict[str, Any] = {"sqlite_strict": True, "sqlite_autoincrement": True}
A_MOMENT = datetime(2026, 11, 19, 8, 0, tzinfo=UTC)
NO_KEY = (
    "The table {} does not have the key every table has: one whole-number column "
    "named id, whose values are never given twice."
)
NO_TIMES = (
    "The table {} does not have the times every table has: created_at and updated_at, "
    "which the store's code sets when a row is first stored and whenever it is changed."
)
NO_CHECK = (
    "The table {} does not refuse empty text in its column {}: it must have the check "
    "that not_empty gives for the column, named by the naming rule."
)
# The check of a column named name, as not_empty writes it.
ITS_CHECK = (
    "trim(name, char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, "
    "8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)) != ''"
)


# The sentence for a name that more than one constraint or index of a table has.
TWICE = (
    "The table {} gives the name {} to {} of its constraints and indexes: "
    "each must have a name of its own."
)

# The sentence for a column of the tests' own type, ShoutedText.
NOT_SHOUTED = (
    "The table {} does not refuse small letters in its column {}: it must have the check "
    "that shouted gives for the column, named by the naming rule."
)


class ShoutedText(WithItsCheck, Text):
    """A column type of the tests' own that brings a check: text in large letters only."""

    refuses = "small letters"
    given_by = "shouted"

    def check_for(self, name: str) -> CheckConstraint:
        return CheckConstraint(column(name) == func.upper(column(name)), name=f"{name}_shouted")


class PromisedText(WithItsCheck, Text):
    """A column type that says it brings a check, and gives none."""

    refuses = "anything"
    given_by = "nothing"


def a_schema() -> MetaData:
    """An empty schema with the naming rule of the real one."""
    return MetaData(naming_convention=NAMING)


def the_key() -> Column[int]:
    """The key every table has."""
    return Column("id", Integer, primary_key=True)


def a_time(name: str, **said: Any) -> Column[datetime]:
    """One of the two times, as every table has it unless ``said`` otherwise."""
    how: dict[str, Any] = {"type_": UtcDateTime, "nullable": False, "default": times.now}
    if name == "updated_at":
        how["onupdate"] = times.now
    return Column(name, **(how | said))


def the_times() -> list[Column[datetime]]:
    """The two times every table has."""
    return [a_time("created_at"), a_time("updated_at")]


def given_by_not_empty(table: Table) -> None:
    table.append_constraint(not_empty("name"))


def written_with_the_tables_column(table: Table) -> None:
    # A check written with a column of a table gives itself to that table.
    CheckConstraint(func.trim(table.c.name, func.char(*WHITE_SPACE)) != "", name="name_not_empty")


def written_as_text(table: Table) -> None:
    table.append_constraint(CheckConstraint(ITS_CHECK, name="name_not_empty"))


def test_the_real_schema_breaks_no_rule() -> None:
    assert broken_rules(Base.metadata) == []


def test_tables_that_keep_the_rules_break_none() -> None:
    schema = a_schema()
    Table("owner", schema, the_key(), Column("name", Text, unique=True), *the_times(), **KEPT)
    Table(
        "item",
        schema,
        the_key(),
        Column("owner_id", Integer, ForeignKey("owner.id")),
        Column("number", Integer),
        Column("place", Text, index=True),
        *the_times(),
        UniqueConstraint("owner_id", "number"),
        CheckConstraint("number > 0", name="number_positive"),
        Index(None, "place", "number"),
        **KEPT,
    )

    assert broken_rules(schema) == []


def test_a_table_that_is_not_strict_is_named() -> None:
    schema = a_schema()
    Table("strict_one", schema, the_key(), *the_times(), **KEPT)
    Table("loose_one", schema, the_key(), *the_times(), sqlite_autoincrement=True)

    assert broken_rules(schema) == ["The table loose_one is not strict."]


@pytest.mark.parametrize(
    ("columns", "options"),
    [
        ([Column("id", Integer)], KEPT),
        ([Column("number", Integer, primary_key=True)], KEPT),
        ([the_key(), Column("number", Integer, primary_key=True)], KEPT),
        ([Column("id", Text, primary_key=True)], KEPT),
        ([Column("id", Integer, ForeignKey("other.id"), primary_key=True)], KEPT),
        ([the_key()], {"sqlite_strict": True}),
    ],
    ids=[
        "no key",
        "a key of another name",
        "a key of two columns",
        "a key that is text",
        "a key that is the key of another table",
        "a key that may be given twice",
    ],
)
def test_a_table_without_the_key_every_table_has_is_named(
    columns: list[Column[Any]], options: dict[str, Any]
) -> None:
    schema = a_schema()
    Table("other", schema, the_key(), *the_times(), **KEPT)
    Table("odd_one", schema, *columns, *the_times(), **options)

    assert broken_rules(schema) == [NO_KEY.format("odd_one")]


@pytest.mark.parametrize(
    "columns",
    [
        [],
        [a_time("updated_at")],
        [a_time("created_at")],
        [a_time("created_at", type_=DateTime), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", type_=DateTime)],
        [a_time("created_at", nullable=True), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", nullable=True)],
        [a_time("created_at", server_default=text("CURRENT_TIMESTAMP")), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", server_default=text("CURRENT_TIMESTAMP"))],
        [a_time("created_at", default=None), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", default=None)],
        [a_time("created_at", default=A_MOMENT), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", default=A_MOMENT)],
        [a_time("created_at", default=func.now()), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", default=func.now())],
        [a_time("created_at", onupdate=times.now), a_time("updated_at")],
        [a_time("created_at"), a_time("updated_at", onupdate=None)],
        [a_time("created_at"), a_time("updated_at", onupdate=A_MOMENT)],
        [a_time("created_at"), a_time("updated_at", onupdate=func.now())],
    ],
    ids=[
        "no times",
        "no time of the first storing",
        "no time of the last change",
        "a first time of another type",
        "a last time of another type",
        "a first time that may be empty",
        "a last time that may be empty",
        "a first time the table sets itself",
        "a last time the table sets itself",
        "a first time the store's code does not set",
        "a last time the store's code does not set",
        "a first time that is one fixed moment",
        "a last time that is one fixed moment",
        "a first time that SQLite is asked for",
        "a last time that SQLite is asked for",
        "a first time that is set anew at a change",
        "a last time that is not set anew at a change",
        "a last time that a change sets to one fixed moment",
        "a last time that a change asks SQLite for",
    ],
)
def test_a_table_without_the_times_every_table_has_is_named(columns: list[Column[Any]]) -> None:
    schema = a_schema()
    Table("odd_one", schema, the_key(), *columns, **KEPT)

    assert broken_rules(schema) == [NO_TIMES.format("odd_one")]


@pytest.mark.parametrize(
    "checks",
    [
        [],
        [CheckConstraint(ITS_CHECK, name="name_filled")],
        [CheckConstraint("name != ''", name="name_not_empty")],
        [CheckConstraint("trim(name) != ''", name="name_not_empty")],
        [CheckConstraint(ITS_CHECK.replace("name", "title"), name="name_not_empty")],
    ],
    ids=[
        "no check",
        "its check under another name",
        "a check of its name that takes text of white space",
        "a check of its name that takes off spaces only",
        "a check of its name that is of another column",
    ],
)
def test_a_column_without_its_check_for_empty_text_is_named(
    checks: list[CheckConstraint],
) -> None:
    schema = a_schema()
    Table(
        "odd_one",
        schema,
        the_key(),
        Column("name", NotEmptyText),
        Column("title", NotEmptyText),
        *the_times(),
        not_empty("title"),
        *checks,
        **KEPT,
    )

    assert broken_rules(schema) == [NO_CHECK.format("odd_one", "name")]


@pytest.mark.parametrize(
    "give_the_check",
    [given_by_not_empty, written_with_the_tables_column, written_as_text],
    ids=[
        "the check not_empty gives",
        "the same check written with the table's column",
        "the same check written as text",
    ],
)
def test_a_column_is_named_until_its_table_has_the_check(
    give_the_check: Callable[[Table], None],
) -> None:
    schema = a_schema()
    kept = Table("kept", schema, the_key(), Column("name", NotEmptyText), *the_times(), **KEPT)

    assert broken_rules(schema) == [NO_CHECK.format("kept", "name")]

    give_the_check(kept)

    assert broken_rules(schema) == []


def test_columns_without_their_check_are_named_in_the_order_of_the_columns() -> None:
    schema = a_schema()
    Table(
        "odd_one",
        schema,
        the_key(),
        Column("title", NotEmptyText, nullable=False),
        Column("note", Text),
        Column("name", NotEmptyText),
        *the_times(),
        **KEPT,
    )

    assert broken_rules(schema) == [
        NO_CHECK.format("odd_one", "title"),
        NO_CHECK.format("odd_one", "name"),
    ]


def test_a_column_of_any_type_that_brings_a_check_is_named_until_its_table_has_the_check() -> None:
    schema = a_schema()
    kept = Table("kept", schema, the_key(), Column("code", ShoutedText), *the_times(), **KEPT)

    assert broken_rules(schema) == [NOT_SHOUTED.format("kept", "code")]

    kept.append_constraint(ShoutedText().check_for("code"))

    assert [
        str(check.name) for check in kept.constraints if isinstance(check, CheckConstraint)
    ] == ["ck_kept_code_shouted"]
    assert broken_rules(schema) == []


@pytest.mark.parametrize(
    ("of_the_code", "of_the_name", "found"),
    [
        (not_empty("code"), ShoutedText().check_for("name"), ["code", "name"]),
        (
            CheckConstraint(ITS_CHECK.replace("name", "code"), name="code_shouted"),
            CheckConstraint("name = upper(name)", name="name_not_empty"),
            ["code", "name"],
        ),
        (ShoutedText().check_for("code"), ShoutedText().check_for("name"), ["name"]),
        (not_empty("code"), not_empty("name"), ["code"]),
    ],
    ids=[
        "each has the check the other's type gives",
        "each has the other's check under its own check's name",
        "both have the check of the first one's type",
        "both have the check of the second one's type",
    ],
)
def test_the_check_of_one_type_does_not_count_for_a_column_of_another(
    of_the_code: CheckConstraint, of_the_name: CheckConstraint, found: list[str]
) -> None:
    schema = a_schema()
    Table(
        "odd_one",
        schema,
        the_key(),
        Column("code", ShoutedText),
        Column("name", NotEmptyText),
        *the_times(),
        of_the_code,
        of_the_name,
        **KEPT,
    )
    sentences = {"code": NOT_SHOUTED, "name": NO_CHECK}

    assert broken_rules(schema) == [sentences[name].format("odd_one", name) for name in found]


def test_columns_of_several_types_are_named_in_their_order_each_in_its_types_words() -> None:
    schema = a_schema()
    Table(
        "odd_one",
        schema,
        the_key(),
        Column("tag", ShoutedText),
        Column("name", NotEmptyText),
        Column("note", Text),
        Column("code", ShoutedText),
        *the_times(),
        **KEPT,
    )

    assert broken_rules(schema) == [
        NOT_SHOUTED.format("odd_one", "tag"),
        NO_CHECK.format("odd_one", "name"),
        NOT_SHOUTED.format("odd_one", "code"),
    ]


def test_a_type_that_says_it_brings_a_check_and_gives_none_is_an_error() -> None:
    schema = a_schema()
    Table("odd_one", schema, the_key(), Column("code", PromisedText), *the_times(), **KEPT)

    with pytest.raises(NotImplementedError):
        broken_rules(schema)

    class Proof(Base):
        __abstract__ = True
        metadata = a_schema()

    with pytest.raises(NotImplementedError):

        class ProofSign(Proof):
            __tablename__ = "proof_sign"

            code: Mapped[str] = mapped_column(PromisedText)


@pytest.mark.parametrize(
    "by_hand",
    [
        UniqueConstraint("number", name="mine"),
        ForeignKeyConstraint(["number"], ["other.id"], name="mine"),
        Index("mine", "number"),
    ],
    ids=["a unique constraint", "a foreign key", "an index"],
)
def test_a_name_given_by_hand_is_named(by_hand: SchemaItem) -> None:
    schema = a_schema()
    Table("other", schema, the_key(), *the_times(), **KEPT)
    Table("named", schema, the_key(), Column("number", Integer), *the_times(), by_hand, **KEPT)

    assert broken_rules(schema) == [
        "The table named has a name given by hand, mine: "
        "constraints and indexes are named by the naming rule."
    ]


def test_the_breaks_are_listed_table_by_table_and_rule_by_rule() -> None:
    schema = a_schema()
    Table(
        "zebra",
        schema,
        the_key(),
        Column("a", Integer),
        Column("b", Integer),
        *the_times(),
        UniqueConstraint("b", name="second"),
        UniqueConstraint("a", name="first"),
        **KEPT,
    )
    Table(
        "aardvark",
        schema,
        the_key(),
        Column("a", Integer),
        Column("name", NotEmptyText),
        UniqueConstraint("a", name="mine"),
    )

    assert broken_rules(schema) == [
        "The table aardvark is not strict.",
        NO_KEY.format("aardvark"),
        NO_TIMES.format("aardvark"),
        NO_CHECK.format("aardvark", "name"),
        "The table aardvark has a name given by hand, mine: "
        "constraints and indexes are named by the naming rule.",
        "The table zebra has a name given by hand, first: "
        "constraints and indexes are named by the naming rule.",
        "The table zebra has a name given by hand, second: "
        "constraints and indexes are named by the naming rule.",
    ]


def twice_a_check() -> list[SchemaItem]:
    return [
        Column("laps", Integer),
        CheckConstraint("laps > 0", name="laps_sane"),
        CheckConstraint("laps < 99", name="laps_sane"),
    ]


def thrice_a_check() -> list[SchemaItem]:
    return [*twice_a_check(), CheckConstraint("laps != 13", name="laps_sane")]


def twice_unique() -> list[SchemaItem]:
    # Said with the column and said again of the table: the naming rule gives both one name.
    return [Column("code", Text, unique=True), UniqueConstraint("code")]


def twice_an_index() -> list[SchemaItem]:
    return [Column("code", Text, index=True), Index(None, "code")]


def twice_a_foreign_key() -> list[SchemaItem]:
    return [
        Column("other_id", Integer, ForeignKey("other.id")),
        ForeignKeyConstraint(["other_id"], ["other.id"]),
    ]


@pytest.mark.parametrize(
    ("said", "name", "times_given"),
    [
        (twice_a_check, "ck_odd_one_laps_sane", 2),
        (thrice_a_check, "ck_odd_one_laps_sane", 3),
        (twice_unique, "uq_odd_one_code", 2),
        (twice_an_index, "ix_odd_one_code", 2),
        (twice_a_foreign_key, "fk_odd_one_other_id_other", 2),
    ],
    ids=[
        "two checks of one name",
        "three checks of one name",
        "a column that is unique, said twice",
        "an index, said twice",
        "a foreign key, said twice",
    ],
)
def test_a_name_that_two_constraints_or_indexes_have_is_named(
    said: Callable[[], list[SchemaItem]], name: str, times_given: int
) -> None:
    schema = a_schema()
    Table("other", schema, the_key(), *the_times(), **KEPT)
    Table("odd_one", schema, the_key(), *said(), *the_times(), **KEPT)

    assert broken_rules(schema) == [TWICE.format("odd_one", name, times_given)]


def test_names_given_twice_are_listed_once_each_by_the_alphabet_and_after_the_other_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = a_schema()
    odd_one = Table(
        "odd_one",
        schema,
        the_key(),
        Column("laps", Integer),
        Column("code", Text),
        Column("note", Text),
        *the_times(),
        CheckConstraint("laps > 0", name="laps_sane"),
        CheckConstraint("laps < 99", name="laps_sane"),
        CheckConstraint("code != ''", name="code_sane"),
        CheckConstraint("code != 'x'", name="code_sane"),
        UniqueConstraint("code", name="mine"),
        UniqueConstraint("note", name="mine"),
        UniqueConstraint("laps"),
        **KEPT,
    )
    # SQLAlchemy keeps the constraints of a table as a set, which has no order
    # to rely on. Here they are given one: the alphabet, from its end.
    from_the_end = sorted(odd_one.constraints, key=lambda one: str(one.name), reverse=True)
    monkeypatch.setattr(odd_one, "constraints", from_the_end)
    by_hand = (
        "The table odd_one has a name given by hand, mine: "
        "constraints and indexes are named by the naming rule."
    )

    assert [str(one.name) for one in from_the_end] == [
        "uq_odd_one_laps",
        "mine",
        "mine",
        "ck_odd_one_laps_sane",
        "ck_odd_one_laps_sane",
        "ck_odd_one_code_sane",
        "ck_odd_one_code_sane",
        "None",
    ]
    assert broken_rules(schema) == [
        by_hand,
        by_hand,
        TWICE.format("odd_one", "ck_odd_one_code_sane", 2),
        TWICE.format("odd_one", "ck_odd_one_laps_sane", 2),
        TWICE.format("odd_one", "mine", 2),
    ]


def test_one_name_in_two_tables_is_not_a_name_given_twice() -> None:
    schema = a_schema()
    for name in ("one", "other"):
        Table(
            name,
            schema,
            the_key(),
            Column("code", Text),
            *the_times(),
            # Only a name given by hand can be the same in two tables: the
            # naming rule puts the name of the table in every name it gives.
            UniqueConstraint("code", name="mine"),
            **KEPT,
        )

    assert broken_rules(schema) == [
        "The table one has a name given by hand, mine: "
        "constraints and indexes are named by the naming rule.",
        "The table other has a name given by hand, mine: "
        "constraints and indexes are named by the naming rule.",
    ]


@pytest.mark.parametrize("right_one_first", [True, False], ids=["first", "last"])
@pytest.mark.parametrize(
    ("of_the_name", "found"),
    [
        (lambda: not_empty("name"), []),
        (lambda: CheckConstraint("name != 'y'", name="name_not_empty"), ["name"]),
    ],
    ids=["one of the two is the column's own check", "neither is"],
)
def test_a_column_with_two_checks_of_its_checks_name_is_judged_the_same_in_either_order(
    monkeypatch: pytest.MonkeyPatch,
    of_the_name: Callable[[], CheckConstraint],
    found: list[str],
    right_one_first: bool,
) -> None:
    schema = a_schema()
    odd_one = Table(
        "odd_one", schema, the_key(), Column("name", NotEmptyText), *the_times(), **KEPT
    )
    the_rest = list(odd_one.constraints)
    one = of_the_name()
    another = CheckConstraint("name != 'x'", name="name_not_empty")
    odd_one.append_constraint(one)
    odd_one.append_constraint(another)
    # SQLAlchemy keeps the constraints of a table as a set, which has no
    # order to rely on. Here they are given one, and then the other.
    in_this_order = [one, another] if right_one_first else [another, one]
    monkeypatch.setattr(odd_one, "constraints", [*the_rest, *in_this_order])

    assert broken_rules(schema) == [
        *(NO_CHECK.format("odd_one", name) for name in found),
        TWICE.format("odd_one", "ck_odd_one_name_not_empty", 2),
    ]


def test_a_check_without_a_name_is_refused_when_its_table_is_defined() -> None:
    schema = a_schema()

    with pytest.raises(InvalidRequestError, match="requires that constraint is explicitly named"):
        Table(
            "nameless",
            schema,
            the_key(),
            Column("number", Integer),
            CheckConstraint("number > 0"),
            **KEPT,
        )
