"""Tests of a column whose value is one of a list, with tables made in a real SQLite file.

The lists and the models here are made for the tests. The models are
subclasses of the real ``Base``, so they prove what a model gets when it
says that a column's value is one of a list, but they are kept in schemas
of their own, so the real schema never sees them.
"""

from enum import StrEnum
from typing import Any

import pytest
from sqlalchemy import Engine, MetaData, literal, select
from sqlalchemy.exc import IntegrityError, OperationalError, StatementError
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base, broken_rules
from motosphere.db.lists import OneOf
from motosphere.db.work import unit_of_work

A_TIME = "2026-11-19T08:00:00.000000+00:00"
REFUSED = "CHECK constraint failed: ck_proof_place_{}_one_of"
NOT_OF_THE_LIST = "Only a value of the list Kind is stored in this column"
# A row written with plain SQL. Its first two "?" are kind and surface; the
# last two are its two times, which only the store's code sets.
PAST_THE_MODEL = (
    "INSERT INTO proof_place (kind, surface, created_at, updated_at) VALUES (?, ?, ?, ?)"
)


class Kind(StrEnum):
    TRACK = "track"
    CLUB = "club"
    SHOP = "shop"


class Surface(StrEnum):
    """A second list. One of its texts is a text of the first list too."""

    SAND = "sand"
    HARD_PACK = "hard pack"
    TRACK = "track"


class Odd(StrEnum):
    """Texts with the characters SQL has a use for, in large letters, and beyond ASCII."""

    QUOTE = "o'brien"
    TWO_QUOTES = 'say "go"'
    PERCENT = "50%"
    COLON = "a:b"
    QUESTION = "what?"
    BACKSLASH = "a\\b"
    LARGE = "MXoN"
    ACCENT = "caf" + chr(233)


class Proof(Base):
    """A model of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofPlace(Proof):
    __tablename__ = "proof_place"

    kind: Mapped[Kind] = mapped_column(OneOf(Kind))
    # No value, or a value of a second list.
    surface: Mapped[Surface | None] = mapped_column(OneOf(Surface))
    mark: Mapped[Odd | None] = mapped_column(OneOf(Odd))
    # Text that is of no list, as before.
    note: Mapped[str | None]


class Forgotten(Base):
    """A model that names its list and not the type, in a schema of its own."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofStall(Forgotten):
    __tablename__ = "proof_stall"

    kind: Mapped[Kind]


class Shorter(StrEnum):
    """The first list as it is once a value has been taken off it."""

    TRACK = "track"
    CLUB = "club"


