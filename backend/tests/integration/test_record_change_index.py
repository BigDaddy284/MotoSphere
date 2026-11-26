"""Tests of the two indexes of the history, against a real SQLite file.

An index is there to be used. These tests ask SQLite itself how it will
answer what is asked about the changes of one record and about the
changes one run caused, in a store that the migrations built, and hold
it to the indexes.
"""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, delete, event, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from motosphere.db.models import CollectionRun, RecordChange, Source
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

OF_A_RECORD = "ix_record_change_record_table_record_id"
OF_A_RUN = "ix_record_change_collection_run_id"
# What SQLite says when it goes straight to the changes of one record and
# to those one run caused, when it needs the rows and when the index
# alone answers. Each is the whole plan: nothing is sorted afterwards.
BY_THE_RECORD = f"SEARCH record_change USING INDEX {OF_A_RECORD} (record_table=? AND record_id=?)"
BY_THE_RECORD_ALONE = (
    f"SEARCH record_change USING COVERING INDEX {OF_A_RECORD} (record_table=? AND record_id=?)"
)
BY_THE_RUN = f"SEARCH record_change USING INDEX {OF_A_RUN} (collection_run_id=?)"
BY_THE_RUN_ALONE = f"SEARCH record_change USING COVERING INDEX {OF_A_RUN} (collection_run_id=?)"
BROKEN_KEY = "FOREIGN KEY constraint failed"
# The record and the run these tests ask about: a track, and the second run.
OF_THE_TRACK = (RecordChange.record_table == "track", RecordChange.record_id == 7)
THE_RUN = 2
# The history of these tests, in the order it is stored: the table and
# the key of the record, the field, the old and the new value, and the
# run that caused the change or the person who decided it.
THE_HISTORY: list[tuple[str, int, str, str | None, str, int | None, str | None]] = [
    ("track", 7, "name", "Example Park", "Example Raceway", 1, None),
    ("track", 8, "name", "Example Hill", "Example Heights", 2, None),
    # The same key in another table: another record.
    ("event", 7, "name", "Example Cup", "Example Trophy", 2, None),
    ("track", 7, "length_in_metres", None, "1600", 2, None),
    ("track", 7, "name", "Example Raceway", "Example Ring", None, "Jo Example"),
    ("track", 7, "name", "Example Ring", "Example Raceway", 2, None),
]

# What is asked about the history, as the store's code will ask it: each
# question with what SQLite says of how it answers.
QUESTIONS: dict[str, tuple[Callable[[Session], Any], str]] = {
    "what a record said before, in the order of its changes": (
        lambda work: work.scalars(
            select(RecordChange.id).where(*OF_THE_TRACK).order_by(RecordChange.id)
        ).all(),
        BY_THE_RECORD_ALONE,
    ),
    "the changes of a record with all they say": (
        lambda work: [
            (row.field, row.old_value, row.new_value)
            for row in work.scalars(
                select(RecordChange).where(*OF_THE_TRACK).order_by(RecordChange.id)
            )
        ],
        BY_THE_RECORD,
    ),
    "the changes of a record, the newest first": (
        lambda work: [
            row.id
            for row in work.scalars(
                select(RecordChange).where(*OF_THE_TRACK).order_by(RecordChange.id.desc())
            )
        ],
        BY_THE_RECORD,
    ),
    "the last change to a record": (
        lambda work: (
            work.scalars(
                select(RecordChange).where(*OF_THE_TRACK).order_by(RecordChange.id.desc()).limit(1)
            )
            .one()
            .new_value
        ),
        BY_THE_RECORD,
    ),
    "the changes to one field of a record": (
        lambda work: [
            row.id
            for row in work.scalars(
                select(RecordChange)
                .where(*OF_THE_TRACK, RecordChange.field == "name")
                .order_by(RecordChange.id)
            )
        ],
        BY_THE_RECORD,
    ),
    "how many times a record was changed": (
        lambda work: work.scalar(
            select(func.count()).select_from(RecordChange).where(*OF_THE_TRACK)
        ),
        BY_THE_RECORD_ALONE,
    ),
    "what a run changed, in the order of the changes": (
        lambda work: [
            (row.record_table, row.record_id, row.field)
            for row in work.scalars(
                select(RecordChange)
                .where(RecordChange.collection_run_id == THE_RUN)
                .order_by(RecordChange.id)
            )
        ],
        BY_THE_RUN,
    ),
    "how many changes a run caused": (
        lambda work: work.scalar(
            select(func.count())
            .select_from(RecordChange)
            .where(RecordChange.collection_run_id == THE_RUN)
        ),
        BY_THE_RUN_ALONE,
    ),
}
EACH_QUESTION = pytest.mark.parametrize("question", list(QUESTIONS))


