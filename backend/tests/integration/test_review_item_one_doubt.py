"""Tests that one doubt is one review item, against a real SQLite file.

The store of every test is built by the migrations, as a real store is.
The store itself refuses the same doubt a second time, by two indexes,
and these tests say what the same doubt is and what is another.
"""

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from motosphere.db.models import ReviewItem, Source
from motosphere.db.models.review_item import ReviewKind
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

MOMENT = "2026-11-26T09:00:00.000000+00:00"
OF_A_PAIR = "ix_review_item_record_table_record_id_other_record_id"
OF_WHAT_A_SOURCE_SAYS = "ix_review_item_record_table_record_id_field_source_id_source_value"
OF_A_SOURCE = "ix_review_item_source_id"
# What SQLite says when it refuses the same doubt a second time.
THE_PAIR_IS_THERE = (
    "UNIQUE constraint failed: review_item.record_table, review_item.record_id, "
    "review_item.other_record_id"
)
WHAT_THE_SOURCE_SAYS_IS_THERE = (
    "UNIQUE constraint failed: review_item.record_table, review_item.record_id, "
    "review_item.field, review_item.source_id, review_item.source_value"
)
# A row written past the model: every column but the key, in the table's order.
PAST_THE_MODEL = (
    "INSERT INTO review_item (kind, record_table, record_id, other_record_id, field, "
    "source_id, source_address, source_value, reason, state, decided_by, decided_at, note, "
    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
WHAT_IT_HOLDS = (
    "SELECT kind, record_table, record_id, other_record_id, field, source_id, source_address, "
    "source_value, reason, state, decided_by, decided_at, note FROM review_item ORDER BY id"
)
# The three states an item can be in when its doubt comes a second time.
DECIDED: dict[str, object] = {
    "state": "accepted",
    "decided_by": "Jo Example",
    "decided_at": MOMENT,
}
STATES: dict[str, dict[str, object]] = {
    "open": {},
    "accepted": DECIDED,
    "rejected": {**DECIDED, "state": "rejected"},
}
IN_EACH_STATE = pytest.mark.parametrize("state", list(STATES))
OF_A_FIELD = ["sources disagree", "value outside its rules"]


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def a_pair(**given: object) -> dict[str, object]:
    """A possible duplicate that nobody has decided, as a row, but for what is given."""
    row: dict[str, object] = {
        "kind": "possible duplicate",
        "record_table": "track",
        "record_id": 7,
        "other_record_id": 12,
        "field": None,
        "source_id": None,
        "source_address": None,
        "source_value": None,
        "reason": "The two tracks have one name and lie 140 metres apart.",
        "state": "open",
        "decided_by": None,
        "decided_at": None,
        "note": None,
    }
    assert set(given) <= set(row)
    row.update(given)
    return row


def of_a_field(**given: object) -> dict[str, object]:
    """A doubt about what the first source says of a field, as a row, but for what is given."""
    return a_pair(
        **{
            "kind": "sources disagree",
            "other_record_id": None,
            "field": "length_in_metres",
            "source_id": 1,
            "source_address": "https://federation.example/tracks/7",
            "source_value": "1750",
            "reason": "The record says 1600.",
            **given,
        }
    )


def write(store: Engine, row: dict[str, object]) -> None:
    """Write an item past the model, as plain SQL."""
    with store.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (*row.values(), MOMENT, MOMENT))


def held(store: Engine) -> list[tuple[object, ...]]:
    """What the table holds, as SQLite holds it, by the key, without the two times."""
    with store.connect() as connection:
        return [tuple(row) for row in connection.exec_driver_sql(WHAT_IT_HOLDS)]


@pytest.fixture
def queue(newest: Engine) -> Engine:
    """The newest store with two sources, and no item yet."""
    with unit_of_work(newest) as work:
        for name in ("Example Federation", "Example Club"):
            work.add(
                Source(
                    name=name,
                    website="https://federation.example",
                    category=SourceCategory.GOVERNING_BODY,
                    collection_method=CollectionMethod.RSS,
                )
            )
            # One at a time, so that the keys follow the order above.
            work.flush()
    return newest


