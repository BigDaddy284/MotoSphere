"""Tests of the function that opens a possible duplicate, against a real SQLite file.

The store of every test is built by the migrations, as a real store is,
so an item is written to the real table of the review queue. The records
an item is about are of tables made for the tests: the real schema has
no table of records yet. Their models are kept in a schema of their own
(``PROOF``), so the real schema never sees them. What the store holds
afterwards is read with plain SQL, past the models.
"""

import sqlite3
from collections.abc import Callable, Sequence
from contextlib import closing
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import Connection, Engine, MetaData, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session

from motosphere.db import times
from motosphere.db.base import NAMING, Base
from motosphere.db.models import SCHEMA, CollectionRun, RecordChange, ReviewItem, Source
from motosphere.db.models.provenance import Collected, Confidence, VerificationStatus
from motosphere.db.models.provenance_rule import NOT_COLLECTED
from motosphere.db.models.review_item import ReviewKind, ReviewState
from motosphere.db.models.source import (
    CollectionMethod,
    InformationType,
    SourceCategory,
    SourceOffer,
)
from motosphere.db.review import open_possible_duplicate
from motosphere.db.texts import NotEmpty
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 20, 6, 0, tzinfo=UTC)
DECIDED_AT = "2026-11-26T09:00:00.000000+00:00"
REASON = "The two have one name and lie 140 metres apart."
OF_A_PAIR = "ix_review_item_record_table_record_id_other_record_id"
NOT_STORED = (
    "Only records that are stored, and that this unit of work read or stored, "
    "are put to the review queue."
)
TWO_TABLES = "A possible duplicate is two records of one table: these are of {} and of {}."
NOT_OF_COLLECTED = (
    "The review queue is for doubts about collected records, and the table {} holds none."
)
ITS_OWN = "A record is not its own duplicate."
WHAT_IT_HOLDS = (
    "SELECT kind, record_table, record_id, other_record_id, field, source_id, source_address, "
    "source_value, reason, state, decided_by, decided_at, note FROM review_item ORDER BY id"
)
EVERYTHING_IT_HOLDS = "SELECT * FROM review_item ORDER BY id"
# The same pair as the tests give the function, written past the model.
THE_PAIR_PAST_THE_MODEL = (
    "INSERT INTO review_item (kind, record_table, record_id, other_record_id, reason, state, "
    "created_at, updated_at) VALUES ('possible duplicate', 'proof_venue', 1, 2, "
    "'Written by another connection.', 'open', '2026-11-26T09:00:00.000000+00:00', "
    "'2026-11-26T09:00:00.000000+00:00')"
)

PROOF = MetaData(naming_convention=NAMING)


class Proof(Base):
    """A model of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = PROOF


class ProofOfCollected(Collected):
    """A model of collected records of the tests' own, in the same schema apart."""

    __abstract__ = True
    metadata = PROOF


# A collected record refers to its source, so the schema of the tests knows
# that table too. It is not made from here: the migrations have made it.
SCHEMA.tables["source"].to_metadata(PROOF)


class ProofVenue(Proof):
    """A record of the tests."""

    __tablename__ = "proof_venue"

    name: Mapped[NotEmpty]


class ProofPerson(Proof):
    """A record of a second table, whose keys are the keys of the first."""

    __tablename__ = "proof_person"

    name: Mapped[NotEmpty]


class ProofFinish(ProofOfCollected):
    """A collected record: it says where it came from, as every such record does."""

    __tablename__ = "proof_finish"

    position: Mapped[int]


@pytest.fixture
def made(newest: Engine) -> Engine:
    """The newest store with the tables of the tests, three venues and two persons.

    The venues have the keys 1, 2 and 3 and the persons the keys 1 and 2.
    """
    with newest.begin() as connection:
        PROOF.create_all(connection)
    with unit_of_work(newest) as work:
        for record in (
            ProofVenue(name="Example Park"),
            ProofVenue(name="Example Park MX"),
            ProofVenue(name="Other Park"),
            ProofPerson(name="A. Rider"),
            ProofPerson(name="A Rider"),
        ):
            work.add(record)
            # One at a time, so that the keys follow the order above.
            work.flush()
    return newest


