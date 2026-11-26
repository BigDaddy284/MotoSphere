"""Tests of the function that opens a doubt about a field, against a real SQLite file.

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
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, MetaData, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session

from motosphere.db import review, times
from motosphere.db.base import NAMING, Base
from motosphere.db.models import CollectionRun, RecordChange, ReviewItem, Source
from motosphere.db.models.provenance_rule import NOT_COLLECTED
from motosphere.db.models.review_item import ReviewKind, ReviewState
from motosphere.db.models.source import (
    CollectionMethod,
    InformationType,
    SourceCategory,
    SourceOffer,
)
from motosphere.db.review import open_field_doubt, open_possible_duplicate
from motosphere.db.texts import NotEmpty
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 20, 6, 0, tzinfo=UTC)
DECIDED_AT = "2026-11-26T09:00:00.000000+00:00"
ADDRESS = "https://federation.example/tracks/7"
ELSEWHERE = "https://federation.example/tracks/7/print"
SAYS = "1750"
REASON = "The record says 1600."
OF_WHAT_A_SOURCE_SAYS = "ix_review_item_record_table_record_id_field_source_id_source_value"
NOT_STORED = (
    "Only records that are stored, and that this unit of work read or stored, "
    "are put to the review queue."
)
NOT_OF_COLLECTED = (
    "The review queue is for doubts about collected records, and the table {} holds none."
)
NOT_A_FIELD_DOUBT = (
    "A possible duplicate is two records and no field: it is opened with open_possible_duplicate."
)
THE_STORES_OWN = "The column {} is the store's own in every table: no source says what it holds."
NO_COLUMN = "The table proof_venue has no column {}."
NOT_TEXT = "What a source says is given as the text it said, which {} is not."
CHECK = "CHECK constraint failed: ck_review_item_"
WHAT_IT_HOLDS = (
    "SELECT kind, record_table, record_id, other_record_id, field, source_id, source_address, "
    "source_value, reason, state, decided_by, decided_at, note FROM review_item ORDER BY id"
)
EVERYTHING_IT_HOLDS = "SELECT * FROM review_item ORDER BY id"
# The same doubt as the tests give the function, written past the model.
THE_DOUBT_PAST_THE_MODEL = (
    "INSERT INTO review_item (kind, record_table, record_id, field, source_id, source_address, "
    "source_value, reason, state, created_at, updated_at) VALUES ('sources disagree', "
    "'proof_venue', 1, 'length_in_metres', 1, 'https://federation.example/tracks/7', '1750', "
    "'Written by another connection.', 'open', '2026-11-26T09:00:00.000000+00:00', "
    "'2026-11-26T09:00:00.000000+00:00')"
)
OF_A_FIELD = [ReviewKind.SOURCES_DISAGREE, ReviewKind.VALUE_OUTSIDE_ITS_RULES]

PROOF = MetaData(naming_convention=NAMING)


class Proof(Base):
    """A model of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = PROOF


class ProofVenue(Proof):
    """A record of the tests."""

    __tablename__ = "proof_venue"

    name: Mapped[NotEmpty]
    length_in_metres: Mapped[int | None]


class ProofPerson(Proof):
    """A record of a second table, whose keys are the keys of the first."""

    __tablename__ = "proof_person"

    name: Mapped[NotEmpty]


def a_source(name: str) -> Source:
    """A source of this name, not yet stored."""
    return Source(
        name=name,
        website="https://federation.example",
        category=SourceCategory.GOVERNING_BODY,
        collection_method=CollectionMethod.HTML,
    )


@pytest.fixture
def made(newest: Engine) -> Engine:
    """The newest store with the tables of the tests, two sources, two venues and a person.

    The sources have the keys 1 and 2, the venues the keys 1 and 2, and
    the person the key 1.
    """
    with newest.begin() as connection:
        PROOF.create_all(connection)
    with unit_of_work(newest) as work:
        for record in (
            a_source("Example Federation"),
            a_source("Example Club"),
            ProofVenue(name="Example Park", length_in_metres=1600),
            ProofVenue(name="Other Park", length_in_metres=1600),
            ProofPerson(name="A. Rider"),
        ):
            work.add(record)
            # One at a time, so that the keys follow the order above.
            work.flush()
    return newest