def test_in_the_file_the_review_queue_has_its_two_indexes_of_one_doubt(newest: Engine) -> None:
    with newest.connect() as connection:
        listed = sorted(
            (name, bool(unique), made_by, bool(partial))
            for _, name, unique, made_by, partial in connection.exec_driver_sql(
                "PRAGMA index_list(review_item)"
            )
        )
        indexed = {
            index: [
                name for _, _, name in connection.exec_driver_sql(f"PRAGMA index_info({index})")
            ]
            for index in (OF_A_PAIR, OF_WHAT_A_SOURCE_SAYS)
        }
        written = {
            str(name): " ".join(str(sql).split())
            for name, sql in connection.exec_driver_sql(
                "SELECT name, sql FROM sqlite_master WHERE type = 'index' "
                "AND tbl_name = 'review_item'"
            )
        }

    # Its name, that no two rows can be alike in it, that a statement made
    # it, and that it is over some of the rows only. The index of the
    # source is as it was.
    assert listed == [
        (OF_WHAT_A_SOURCE_SAYS, True, "c", True),
        (OF_A_PAIR, True, "c", True),
        (OF_A_SOURCE, False, "c", False),
    ]
    assert indexed == {
        OF_A_PAIR: ["record_table", "record_id", "other_record_id"],
        OF_WHAT_A_SOURCE_SAYS: ["record_table", "record_id", "field", "source_id", "source_value"],
    }
    # Which rows each is over, letter for letter: those that name another
    # record, and those that name a field.
    assert written[OF_A_PAIR] == (
        f"CREATE UNIQUE INDEX {OF_A_PAIR} ON review_item "
        "(record_table, record_id, other_record_id) WHERE other_record_id IS NOT NULL"
    )
    assert written[OF_WHAT_A_SOURCE_SAYS] == (
        f"CREATE UNIQUE INDEX {OF_WHAT_A_SOURCE_SAYS} ON review_item "
        "(record_table, record_id, field, source_id, source_value) WHERE field IS NOT NULL"
    )


@IN_EACH_STATE
def test_the_same_possible_duplicate_is_refused_a_second_time(newest: Engine, state: str) -> None:
    # Whatever became of the first: a doubt that a person has decided is
    # not put to them again.
    first = a_pair(**STATES[state])
    write(newest, first)

    with refused(THE_PAIR_IS_THERE):
        write(newest, a_pair(reason="Found again by the next run.", note="Seen twice."))

    assert held(newest) == [tuple(first.values())]


@IN_EACH_STATE
@pytest.mark.parametrize("again", OF_A_FIELD)
@pytest.mark.parametrize("kind", OF_A_FIELD)
def test_the_same_doubt_about_a_field_is_refused_a_second_time(
    queue: Engine, kind: str, again: str, state: str
) -> None:
    # The same record and field, and the same source saying the same thing
    # of it. Whether that thing is another value or one the rules refuse
    # does not make it another doubt, nor does the address at which the
    # source says it, nor what became of the first.
    first = of_a_field(kind=kind, **STATES[state])
    write(queue, first)

    with refused(WHAT_THE_SOURCE_SAYS_IS_THERE):
        write(
            queue,
            of_a_field(
                kind=again,
                source_address="https://federation.example/venues/7",
                reason="Found again by the next run.",
            ),
        )

    assert held(queue) == [tuple(first.values())]