def a_pair(table: str, record: int, other: int, reason: str = REASON) -> tuple[object, ...]:
    """A possible duplicate that nobody has decided, as the table holds it without its times."""
    return (
        "possible duplicate",
        table,
        record,
        other,
        None,
        None,
        None,
        None,
        reason,
        "open",
        None,
        None,
        None,
    )


def held(store: Engine) -> list[tuple[object, ...]]:
    """What the queue holds, as SQLite holds it, by the key, without the key and the times."""
    with store.connect() as connection:
        return [tuple(row) for row in connection.exec_driver_sql(WHAT_IT_HOLDS)]


def everything(store: Engine) -> list[tuple[object, ...]]:
    """Every column of every item, as SQLite holds it, by the key."""
    with store.connect() as connection:
        return [tuple(row) for row in connection.exec_driver_sql(EVERYTHING_IT_HOLDS)]


def rows_of(store: Engine, statement: str) -> list[tuple[object, ...]]:
    """What a plain statement finds in the file."""
    with store.connect() as connection:
        return [tuple(row) for row in connection.exec_driver_sql(statement)]


def opened(store: Engine, record: int, other: int, reason: str = REASON) -> ReviewItem:
    """Open the possible duplicate of two venues in a unit of work of its own."""
    with unit_of_work(store) as work:
        return open_possible_duplicate(
            work, work.get_one(ProofVenue, record), work.get_one(ProofVenue, other), reason=reason
        )


def test_a_possible_duplicate_is_one_open_item_that_names_its_two_records(
    made: Engine, clock: list[datetime]
) -> None:
    asked = len(clock)

    item = opened(made, 1, 2)

    # The name of the table and the two keys are those of the records. It
    # is open, and nothing else is said of it.
    assert held(made) == [a_pair("proof_venue", 1, 2)]
    # One reading of the clock: the item was stored at that moment.
    assert len(clock) == asked + 1
    moment = times.to_text(clock[-1])
    assert rows_of(made, "SELECT id, created_at, updated_at FROM review_item") == [
        (1, moment, moment)
    ]
    assert (item.id, item.kind, item.record_table, item.record_id, item.other_record_id) == (
        1,
        ReviewKind.POSSIBLE_DUPLICATE,
        "proof_venue",
        1,
        2,
    )
    assert (item.reason, item.state, item.decided_by, item.decided_at, item.note) == (
        REASON,
        ReviewState.OPEN,
        None,
        None,
        None,
    )
    assert (item.field, item.source_id, item.source_address, item.source_value) == (
        None,
        None,
        None,
        None,
    )
    assert item.created_at == item.updated_at == clock[-1]


@pytest.mark.parametrize(("record", "other"), [(1, 2), (2, 1), (1, 3), (3, 1), (2, 3), (3, 2)])
def test_the_two_records_can_be_given_in_either_order(
    made: Engine, record: int, other: int
) -> None:
    item = opened(made, record, other)

    # The smaller key is the record and the greater the other, whichever
    # was given first.
    assert held(made) == [a_pair("proof_venue", min(record, other), max(record, other))]
    assert (item.record_id, item.other_record_id) == (min(record, other), max(record, other))


@pytest.mark.parametrize(("record", "other"), [(1, 2), (2, 1)], ids=["as before", "turned"])
def test_the_same_doubt_again_gives_the_item_that_is_there_and_stores_none(
    made: Engine, clock: list[datetime], record: int, other: int
) -> None:
    first = opened(made, 1, 2)
    before = everything(made)
    asked = len(clock)

    again = opened(made, record, other)

    assert again.id == first.id == 1
    # Not one column of the item is another, its times among them, and
    # the clock was not asked.
    assert everything(made) == before
    assert len(before) == 1
    assert len(clock) == asked