def a_doubt(**given: object) -> tuple[object, ...]:
    """A doubt about a field that nobody has decided, as the table holds it without its times."""
    row: dict[str, object] = {
        "kind": "sources disagree",
        "record_table": "proof_venue",
        "record_id": 1,
        "other_record_id": None,
        "field": "length_in_metres",
        "source_id": 1,
        "source_address": ADDRESS,
        "source_value": SAYS,
        "reason": REASON,
        "state": "open",
        "decided_by": None,
        "decided_at": None,
        "note": None,
    }
    assert set(given) <= set(row)
    row.update(given)
    return tuple(row.values())


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


def asked(work: Session, record: Base, **given: Any) -> ReviewItem:
    """Open the doubt of the tests about a record, but for what is given."""
    said: dict[str, Any] = {
        "field": "length_in_metres",
        "kind": ReviewKind.SOURCES_DISAGREE,
        "source": 1,
        "address": ADDRESS,
        "says": SAYS,
        "reason": REASON,
    }
    assert set(given) <= set(said)
    said.update(given)
    return open_field_doubt(work, record, said.pop("field"), **said)


def opened(store: Engine, venue: int = 1, **given: Any) -> ReviewItem:
    """Open the doubt of the tests about a venue in a unit of work of its own."""
    with unit_of_work(store) as work:
        return asked(work, work.get_one(ProofVenue, venue), **given)


def test_the_module_gives_its_two_functions_by_name() -> None:
    assert review.__all__ == ["open_field_doubt", "open_possible_duplicate"]


@pytest.mark.parametrize("kind", OF_A_FIELD)
def test_a_doubt_about_a_field_is_one_open_item_that_names_what_the_source_says(
    made: Engine, clock: list[datetime], kind: ReviewKind
) -> None:
    before = len(clock)

    item = opened(made, kind=kind)

    # The name of the table and the key are those of the record. It is
    # open, and nothing else is said of it.
    assert held(made) == [a_doubt(kind=str(kind))]
    # One reading of the clock: the item was stored at that moment.
    assert len(clock) == before + 1
    moment = times.to_text(clock[-1])
    assert rows_of(made, "SELECT id, created_at, updated_at FROM review_item") == [
        (1, moment, moment)
    ]
    assert (item.id, item.kind, item.record_table, item.record_id, item.other_record_id) == (
        1,
        kind,
        "proof_venue",
        1,
        None,
    )
    assert (item.field, item.source_id, item.source_address, item.source_value) == (
        "length_in_metres",
        1,
        ADDRESS,
        SAYS,
    )
    assert (item.reason, item.state, item.decided_by, item.decided_at, item.note) == (
        REASON,
        ReviewState.OPEN,
        None,
        None,
        None,
    )
    assert item.created_at == item.updated_at == clock[-1]


def test_the_same_doubt_again_gives_the_item_that_is_there_and_stores_none(
    made: Engine, clock: list[datetime]
) -> None:
    first = opened(made)
    before = everything(made)
    read = len(clock)

    again = opened(made)

    assert again.id == first.id == 1
    # Not one column of the item is another, its times among them, and
    # the clock was not asked.
    assert everything(made) == before
    assert len(before) == 1
    assert len(clock) == read


def test_the_same_doubt_again_in_one_unit_of_work_gives_the_same_item(made: Engine) -> None:
    with unit_of_work(made) as work:
        venue = work.get_one(ProofVenue, 1)
        first = asked(work, venue)
        again = asked(work, venue)

        assert again is first

    assert held(made) == [a_doubt()]


