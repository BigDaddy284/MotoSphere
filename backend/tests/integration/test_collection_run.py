"""Tests of the table of the collection runs, against a real SQLite file.

The store of every test is built by the migrations, as a real store is.
What the table must refuse is also written past the model.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import IntegrityError

from motosphere.db.models import CollectionRun, Source
from motosphere.db.models.collection_run import RunOutcome
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

STARTED = datetime(2026, 11, 23, 6, 0, tzinfo=UTC)
ENDED = STARTED + timedelta(minutes=4)
START = "2026-11-23T06:00:00.000000+00:00"
END = "2026-11-23T06:04:00.000000+00:00"
BEFORE = "2026-11-23T05:59:59.999999+00:00"
MOMENT = "2026-11-23T06:05:00.000000+00:00"
BROKEN_KEY = "FOREIGN KEY constraint failed"
COUNTS = ["records_seen", "records_added", "records_changed", "records_unchanged"]
# A run of each outcome that the table takes: its end and its error.
TAKEN = {
    "running": (None, None),
    "succeeded": (END, None),
    "failed": (END, "The feed did not answer."),
    "interrupted": (None, None),
}


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def a_source(store: Engine, name: str = "Example Federation") -> int:
    """Store a source, and give its key."""
    source = Source(
        name=name,
        website="https://federation.example",
        category=SourceCategory.GOVERNING_BODY,
        collection_method=CollectionMethod.RSS,
    )
    with unit_of_work(store) as work:
        work.add(source)
    return source.id


def write(store: Engine, **given: object) -> None:
    """Write a run past the model, as plain SQL: a running run, but for what is given."""
    row: dict[str, object] = {
        "source_id": 1,
        "started_at": START,
        "ended_at": None,
        "outcome": "running",
        "records_seen": 0,
        "records_added": 0,
        "records_changed": 0,
        "records_unchanged": 0,
        "error": None,
        "created_at": MOMENT,
        "updated_at": MOMENT,
    }
    assert set(given) <= set(row)
    row.update(given)
    with store.begin() as connection:
        connection.exec_driver_sql(
            f"INSERT INTO collection_run ({', '.join(row)}) "  # noqa: S608
            f"VALUES ({', '.join('?' * len(row))})",
            tuple(row.values()),
        )


def held(store: Engine) -> list[tuple[object, ...]]:
    """What the table holds, as SQLite holds it, by the key, without the two times."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT source_id, started_at, ended_at, outcome, records_seen, records_added, "
            "records_changed, records_unchanged, error FROM collection_run ORDER BY id"
        )
        return [tuple(row) for row in found]