@pytest.mark.parametrize(("record", "other"), [(1, 2), (2, 1)], ids=["as before", "turned"])
def test_the_same_doubt_again_in_one_unit_of_work_gives_the_same_item(
    made: Engine, record: int, other: int
) -> None:
    with unit_of_work(made) as work:
        venues = {key: work.get_one(ProofVenue, key) for key in (1, 2)}
        first = open_possible_duplicate(work, venues[1], venues[2], reason=REASON)
        again = open_possible_duplicate(work, venues[record], venues[other], reason=REASON)

        assert again is first

    assert held(made) == [a_pair("proof_venue", 1, 2)]


@pytest.mark.parametrize("reason", ["Found again by the next run.", ""])
def test_the_reason_given_for_a_doubt_that_is_there_is_not_read(made: Engine, reason: str) -> None:
    opened(made, 1, 2)
    before = everything(made)

    again = opened(made, 2, 1, reason)

    # The item keeps the reason it was opened with. A reason that the
    # store would refuse in a new item is not looked at either.
    assert again.reason == REASON
    assert everything(made) == before


@pytest.mark.parametrize("state", ["accepted", "rejected"])
@pytest.mark.parametrize(("record", "other"), [(1, 2), (2, 1)], ids=["as before", "turned"])
def test_a_doubt_that_was_decided_is_given_back_as_it_was_decided(
    made: Engine, clock: list[datetime], state: str, record: int, other: int
) -> None:
    opened(made, 1, 2)
    with made.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE review_item SET state = ?, decided_by = 'Jo Example', decided_at = ?, "
            "note = 'Looked at both on the map.'",
            (state, DECIDED_AT),
        )
    before = everything(made)
    asked = len(clock)

    again = opened(made, record, other, "Found again by the next run.")

    # A question a person has answered is not put to them again: no new
    # item, and the one that is there says what was decided.
    assert (again.id, again.state, again.decided_by, again.note) == (
        1,
        ReviewState(state),
        "Jo Example",
        "Looked at both on the map.",
    )
    assert again.decided_at == datetime(2026, 11, 26, 9, 0, tzinfo=UTC)
    assert again.reason == REASON
    assert everything(made) == before
    assert len(before) == 1
    assert len(clock) == asked


def test_other_records_are_another_doubt(made: Engine) -> None:
    with unit_of_work(made) as work:
        venues = {key: work.get_one(ProofVenue, key) for key in (1, 2, 3)}
        persons = {key: work.get_one(ProofPerson, key) for key in (1, 2)}
        items = [
            open_possible_duplicate(work, venues[1], venues[2], reason=REASON),
            # A pair that has one record of the first, each way.
            open_possible_duplicate(work, venues[3], venues[1], reason="One address."),
            open_possible_duplicate(work, venues[2], venues[3], reason="One owner."),
            # The same two keys in another table.
            open_possible_duplicate(work, persons[1], persons[2], reason="One name."),
        ]

    assert [item.id for item in items] == [1, 2, 3, 4]
    assert held(made) == [
        a_pair("proof_venue", 1, 2),
        a_pair("proof_venue", 1, 3, "One address."),
        a_pair("proof_venue", 2, 3, "One owner."),
        a_pair("proof_person", 1, 2, "One name."),
    ]


def test_the_item_is_written_to_the_unit_of_work_before_the_function_returns(
    made: Engine,
) -> None:
    with unit_of_work(made) as work:
        item = open_possible_duplicate(
            work, work.get_one(ProofVenue, 1), work.get_one(ProofVenue, 2), reason=REASON
        )

        # It has its key, and the unit of work finds it in the table.
        assert item.id == 1
        written = work.connection().exec_driver_sql("SELECT count(*) FROM review_item")
        assert written.scalar_one() == 1
        # It is not kept yet: another connection does not see it.
        assert held(made) == []

    assert held(made) == [a_pair("proof_venue", 1, 2)]


def test_a_unit_of_work_that_fails_leaves_no_item(made: Engine) -> None:
    def work_that_fails() -> None:
        with unit_of_work(made) as work:
            open_possible_duplicate(
                work, work.get_one(ProofVenue, 1), work.get_one(ProofVenue, 2), reason=REASON
            )
            raise RuntimeError("The source went away.")

    with pytest.raises(RuntimeError, match=r"^The source went away\.$"):
        work_that_fails()

    assert held(made) == []