@pytest.mark.parametrize(
    "otherwise",
    [
        {"kind": ReviewKind.VALUE_OUTSIDE_ITS_RULES},
        {"address": ELSEWHERE},
        {"reason": "Found again by the next run."},
        {"address": "not an address"},
        {"reason": ""},
    ],
    ids=["the other kind", "another address", "another reason", "no address", "no reason"],
)
def test_what_else_is_given_for_a_doubt_that_is_there_is_not_read(
    made: Engine, otherwise: dict[str, Any]
) -> None:
    opened(made)
    before = everything(made)

    again = opened(made, **otherwise)

    # The same source says the same thing of the same field of the same
    # record: it is the doubt that is there. The item keeps its kind, its
    # address and its reason, and what the store would refuse in a new
    # item is not looked at either.
    assert (again.id, again.kind, again.source_address, again.reason) == (
        1,
        ReviewKind.SOURCES_DISAGREE,
        ADDRESS,
        REASON,
    )
    assert everything(made) == before


@pytest.mark.parametrize("state", ["accepted", "rejected"])
def test_a_doubt_that_was_decided_is_given_back_as_it_was_decided(
    made: Engine, clock: list[datetime], state: str
) -> None:
    opened(made)
    with made.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE review_item SET state = ?, decided_by = 'Jo Example', decided_at = ?, "
            "note = 'Measured on the map.'",
            (state, DECIDED_AT),
        )
    before = everything(made)
    read = len(clock)

    again = opened(made, reason="Found again by the next run.")

    # A question a person has answered is not put to them again: no new
    # item, and the one that is there says what was decided.
    assert (again.id, again.state, again.decided_by, again.note) == (
        1,
        ReviewState(state),
        "Jo Example",
        "Measured on the map.",
    )
    assert again.decided_at == datetime(2026, 11, 26, 9, 0, tzinfo=UTC)
    assert again.reason == REASON
    assert everything(made) == before
    assert len(before) == 1
    assert len(clock) == read


@pytest.mark.parametrize(
    ("otherwise", "stored"),
    [
        ({"field": "name"}, {"field": "name"}),
        ({"source": 2}, {"source_id": 2}),
        ({"says": "1750.0"}, {"source_value": "1750.0"}),
        ({"says": "1750 "}, {"source_value": "1750 "}),
        ({"says": "1 750"}, {"source_value": "1 750"}),
        ({"says": ""}, {"source_value": ""}),
    ],
    ids=[
        "another field",
        "another source",
        "written otherwise",
        "a space after",
        "a space in",
        "empty",
    ],
)
def test_a_doubt_that_differs_in_one_thing_is_another_doubt(
    made: Engine, otherwise: dict[str, Any], stored: dict[str, object]
) -> None:
    first = opened(made)

    second = opened(made, **otherwise)

    # What a source says is compared as the text it is, letter for letter.
    assert (first.id, second.id) == (1, 2)
    assert held(made) == [a_doubt(), a_doubt(**stored)]


def test_the_same_thing_said_of_another_record_is_another_doubt(made: Engine) -> None:
    with unit_of_work(made) as work:
        items = [
            asked(work, work.get_one(ProofVenue, 1), field="name", says="Example Park MX"),
            # Another record of the same table.
            asked(work, work.get_one(ProofVenue, 2), field="name", says="Example Park MX"),
            # The same key and the same field in another table.
            asked(work, work.get_one(ProofPerson, 1), field="name", says="Example Park MX"),
        ]

    assert [item.id for item in items] == [1, 2, 3]
    assert held(made) == [
        a_doubt(field="name", source_value="Example Park MX"),
        a_doubt(field="name", source_value="Example Park MX", record_id=2),
        a_doubt(field="name", source_value="Example Park MX", record_table="proof_person"),
    ]