@pytest.mark.parametrize(
    "first",
    [
        ReviewItem(
            kind=ReviewKind.POSSIBLE_DUPLICATE,
            record_table="track",
            record_id=7,
            other_record_id=12,
            reason="They have one name.",
        ),
        ReviewItem(
            kind=ReviewKind.SOURCES_DISAGREE,
            record_table="track",
            record_id=7,
            field="length_in_metres",
            source_id=1,
            source_address="https://federation.example/tracks/7",
            source_value="1750",
            reason="The record says 1600.",
        ),
    ],
    ids=["a possible duplicate", "a doubt about a field"],
)
def test_the_same_doubt_is_refused_through_the_model_and_nothing_of_its_work_is_kept(
    queue: Engine, first: ReviewItem
) -> None:
    said = {
        column.key: getattr(first, column.key)
        for column in ReviewItem.__table__.columns
        if column.key not in {"id", "state", "created_at", "updated_at"}
    }
    with unit_of_work(queue) as work:
        work.add(ReviewItem(**said))
    stored = held(queue)

    def another_doubt_and_then_the_same() -> None:
        # Another doubt, stored in the same unit of work before the one
        # that is refused: it goes with it.
        with unit_of_work(queue) as work:
            work.add(ReviewItem(**{**said, "record_id": 3}))
            work.flush()
            work.add(ReviewItem(**said))

    with pytest.raises(IntegrityError, match="UNIQUE constraint failed: review_item"):
        another_doubt_and_then_the_same()

    assert len(stored) == 1
    assert held(queue) == stored


@pytest.mark.parametrize(
    "other",
    [
        {"record_table": "rider"},
        {"record_id": 8},
        {"other_record_id": 13},
        # The other record of the first pair, with a third record.
        {"record_id": 12, "other_record_id": 15},
    ],
    ids=["of another table", "another record", "with another record", "the other with a third"],
)
def test_a_possible_duplicate_of_other_records_is_another_doubt(
    newest: Engine, other: dict[str, object]
) -> None:
    write(newest, a_pair())

    write(newest, a_pair(**other))

    assert held(newest) == [tuple(a_pair().values()), tuple(a_pair(**other).values())]


@pytest.mark.parametrize(
    "other",
    [
        {"record_table": "event"},
        {"record_id": 8},
        {"field": "name"},
        {"source_id": 2},
        {"source_value": "1751"},
        {"source_value": ""},
        {"source_value": "1750 "},
        {"source_value": "1750.0"},
    ],
    ids=[
        "of another table",
        "of another record",
        "about another field",
        "from another source",
        "another value",
        "empty text",
        "a space after the value",
        "the number written otherwise",
    ],
)
def test_a_doubt_that_differs_in_one_thing_is_another_doubt(
    queue: Engine, other: dict[str, object]
) -> None:
    # What a source says is compared as the text it is, letter for letter.
    write(queue, of_a_field())

    write(queue, of_a_field(**other))

    assert held(queue) == [tuple(of_a_field().values()), tuple(of_a_field(**other).values())]


def test_a_possible_duplicate_and_a_doubt_about_a_field_of_one_record_are_two_doubts(
    queue: Engine,
) -> None:
    # Each index is over the items of its own shape only: an item that
    # names no other record is not in the first, and one that names no
    # field is not in the second, so neither stands in the other's way.
    write(queue, a_pair())
    write(queue, of_a_field())
    write(queue, a_pair(record_id=8))
    write(queue, of_a_field(record_id=8))

    assert len(held(queue)) == 4