def sources(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM source ORDER BY id")
        return [str(name) for (name,) in found]


def test_a_new_run_is_running_and_has_counted_nothing(
    newest: Engine, clock: list[datetime]
) -> None:
    source = a_source(newest)

    with unit_of_work(newest) as work:
        work.add(CollectionRun(source_id=source, started_at=STARTED))

    with unit_of_work(newest) as work:
        found = work.execute(select(CollectionRun)).scalar_one()
    assert found.id == 1
    assert found.source_id == source
    assert found.started_at == STARTED
    assert found.ended_at is None
    assert found.outcome is RunOutcome.RUNNING
    assert [getattr(found, count) for count in COUNTS] == [0, 0, 0, 0]
    assert found.error is None
    assert found.created_at == found.updated_at == clock[1]
    assert held(newest) == [(source, START, None, "running", 0, 0, 0, 0, None)]


def test_a_run_that_ends_says_when_how_and_what_it_changed(
    newest: Engine, clock: list[datetime]
) -> None:
    source = a_source(newest)
    with unit_of_work(newest) as work:
        work.add(CollectionRun(source_id=source, started_at=STARTED))

    with unit_of_work(newest) as work:
        run = work.execute(select(CollectionRun)).scalar_one()
        run.ended_at = ENDED
        run.outcome = RunOutcome.SUCCEEDED
        run.records_seen = 40
        run.records_added = 3
        run.records_changed = 2
        run.records_unchanged = 34

    assert held(newest) == [(source, START, END, "succeeded", 40, 3, 2, 34, None)]
    with unit_of_work(newest) as work:
        found = work.execute(select(CollectionRun)).scalar_one()
    assert found.ended_at == ENDED
    assert found.outcome is RunOutcome.SUCCEEDED
    assert found.created_at == clock[1]
    assert found.updated_at == clock[2]


def test_a_run_that_fails_says_what_went_wrong(newest: Engine) -> None:
    source = a_source(newest)
    with unit_of_work(newest) as work:
        work.add(CollectionRun(source_id=source, started_at=STARTED))

    with unit_of_work(newest) as work:
        run = work.execute(select(CollectionRun)).scalar_one()
        run.ended_at = ENDED
        run.outcome = RunOutcome.FAILED
        run.records_seen = 7
        run.error = "The feed did not answer."

    assert held(newest) == [(source, START, END, "failed", 7, 0, 0, 0, "The feed did not answer.")]


@pytest.mark.parametrize("outcome", list(RunOutcome))
def test_a_run_can_have_every_outcome_on_the_list(newest: Engine, outcome: RunOutcome) -> None:
    source = a_source(newest)
    ended, error = TAKEN[outcome.value]

    with unit_of_work(newest) as work:
        work.add(
            CollectionRun(
                source_id=source,
                started_at=STARTED,
                ended_at=None if ended is None else ENDED,
                outcome=outcome,
                error=error,
            )
        )

    with unit_of_work(newest) as work:
        assert work.execute(select(CollectionRun.outcome)).scalar_one() is outcome
    assert held(newest) == [(source, START, ended, outcome.value, 0, 0, 0, 0, error)]


@pytest.mark.parametrize("text", ["cancelled", "Succeeded", "success", "events", ""])
def test_the_table_refuses_an_outcome_that_is_not_on_the_list(newest: Engine, text: str) -> None:
    a_source(newest)

    with refused("CHECK constraint failed: ck_collection_run_outcome_one_of"):
        write(newest, outcome=text, ended_at=END)

    assert held(newest) == []


def test_a_source_can_have_several_runs_and_two_that_started_together(newest: Engine) -> None:
    source = a_source(newest)

    with unit_of_work(newest) as work:
        work.add_all(
            [
                CollectionRun(source_id=source, started_at=STARTED),
                CollectionRun(source_id=source, started_at=STARTED),
                CollectionRun(source_id=source, started_at=ENDED),
            ]
        )

    assert [(row[0], row[1]) for row in held(newest)] == [
        (source, START),
        (source, START),
        (source, END),
    ]


def test_a_run_belongs_to_a_source_that_exists(newest: Engine) -> None:
    source = a_source(newest)

    with refused(BROKEN_KEY), unit_of_work(newest) as work:
        work.add(CollectionRun(source_id=source + 1, started_at=STARTED))

    assert held(newest) == []


@pytest.mark.parametrize("column", ["source_id", "started_at", "outcome", *COUNTS])
def test_a_run_names_its_source_its_start_its_outcome_and_its_counts(
    newest: Engine, column: str
) -> None:
    a_source(newest)

    with refused(f"NOT NULL constraint failed: collection_run.{column}"):
        write(newest, **{column: None})

    assert held(newest) == []


def test_a_source_that_has_runs_cannot_be_deleted(newest: Engine) -> None:
    source = a_source(newest)
    with unit_of_work(newest) as work:
        work.add(CollectionRun(source_id=source, started_at=STARTED))

    with refused(BROKEN_KEY), unit_of_work(newest) as work:
        work.execute(delete(Source).where(Source.id == source))

    assert sources(newest) == ["Example Federation"]
    assert held(newest) == [(source, START, None, "running", 0, 0, 0, 0, None)]


def test_a_source_whose_runs_were_taken_away_can_be_deleted(newest: Engine) -> None:
    source = a_source(newest)
    other = a_source(newest, "Example Club")
    with unit_of_work(newest) as work:
        work.add_all(
            [
                CollectionRun(source_id=source, started_at=STARTED),
                CollectionRun(source_id=other, started_at=STARTED),
            ]
        )

    with unit_of_work(newest) as work:
        work.execute(delete(CollectionRun).where(CollectionRun.source_id == source))
        work.execute(delete(Source).where(Source.id == source))

    assert sources(newest) == ["Example Club"]
    assert held(newest) == [(other, START, None, "running", 0, 0, 0, 0, None)]


def test_a_run_cannot_be_moved_to_a_source_that_does_not_exist(newest: Engine) -> None:
    source = a_source(newest)
    with unit_of_work(newest) as work:
        work.add(CollectionRun(source_id=source, started_at=STARTED))

    with refused(BROKEN_KEY), unit_of_work(newest) as work:
        work.execute(select(CollectionRun)).scalar_one().source_id = source + 1

    assert held(newest) == [(source, START, None, "running", 0, 0, 0, 0, None)]


def test_a_run_cannot_end_before_it_started(newest: Engine) -> None:
    a_source(newest)

    with refused("CHECK constraint failed: ck_collection_run_ended_at_not_before_started_at"):
        write(newest, outcome="succeeded", ended_at=BEFORE)

    assert held(newest) == []


def test_a_run_cannot_be_given_an_end_before_its_start(newest: Engine) -> None:
    source = a_source(newest)
    with unit_of_work(newest) as work:
        work.add(CollectionRun(source_id=source, started_at=STARTED))

    with (
        refused("CHECK constraint failed: ck_collection_run_ended_at_not_before_started_at"),
        unit_of_work(newest) as work,
    ):
        run = work.execute(select(CollectionRun)).scalar_one()
        run.ended_at = STARTED - timedelta(microseconds=1)
        run.outcome = RunOutcome.SUCCEEDED

    assert held(newest) == [(source, START, None, "running", 0, 0, 0, 0, None)]


def test_a_run_can_end_at_the_moment_it_started(newest: Engine) -> None:
    source = a_source(newest)

    write(newest, outcome="succeeded", ended_at=START)

    assert held(newest) == [(source, START, START, "succeeded", 0, 0, 0, 0, None)]


@pytest.mark.parametrize(
    ("outcome", "ended_at", "error"),
    [
        ("running", END, None),
        ("interrupted", END, None),
        ("succeeded", None, None),
        ("failed", None, "The feed did not answer."),
    ],
)
def test_only_a_run_that_succeeded_or_failed_says_when_it_ended_and_it_must(
    newest: Engine, outcome: str, ended_at: str | None, error: str | None
) -> None:
    a_source(newest)

    with refused("CHECK constraint failed: ck_collection_run_ended_at_when_succeeded_or_failed"):
        write(newest, outcome=outcome, ended_at=ended_at, error=error)

    assert held(newest) == []


@pytest.mark.parametrize(
    ("outcome", "error"),
    [
        ("failed", None),
        ("running", "The feed did not answer."),
        ("succeeded", "The feed did not answer."),
        ("interrupted", "The feed did not answer."),
    ],
)
def test_only_a_run_that_failed_has_an_error_and_it_must(
    newest: Engine, outcome: str, error: str | None
) -> None:
    a_source(newest)

    with refused("CHECK constraint failed: ck_collection_run_error_when_failed"):
        write(newest, outcome=outcome, ended_at=TAKEN[outcome][0], error=error)

    assert held(newest) == []


@pytest.mark.parametrize("error", ["", " ", "\t\n"])
def test_the_error_of_a_run_is_not_empty(newest: Engine, error: str) -> None:
    a_source(newest)

    with refused("CHECK constraint failed: ck_collection_run_error_not_empty"):
        write(newest, outcome="failed", ended_at=END, error=error)

    assert held(newest) == []


@pytest.mark.parametrize("count", COUNTS)
def test_a_count_cannot_be_below_nothing(newest: Engine, count: str) -> None:
    a_source(newest)

    with refused(f"CHECK constraint failed: ck_collection_run_{count}_not_negative"):
        write(newest, **{count: -1})

    assert held(newest) == []


@pytest.mark.parametrize("count", COUNTS)
def test_a_count_is_a_whole_number(newest: Engine, count: str) -> None:
    a_source(newest)

    with refused(f"cannot store REAL value in INTEGER column collection_run.{count}"):
        write(newest, **{count: 1.5})

    assert held(newest) == []


def test_the_counts_need_not_add_up(newest: Engine) -> None:
    # A record that was refused was seen, and was neither added nor changed
    # nor unchanged. What a run counts is not held to a sum.
    source = a_source(newest)

    write(newest, records_seen=10, records_added=1, records_changed=2, records_unchanged=3)

    assert held(newest) == [(source, START, None, "running", 10, 1, 2, 3, None)]