@pytest.mark.parametrize(
    "says",
    [
        "",
        "  1750\n",
        "<script>alert('1750')</script>",
        "1750'); DROP TABLE review_item; --",
        "1750 \N{EM DASH} measured in 2019",
    ],
    ids=["empty", "white space around", "markup", "a statement of SQL", "beyond ASCII"],
)
def test_what_a_source_says_is_kept_as_the_text_it_was_and_found_again(
    made: Engine, says: str
) -> None:
    first = opened(made, says=says)

    again = opened(made, says=says)

    # It is what a source said and no more: kept letter for letter, as
    # text, and never run. The second asking finds it by that text.
    assert again.id == first.id == 1
    assert rows_of(made, "SELECT source_value, typeof(source_value) FROM review_item") == [
        (says, "text")
    ]
    assert held(made) == [a_doubt(source_value=says)]


def test_the_item_is_written_to_the_unit_of_work_before_the_function_returns(
    made: Engine,
) -> None:
    with unit_of_work(made) as work:
        item = asked(work, work.get_one(ProofVenue, 1))

        # It has its key, and the unit of work finds it in the table.
        assert item.id == 1
        written = work.connection().exec_driver_sql("SELECT count(*) FROM review_item")
        assert written.scalar_one() == 1
        # It is not kept yet: another connection does not see it.
        assert held(made) == []

    assert held(made) == [a_doubt()]


def test_a_unit_of_work_that_fails_leaves_no_item(made: Engine) -> None:
    def work_that_fails() -> None:
        with unit_of_work(made) as work:
            asked(work, work.get_one(ProofVenue, 1))
            raise RuntimeError("The source went away.")

    with pytest.raises(RuntimeError, match=r"^The source went away\.$"):
        work_that_fails()

    assert held(made) == []


def test_the_record_is_not_touched_and_the_history_gets_no_row(made: Engine) -> None:
    venues = rows_of(made, "SELECT * FROM proof_venue ORDER BY id")

    opened(made)

    assert rows_of(made, "SELECT * FROM proof_venue ORDER BY id") == venues
    assert len(venues) == 2
    assert rows_of(made, "SELECT count(*) FROM record_change") == [(0,)]


@pytest.mark.parametrize("kind", OF_A_FIELD)
def test_the_function_does_not_look_at_what_the_record_holds(
    made: Engine, kind: ReviewKind
) -> None:
    # The record holds 1600, and the source is said to say just that. A
    # source says a thing in its own words, so whether it is what the
    # record holds is for the code that collects to say before it calls.
    opened(made, kind=kind, says="1600")

    assert held(made) == [a_doubt(kind=str(kind), source_value="1600")]


def test_a_record_stored_in_the_same_unit_of_work_can_be_given(made: Engine) -> None:
    with unit_of_work(made) as work:
        new = ProofVenue(name="New Park")
        work.add(new)
        work.flush()
        asked(work, new)

    assert new.id == 3
    assert held(made) == [a_doubt(record_id=3)]


def test_a_possible_duplicate_and_a_doubt_about_a_field_of_one_record_are_two_items(
    made: Engine,
) -> None:
    with unit_of_work(made) as work:
        venues = [work.get_one(ProofVenue, key) for key in (1, 2)]
        pair = open_possible_duplicate(work, *venues, reason="One length, one town.")
        doubt = asked(work, venues[0])

    assert (pair.id, doubt.id) == (1, 2)
    assert [row[:5] for row in held(made)] == [
        ("possible duplicate", "proof_venue", 1, 2, None),
        ("sources disagree", "proof_venue", 1, None, "length_in_metres"),
    ]


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
    record = work.get_one(ProofVenue, 2)
    work.delete(record)
    work.flush()
    return record


def of_a_unit_that_has_ended(work: Session) -> ProofVenue:
    """A stored record that a unit of work read which has ended."""
    with unit_of_work(work.get_bind().engine) as earlier:
        return earlier.get_one(ProofVenue, 2)