# How the store's code will ask whether a doubt is there already, written
# with the model, each with what SQLite says of how it answers, with the
# indexes and without them.
IS_IT_THERE: dict[str, tuple[Callable[[Session], Any], str, str]] = {
    "a possible duplicate": (
        lambda work: work.scalars(
            select(ReviewItem).where(
                ReviewItem.record_table == "track",
                ReviewItem.record_id == 7,
                ReviewItem.other_record_id == 12,
            )
        ).one(),
        f"SEARCH review_item USING INDEX {OF_A_PAIR} "
        "(record_table=? AND record_id=? AND other_record_id=?)",
        "SCAN review_item",
    ),
    "a doubt about a field": (
        lambda work: work.scalars(
            select(ReviewItem).where(
                ReviewItem.record_table == "track",
                ReviewItem.record_id == 7,
                ReviewItem.field == "length_in_metres",
                ReviewItem.source_id == 1,
                ReviewItem.source_value == "1750",
            )
        ).one(),
        f"SEARCH review_item USING INDEX {OF_WHAT_A_SOURCE_SAYS} "
        "(record_table=? AND record_id=? AND field=? AND source_id=? AND source_value=?)",
        # Without its own index SQLite goes by the source, and reads every
        # item that names it.
        f"SEARCH review_item USING INDEX {OF_A_SOURCE} (source_id=?)",
    ),
}
EACH_DOUBT = pytest.mark.parametrize("doubt", list(IS_IT_THERE))


def sent_by(store: Engine, ask: Callable[[Session], Any]) -> list[tuple[str, Sequence[object]]]:
    """Every statement a question sends, with what it is given."""
    sent: list[tuple[str, Sequence[object]]] = []

    def remember(
        _connection: Connection,
        _cursor: object,
        statement: str,
        given: Sequence[object],
        _context: object,
        _many: bool,
    ) -> None:
        sent.append((statement, given))

    event.listen(store, "before_cursor_execute", remember)
    try:
        with Session(store) as work:
            ask(work)
    finally:
        event.remove(store, "before_cursor_execute", remember)
    return sent


def plan_of(store: Engine, statement: str, given: Sequence[object]) -> list[str]:
    """SQLite's own account of how it will answer a statement, step by step."""
    with store.connect() as connection:
        steps = connection.exec_driver_sql("EXPLAIN QUERY PLAN " + statement, tuple(given))
        return [str(step[3]) for step in steps]


@pytest.fixture
def doubts(queue: Engine) -> Engine:
    """The queue with a possible duplicate and a doubt about a field, and others around them."""
    for row in (
        a_pair(),
        of_a_field(),
        a_pair(record_id=8),
        of_a_field(record_id=8),
        of_a_field(source_value="1800"),
    ):
        write(queue, row)
    return queue


@EACH_DOUBT
def test_sqlite_finds_a_doubt_that_is_there_by_its_index(doubts: Engine, doubt: str) -> None:
    # The statement names no kind: that it asks for another record, or for
    # a field, is enough for SQLite to know that the index holds every row
    # that can answer it.
    ask, by_the_index, _ = IS_IT_THERE[doubt]

    ((statement, given),) = sent_by(doubts, ask)

    assert "FROM review_item" in statement
    assert plan_of(doubts, statement, given) == [by_the_index]


@EACH_DOUBT
def test_without_the_indexes_a_doubt_is_looked_for_among_all_items_or_all_of_its_source(
    doubts: Engine, doubt: str
) -> None:
    ask, _, without = IS_IT_THERE[doubt]
    ((statement, given),) = sent_by(doubts, ask)
    with doubts.begin() as connection:
        connection.exec_driver_sql(f"DROP INDEX {OF_A_PAIR}")
        connection.exec_driver_sql(f"DROP INDEX {OF_WHAT_A_SOURCE_SAYS}")

    assert plan_of(doubts, statement, given) == [without]


def test_the_indexes_change_no_answer(doubts: Engine) -> None:
    def answers() -> list[tuple[str, int]]:
        with unit_of_work(doubts) as work:
            return [(found.kind.value, found.id) for found in (a(work) for a, _, _ in asked)]

    asked = list(IS_IT_THERE.values())
    with_them = answers()
    with doubts.begin() as connection:
        connection.exec_driver_sql(f"DROP INDEX {OF_A_PAIR}")
        connection.exec_driver_sql(f"DROP INDEX {OF_WHAT_A_SOURCE_SAYS}")

    assert answers() == with_them
    assert with_them == [("possible duplicate", 1), ("sources disagree", 2)]