def test_the_records_are_not_touched_and_the_history_gets_no_row(made: Engine) -> None:
    venues = rows_of(made, "SELECT * FROM proof_venue ORDER BY id")

    opened(made, 1, 2)

    assert rows_of(made, "SELECT * FROM proof_venue ORDER BY id") == venues
    assert len(venues) == 3
    assert rows_of(made, "SELECT count(*) FROM record_change") == [(0,)]


def test_a_record_stored_in_the_same_unit_of_work_can_be_given(made: Engine) -> None:
    # What the collecting does when it meets a record that may be one it
    # has: it stores the new one, and puts the two to the queue.
    with unit_of_work(made) as work:
        new = ProofVenue(name="Example Park (old site)")
        work.add(new)
        work.flush()
        open_possible_duplicate(work, new, work.get_one(ProofVenue, 1), reason="One name.")

    assert new.id == 4
    assert held(made) == [a_pair("proof_venue", 1, 4, "One name.")]


def test_collected_records_are_put_to_the_queue(made: Engine) -> None:
    with unit_of_work(made) as work:
        source = Source(
            name="Example Federation",
            website="https://federation.example",
            category=SourceCategory.GOVERNING_BODY,
            collection_method=CollectionMethod.HTML,
        )
        work.add(source)
        work.flush()
        finishes = [
            ProofFinish(
                position=position,
                source_id=source.id,
                source_address="https://federation.example/results/2026/round-1",
                collected_at=COLLECTED,
                published_on=date(2026, 11, 19),
                last_verified_at=COLLECTED,
                extraction_method=CollectionMethod.HTML,
                confidence=Confidence.MEDIUM,
                verification_status=VerificationStatus.OFFICIAL,
            )
            for position in (3, 3)
        ]
        work.add_all(finishes)
        work.flush()
        open_possible_duplicate(work, finishes[1], finishes[0], reason="One rider, one race.")

    assert held(made) == [a_pair("proof_finish", 1, 2, "One rider, one race.")]


def new(_work: Session) -> ProofVenue:
    """A record that was never given to a unit of work."""
    return ProofVenue(name="New Park")


def added(work: Session) -> ProofVenue:
    """A record that was given to this unit of work and is not written yet."""
    record = ProofVenue(name="New Park")
    work.add(record)
    return record


def deleted(work: Session) -> ProofVenue:
    """A record that this unit of work has deleted."""
    record = work.get_one(ProofVenue, 3)
    work.delete(record)
    work.flush()
    return record


def of_a_unit_that_has_ended(work: Session) -> ProofVenue:
    """A stored record that a unit of work read which has ended."""
    with unit_of_work(work.get_bind().engine) as earlier:
        return earlier.get_one(ProofVenue, 3)


def of_a_second_table_and_new(_work: Session) -> ProofPerson:
    """A record of another table that was never given to a unit of work."""
    return ProofPerson(name="New Rider")


@pytest.mark.parametrize("place", ["record", "other"])
@pytest.mark.parametrize(
    "not_stored", [new, added, deleted, of_a_unit_that_has_ended, of_a_second_table_and_new]
)
def test_a_record_that_is_not_stored_in_this_unit_of_work_is_refused(
    made: Engine, not_stored: Callable[[Session], Base], place: str
) -> None:
    with unit_of_work(made) as work:
        stored = work.get_one(ProofVenue, 1)
        strange = not_stored(work)
        pair = (strange, stored) if place == "record" else (stored, strange)

        with pytest.raises(ValueError, match=r"^Only records that are stored") as refusal:
            open_possible_duplicate(work, *pair, reason=REASON)

    assert str(refusal.value) == NOT_STORED
    assert held(made) == []


@pytest.mark.parametrize("place", ["record", "other"])
def test_a_record_of_another_unit_of_work_that_is_open_is_refused(made: Engine, place: str) -> None:
    with unit_of_work(made) as elsewhere, unit_of_work(made) as work:
        stored = work.get_one(ProofVenue, 1)
        strange = elsewhere.get_one(ProofVenue, 2)
        pair = (strange, stored) if place == "record" else (stored, strange)

        with pytest.raises(ValueError, match=r"^Only records that are stored") as refusal:
            open_possible_duplicate(work, *pair, reason=REASON)

    assert str(refusal.value) == NOT_STORED
    assert held(made) == []