@pytest.mark.parametrize("not_stored", [new, added, deleted, of_a_unit_that_has_ended])
def test_a_record_that_is_not_stored_in_this_unit_of_work_is_refused(
    made: Engine, not_stored: Callable[[Session], Base]
) -> None:
    with unit_of_work(made) as work:
        strange = not_stored(work)

        with pytest.raises(ValueError, match=r"^Only records that are stored") as refusal:
            asked(work, strange)

    assert str(refusal.value) == NOT_STORED
    assert held(made) == []


def test_a_record_of_another_unit_of_work_that_is_open_is_refused(made: Engine) -> None:
    with unit_of_work(made) as elsewhere, unit_of_work(made) as work:
        strange = elsewhere.get_one(ProofVenue, 1)

        with pytest.raises(ValueError, match=r"^Only records that are stored") as refusal:
            asked(work, strange)

    assert str(refusal.value) == NOT_STORED
    assert held(made) == []


def a_run(work: Session) -> Base:
    """A run of the first source, stored."""
    run = CollectionRun(source_id=1, started_at=COLLECTED)
    work.add(run)
    work.flush()
    return run


def an_offer(work: Session) -> Base:
    """A thing the first source offers, stored."""
    offer = SourceOffer(source_id=1, information_type=InformationType.TRACKS)
    work.add(offer)
    work.flush()
    return offer


def a_change(work: Session) -> Base:
    """A row of the history, stored."""
    change = RecordChange(
        record_table="proof_venue",
        record_id=1,
        field="name",
        old_value="Example Pk",
        new_value="Example Park",
        decided_by="Jo Example",
    )
    work.add(change)
    work.flush()
    return change


def an_item(work: Session) -> Base:
    """An item of the review queue, stored."""
    return asked(work, work.get_one(ProofVenue, 1))


def the_first_source(work: Session) -> Base:
    """The first source."""
    return work.get_one(Source, 1)


# A stored row of every table that holds no collected records. A table
# that is put on that list gets its row here.
ONE_OF: dict[str, Callable[[Session], Base]] = {
    "collection_run": a_run,
    "record_change": a_change,
    "review_item": an_item,
    "source": the_first_source,
    "source_offer": an_offer,
}


@pytest.mark.parametrize("table", sorted(NOT_COLLECTED))
def test_a_row_of_a_table_that_holds_no_collected_records_is_refused(
    made: Engine, table: str
) -> None:
    with unit_of_work(made) as work:
        row = ONE_OF[table](work)
        before = work.connection().exec_driver_sql(WHAT_IT_HOLDS).all()

        with pytest.raises(ValueError, match=r"^The review queue is for doubts") as refusal:
            # Every one of these tables has this column.
            asked(work, row, field="created_at")

        assert work.connection().exec_driver_sql(WHAT_IT_HOLDS).all() == before

    assert str(refusal.value) == NOT_OF_COLLECTED.format(table)
    assert len(held(made)) == (1 if table == "review_item" else 0)


def test_a_possible_duplicate_is_not_opened_as_a_doubt_about_a_field(made: Engine) -> None:
    with unit_of_work(made) as work:
        venue = work.get_one(ProofVenue, 1)

        with pytest.raises(ValueError, match=r"^A possible duplicate is two records") as refusal:
            asked(work, venue, kind=ReviewKind.POSSIBLE_DUPLICATE)

    assert str(refusal.value) == NOT_A_FIELD_DOUBT
    assert held(made) == []


@pytest.mark.parametrize("field", ["id", "created_at", "updated_at"])
def test_the_columns_that_are_the_stores_own_are_no_fields_a_source_says(
    made: Engine, field: str
) -> None:
    with unit_of_work(made) as work:
        venue = work.get_one(ProofVenue, 1)

        with pytest.raises(ValueError, match=r"^The column ") as refusal:
            asked(work, venue, field=field)

    assert str(refusal.value) == THE_STORES_OWN.format(field)
    assert held(made) == []


