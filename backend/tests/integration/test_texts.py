"""Tests of text that must not be empty, with tables made in a real SQLite file.

The two models here are made for the tests. They are subclasses of the
real ``Base``, so they prove what a model gets when it says that a
column's text must not be empty, but they are kept in a schema of their
own (``Proof.metadata``), so the real schema never sees them.
"""

import re

import pytest
from sqlalchemy import Engine, MetaData, UniqueConstraint, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base, broken_rules
from motosphere.db.texts import WHITE_SPACE, NotEmpty, NotEmptyText
from motosphere.db.work import unit_of_work

A_TIME = "2026-11-19T08:00:00.000000+00:00"
REFUSED = "CHECK constraint failed: ck_{}_not_empty"
THE_CHECK = (
    "CONSTRAINT ck_proof_rider_{}_not_empty CHECK (trim({}, char(9, 10, 11, 12, 13, 28, 29, 30, "
    "31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202, "
    "8232, 8233, 8239, 8287, 12288)) != '')"
)


class Proof(Base):
    """Models of the tests' own: what ``Base`` gives such text, in a schema of their own."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofRider(Proof):
    __tablename__ = "proof_rider"

    name: Mapped[NotEmpty]
    # No value, or text that is not empty.
    nickname: Mapped[NotEmpty | None]
    # A model that says more of the column.
    number: Mapped[NotEmpty] = mapped_column(unique=True)
    # A name that is a word of SQL.
    group: Mapped[NotEmpty]
    # Text that may be empty, as before.
    note: Mapped[str]


class ProofTeam(Proof):
    __tablename__ = "proof_team"
    # A model that says something of its table itself.
    __table_args__ = (UniqueConstraint("name", "country"),)

    name: Mapped[NotEmpty]
    country: Mapped[str]


@pytest.fixture
def made(store: Engine) -> Engine:
    """The store, with the two tables of the tests made in it."""
    with store.begin() as connection:
        Proof.metadata.create_all(connection)
    return store


def rider(**said: str | None) -> ProofRider:
    """A rider every column of whom is as it must be, unless ``said`` otherwise."""
    as_it_must_be = {"name": "Ada Example", "nickname": None, "number": "84", "group": "A"}
    return ProofRider(**(as_it_must_be | {"note": ""} | said))


def written(made: Engine, table: str) -> str:
    """How the file itself says the table is made."""
    with made.connect() as connection:
        text = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE name = ?", (table,)
        ).scalar_one()
    return str(text)


def names(made: Engine) -> list[str]:
    """The names of the riders the file holds, read without the model."""
    with made.connect() as connection:
        return list(
            connection.exec_driver_sql("SELECT name FROM proof_rider ORDER BY id").scalars()
        )


def test_text_that_must_not_be_empty_is_text_in_a_strict_table(made: Engine) -> None:
    columns = ProofRider.__table__.c

    assert [column.name for column in columns if isinstance(column.type, NotEmptyText)] == [
        "name",
        "nickname",
        "number",
        "group",
    ]
    assert broken_rules(Proof.metadata) == []

    with made.connect() as connection:
        in_the_file = {
            name: (declared, bool(required))
            for _, name, declared, required, _, _ in connection.exec_driver_sql(
                "PRAGMA table_info(proof_rider)"
            )
        }

    assert in_the_file == {
        "id": ("INTEGER", True),
        "name": ("TEXT", True),
        "nickname": ("TEXT", False),
        "number": ("TEXT", True),
        "group": ("TEXT", True),
        "note": ("TEXT", True),
        "created_at": ("TEXT", True),
        "updated_at": ("TEXT", True),
    }


def test_the_file_has_a_check_named_by_the_rule_for_each_such_column_and_for_no_other(
    made: Engine,
) -> None:
    riders = written(made, "proof_rider")

    assert sorted(re.findall(r"CONSTRAINT (\w+) CHECK", riders)) == [
        "ck_proof_rider_group_not_empty",
        "ck_proof_rider_name_not_empty",
        "ck_proof_rider_nickname_not_empty",
        "ck_proof_rider_number_not_empty",
    ]
    assert THE_CHECK.format("name", "name") in riders
    assert THE_CHECK.format("group", '"group"') in riders
    assert "CONSTRAINT uq_proof_rider_number UNIQUE (number)" in riders
    assert re.findall(r"CONSTRAINT (\w+) CHECK", written(made, "proof_team")) == [
        "ck_proof_team_name_not_empty"
    ]


@pytest.mark.parametrize(
    "name",
    ["Ada Example", "  Ada Example \n", "0", "\u00e9", "a\tb", "\u200b"],
    ids=[
        "a name",
        "white space around a name",
        "a nought",
        "a letter with an accent",
        "white space between letters",
        "a space without width, which Python does not call white space",
    ],
)
def test_text_that_is_not_empty_is_stored_as_it_was_given(made: Engine, name: str) -> None:
    with unit_of_work(made) as work:
        work.add(rider(name=name))

    assert names(made) == [name]
    with unit_of_work(made) as work:
        assert work.scalars(select(ProofRider.name)).one() == name


@pytest.mark.parametrize(
    "empty",
    ["", " ", "   ", "\t", "\n", "\r\n", "\u00a0", "\u3000", " \t\u00a0\n"],
    ids=[
        "no characters",
        "a space",
        "three spaces",
        "a tab",
        "a line feed",
        "the line end of Windows",
        "the space that cannot be broken",
        "the wide space",
        "white space of four kinds",
    ],
)
def test_empty_text_is_refused_by_the_store_and_the_refusal_names_the_check(
    made: Engine, empty: str
) -> None:
    refusal = REFUSED.format("proof_rider_name")

    with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
        work.add_all([rider(), rider(number="85", name=empty)])

    assert names(made) == []


def test_every_white_space_character_alone_is_empty_text(made: Engine) -> None:
    stored = []
    for number in WHITE_SPACE:
        try:
            with unit_of_work(made) as work:
                work.add(rider(number=str(number), name=chr(number)))
        except IntegrityError:
            continue
        stored.append(number)

    assert stored == []
    assert names(made) == []


def test_every_white_space_character_around_text_is_kept(made: Engine) -> None:
    given = [chr(number) + "Ada" + chr(number) for number in WHITE_SPACE]

    with unit_of_work(made) as work:
        work.add_all(rider(number=str(place), name=name) for place, name in enumerate(given))

    assert names(made) == given


def test_empty_text_written_past_the_model_is_refused(made: Engine) -> None:
    statement = (
        'INSERT INTO proof_rider (name, number, "group", note, created_at, updated_at) '
        "VALUES (?, '84', 'A', '', ?, ?)"
    )

    with made.begin() as connection:
        connection.exec_driver_sql(statement, ("Ada Example", A_TIME, A_TIME))
    for empty in ("", " \u00a0"):
        refusal = REFUSED.format("proof_rider_name")
        with pytest.raises(IntegrityError, match=refusal), made.begin() as connection:
            connection.exec_driver_sql(statement, (empty, A_TIME, A_TIME))

    assert names(made) == ["Ada Example"]


def test_a_change_to_empty_text_is_refused_and_the_row_stays_as_it_was(made: Engine) -> None:
    refusal = REFUSED.format("proof_rider_name")
    with unit_of_work(made) as work:
        work.add(rider())

    with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
        work.scalars(select(ProofRider)).one().name = " "
    with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
        work.execute(update(ProofRider).values(name=""))
    with pytest.raises(IntegrityError, match=refusal), made.begin() as connection:
        connection.exec_driver_sql("UPDATE proof_rider SET name = '\t'")

    assert names(made) == ["Ada Example"]


def test_a_column_that_may_be_without_a_value_holds_none_or_text_that_is_not_empty(
    made: Engine,
) -> None:
    refusal = REFUSED.format("proof_rider_nickname")

    with unit_of_work(made) as work:
        work.add_all([rider(), rider(number="85", nickname="The Example")])
    for empty in ("", " "):
        with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
            work.add(rider(number="86", nickname=empty))

    with made.connect() as connection:
        nicknames = connection.exec_driver_sql(
            "SELECT nickname FROM proof_rider ORDER BY id"
        ).scalars()
        assert list(nicknames) == [None, "The Example"]


@pytest.mark.parametrize("column", ["number", "group"])
def test_every_such_column_has_a_check_of_its_own(made: Engine, column: str) -> None:
    refusal = REFUSED.format(f"proof_rider_{column}")

    with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
        work.add(rider(**{column: ""}))

    assert names(made) == []


def test_a_model_that_says_something_of_its_table_gets_the_check_too(made: Engine) -> None:
    refusal = REFUSED.format("proof_team_name")

    with unit_of_work(made) as work:
        work.add(ProofTeam(name="Example Racing", country=""))
    with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
        work.add(ProofTeam(name="", country="NL"))

    with made.connect() as connection:
        teams = connection.exec_driver_sql("SELECT name, country FROM proof_team").all()
    assert [tuple(team) for team in teams] == [("Example Racing", "")]


def test_text_that_may_be_empty_is_stored_empty_as_before(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all([rider(note=""), rider(number="85", note="  ")])

    with made.connect() as connection:
        notes = connection.exec_driver_sql("SELECT note FROM proof_rider ORDER BY id").scalars()
        assert list(notes) == ["", "  "]
