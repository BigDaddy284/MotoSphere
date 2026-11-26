"""Tests of the function that changes a record with its history, against a real SQLite file.

The store of every test is built by the migrations, as a real store is,
so the history is written to the real table of the changes. The records
that are changed are of tables made for the tests: the real schema has
no table of records yet. Their models are kept in a schema of their own
(``PROOF``), so the real schema never sees them. What the store holds
afterwards is read with plain SQL, past the models.
"""

from datetime import UTC, date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

import pytest
from sqlalchemy import Engine, MetaData, Text, cast, select
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db import times
from motosphere.db.base import NAMING, Base
from motosphere.db.changes import change
from motosphere.db.lists import OneOf
from motosphere.db.models import SCHEMA, CollectionRun, RecordChange, Source
from motosphere.db.models.provenance import Collected, Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.texts import NotEmpty
from motosphere.db.web import WebAddress
from motosphere.db.work import unit_of_work

# An offset of one hour ahead of UTC, as Paris has it in winter.
IN_PARIS = timezone(timedelta(hours=1))
INSPECTED = datetime(2026, 11, 25, 9, 30, tzinfo=UTC)
COLLECTED = datetime(2026, 11, 20, 6, 0, tzinfo=UTC)
COLLECTED_AGAIN = datetime(2026, 11, 27, 6, 0, tzinfo=UTC)
ADDRESS = "https://federation.example/results/2026/round-1"
NEW_ADDRESS = "https://federation.example/results/2026/round-1/revised"
NO_CAUSE = "A change is caused by a collection run or decided by a person: say one of the two"
NOT_STORED = "Only a record that is stored, and that this unit of work read or stored, is changed"
NO_TEXT = "The history has no text for what the column proof_track.{} keeps: it has one for"
NOT_A_NUMBER = "The column proof_track.length_in_metres keeps a whole number, which {} is not."
NOT_TEXT = "The column proof_track.{} keeps text, which {} is not."
THE_HISTORY = (
    "SELECT record_table, record_id, field, old_value, new_value, collection_run_id, "
    "decided_by, created_at, updated_at FROM record_change ORDER BY id"
)
THE_ROW = {
    "proof_track": "SELECT * FROM proof_track WHERE id = ?",
    "proof_rider": "SELECT * FROM proof_rider WHERE id = ?",
}

PROOF = MetaData(naming_convention=NAMING)


class Surface(StrEnum):
    """What a track of the tests is made of."""

    SAND = "sand"
    HARD_PACK = "hard pack"


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


class ProofTrack(Proof):
    """A record with a column of every kind the store keeps."""

    __tablename__ = "proof_track"

    name: Mapped[NotEmpty]
    website: Mapped[WebAddress | None]
    notes: Mapped[str | None]
    length_in_metres: Mapped[int | None]
    opened_on: Mapped[date | None]
    inspected_at: Mapped[datetime | None]
    floodlit: Mapped[bool | None]
    surface: Mapped[Surface | None] = mapped_column(OneOf(Surface))
    width_in_metres: Mapped[float | None]
    emblem: Mapped[bytes | None]


class ProofRider(Proof):
    """A record of a second table, whose keys are the keys of the first."""

    __tablename__ = "proof_rider"

    name: Mapped[NotEmpty]


class ProofResult(ProofOfCollected):
    """A collected record: it says where it came from, as every such record does."""

    __tablename__ = "proof_result"

    position: Mapped[int]


@pytest.fixture
def made(newest: Engine) -> Engine:
    """The newest store, with the tables of the tests made in it next to the real ones."""
    with newest.begin() as connection:
        PROOF.create_all(connection)
    return newest


def a_track(store: Engine, **given: Any) -> int:
    """Store a track through the model, and give its key."""
    said: dict[str, Any] = {
        "name": "Example Park",
        "length_in_metres": 1600,
        "opened_on": date(1998, 5, 1),
        "inspected_at": INSPECTED,
        "floodlit": False,
        "surface": Surface.SAND,
    }
    said.update(given)
    with unit_of_work(store) as work:
        track = ProofTrack(**said)
        work.add(track)
    return track.id