@pytest.mark.parametrize(
    "field",
    ["lenght_in_metres", "Name", "", "proof_venue.name", "website"],
    ids=["misspelled", "a capital letter", "empty", "with its table", "of no table here"],
)
def test_a_field_its_table_does_not_have_is_refused(made: Engine, field: str) -> None:
    with unit_of_work(made) as work:
        venue = work.get_one(ProofVenue, 1)

        with pytest.raises(ValueError, match=r"^The table proof_venue has no column") as refusal:
            asked(work, venue, field=field)

    assert str(refusal.value) == NO_COLUMN.format(field)
    assert held(made) == []


class Loud(str):
    """Text of a kind of its own, which is not exactly text."""

    __slots__ = ()


@pytest.mark.parametrize(
    "not_text",
    [1750, 1750.0, None, b"1750", True, Loud("1750")],
    ids=["a whole number", "a number", "nothing", "bytes", "yes", "a kind of text"],
)
def test_something_said_that_is_not_text_is_refused(made: Engine, not_text: Any) -> None:
    with unit_of_work(made) as work:
        venue = work.get_one(ProofVenue, 1)

        with pytest.raises(TypeError, match=r"^What a source says is given as the text") as refusal:
            asked(work, venue, says=not_text)

    assert str(refusal.value) == NOT_TEXT.format(repr(not_text))
    assert held(made) == []


@pytest.mark.parametrize(
    ("otherwise", "refused"),
    [
        ({"source": 3}, "FOREIGN KEY constraint failed"),
        ({"address": "federation.example/tracks/7"}, CHECK + "source_address_web_address"),
        ({"address": ""}, CHECK + "source_address_web_address"),
        ({"reason": ""}, CHECK + "reason_not_empty"),
        ({"reason": " \t"}, CHECK + "reason_not_empty"),
    ],
    ids=["no such source", "no web address", "an empty address", "no reason", "a blank reason"],
)
def test_what_the_store_refuses_is_refused_at_the_call(
    made: Engine, otherwise: dict[str, Any], refused: str
) -> None:
    reached: list[str] = []

    def work_the_store_refuses() -> None:
        with unit_of_work(made) as work:
            work.add(ProofVenue(name="New Park"))
            asked(work, work.get_one(ProofVenue, 1), **otherwise)
            reached.append("after the call")

    with pytest.raises(IntegrityError) as refusal:
        work_the_store_refuses()

    assert str(refusal.value.orig) == refused
    assert reached == []
    # The unit of work failed as a whole: neither the item nor the venue is kept.
    assert held(made) == []
    assert rows_of(made, "SELECT count(*) FROM proof_venue") == [(2,)]


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
        opened(made)
    # More items than SQLite would read through for nothing.
    opened(made, 2)
    opened(made, source=2)

    with unit_of_work(made) as work:
        venue = work.get_one(ProofVenue, 1)
        sent = sent_by(made, lambda: asked(work, venue))

    # One look, and a write only where the doubt is new. The look is given
    # the table, the key, the field, the source and what it says, and
    # neither the kind nor the address.
    kinds = [statement.split(None, 2)[0] for statement, _ in sent]
    assert kinds == (["SELECT"] if there else ["SELECT", "INSERT"])
    look, given = sent[0]
    assert tuple(given) == ("proof_venue", 1, "length_in_metres", 1, SAYS)
    assert plan_of(made, look, given) == [
        f"SEARCH review_item USING INDEX {OF_WHAT_A_SOURCE_SAYS} "
        "(record_table=? AND record_id=? AND field=? AND source_id=? AND source_value=?)"
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
            elsewhere.execute(THE_DOUBT_PAST_THE_MODEL)
            try:
                elsewhere.commit()
            except sqlite3.OperationalError as refusal:
                said.append(str(refusal))
            else:
                said.append("kept")
            elsewhere.rollback()

    event.listen(made, "before_cursor_execute", write_from_elsewhere)
    try:
        opened(made)
    finally:
        event.remove(made, "before_cursor_execute", write_from_elsewhere)

    assert said == ["database is locked"]
    assert held(made) == [a_doubt()]
