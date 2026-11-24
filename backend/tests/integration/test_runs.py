"""Tests of what the store does with its collection runs, against a real SQLite file.

A job that died leaves its run running. These tests prove that the next
start marks exactly those runs interrupted and touches nothing else.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, select

from motosphere.db.models import CollectionRun, Source, SourceOffer
from motosphere.db.models.collection_run import RunOutcome
from motosphere.db.models.source import CollectionMethod, InformationType, SourceCategory
from motosphere.db.runs import mark_interrupted
from motosphere.db.times import to_text
from motosphere.db.work import unit_of_work

STARTED = datetime(2026, 11, 23, 6, 0, tzinfo=UTC)
ENDED = STARTED + timedelta(minutes=4)
START = to_text(STARTED)
END = to_text(ENDED)


def a_source(store: Engine, name: str = "Example Federation") -> int:
    """Store a source that offers events, and give its key."""
    source = Source(
        name=name,
        website="https://federation.example",
        category=SourceCategory.GOVERNING_BODY,
        collection_method=CollectionMethod.RSS,
    )
    with unit_of_work(store) as work:
        work.add(source)
        work.flush()
        work.add(SourceOffer(source_id=source.id, information_type=InformationType.EVENTS))
    return source.id


def a_run(store: Engine, source: int, outcome: RunOutcome, seen: int = 0) -> int:
    """Store a run of this outcome as the table takes it, and give its key."""
    run = CollectionRun(
        source_id=source,
        started_at=STARTED,
        ended_at=ENDED if outcome in (RunOutcome.SUCCEEDED, RunOutcome.FAILED) else None,
        outcome=outcome,
        records_seen=seen,
        records_added=seen,
        error="The feed did not answer." if outcome is RunOutcome.FAILED else None,
    )
    with unit_of_work(store) as work:
        work.add(run)
    return run.id


def everything(store: Engine, table: str) -> list[tuple[object, ...]]:
    """Every column of every row of a table, as SQLite holds it, by the key."""
    assert table in ("collection_run", "source", "source_offer")
    with store.connect() as connection:
        found = connection.exec_driver_sql(f"SELECT * FROM {table} ORDER BY id")  # noqa: S608
        return [tuple(row) for row in found]


def outcomes(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT outcome FROM collection_run ORDER BY id")
        return [str(outcome) for (outcome,) in found]


def test_where_no_run_is_running_nothing_is_marked(newest: Engine) -> None:
    source = a_source(newest)
    for outcome in (RunOutcome.SUCCEEDED, RunOutcome.FAILED, RunOutcome.INTERRUPTED):
        a_run(newest, source, outcome)
    before = everything(newest, "collection_run")

    with unit_of_work(newest) as work:
        marked = mark_interrupted(work)

    assert marked == []
    assert everything(newest, "collection_run") == before


def test_in_a_store_without_runs_nothing_is_marked(newest: Engine) -> None:
    with unit_of_work(newest) as work:
        assert mark_interrupted(work) == []

    assert everything(newest, "collection_run") == []


def test_a_run_left_running_is_marked_interrupted_and_only_that_is_changed(
    newest: Engine, clock: list[datetime]
) -> None:
    source = a_source(newest)
    run = a_run(newest, source, RunOutcome.RUNNING, seen=12)
    stored = clock[-1]

    with unit_of_work(newest) as work:
        marked = mark_interrupted(work)

    assert marked == [run]
    marked_at = clock[-1]
    assert marked_at == stored + timedelta(seconds=1)
    # The key, the source, the start, no end, the outcome, the four counts,
    # no error, when it was stored and when it was last changed.
    assert everything(newest, "collection_run") == [
        (
            run,
            source,
            START,
            None,
            "interrupted",
            12,
            12,
            0,
            0,
            None,
            to_text(stored),
            to_text(marked_at),
        )
    ]


def test_every_run_left_running_is_marked_whichever_source_it_is_of(newest: Engine) -> None:
    first = a_source(newest)
    second = a_source(newest, "Example Club")
    runs = [
        a_run(newest, first, RunOutcome.RUNNING),
        a_run(newest, second, RunOutcome.SUCCEEDED),
        a_run(newest, second, RunOutcome.RUNNING),
        a_run(newest, first, RunOutcome.RUNNING),
    ]

    with unit_of_work(newest) as work:
        marked = mark_interrupted(work)

    assert marked == [runs[0], runs[2], runs[3]]
    assert outcomes(newest) == ["interrupted", "succeeded", "interrupted", "interrupted"]


def test_no_other_run_and_no_other_table_is_touched(newest: Engine) -> None:
    source = a_source(newest)
    ended = [
        a_run(newest, source, RunOutcome.SUCCEEDED, seen=40),
        a_run(newest, source, RunOutcome.FAILED, seen=7),
        a_run(newest, source, RunOutcome.INTERRUPTED, seen=3),
    ]
    running = a_run(newest, source, RunOutcome.RUNNING)
    before = {
        table: everything(newest, table) for table in ("collection_run", "source", "source_offer")
    }

    with unit_of_work(newest) as work:
        marked = mark_interrupted(work)

    assert marked == [running]
    after = everything(newest, "collection_run")
    assert [row[0] for row in after] == [*ended, running]
    assert after[:3] == before["collection_run"][:3]
    assert everything(newest, "source") == before["source"]
    assert everything(newest, "source_offer") == before["source_offer"]


def test_a_run_that_was_marked_is_not_marked_again(newest: Engine) -> None:
    source = a_source(newest)
    run = a_run(newest, source, RunOutcome.RUNNING)
    with unit_of_work(newest) as work:
        assert mark_interrupted(work) == [run]
    once = everything(newest, "collection_run")

    with unit_of_work(newest) as work:
        marked = mark_interrupted(work)

    assert marked == []
    assert everything(newest, "collection_run") == once


def test_the_marking_is_taken_back_with_the_unit_of_work_it_is_part_of(newest: Engine) -> None:
    source = a_source(newest)
    a_run(newest, source, RunOutcome.RUNNING)
    before = everything(newest, "collection_run")

    def mark_and_die() -> None:
        with unit_of_work(newest) as work:
            assert mark_interrupted(work) == [1]
            raise RuntimeError("the job died again")

    with pytest.raises(RuntimeError, match="the job died again"):
        mark_and_die()

    assert everything(newest, "collection_run") == before


def test_a_run_the_unit_of_work_had_read_already_says_it_was_interrupted(newest: Engine) -> None:
    source = a_source(newest)
    a_run(newest, source, RunOutcome.RUNNING)

    with unit_of_work(newest) as work:
        run = work.execute(select(CollectionRun)).scalar_one()
        read = run.outcome
        mark_interrupted(work)
        assert (read, run.outcome) == (RunOutcome.RUNNING, RunOutcome.INTERRUPTED)


def test_a_new_run_can_start_once_the_old_one_was_marked(newest: Engine) -> None:
    source = a_source(newest)
    a_run(newest, source, RunOutcome.RUNNING)

    with unit_of_work(newest) as work:
        mark_interrupted(work)
        work.add(CollectionRun(source_id=source, started_at=ENDED))

    assert outcomes(newest) == ["interrupted", "running"]