@pytest.mark.parametrize("turned", [False, True], ids=["venue first", "person first"])
def test_two_records_of_two_tables_are_refused(made: Engine, turned: bool) -> None:
    # They have the same key, each in its table.
    with unit_of_work(made) as work:
        venue, person = work.get_one(ProofVenue, 1), work.get_one(ProofPerson, 1)
        pair: tuple[Base, Base] = (person, venue) if turned else (venue, person)

        with pytest.raises(ValueError, match=r"^A possible duplicate is two records") as refusal:
            open_possible_duplicate(work, *pair, reason=REASON)

    tables = ("proof_person", "proof_venue") if turned else ("proof_venue", "proof_person")
    assert str(refusal.value) == TWO_TABLES.format(*tables)
    assert held(made) == []


def test_a_record_is_not_its_own_duplicate(made: Engine) -> None:
    with unit_of_work(made) as work:
        venue = work.get_one(ProofVenue, 2)

        with pytest.raises(ValueError, match=r"^A record is not its own duplicate\.$"):
            open_possible_duplicate(work, venue, venue, reason=REASON)

    assert held(made) == []


def two_sources(work: Session) -> list[Base]:
    """Two sources, stored."""
    sources: list[Base] = [
        Source(
            name=name,
            website="https://federation.example",
            category=SourceCategory.GOVERNING_BODY,
            collection_method=CollectionMethod.HTML,
        )
        for name in ("Example Federation", "Example Federation (old)")
    ]
    work.add_all(sources)
    work.flush()
    return sources


def two_offers(work: Session) -> list[Base]:
    """Two things one source offers, stored."""
    source = two_sources(work)[0]
    offers: list[Base] = [
        SourceOffer(source_id=source.id, information_type=one)
        for one in (InformationType.TRACKS, InformationType.EVENTS)
    ]
    work.add_all(offers)
    work.flush()
    return offers


def two_runs(work: Session) -> list[Base]:
    """Two runs of one source, stored."""
    source = two_sources(work)[0]
    runs: list[Base] = [CollectionRun(source_id=source.id, started_at=COLLECTED) for _ in "ab"]
    work.add_all(runs)
    work.flush()
    return runs


def two_changes(work: Session) -> list[Base]:
    """Two rows of the history, stored."""
    changes: list[Base] = [
        RecordChange(
            record_table="proof_venue",
            record_id=1,
            field="name",
            old_value=old,
            new_value="Example Park",
            decided_by="Jo Example",
        )
        for old in ("Example Pk", "Example Pk.")
    ]
    work.add_all(changes)
    work.flush()
    return changes


def two_items(work: Session) -> list[Base]:
    """Two items of the review queue, stored."""
    venues = [work.get_one(ProofVenue, key) for key in (1, 2, 3)]
    return [open_possible_duplicate(work, venues[0], other, reason=REASON) for other in venues[1:]]


# Two stored rows of every table that holds no collected records. A table
# that is put on that list gets its two rows here.
TWO_OF: dict[str, Callable[[Session], list[Base]]] = {
    "collection_run": two_runs,
    "record_change": two_changes,
    "review_item": two_items,
    "source": two_sources,
    "source_offer": two_offers,
}


@pytest.mark.parametrize("table", sorted(NOT_COLLECTED))
@pytest.mark.parametrize("twice", [False, True], ids=["two rows", "one row twice"])
def test_rows_of_a_table_that_holds_no_collected_records_are_refused(
    made: Engine, table: str, twice: bool
) -> None:
    with unit_of_work(made) as work:
        first, second = TWO_OF[table](work)
        before = work.connection().exec_driver_sql(WHAT_IT_HOLDS).all()

        with pytest.raises(ValueError, match=r"^The review queue is for doubts") as refusal:
            # Given twice, a row is refused for its table, as any row of it is.
            open_possible_duplicate(work, first, first if twice else second, reason=REASON)

        assert work.connection().exec_driver_sql(WHAT_IT_HOLDS).all() == before

    assert str(refusal.value) == NOT_OF_COLLECTED.format(table)
    assert len(held(made)) == (2 if table == "review_item" else 0)


