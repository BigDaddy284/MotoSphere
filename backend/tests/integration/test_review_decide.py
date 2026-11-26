"""Tests of the function that decides a review item, against a real SQLite file.

The store of every test is built by the migrations, as a real store is,
so an item is a row of the real table of the review queue. The table
names the record an item is about by the name of its table and its key
and holds neither to a row that exists, so the tests need no table of
records. What the store holds afterwards is read with plain SQL, past
the models.
"""

import re
import sqlite3
from collections.abc import Callable, Sequence
from contextlib import closing
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from motosphere.db import times
from motosphere.db.models import ReviewItem, Source
from motosphere.db.models.review_item import ReviewKind, ReviewState
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.review import decide
from motosphere.db.work import unit_of_work

ACCEPTED = ReviewState.ACCEPTED
REJECTED = ReviewState.REJECTED
DECISIONS = [ACCEPTED, REJECTED]
NOTE_BEFORE = "Seen on the map."
NOT_STORED = "Only an item that is stored, and that this unit of work read or stored, is decided."
DECIDED_ALREADY = "The review item {} was {} already, and a decision is kept."
NO_DECISION = "To decide an item is to accept it or to reject it."
CHECK = "CHECK constraint failed: ck_review_item_"
# What a decision changes of an item, and nothing else.
OF_A_DECISION = {"state", "decided_by", "decided_at", "updated_at"}
# The other decision on the first item, written past the model.
THE_OTHER_DECISION_PAST_THE_MODEL = (
    "UPDATE review_item SET state = 'rejected', decided_by = 'Sam Example', "
    "decided_at = '2026-11-26T09:00:00.000000+00:00', "
    "updated_at = '2026-11-26T09:00:00.000000+00:00' WHERE id = 1 AND state = 'open'"
)


def a_duplicate(record: int, other: int) -> ReviewItem:
    """An open item that two venues may be one, not yet stored."""
    return ReviewItem(
        kind=ReviewKind.POSSIBLE_DUPLICATE,
        record_table="venue",
        record_id=record,
        other_record_id=other,
        reason="The same name, 40 metres apart.",
    )


@pytest.fixture
def made(newest: Engine) -> Engine:
    """The newest store with a source and two open items.

    Item 1 is a possible duplicate. Item 2 is a doubt about a field, and
    it has a note already.
    """
    with unit_of_work(newest) as work:
        work.add(
            Source(
                name="Example Federation",
                website="https://federation.example",
                category=SourceCategory.GOVERNING_BODY,
                collection_method=CollectionMethod.HTML,
            )
        )
        work.flush()
        for item in (
            a_duplicate(1, 2),
            ReviewItem(
                kind=ReviewKind.SOURCES_DISAGREE,
                record_table="venue",
                record_id=1,
                field="length_in_metres",
                source_id=1,
                source_address="https://federation.example/tracks/7",
                source_value="1750",
                reason="The record says 1600.",
                note=NOTE_BEFORE,
            ),
        ):
            work.add(item)
            # One at a time, so that the keys follow the order above.
            work.flush()
    return newest