def a_run(store: Engine) -> int:
    """Store a source and a run of it, and give the key of the run. The source has the key 1."""
    with unit_of_work(store) as work:
        source = Source(
            name="Example Federation",
            website="https://federation.example",
            category=SourceCategory.GOVERNING_BODY,
            collection_method=CollectionMethod.HTML,
        )
        work.add(source)
        work.flush()
        run = CollectionRun(source_id=source.id, started_at=COLLECTED_AGAIN)
        work.add(run)
    return run.id


def in_the_file(store: Engine, table: str, key: int) -> dict[str, object]:
    """One row as SQLite holds it, by the names of its columns."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(THE_ROW[table], (key,))
        return dict(found.mappings().one())


def history(store: Engine) -> list[tuple[object, ...]]:
    """The table of the changes as SQLite holds it, by the key, without the key."""
    with store.connect() as connection:
        return [tuple(row) for row in connection.exec_driver_sql(THE_HISTORY)]


def test_a_changed_field_is_in_the_record_and_its_old_value_in_the_history(
    made: Engine, clock: list[datetime]
) -> None:
    key = a_track(made)
    before = in_the_file(made, "proof_track", key)
    asked = len(clock)

    with unit_of_work(made) as work:
        track = work.get_one(ProofTrack, key)
        written = change(work, track, {"name": "Example Raceway"}, decided_by="Jo Example")

    # One reading of the clock: the row of the history was stored at that
    # moment, and the record says it was last changed at that moment.
    assert len(clock) == asked + 1
    moment = times.to_text(clock[-1])
    assert in_the_file(made, "proof_track", key) == {
        **before,
        "name": "Example Raceway",
        "updated_at": moment,
    }
    assert [row[:7] for row in history(made)] == [
        ("proof_track", key, "name", "Example Park", "Example Raceway", None, "Jo Example")
    ]
    assert [row[7:] for row in history(made)] == [(moment, moment)]
    assert [(row.id, row.field, row.old_value, row.new_value) for row in written] == [
        (1, "name", "Example Park", "Example Raceway")
    ]
    assert track.name == "Example Raceway"
    assert track.updated_at == written[0].created_at == clock[-1]


def test_a_change_to_three_fields_is_three_rows_of_one_moment_in_the_order_given(
    made: Engine, clock: list[datetime]
) -> None:
    key = a_track(made)
    asked = len(clock)

    with unit_of_work(made) as work:
        track = work.get_one(ProofTrack, key)
        written = change(
            work,
            track,
            {"surface": Surface.HARD_PACK, "name": "Example Raceway", "length_in_metres": 1750},
            decided_by="Jo Example",
        )

    assert len(clock) == asked + 1
    moment = times.to_text(clock[-1])
    assert [row[:7] for row in history(made)] == [
        ("proof_track", key, "surface", "sand", "hard pack", None, "Jo Example"),
        ("proof_track", key, "name", "Example Park", "Example Raceway", None, "Jo Example"),
        ("proof_track", key, "length_in_metres", "1600", "1750", None, "Jo Example"),
    ]
    assert [row[7:] for row in history(made)] == [(moment, moment)] * 3
    assert [row.id for row in written] == [1, 2, 3]
    row = in_the_file(made, "proof_track", key)
    assert (row["surface"], row["name"], row["length_in_metres"]) == (
        "hard pack",
        "Example Raceway",
        1750,
    )
    assert row["updated_at"] == moment


@pytest.mark.parametrize(
    ("field", "old", "new"),
    [
        ("name", "Example Park", "example park"),
        ("name", "Example Park", "Example Park "),
        ("notes", None, "Sandy after rain."),
        ("notes", "Sandy after rain.", None),
        ("notes", "", None),
        ("notes", None, ""),
        ("website", "https://park.example", "https://raceway.example/tracks?id=7"),
        ("length_in_metres", 1600, 1750),
        ("length_in_metres", 1600, None),
        ("length_in_metres", 0, -1),
        ("opened_on", date(1998, 5, 1), date(1999, 12, 31)),
        ("inspected_at", INSPECTED, datetime(2026, 11, 26, 10, 0, 0, 5, tzinfo=IN_PARIS)),
        ("inspected_at", None, INSPECTED),
        ("floodlit", False, True),
        ("floodlit", None, False),
        ("surface", Surface.SAND, Surface.HARD_PACK),
        ("surface", Surface.SAND, None),
    ],
    ids=[
        "a text",
        "a space at the end of a text",
        "from no text to a text",
        "from a text to none",
        "from empty text to none",
        "from no text to empty text",
        "a web address",
        "a whole number",
        "from a whole number to none",
        "nothing and a number below it",
        "a day",
        "a time, said in Paris",
        "from no time to a time",
        "yes or no",
        "from unknown to no",
        "a word of a list",
        "from a word of a list to none",
    ],
)
def test_the_history_holds_the_text_of_what_the_store_kept_and_keeps(
    made: Engine, field: str, old: object, new: object
) -> None:
    key = a_track(made, **{field: old})
    # SQLite itself says the text of what it keeps: CAST(<field> AS TEXT).
    table = PROOF.tables["proof_track"]
    as_text = select(cast(table.columns[field], Text)).where(table.columns["id"] == key)
    with made.connect() as connection:
        kept_before = connection.execute(as_text).scalar_one()

    with unit_of_work(made) as work:
        change(work, work.get_one(ProofTrack, key), {field: new}, decided_by="Jo Example")

    with made.connect() as connection:
        kept_now = connection.execute(as_text).scalar_one()
    assert kept_before != kept_now
    assert [(row[2], row[3], row[4]) for row in history(made)] == [(field, kept_before, kept_now)]


def test_a_field_that_holds_the_value_already_is_left_alone(
    made: Engine, clock: list[datetime]
) -> None:
    key = a_track(made)
    before = in_the_file(made, "proof_track", key)
    asked = len(clock)

    with unit_of_work(made) as work:
        track = work.get_one(ProofTrack, key)
        written = change(
            work,
            track,
            {
                "name": "Example Park",
                "notes": None,
                "length_in_metres": 1600,
                "opened_on": date(1998, 5, 1),
                # The same moment, said as Paris says it.
                "inspected_at": INSPECTED.astimezone(IN_PARIS),
                "floodlit": False,
                "surface": Surface.SAND,
            },
            decided_by="Jo Example",
        )

    assert written == []
    assert history(made) == []
    # Not even the moment the record was last changed has moved, and the
    # clock was not asked.
    assert in_the_file(made, "proof_track", key) == before
    assert len(clock) == asked


def test_only_the_fields_that_hold_another_value_get_a_row(made: Engine) -> None:
    key = a_track(made)

    with unit_of_work(made) as work:
        written = change(
            work,
            work.get_one(ProofTrack, key),
            {
                "name": "Example Park",
                "length_in_metres": 1750,
                "floodlit": False,
                "notes": "Sandy.",
            },
            decided_by="Jo Example",
        )

    assert [(row.field, row.old_value, row.new_value) for row in written] == [
        ("length_in_metres", "1600", "1750"),
        ("notes", None, "Sandy."),
    ]
    assert [(row[2], row[3], row[4]) for row in history(made)] == [
        ("length_in_metres", "1600", "1750"),
        ("notes", None, "Sandy."),
    ]


def test_a_change_with_nothing_to_change_changes_nothing(made: Engine) -> None:
    key = a_track(made)
    before = in_the_file(made, "proof_track", key)

    with unit_of_work(made) as work:
        assert change(work, work.get_one(ProofTrack, key), {}, decided_by="Jo Example") == []

    assert history(made) == []
    assert in_the_file(made, "proof_track", key) == before


def test_a_change_that_a_run_caused_names_the_run(made: Engine) -> None:
    key = a_track(made)
    run = a_run(made)

    with unit_of_work(made) as work:
        change(work, work.get_one(ProofTrack, key), {"length_in_metres": 1750}, run=run)

    assert [row[:7] for row in history(made)] == [
        ("proof_track", key, "length_in_metres", "1600", "1750", run, None)
    ]


@pytest.mark.parametrize(
    "cause",
    [{}, {"run": 1, "decided_by": "Jo Example"}, {"run": None, "decided_by": None}],
    ids=["no cause", "both causes", "both said to be none"],
)
def test_a_change_without_one_cause_is_refused_before_anything_is_changed(
    made: Engine, cause: dict[str, Any]
) -> None:
    key = a_track(made)
    a_run(made)
    before = in_the_file(made, "proof_track", key)

    with unit_of_work(made) as work:
        track = work.get_one(ProofTrack, key)
        with pytest.raises(ValueError, match=NO_CAUSE):
            change(work, track, {"name": "Example Raceway"}, **cause)
        assert track.name == "Example Park"

    assert history(made) == []
    assert in_the_file(made, "proof_track", key) == before


@pytest.mark.parametrize(
    ("to", "cause", "why"),
    [
        (
            {"length_in_metres": 1750, "name": ""},
            {"decided_by": "Jo Example"},
            "CHECK constraint failed: ck_proof_track_name_not_empty",
        ),
        (
            {"length_in_metres": 1750, "website": "raceway.example"},
            {"decided_by": "Jo Example"},
            "CHECK constraint failed: ck_proof_track_website_web_address",
        ),
        ({"length_in_metres": 1750}, {"run": 99}, "FOREIGN KEY constraint failed"),
        (
            {"length_in_metres": 1750},
            {"decided_by": " "},
            "CHECK constraint failed: ck_record_change_decided_by_not_empty",
        ),
    ],
    ids=[
        "a value the record's table refuses",
        "an address the record's table refuses",
        "a run that is not there",
        "a person without a name",
    ],
)
def test_a_change_the_store_refuses_leaves_neither_the_change_nor_its_history(
    made: Engine, to: dict[str, object], cause: dict[str, Any], why: str
) -> None:
    key = a_track(made)
    before = in_the_file(made, "proof_track", key)

    with pytest.raises(IntegrityError) as refusal, unit_of_work(made) as work:
        change(work, work.get_one(ProofTrack, key), to, **cause)

    assert str(refusal.value.orig) == why
    assert history(made) == []
    assert in_the_file(made, "proof_track", key) == before


def test_work_that_fails_later_takes_the_change_and_its_history_back(made: Engine) -> None:
    key = a_track(made)
    before = in_the_file(made, "proof_track", key)

    def the_work() -> None:
        with unit_of_work(made) as work:
            track = work.get_one(ProofTrack, key)
            written = change(work, track, {"name": "Example Raceway"}, decided_by="Jo Example")
            assert len(written) == 1
            raise RuntimeError("the job died")

    with pytest.raises(RuntimeError, match="the job died"):
        the_work()

    assert history(made) == []
    assert in_the_file(made, "proof_track", key) == before


def test_a_unit_of_work_does_not_go_on_after_a_change_the_store_refused(made: Engine) -> None:
    key = a_track(made)
    before = in_the_file(made, "proof_track", key)

    def the_work() -> None:
        with unit_of_work(made) as work:
            track = work.get_one(ProofTrack, key)
            change(work, track, {"length_in_metres": 1750}, decided_by="Jo Example")
            with pytest.raises(IntegrityError):
                change(work, track, {"name": ""}, decided_by="Jo Example")
            change(work, track, {"notes": "Sandy."}, decided_by="Jo Example")

    # Whoever catches the refusal and carries on is stopped at the next
    # thing the unit of work is asked: nothing of it can be kept any more.
    with pytest.raises(InvalidRequestError, match="The transaction was rolled back"):
        the_work()

    assert history(made) == []
    assert in_the_file(made, "proof_track", key) == before


@pytest.mark.parametrize(
    ("field", "value", "why"),
    [
        ("width_in_metres", 12.5, NO_TEXT.format("width_in_metres")),
        ("width_in_metres", None, NO_TEXT.format("width_in_metres")),
        ("emblem", b"\x89PNG", NO_TEXT.format("emblem")),
        ("length_in_metres", True, NOT_A_NUMBER.format("True")),
        ("length_in_metres", 1750.0, NOT_A_NUMBER.format("1750.0")),
        ("length_in_metres", "1750", NOT_A_NUMBER.format("'1750'")),
        ("notes", 7, NOT_TEXT.format("notes", "7")),
        ("notes", ["Sandy."], NOT_TEXT.format("notes", "['Sandy.']")),
        ("name", Surface.SAND, NOT_TEXT.format("name", "<Surface.SAND: 'sand'>")),
        ("floodlit", 1, "Only yes or no (True or False) is stored as yes or no, not int: 1."),
        ("surface", "sand", "Only a value of the list Surface is stored in this column, not str"),
        ("opened_on", "1999-12-31", "Only a day (a date) is stored as a day, not str"),
        ("inspected_at", "2026-11-26", "Only a time (a datetime) is stored as a time, not str"),
    ],
    ids=[
        "a number with a fraction",
        "no value for a column of numbers with a fraction",
        "bytes",
        "yes for a whole number",
        "a number with a fraction for a whole number",
        "digits as text for a whole number",
        "a number for a text",
        "a list for a text",
        "a word of a list for a text",
        "a number for yes or no",
        "a word of a list as plain text",
        "a day as text",
        "a time as text",
    ],
)
def test_a_value_without_a_text_for_the_history_is_refused_before_anything_is_changed(
    made: Engine, field: str, value: object, why: str
) -> None:
    key = a_track(made)
    before = in_the_file(made, "proof_track", key)

    with unit_of_work(made) as work:
        track = work.get_one(ProofTrack, key)
        with pytest.raises(TypeError) as refusal:
            change(work, track, {"name": "Example Raceway", field: value}, decided_by="Jo Example")
        # The field that came before it in the same call was not changed either.
        assert track.name == "Example Park"

    assert str(refusal.value).startswith(why)
    assert history(made) == []
    assert in_the_file(made, "proof_track", key) == before


def test_a_time_without_an_offset_is_refused_before_anything_is_changed(made: Engine) -> None:
    key = a_track(made)
    before = in_the_file(made, "proof_track", key)

    with unit_of_work(made) as work:
        track = work.get_one(ProofTrack, key)
        with pytest.raises(ValueError, match="A time without an offset is not stored"):
            change(
                work,
                track,
                {"name": "Example Raceway", "inspected_at": INSPECTED.replace(tzinfo=None)},
                decided_by="Jo Example",
            )

    assert history(made) == []
    assert in_the_file(made, "proof_track", key) == before


def test_a_record_that_holds_what_has_no_text_can_have_its_other_fields_changed(
    made: Engine,
) -> None:
    key = a_track(made, width_in_metres=12.5, emblem=b"\x89PNG")

    with unit_of_work(made) as work:
        change(work, work.get_one(ProofTrack, key), {"name": "Example Raceway"}, decided_by="Jo")

    assert [(row[2], row[3], row[4]) for row in history(made)] == [
        ("name", "Example Park", "Example Raceway")
    ]
    row = in_the_file(made, "proof_track", key)
    assert (row["width_in_metres"], row["emblem"]) == (12.5, b"\x89PNG")


@pytest.mark.parametrize("field", ["id", "created_at", "updated_at"])
def test_the_columns_that_are_the_stores_own_are_not_changed_by_hand(
    made: Engine, field: str
) -> None:
    key = a_track(made)
    before = in_the_file(made, "proof_track", key)
    value = {"id": 99, "created_at": INSPECTED, "updated_at": INSPECTED}[field]

    with unit_of_work(made) as work:
        track = work.get_one(ProofTrack, key)
        with pytest.raises(ValueError, match=f"The column {field} is the store's own"):
            change(work, track, {"name": "Example Raceway", field: value}, decided_by="Jo")
        assert track.name == "Example Park"

    assert history(made) == []
    assert in_the_file(made, "proof_track", key) == before


@pytest.mark.parametrize("field", ["length", "Name", "name ", "proof_track.name", ""])
def test_a_field_its_table_does_not_have_is_refused_before_anything_is_changed(
    made: Engine, field: str
) -> None:
    key = a_track(made)
    before = in_the_file(made, "proof_track", key)

    with unit_of_work(made) as work:
        track = work.get_one(ProofTrack, key)
        with pytest.raises(ValueError, match="The table proof_track has no column") as refusal:
            change(work, track, {"name": "Example Raceway", field: 1750}, decided_by="Jo Example")
        assert track.name == "Example Park"

    assert str(refusal.value) == f"The table proof_track has no column {field}."
    assert history(made) == []
    assert in_the_file(made, "proof_track", key) == before


def test_a_record_that_is_not_stored_yet_has_no_history_to_write(made: Engine) -> None:
    with unit_of_work(made) as work:
        never_added = ProofTrack(name="Example Park")
        with pytest.raises(ValueError, match=NOT_STORED):
            change(work, never_added, {"name": "Example Raceway"}, decided_by="Jo Example")

        added = ProofTrack(name="Example Park")
        work.add(added)
        with pytest.raises(ValueError, match=NOT_STORED):
            change(work, added, {"name": "Example Raceway"}, decided_by="Jo Example")
        assert added.name == "Example Park"

        # Once the unit of work has stored it, it is a record like any other.
        work.flush()
        change(work, added, {"name": "Example Raceway"}, decided_by="Jo Example")

    assert [row[:7] for row in history(made)] == [
        ("proof_track", added.id, "name", "Example Park", "Example Raceway", None, "Jo Example")
    ]


def test_a_record_of_another_unit_of_work_or_a_deleted_one_is_refused(made: Engine) -> None:
    key = a_track(made)
    other = a_track(made, name="Other Park")
    with unit_of_work(made) as work:
        of_an_ended_unit = work.get_one(ProofTrack, key)

    with unit_of_work(made) as work:
        with pytest.raises(ValueError, match=NOT_STORED):
            change(work, of_an_ended_unit, {"name": "Example Raceway"}, decided_by="Jo Example")
        # A record that another unit of work holds, which has not ended.
        with unit_of_work(made) as another:
            of_another_unit = another.get_one(ProofTrack, key)
            with pytest.raises(ValueError, match=NOT_STORED):
                change(work, of_another_unit, {"name": "Example Raceway"}, decided_by="Jo")
        deleted = work.get_one(ProofTrack, other)
        work.delete(deleted)
        work.flush()
        with pytest.raises(ValueError, match=NOT_STORED):
            change(work, deleted, {"name": "Other Raceway"}, decided_by="Jo Example")

    assert of_an_ended_unit.name == "Example Park"
    assert history(made) == []
    assert in_the_file(made, "proof_track", key)["name"] == "Example Park"


def test_a_row_of_the_history_is_not_a_record_to_change(made: Engine) -> None:
    key = a_track(made)
    with unit_of_work(made) as work:
        change(work, work.get_one(ProofTrack, key), {"name": "Example Raceway"}, decided_by="Jo")
    before = history(made)

    with unit_of_work(made) as work:
        row = work.get_one(RecordChange, 1)
        with pytest.raises(ValueError, match="The history is added to and never changed"):
            change(work, row, {"new_value": "Example Speedway"}, decided_by="Jo Example")

    assert history(made) == before


def test_what_was_set_by_hand_before_the_call_is_the_old_value_of_the_history(
    made: Engine,
) -> None:
    key = a_track(made)

    with unit_of_work(made) as work:
        track = work.get_one(ProofTrack, key)
        # Set by hand, and not written to the store when the function is called.
        track.notes = "Set by hand."
        track.length_in_metres = 1700
        change(work, track, {"notes": "Sandy."}, decided_by="Jo Example")

    # The record is compared as the unit of work holds it. What was set by
    # hand beside it is kept, without a row: the function saw none of it
    # change.
    assert [(row[2], row[3], row[4]) for row in history(made)] == [
        ("notes", "Set by hand.", "Sandy.")
    ]
    row = in_the_file(made, "proof_track", key)
    assert (row["notes"], row["length_in_metres"]) == ("Sandy.", 1700)


def test_two_changes_in_one_unit_of_work_follow_each_other(
    made: Engine, clock: list[datetime]
) -> None:
    key = a_track(made)

    with unit_of_work(made) as work:
        track = work.get_one(ProofTrack, key)
        change(work, track, {"name": "Example Raceway"}, decided_by="Jo Example")
        first = clock[-1]
        change(work, track, {"name": "Example Speedway"}, decided_by="Jo Example")
        # And back again: nothing forbids it, and it is a change like any other.
        change(work, track, {"name": "Example Raceway"}, decided_by="Jo Example")

    rows = history(made)
    assert [(row[3], row[4]) for row in rows] == [
        ("Example Park", "Example Raceway"),
        ("Example Raceway", "Example Speedway"),
        ("Example Speedway", "Example Raceway"),
    ]
    # Each call read the clock once, and the record says the last of them.
    assert [row[7] for row in rows] == [times.to_text(moment) for moment in clock[-3:]]
    assert clock[-3] == first
    assert in_the_file(made, "proof_track", key)["updated_at"] == times.to_text(clock[-1])


def test_the_history_names_the_record_by_its_table_and_its_key(made: Engine) -> None:
    track = a_track(made)
    second = a_track(made, name="Other Park")
    with unit_of_work(made) as work:
        rider = ProofRider(name="A. Rider")
        work.add(rider)
    assert rider.id == track

    with unit_of_work(made) as work:
        change(work, work.get_one(ProofRider, rider.id), {"name": "B. Rider"}, decided_by="Jo")
        change(work, work.get_one(ProofTrack, second), {"name": "Other Raceway"}, decided_by="Jo")
        change(work, work.get_one(ProofTrack, track), {"name": "Example Raceway"}, decided_by="Jo")

    assert [row[:5] for row in history(made)] == [
        ("proof_rider", rider.id, "name", "A. Rider", "B. Rider"),
        ("proof_track", second, "name", "Other Park", "Other Raceway"),
        ("proof_track", track, "name", "Example Park", "Example Raceway"),
    ]
    # No record but the three was touched, and each holds its own new name.
    assert in_the_file(made, "proof_track", track)["name"] == "Example Raceway"
    assert in_the_file(made, "proof_track", second)["name"] == "Other Raceway"
    assert in_the_file(made, "proof_rider", rider.id)["name"] == "B. Rider"


def test_what_a_collected_record_said_before_keeps_its_original_dates(made: Engine) -> None:
    run = a_run(made)
    with unit_of_work(made) as work:
        result = ProofResult(
            position=3,
            source_id=1,
            source_address=ADDRESS,
            collected_at=COLLECTED,
            published_on=date(2026, 11, 19),
            last_verified_at=COLLECTED,
            extraction_method=CollectionMethod.HTML,
            confidence=Confidence.MEDIUM,
            verification_status=VerificationStatus.OFFICIAL,
        )
        work.add(result)

    # A week later the source says another position, at another address.
    # What says where the record came from is changed with it, in one call.
    with unit_of_work(made) as work:
        change(
            work,
            work.get_one(ProofResult, result.id),
            {
                "position": 2,
                "source_address": NEW_ADDRESS,
                "collected_at": COLLECTED_AGAIN,
                "published_on": date(2026, 11, 26),
                "last_verified_at": COLLECTED_AGAIN,
                "extraction_method": CollectionMethod.HTML,
                "confidence": Confidence.HIGH,
                "verification_status": VerificationStatus.OFFICIAL,
            },
            run=run,
        )

    assert [(row[2], row[3], row[4], row[5]) for row in history(made)] == [
        ("position", "3", "2", run),
        ("source_address", ADDRESS, NEW_ADDRESS, run),
        ("collected_at", times.to_text(COLLECTED), times.to_text(COLLECTED_AGAIN), run),
        ("published_on", "2026-11-19", "2026-11-26", run),
        ("last_verified_at", times.to_text(COLLECTED), times.to_text(COLLECTED_AGAIN), run),
        ("confidence", "medium", "high", run),
    ]
    assert len({row[7] for row in history(made)}) == 1


def test_a_change_made_past_the_function_leaves_no_history(made: Engine) -> None:
    # Nothing stops it. The test is here so that this is not taken for
    # something the function does: whoever changes a record calls it.
    key = a_track(made)

    with unit_of_work(made) as work:
        work.get_one(ProofTrack, key).name = "Example Raceway"

    assert in_the_file(made, "proof_track", key)["name"] == "Example Raceway"
    assert history(made) == []