@pytest.mark.parametrize("reason", ["", "  ", "\t\n"], ids=["empty", "spaces", "tab and line"])
def test_an_empty_reason_is_refused_by_the_store_at_the_call(made: Engine, reason: str) -> None:
    reached: list[str] = []

    def work_with_an_empty_reason() -> None:
        with unit_of_work(made) as work:
            work.add(ProofVenue(name="New Park"))
            open_possible_duplicate(
                work, work.get_one(ProofVenue, 1), work.get_one(ProofVenue, 2), reason=reason
            )
            reached.append("after the call")

    with pytest.raises(IntegrityError) as refusal:
        work_with_an_empty_reason()

    assert str(refusal.value.orig) == "CHECK constraint failed: ck_review_item_reason_not_empty"
    assert reached == []
    # The unit of work failed as a whole: neither the item nor the venue is kept.
    assert held(made) == []
    assert rows_of(made, "SELECT count(*) FROM proof_venue") == [(3,)]


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


def plan_of(store: Engine, statement: str, given: Sequence[object]) -> list[str]:
    """SQLite's own account of how it will answer a statement, step by step."""
    with store.connect() as connection:
        steps = connection.exec_driver_sql("EXPLAIN QUERY PLAN " + statement, tuple(given))
        return [str(step[3]) for step in steps]


@pytest.mark.parametrize("there", [False, True], ids=["a new doubt", "a doubt that is there"])
def test_the_function_looks_for_the_doubt_once_and_by_its_index(made: Engine, there: bool) -> None:
    if there:
        opened(made, 1, 2)
    # More items than SQLite would read through for nothing.
    with unit_of_work(made) as work:
        persons = [work.get_one(ProofPerson, key) for key in (1, 2)]
        open_possible_duplicate(work, *persons, reason="One name.")

    with unit_of_work(made) as work:
        venues = [work.get_one(ProofVenue, key) for key in (2, 1)]
        sent = sent_by(made, lambda: open_possible_duplicate(work, *venues, reason=REASON))

    # One look, and a write only where the doubt is new. The look is given
    # the table and the two keys, the smaller first.
    kinds = [statement.split(None, 2)[0] for statement, _ in sent]
    assert kinds == (["SELECT"] if there else ["SELECT", "INSERT"])
    look, given = sent[0]
    assert tuple(given) == ("proof_venue", 1, 2)
    assert plan_of(made, look, given) == [
        f"SEARCH review_item USING INDEX {OF_A_PAIR} "
        "(record_table=? AND record_id=? AND other_record_id=?)"
    ]
    if not there:
        assert sent[1][0].startswith("INSERT INTO review_item ")


def test_no_other_connection_stores_the_doubt_between_the_look_and_the_write(
    made: Engine,
) -> None:
    # The function looks and then writes. Were another connection able to
    # store the same doubt in between, the write would be refused. SQLite
    # lets none: it keeps nothing another connection writes while this
    # unit of work, which has read, is open.
    said: list[str] = []

    def write_from_elsewhere(
        _connection: Connection,
        _cursor: object,
        statement: str,
        _given: Sequence[object],
        _context: object,
        _many: bool,
    ) -> None:
        if not statement.startswith("INSERT INTO review_item "):
            return
        with closing(sqlite3.connect(str(made.url.database), timeout=0)) as elsewhere:
            elsewhere.execute(THE_PAIR_PAST_THE_MODEL)
            try:
                elsewhere.commit()
            except sqlite3.OperationalError as refusal:
                said.append(str(refusal))
            else:
                said.append("kept")
            elsewhere.rollback()

    event.listen(made, "before_cursor_execute", write_from_elsewhere)
    try:
        opened(made, 1, 2)
    finally:
        event.remove(made, "before_cursor_execute", write_from_elsewhere)

    assert said == ["database is locked"]
    assert held(made) == [a_pair("proof_venue", 1, 2)]