def to_delete_the_run(work: Session) -> None:
    """Delete a run that caused changes, which SQLite refuses when it has looked."""
    work.execute(delete(CollectionRun).where(CollectionRun.id == THE_RUN))


def to_give_the_run_another_key(work: Session) -> None:
    """Change the key of a run that caused changes, which SQLite refuses as well."""
    work.execute(update(CollectionRun).where(CollectionRun.id == THE_RUN).values(id=99))


# What SQLite must look into the history for, without being asked to:
# each with the statement it is sent as.
LOOKED_FOR: dict[str, tuple[Callable[[Session], None], str]] = {
    "a run is deleted": (to_delete_the_run, "DELETE FROM collection_run"),
    "a run is given another key": (to_give_the_run_another_key, "UPDATE collection_run"),
}
EACH_LOOK = pytest.mark.parametrize("look", list(LOOKED_FOR))


@pytest.fixture
def history(newest: Engine) -> Engine:
    """The newest store with a source, three runs of it and the history of these tests."""
    with unit_of_work(newest) as work:
        source = Source(
            name="Example Federation",
            website="https://federation.example",
            category=SourceCategory.GOVERNING_BODY,
            collection_method=CollectionMethod.RSS,
        )
        work.add(source)
        work.flush()
        for hour in (6, 7, 8):
            work.add(
                CollectionRun(
                    source_id=source.id, started_at=datetime(2026, 11, 26, hour, tzinfo=UTC)
                )
            )
        work.flush()
        for table, key, field, old, new, run, person in THE_HISTORY:
            work.add(
                RecordChange(
                    record_table=table,
                    record_id=key,
                    field=field,
                    old_value=old,
                    new_value=new,
                    collection_run_id=run,
                    decided_by=person,
                )
            )
            # One at a time, so that the keys follow the order above.
            work.flush()
    return newest


def sent_by(
    store: Engine, ask: Callable[[Session], Any], refused: bool = False
) -> list[tuple[str, Sequence[object]]]:
    """Every statement a question sends, with what it is given. Nothing it changes is kept.

    ``refused`` says that SQLite is expected to refuse what is asked.
    """
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
            if refused:
                with pytest.raises(IntegrityError, match=BROKEN_KEY):
                    ask(work)
            else:
                ask(work)
            work.rollback()
    finally:
        event.remove(store, "before_cursor_execute", remember)
    return sent


def plan_of(store: Engine, statement: str, given: Sequence[object]) -> list[str]:
    """SQLite's own account of how it will answer a statement, step by step."""
    with store.connect() as connection:
        steps = connection.exec_driver_sql("EXPLAIN QUERY PLAN " + statement, tuple(given))
        return [str(step[3]) for step in steps]


def without_the_indexes(store: Engine) -> None:
    with store.begin() as connection:
        connection.exec_driver_sql(f"DROP INDEX {OF_A_RECORD}")
        connection.exec_driver_sql(f"DROP INDEX {OF_A_RUN}")