def items(store: Engine) -> list[dict[str, object]]:
    """Every column of every item, as SQLite holds it, by the key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id").mappings()
        return [dict(row) for row in found]


def rows_of(store: Engine, statement: str) -> list[tuple[object, ...]]:
    """What a plain statement finds in the file."""
    with store.connect() as connection:
        return [tuple(row) for row in connection.exec_driver_sql(statement)]


def changed(before: dict[str, object], after: dict[str, object]) -> set[str]:
    """The columns of an item that hold something else afterwards."""
    assert list(before) == list(after)
    return {column for column in before if after[column] != before[column]}


def decided(store: Engine, key: int, decision: Any, **given: Any) -> None:
    """Decide an item in a unit of work of its own, by Jo Example but for what is given."""
    said: dict[str, Any] = {"by": "Jo Example"}
    said.update(given)
    with unit_of_work(store) as work:
        decide(work, work.get_one(ReviewItem, key), decision, **said)


@pytest.mark.parametrize("key", [1, 2], ids=["a possible duplicate", "a doubt about a field"])
@pytest.mark.parametrize("decision", DECISIONS)
def test_deciding_an_open_item_stores_how_by_whom_and_when(
    made: Engine, clock: list[datetime], decision: ReviewState, key: int
) -> None:
    before = items(made)

    with unit_of_work(made) as work:
        item = work.get_one(ReviewItem, key)
        decide(work, item, decision, by="Jo Example")
        said = (item.state, item.decided_by, item.decided_at, item.updated_at, item.note)

    after = items(made)
    mine, other = key - 1, 2 - key
    # One reading of the clock: the moment of the decision is the moment
    # the item was last changed. When it was first stored stays.
    assert len(clock) == 1
    moment = times.to_text(clock[0])
    assert changed(before[mine], after[mine]) == OF_A_DECISION
    assert [after[mine][column] for column in sorted(OF_A_DECISION)] == [
        moment,
        "Jo Example",
        str(decision),
        moment,
    ]
    # The other item is as it was, and the item given says what was stored.
    assert after[other] == before[other]
    assert len(after) == 2
    assert said == (decision, "Jo Example", clock[0], clock[0], before[mine]["note"])


@pytest.mark.parametrize(
    ("key", "note", "kept", "written"),
    [
        (1, None, None, False),
        (2, None, NOTE_BEFORE, False),
        (1, "Two gates of one track.", "Two gates of one track.", True),
        (2, "Measured again: 1750.", "Measured again: 1750.", True),
        (2, NOTE_BEFORE, NOTE_BEFORE, False),
        (1, "  Two gates.\n", "  Two gates.\n", True),
    ],
    ids=[
        "no note, and none before",
        "no note, and one before",
        "a note, and none before",
        "a note, and one before",
        "the note it has",
        "a note with white space around",
    ],
)
def test_a_note_is_kept_with_the_decision_and_without_one_the_note_stays(
    made: Engine, key: int, note: str | None, kept: str | None, written: bool
) -> None:
    before = items(made)

    decided(made, key, ACCEPTED, note=note)

    after = items(made)
    assert after[key - 1]["note"] == kept
    assert changed(before[key - 1], after[key - 1]) == OF_A_DECISION | (
        {"note"} if written else set()
    )
    assert after[2 - key] == before[2 - key]


@pytest.mark.parametrize(
    "name",
    ["  Jo Example ", "jo example", "Zo\N{LATIN SMALL LETTER E WITH DIAERESIS} Example"],
    ids=["white space around", "small letters", "beyond ASCII"],
)
def test_the_name_of_who_decided_is_kept_as_it_was_given(made: Engine, name: str) -> None:
    decided(made, 1, REJECTED, by=name)

    assert rows_of(made, "SELECT decided_by, typeof(decided_by) FROM review_item WHERE id = 1") == [
        (name, "text")
    ]


@pytest.mark.parametrize("given", [ACCEPTED, REJECTED, ReviewState.OPEN])
@pytest.mark.parametrize("was", DECISIONS)
def test_an_item_that_was_decided_is_refused_and_stays_as_it_was(
    made: Engine, clock: list[datetime], was: ReviewState, given: ReviewState
) -> None:
    decided(made, 1, was, note="Checked on the map.")
    before = items(made)
    read = len(clock)

    with unit_of_work(made) as work:
        item = work.get_one(ReviewItem, 1)

        with pytest.raises(ValueError, match=r"^The review item 1 was") as refusal:
            decide(work, item, given, by="Sam Example", note="Looked again.")

    # A decision is kept: not the same again, not the other, and not
    # taken back. Not one column is another, and the clock was not asked.
    assert str(refusal.value) == DECIDED_ALREADY.format(1, str(was))
    assert items(made) == before
    assert len(clock) == read


def test_an_item_is_decided_once_in_one_unit_of_work_too(
    made: Engine, clock: list[datetime]
) -> None:
    with unit_of_work(made) as work:
        item = work.get_one(ReviewItem, 2)
        decide(work, item, ACCEPTED, by="Jo Example")

        with pytest.raises(ValueError, match=r"^The review item 2 was") as refusal:
            decide(work, item, REJECTED, by="Sam Example")

    assert str(refusal.value) == DECIDED_ALREADY.format(2, "accepted")
    # The first decision is the one that is kept.
    assert rows_of(made, "SELECT state, decided_by FROM review_item ORDER BY id") == [
        ("open", None),
        ("accepted", "Jo Example"),
    ]
    assert len(clock) == 1


@pytest.mark.parametrize(
    "no_decision",
    [ReviewState.OPEN, "accepted", "rejected", None, ReviewKind.SOURCES_DISAGREE, True],
    ids=["open", "text like accepted", "text like rejected", "nothing", "of another list", "yes"],
)
def test_what_is_no_decision_is_refused(
    made: Engine, clock: list[datetime], no_decision: Any
) -> None:
    before = items(made)

    with unit_of_work(made) as work:
        item = work.get_one(ReviewItem, 1)

        with pytest.raises(ValueError, match=r"^To decide an item") as refusal:
            decide(work, item, no_decision, by="Jo Example")

    assert str(refusal.value) == NO_DECISION
    assert items(made) == before
    assert len(clock) == 0


def new(_work: Session) -> ReviewItem:
    """An item that was never given to a unit of work."""
    return a_duplicate(3, 4)


def added(work: Session) -> ReviewItem:
    """An item that was given to this unit of work and is not written yet."""
    item = a_duplicate(3, 4)
    work.add(item)
    return item


def deleted(work: Session) -> ReviewItem:
    """An item that this unit of work has deleted."""
    item = work.get_one(ReviewItem, 2)
    work.delete(item)
    work.flush()
    return item


def of_a_unit_that_has_ended(work: Session) -> ReviewItem:
    """A stored item that a unit of work read which has ended."""
    with unit_of_work(work.get_bind().engine) as earlier:
        return earlier.get_one(ReviewItem, 2)


@pytest.mark.parametrize("not_stored", [new, added, deleted, of_a_unit_that_has_ended])
def test_an_item_that_is_not_stored_in_this_unit_of_work_is_refused(
    made: Engine, clock: list[datetime], not_stored: Callable[[Session], ReviewItem]
) -> None:
    before = items(made)

    with unit_of_work(made) as work:
        strange = not_stored(work)
        read = len(clock)

        with pytest.raises(ValueError, match=r"^Only an item that is stored") as refusal:
            decide(work, strange, ACCEPTED, by="Jo Example")

        # Nothing was decided, and the clock was not asked for it.
        assert len(clock) == read

    assert str(refusal.value) == NOT_STORED
    after = items(made)
    assert {item["state"] for item in after} == {"open"}
    assert [item for item in after if item["id"] in (1, 2)] == [
        item for item in before if item["id"] in {found["id"] for found in after}
    ]


def test_an_item_of_another_unit_of_work_that_is_open_is_refused(made: Engine) -> None:
    before = items(made)

    with unit_of_work(made) as elsewhere, unit_of_work(made) as work:
        strange = elsewhere.get_one(ReviewItem, 1)

        with pytest.raises(ValueError, match=r"^Only an item that is stored") as refusal:
            decide(work, strange, ACCEPTED, by="Jo Example")

    # The other unit of work ended well, and wrote no decision either.
    assert str(refusal.value) == NOT_STORED
    assert items(made) == before


def test_an_item_stored_in_the_same_unit_of_work_can_be_decided(made: Engine) -> None:
    with unit_of_work(made) as work:
        item = a_duplicate(3, 4)
        work.add(item)
        work.flush()

        decide(work, item, REJECTED, by="Jo Example")

    assert rows_of(made, "SELECT id, state, decided_by FROM review_item ORDER BY id") == [
        (1, "open", None),
        (2, "open", None),
        (3, "rejected", "Jo Example"),
    ]


@pytest.mark.parametrize(
    ("given", "refused"),
    [
        ({"by": ""}, CHECK + "decided_by_not_empty"),
        ({"by": " \t"}, CHECK + "decided_by_not_empty"),
        ({"by": None}, CHECK + "decided_by_when_decided"),
        ({"note": ""}, CHECK + "note_not_empty"),
        ({"note": " \n"}, CHECK + "note_not_empty"),
    ],
    ids=["no name", "a blank name", "nobody", "an empty note", "a blank note"],
)
def test_what_the_store_refuses_is_refused_at_the_call(
    made: Engine, given: dict[str, Any], refused: str
) -> None:
    before = items(made)
    reached: list[str] = []

    def work_the_store_refuses() -> None:
        with unit_of_work(made) as work:
            work.add(a_duplicate(3, 4))
            decide(work, work.get_one(ReviewItem, 2), ACCEPTED, **{"by": "Jo Example", **given})
            reached.append("after the call")

    with pytest.raises(IntegrityError) as refusal:
        work_the_store_refuses()

    assert str(refusal.value.orig) == refused
    assert reached == []
    # The unit of work failed as a whole: the item is open as it was, and
    # the other item of the unit is not kept.
    assert items(made) == before


def test_the_decision_is_written_to_the_unit_of_work_before_the_function_returns(
    made: Engine,
) -> None:
    before = items(made)

    with unit_of_work(made) as work:
        decide(work, work.get_one(ReviewItem, 1), ACCEPTED, by="Jo Example")

        # The unit of work finds it in the table.
        written = work.connection().exec_driver_sql(
            "SELECT state, decided_by FROM review_item WHERE id = 1"
        )
        assert tuple(written.one()) == ("accepted", "Jo Example")
        # It is not kept yet: another connection finds the item open.
        assert items(made) == before

    assert items(made)[0]["state"] == "accepted"


def test_a_unit_of_work_that_fails_leaves_the_item_open(made: Engine) -> None:
    before = items(made)

    def work_that_fails() -> None:
        with unit_of_work(made) as work:
            decide(work, work.get_one(ReviewItem, 1), ACCEPTED, by="Jo Example")
            raise RuntimeError("The power went.")

    with pytest.raises(RuntimeError, match=r"^The power went\.$"):
        work_that_fails()

    assert items(made) == before


def test_only_the_item_is_touched_and_the_history_gets_no_row(made: Engine) -> None:
    sources = rows_of(made, "SELECT * FROM source")

    decided(made, 2, ACCEPTED)

    # What follows from a decision is not done here: the item says that
    # the field shall hold 1750, and nothing was changed for it.
    assert rows_of(made, "SELECT * FROM source") == sources
    assert len(sources) == 1
    assert rows_of(made, "SELECT count(*) FROM record_change") == [(0,)]
    assert rows_of(made, "SELECT count(*) FROM review_item") == [(2,)]


def sent_by(store: Engine, call: Callable[[], object]) -> list[tuple[str, Sequence[object]]]:
    """Every statement a call sends to the store, with what it is given."""
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
        call()
    finally:
        event.remove(store, "before_cursor_execute", remember)
    return sent


@pytest.mark.parametrize(
    ("note", "columns"),
    [
        (None, ["state", "decided_by", "decided_at", "updated_at"]),
        ("Measured again.", ["state", "decided_by", "decided_at", "note", "updated_at"]),
    ],
    ids=["without a note", "with a note"],
)
def test_the_function_sends_one_statement_that_changes_the_item_by_its_key(
    made: Engine, clock: list[datetime], note: str | None, columns: list[str]
) -> None:
    with unit_of_work(made) as work:
        item = work.get_one(ReviewItem, 2)
        sent = sent_by(made, lambda: decide(work, item, REJECTED, by="Jo Example", note=note))

    # It does not read the item again: the unit of work has read it, and
    # SQLite keeps nothing another connection writes while it is open.
    assert len(sent) == 1
    statement, given = sent[0]
    said = re.fullmatch(r"UPDATE review_item SET (.+) WHERE review_item\.id = \?", statement)
    assert said is not None
    assert re.findall(r"(\w+)=\?", said[1]) == columns
    moment = times.to_text(clock[0])
    expected = ["rejected", "Jo Example", moment, *([note] if note else []), moment, 2]
    assert list(given) == expected


def test_no_other_connection_decides_the_item_before_the_decision_is_written(
    made: Engine,
) -> None:
    # The function decides the item as the unit of work read it. Were
    # another connection able to decide it after that reading, one of the
    # two decisions would be lost. SQLite lets none: it keeps nothing
    # another connection writes while this unit of work, which has read,
    # is open.
    said: list[str] = []

    def decide_from_elsewhere(
        _connection: Connection,
        _cursor: object,
        statement: str,
        _given: Sequence[object],
        _context: object,
        _many: bool,
    ) -> None:
        if not statement.startswith("UPDATE review_item "):
            return
        with closing(sqlite3.connect(str(made.url.database), timeout=0)) as elsewhere:
            said.append(str(elsewhere.execute(THE_OTHER_DECISION_PAST_THE_MODEL).rowcount))
            try:
                elsewhere.commit()
            except sqlite3.OperationalError as refusal:
                said.append(str(refusal))
            else:
                said.append("kept")
            elsewhere.rollback()

    event.listen(made, "before_cursor_execute", decide_from_elsewhere)
    try:
        decided(made, 1, ACCEPTED)
    finally:
        event.remove(made, "before_cursor_execute", decide_from_elsewhere)

    # The other connection found the item open and changed it, and was
    # not let keep that.
    assert said == ["1", "database is locked"]
    assert rows_of(made, "SELECT state, decided_by FROM review_item WHERE id = 1") == [
        ("accepted", "Jo Example")
    ]