class Later(Base):
    """A model of the table of ``ProofPlace`` with the shorter list, in a schema of its own."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class LaterPlace(Later):
    __tablename__ = "proof_place"

    kind: Mapped[Shorter] = mapped_column(OneOf(Shorter))


@pytest.fixture
def made(store: Engine) -> Engine:
    """The store, with the table of the tests made in it."""
    with store.begin() as connection:
        Proof.metadata.create_all(connection)
    return store


def stored(made: Engine) -> list[tuple[Any, ...]]:
    """The kind, the surface and the mark of every place the file holds, read without the model."""
    with made.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT kind, surface, mark FROM proof_place ORDER BY id"
        ).all()
    return [tuple(row) for row in rows]


def test_a_value_of_a_list_is_text_in_a_strict_table(made: Engine) -> None:
    columns = ProofPlace.__table__.c

    assert [column.name for column in columns if isinstance(column.type, OneOf)] == [
        "kind",
        "surface",
        "mark",
    ]
    assert broken_rules(Proof.metadata) == []

    with made.connect() as connection:
        in_the_file = {
            name: (declared, bool(required))
            for _, name, declared, required, _, _ in connection.exec_driver_sql(
                "PRAGMA table_info(proof_place)"
            )
        }

    assert in_the_file == {
        "id": ("INTEGER", True),
        "kind": ("TEXT", True),
        "surface": ("TEXT", False),
        "mark": ("TEXT", False),
        "note": ("TEXT", False),
        "created_at": ("TEXT", True),
        "updated_at": ("TEXT", True),
    }


def test_the_file_has_a_check_that_names_the_texts_of_each_columns_own_list(made: Engine) -> None:
    with made.connect() as connection:
        written = str(
            connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'proof_place'"
            ).scalar_one()
        )

    assert [line.strip().rstrip(",") for line in written.splitlines() if "CHECK" in line] == [
        "CONSTRAINT ck_proof_place_kind_one_of CHECK (kind IN ('track', 'club', 'shop'))",
        "CONSTRAINT ck_proof_place_surface_one_of CHECK "
        "(surface IN ('sand', 'hard pack', 'track'))",
        "CONSTRAINT ck_proof_place_mark_one_of CHECK "
        "(mark IN ('o''brien', 'say \"go\"', '50%', 'a:b', 'what?', 'a\\b', 'MXoN', 'caf"
        + chr(233)
        + "'))",
    ]


def test_every_value_of_a_list_is_stored_as_its_text_and_comes_back_as_the_value(
    made: Engine,
) -> None:
    with unit_of_work(made) as work:
        work.add_all([ProofPlace(kind=kind) for kind in Kind])

    assert stored(made) == [("track", None, None), ("club", None, None), ("shop", None, None)]
    with unit_of_work(made) as work:
        places = work.scalars(select(ProofPlace).order_by(ProofPlace.id)).all()
        assert [place.kind for place in places] == [Kind.TRACK, Kind.CLUB, Kind.SHOP]
        assert places[0].kind is Kind.TRACK


def test_a_text_with_any_characters_is_stored_and_comes_back(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all([ProofPlace(kind=Kind.TRACK, mark=mark) for mark in Odd])

    assert [mark for _, _, mark in stored(made)] == [
        "o'brien",
        'say "go"',
        "50%",
        "a:b",
        "what?",
        "a\\b",
        "MXoN",
        "caf" + chr(233),
    ]
    with unit_of_work(made) as work:
        places = work.scalars(select(ProofPlace).order_by(ProofPlace.id)).all()
        assert [place.mark for place in places] == list(Odd)


def test_a_column_that_may_be_without_a_value_holds_none_or_a_value_of_its_list(
    made: Engine,
) -> None:
    with unit_of_work(made) as work:
        work.add(ProofPlace(kind=Kind.TRACK, surface=None))
        work.add(ProofPlace(kind=Kind.TRACK, surface=Surface.HARD_PACK))

    assert stored(made) == [("track", None, None), ("track", "hard pack", None)]
    with unit_of_work(made) as work:
        places = work.scalars(select(ProofPlace).order_by(ProofPlace.id)).all()
        assert [place.surface for place in places] == [None, Surface.HARD_PACK]


def test_two_columns_each_keep_their_own_list(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofPlace(kind=Kind.TRACK, surface=Surface.TRACK))

    # The same text in both, and each column reads it as the value of its own list.
    assert stored(made) == [("track", "track", None)]
    with unit_of_work(made) as work:
        place = work.scalars(select(ProofPlace)).one()
        assert place.kind is Kind.TRACK
        assert place.surface is Surface.TRACK
    # Sand is on the second list only, and club on the first only.
    with pytest.raises(IntegrityError, match=REFUSED.format("kind")), made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, ("sand", None, A_TIME, A_TIME))
    with pytest.raises(IntegrityError, match=REFUSED.format("surface")), made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, ("track", "club", A_TIME, A_TIME))

    assert stored(made) == [("track", "track", None)]


def test_a_change_to_another_value_of_the_list_is_stored(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofPlace(kind=Kind.TRACK, surface=Surface.SAND))
    with unit_of_work(made) as work:
        place = work.scalars(select(ProofPlace)).one()
        place.kind = Kind.SHOP
        place.surface = None

    assert stored(made) == [("shop", None, None)]


@pytest.mark.parametrize(
    "value",
    ["track", "garage", Surface.TRACK, 1],
    ids=[
        "text that is spelled like a value",
        "text that is not on the list",
        "a value of another list with the same text",
        "a number",
    ],
)
def test_what_is_not_a_value_of_the_list_is_refused_and_nothing_is_stored(
    made: Engine, value: Any
) -> None:
    places = [ProofPlace(kind=Kind.CLUB), ProofPlace(kind=value)]

    with (
        pytest.raises(StatementError, match=NOT_OF_THE_LIST) as refused,
        unit_of_work(made) as work,
    ):
        work.add_all(places)

    assert isinstance(refused.value.orig, TypeError)
    assert stored(made) == []


@pytest.mark.parametrize(
    "text",
    ["garage", "TRACK", "track ", " track", "", "tr", 1],
    ids=[
        "another word",
        "in large letters",
        "with a space after it",
        "with a space before it",
        "nothing",
        "the beginning of a value",
        "a number",
    ],
)
def test_text_that_is_not_on_the_list_written_past_the_model_is_refused(
    made: Engine, text: Any
) -> None:
    with made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, ("club", None, A_TIME, A_TIME))

    refusal = REFUSED.format("kind")
    with pytest.raises(IntegrityError, match=refusal), made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (text, None, A_TIME, A_TIME))

    assert stored(made) == [("club", None, None)]


def test_a_change_to_text_that_is_not_on_the_list_is_refused_and_the_row_stays_as_it_was(
    made: Engine,
) -> None:
    with unit_of_work(made) as work:
        work.add(ProofPlace(kind=Kind.TRACK, surface=Surface.SAND))

    with pytest.raises(IntegrityError, match=REFUSED.format("kind")), made.begin() as connection:
        connection.exec_driver_sql("UPDATE proof_place SET kind = 'garage'")
    with pytest.raises(IntegrityError, match=REFUSED.format("surface")), made.begin() as connection:
        connection.exec_driver_sql("UPDATE proof_place SET surface = 'Sand'")

    assert stored(made) == [("track", "sand", None)]


def test_rows_are_found_by_a_value_by_several_and_by_no_value(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all(
            [
                ProofPlace(kind=Kind.TRACK, surface=None),
                ProofPlace(kind=Kind.CLUB, surface=Surface.SAND),
                ProofPlace(kind=Kind.SHOP, surface=Surface.TRACK),
            ]
        )

    def found(asked: Any) -> list[int]:
        with unit_of_work(made) as work:
            return list(work.scalars(select(ProofPlace.id).where(asked).order_by(ProofPlace.id)))

    assert found(ProofPlace.kind == Kind.CLUB) == [2]
    assert found(ProofPlace.kind != Kind.CLUB) == [1, 3]
    assert found(ProofPlace.kind.in_([Kind.TRACK, Kind.SHOP])) == [1, 3]
    assert found(ProofPlace.surface.is_(None)) == [1]
    assert found(ProofPlace.surface == Surface.TRACK) == [3]


def test_a_question_with_what_is_not_a_value_of_the_list_is_refused(made: Engine) -> None:
    with (
        pytest.raises(StatementError, match=NOT_OF_THE_LIST) as refused,
        unit_of_work(made) as work,
    ):
        work.scalars(select(ProofPlace).where(ProofPlace.kind == "track"))

    assert isinstance(refused.value.orig, TypeError)


def test_rows_sorted_by_such_a_column_come_in_the_order_of_the_texts(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all([ProofPlace(kind=kind) for kind in Kind])

    with unit_of_work(made) as work:
        kinds = list(work.scalars(select(ProofPlace.kind).order_by(ProofPlace.kind)))

    # By the alphabet, not in the order of the list (track, club, shop).
    assert kinds == [Kind.CLUB, Kind.SHOP, Kind.TRACK]


def test_two_statements_that_differ_in_the_list_only_each_keep_their_own(made: Engine) -> None:
    # SQLAlchemy keeps a statement it has seen and uses it again for one that
    # is the same but for its values. These two are the same but for the list.
    with unit_of_work(made) as work:
        assert work.scalar(select(literal(Kind.CLUB, OneOf(Kind)))) is Kind.CLUB
        assert work.scalar(select(literal(Surface.SAND, OneOf(Surface)))) is Surface.SAND
        assert work.scalar(select(literal(Kind.TRACK, OneOf(Kind)))) is Kind.TRACK
        assert work.scalar(select(literal(Surface.TRACK, OneOf(Surface)))) is Surface.TRACK


def test_a_text_the_list_no_longer_has_is_refused_when_it_is_read(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all([ProofPlace(kind=Kind.CLUB), ProofPlace(kind=Kind.SHOP)])

    refusal = "The store holds what is not on the list Shorter: 'shop'\\."
    with unit_of_work(made) as work:
        first = select(LaterPlace).where(LaterPlace.id == 1)
        assert work.scalars(first).one().kind is Shorter.CLUB
    with pytest.raises(ValueError, match=refusal), unit_of_work(made) as work:
        work.scalars(select(LaterPlace).where(LaterPlace.id == 2)).all()


def test_a_model_that_names_its_list_and_not_the_type_gets_a_table_sqlite_refuses_to_make(
    store: Engine,
) -> None:
    refusal = 'unknown datatype for proof_stall.kind: "VARCHAR\\(5\\)"'

    with pytest.raises(OperationalError, match=refusal), store.begin() as connection:
        Forgotten.metadata.create_all(connection)


def test_text_of_no_list_is_stored_as_before(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofPlace(kind=Kind.TRACK, note="garage"))

    with made.connect() as connection:
        assert connection.exec_driver_sql("SELECT note FROM proof_place").scalar_one() == "garage"
