"""Tests of the two times every row has, with a table made in a real SQLite file.

The model here is made for the tests. It is a subclass of the real ``Base``
and names no time, so it proves what ``Base`` gives it, but it is kept in a
schema of its own (``Proof.metadata``), so the real schema never sees it.

Most tests set the store's clock with the fixture ``clock``: it is the list
of the moments the clock said, a second apart, in order.
"""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, MetaData, insert, select, update
from sqlalchemy.dialects import sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base
from motosphere.db.times import to_text
from motosphere.db.work import unit_of_work

LONG_AGO = datetime(2019, 3, 9, 14, 30, tzinfo=UTC)
ITS_TEXT = "2019-03-09T14:30:00.000000+00:00"


class Proof(Base):
    """Models of the tests' own: the times ``Base`` gives, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofNote(Proof):
    __tablename__ = "proof_note"

    words: Mapped[str] = mapped_column(unique=True)
    stars: Mapped[int | None]


@pytest.fixture
def made(store: Engine) -> Engine:
    """The store, with the table of the tests made in it."""
    with store.begin() as connection:
        Proof.metadata.create_all(connection)
    return store


def add(made: Engine, *words: str) -> None:
    """Store a note of each of the words, each in a unit of work of its own."""
    for its_words in words:
        with unit_of_work(made) as work:
            work.add(ProofNote(words=its_words))


def stored(made: Engine) -> list[tuple[str, str, str]]:
    """What the file itself holds, read without the model."""
    with made.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT words, created_at, updated_at FROM proof_note ORDER BY id"
        ).all()
    return [(words, created_at, updated_at) for words, created_at, updated_at in rows]


def test_the_two_times_are_the_last_columns_and_the_table_does_not_set_them(made: Engine) -> None:
    with made.connect() as connection:
        columns = [
            (name, declared, bool(required), set_by_the_table)
            for _, name, declared, required, set_by_the_table, _ in connection.exec_driver_sql(
                "PRAGMA table_info(proof_note)"
            )
        ]

    assert [name for name, _, _, _ in columns] == [
        "id",
        "words",
        "stars",
        "created_at",
        "updated_at",
    ]
    assert columns[-2:] == [("created_at", "TEXT", True, None), ("updated_at", "TEXT", True, None)]


def test_a_new_row_says_when_it_was_first_stored_and_was_last_changed_then(
    made: Engine, clock: list[datetime]
) -> None:
    with unit_of_work(made) as work:
        note = ProofNote(words="first")
        work.add(note)

    assert len(clock) == 1
    assert stored(made) == [("first", to_text(clock[0]), to_text(clock[0]))]
    assert (note.created_at, note.updated_at) == (clock[0], clock[0])


def test_the_times_come_back_as_aware_utc_times(made: Engine, clock: list[datetime]) -> None:
    add(made, "first")

    with unit_of_work(made) as work:
        note = work.scalars(select(ProofNote)).one()

    assert (note.created_at, note.updated_at) == (clock[0], clock[0])
    assert note.created_at.utcoffset() == timedelta(0)
    assert note.updated_at.utcoffset() == timedelta(0)


def test_a_changed_row_says_when_it_was_changed_and_keeps_when_it_was_first_stored(
    made: Engine, clock: list[datetime]
) -> None:
    add(made, "first")

    with unit_of_work(made) as work:
        note = work.scalars(select(ProofNote)).one()
        note.words = "changed"

    assert len(clock) == 2
    assert stored(made) == [("changed", to_text(clock[0]), to_text(clock[1]))]
    assert (note.created_at, note.updated_at) == (clock[0], clock[1])


def test_a_row_stored_again_as_it_was_keeps_both_times(made: Engine, clock: list[datetime]) -> None:
    add(made, "first")

    with unit_of_work(made) as work:
        note = work.scalars(select(ProofNote)).one()
        note.words = "first"
        note.stars = None
        work.add(note)

    assert len(clock) == 1
    assert stored(made) == [("first", to_text(clock[0]), to_text(clock[0]))]


def test_only_the_row_that_changed_gets_a_new_time(made: Engine, clock: list[datetime]) -> None:
    add(made, "first", "second")

    with unit_of_work(made) as work:
        note = work.scalars(select(ProofNote).where(ProofNote.words == "second")).one()
        note.stars = 5

    assert len(clock) == 3
    assert stored(made) == [
        ("first", to_text(clock[0]), to_text(clock[0])),
        ("second", to_text(clock[1]), to_text(clock[2])),
    ]


def test_rows_changed_in_one_unit_of_work_each_get_a_moment_of_their_own(
    made: Engine, clock: list[datetime]
) -> None:
    add(made, "first", "second")

    with unit_of_work(made) as work:
        for note in work.scalars(select(ProofNote).order_by(ProofNote.id)):
            note.stars = 5

    assert len(clock) == 4
    assert stored(made) == [
        ("first", to_text(clock[0]), to_text(clock[2])),
        ("second", to_text(clock[1]), to_text(clock[3])),
    ]


@pytest.mark.parametrize(
    "way",
    ["added to one unit of work", "a list of rows", "rows in the statement itself"],
)
def test_every_row_stored_together_gets_one_moment_of_its_own_for_both_times(
    made: Engine, clock: list[datetime], way: str
) -> None:
    with unit_of_work(made) as work:
        if way == "added to one unit of work":
            work.add_all([ProofNote(words="first"), ProofNote(words="second")])
        elif way == "a list of rows":
            work.execute(insert(ProofNote), [{"words": "first"}, {"words": "second"}])
        else:
            work.execute(insert(ProofNote).values([{"words": "first"}, {"words": "second"}]))

    assert len(clock) == 2
    assert stored(made) == [
        ("first", to_text(clock[0]), to_text(clock[0])),
        ("second", to_text(clock[1]), to_text(clock[1])),
    ]


def test_rows_changed_by_one_statement_all_say_when(made: Engine, clock: list[datetime]) -> None:
    add(made, "first", "second", "third")

    with unit_of_work(made) as work:
        work.execute(update(ProofNote).where(ProofNote.words != "second").values(stars=5))

    assert len(clock) == 4
    assert stored(made) == [
        ("first", to_text(clock[0]), to_text(clock[3])),
        ("second", to_text(clock[1]), to_text(clock[1])),
        ("third", to_text(clock[2]), to_text(clock[3])),
    ]


def test_a_row_stored_with_times_of_its_own_keeps_them(made: Engine, clock: list[datetime]) -> None:
    changed = LONG_AGO + timedelta(days=400)

    with unit_of_work(made) as work:
        work.add(ProofNote(words="old", created_at=LONG_AGO, updated_at=changed))

    assert clock == []
    assert stored(made) == [("old", ITS_TEXT, to_text(changed))]


def test_a_row_stored_with_only_its_first_time_was_last_changed_then(
    made: Engine, clock: list[datetime]
) -> None:
    with unit_of_work(made) as work:
        work.add(ProofNote(words="old", created_at=LONG_AGO))

    assert clock == []
    assert stored(made) == [("old", ITS_TEXT, ITS_TEXT)]


@pytest.mark.parametrize(
    ("statement", "missing"),
    [
        ("INSERT INTO proof_note (words) VALUES ('past')", "created_at"),
        (
            "INSERT INTO proof_note (words, created_at) "
            "VALUES ('past', '2019-03-09T14:30:00.000000+00:00')",
            "updated_at",
        ),
    ],
    ids=["neither time", "only when it was first stored"],
)
def test_a_row_written_past_the_model_without_its_times_is_refused(
    made: Engine, statement: str, missing: str
) -> None:
    with pytest.raises(IntegrityError) as refused, made.begin() as connection:
        connection.exec_driver_sql(statement)

    assert isinstance(refused.value.orig, sqlite3.IntegrityError)
    assert str(refused.value.orig) == f"NOT NULL constraint failed: proof_note.{missing}"
    assert stored(made) == []


def test_a_change_written_past_the_model_does_not_say_when(
    made: Engine, clock: list[datetime]
) -> None:
    add(made, "first")

    with made.begin() as connection:
        connection.exec_driver_sql("UPDATE proof_note SET words = 'changed'")

    assert len(clock) == 1
    assert stored(made) == [("changed", to_text(clock[0]), to_text(clock[0]))]


def test_a_change_by_a_statement_that_stores_or_changes_does_not_say_when(
    made: Engine, clock: list[datetime]
) -> None:
    add(made, "first")
    store_or_change = sqlite.insert(ProofNote).values(words="first", stars=5)

    with unit_of_work(made) as work:
        work.execute(
            store_or_change.on_conflict_do_update(
                index_elements=["words"], set_={"stars": store_or_change.excluded.stars}
            )
        )
        stars = work.scalars(select(ProofNote.stars)).one()

    assert stars == 5
    assert stored(made) == [("first", to_text(clock[0]), to_text(clock[0]))]


def test_without_a_set_clock_a_row_gets_the_moment_it_is(made: Engine) -> None:
    before = datetime.now(UTC)
    with unit_of_work(made) as work:
        note = ProofNote(words="now")
        work.add(note)
    after = datetime.now(UTC)

    assert before <= note.created_at <= after
    assert note.updated_at == note.created_at
    assert stored(made) == [("now", to_text(note.created_at), to_text(note.created_at))]