def test_in_the_file_the_history_has_its_two_indexes(newest: Engine) -> None:
    with newest.connect() as connection:
        listed = sorted(
            (name, bool(unique), made_by, bool(partial))
            for _, name, unique, made_by, partial in connection.exec_driver_sql(
                "PRAGMA index_list(record_change)"
            )
        )
        indexed = {
            index: [
                name for _, _, name in connection.exec_driver_sql(f"PRAGMA index_info({index})")
            ]
            for index in (OF_A_RECORD, OF_A_RUN)
        }
        written = [
            str(sql)
            for (sql,) in connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type = 'index' AND tbl_name = 'record_change' "
                "ORDER BY name"
            )
        ]

    # Its name, that two rows can be alike in it, that a statement made it,
    # and that it is over all rows.
    assert listed == [(OF_A_RUN, False, "c", False), (OF_A_RECORD, False, "c", False)]
    assert indexed == {OF_A_RECORD: ["record_table", "record_id"], OF_A_RUN: ["collection_run_id"]}
    assert written == [
        "CREATE INDEX ix_record_change_collection_run_id ON record_change (collection_run_id)",
        "CREATE INDEX ix_record_change_record_table_record_id "
        "ON record_change (record_table, record_id)",
    ]


@EACH_QUESTION
def test_what_is_asked_about_the_history_is_answered_by_an_index(
    history: Engine, question: str
) -> None:
    ask, answered = QUESTIONS[question]

    ((statement, given),) = sent_by(history, ask)

    assert "FROM record_change" in statement
    # One step: the rows are found by the index, and nothing is sorted
    # afterwards, because the index has them in the order of their keys.
    assert plan_of(history, statement, given) == [answered]


@EACH_QUESTION
def test_without_the_indexes_the_whole_history_is_read(history: Engine, question: str) -> None:
    # What the indexes are for: the same statement, in the same store without them.
    ask, _ = QUESTIONS[question]
    ((statement, given),) = sent_by(history, ask)
    without_the_indexes(history)

    assert plan_of(history, statement, given) == ["SCAN record_change"]


@EACH_LOOK
def test_sqlite_looks_for_the_changes_of_a_run_by_the_index(history: Engine, look: str) -> None:
    ask, begins = LOOKED_FOR[look]

    ((statement, given),) = sent_by(history, ask, refused=True)
    plan = plan_of(history, statement, given)

    assert statement.startswith(begins)
    assert {step for step in plan if "record_change" in step} == {BY_THE_RUN_ALONE}
    # Nor does it read the whole of any table.
    assert [step for step in plan if step.startswith("SCAN")] == []


@EACH_LOOK
def test_without_the_indexes_the_whole_history_is_read_for_a_run(
    history: Engine, look: str
) -> None:
    ask, _ = LOOKED_FOR[look]
    ((statement, given),) = sent_by(history, ask, refused=True)
    without_the_indexes(history)

    plan = plan_of(history, statement, given)

    assert {step for step in plan if "record_change" in step} == {"SCAN record_change"}


def answers(store: Engine) -> list[Any]:
    """What the store answers to every question, and whether the run can be deleted."""
    with unit_of_work(store) as work:
        said = [ask(work) for ask, _ in QUESTIONS.values()]
    try:
        with unit_of_work(store) as work:
            to_delete_the_run(work)
    except IntegrityError as refusal:
        said.append(str(refusal.orig))
    return said


def test_the_indexes_change_no_answer(history: Engine) -> None:
    with_them = answers(history)
    without_the_indexes(history)

    without_them = answers(history)

    assert with_them == without_them
    assert with_them == [
        [1, 4, 5, 6],
        [
            ("name", "Example Park", "Example Raceway"),
            ("length_in_metres", None, "1600"),
            ("name", "Example Raceway", "Example Ring"),
            ("name", "Example Ring", "Example Raceway"),
        ],
        [6, 5, 4, 1],
        "Example Raceway",
        [1, 5, 6],
        4,
        [
            ("track", 8, "name"),
            ("event", 7, "name"),
            ("track", 7, "length_in_metres"),
            ("track", 7, "name"),
        ],
        4,
        BROKEN_KEY,
    ]
