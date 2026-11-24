"""Tests of how a source is doing, told by its runs, against a real SQLite file.

The store of every test is built by the migrations, and its runs are of
every outcome. What a test asks is asked of the store itself: nothing
here is a mock.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine

from motosphere.db.models import CollectionRun, Source
from motosphere.db.models.collection_run import RunOutcome
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.source_health import SourceHealth, SourceStanding, standing_of
from motosphere.db.work import unit_of_work

# The moments runs start at, an hour apart: HOUR[3] is three hours after HOUR[0].
HOUR = [datetime(2026, 11, 24, 6, 0, tzinfo=UTC) + timedelta(hours=hours) for hours in range(8)]
RUNNING = RunOutcome.RUNNING
SUCCEEDED = RunOutcome.SUCCEEDED
FAILED = RunOutcome.FAILED
INTERRUPTED = RunOutcome.INTERRUPTED
HEALTH_AFTER = {
    SUCCEEDED: SourceHealth.HEALTHY,
    FAILED: SourceHealth.FAILING,
    INTERRUPTED: SourceHealth.INTERRUPTED,
}


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


def a_run(store: Engine, source: int, started: datetime, outcome: RunOutcome) -> None:
    """Store a run of this outcome as the table takes it. One that failed says so by its start."""
    over = outcome in (SUCCEEDED, FAILED)
    with unit_of_work(store) as work:
        work.add(
            CollectionRun(
                source_id=source,
                started_at=started,
                ended_at=started + timedelta(minutes=4) if over else None,
                outcome=outcome,
                error=error_of(started) if outcome is FAILED else None,
            )
        )


def error_of(started: datetime) -> str:
    """The error of the run that started then and failed."""
    return f"The feed did not answer at {started:%H:%M}."


def asked(store: Engine, source: int) -> SourceStanding:
    with unit_of_work(store) as work:
        return standing_of(work, source)


def test_of_a_source_that_has_no_run_nothing_is_said_but_that(newest: Engine) -> None:
    source = a_source(newest)

    assert asked(newest, source) == SourceStanding(
        last_attempt=None,
        last_success=None,
        last_error=None,
        health=SourceHealth.NOT_YET_SCANNED,
    )


def test_a_source_whose_first_run_is_still_running_was_attempted_and_not_yet_scanned(
    newest: Engine,
) -> None:
    source = a_source(newest)
    a_run(newest, source, HOUR[0], RUNNING)

    assert asked(newest, source) == SourceStanding(
        last_attempt=HOUR[0],
        last_success=None,
        last_error=None,
        health=SourceHealth.NOT_YET_SCANNED,
    )


def test_a_source_whose_only_run_succeeded_is_healthy(newest: Engine) -> None:
    source = a_source(newest)
    a_run(newest, source, HOUR[0], SUCCEEDED)

    assert asked(newest, source) == SourceStanding(
        last_attempt=HOUR[0], last_success=HOUR[0], last_error=None, health=SourceHealth.HEALTHY
    )


def test_a_source_whose_only_run_failed_is_failing_and_says_why(newest: Engine) -> None:
    source = a_source(newest)
    a_run(newest, source, HOUR[0], FAILED)

    assert asked(newest, source) == SourceStanding(
        last_attempt=HOUR[0],
        last_success=None,
        last_error="The feed did not answer at 06:00.",
        health=SourceHealth.FAILING,
    )


def test_a_source_whose_only_run_was_interrupted_says_so_and_has_no_error(newest: Engine) -> None:
    source = a_source(newest)
    a_run(newest, source, HOUR[0], INTERRUPTED)

    assert asked(newest, source) == SourceStanding(
        last_attempt=HOUR[0],
        last_success=None,
        last_error=None,
        health=SourceHealth.INTERRUPTED,
    )


@pytest.mark.parametrize("last", list(RunOutcome))
def test_the_last_attempt_is_the_newest_run_whatever_became_of_it(
    newest: Engine, last: RunOutcome
) -> None:
    source = a_source(newest)
    for started, outcome in zip(HOUR, [SUCCEEDED, FAILED, INTERRUPTED, last], strict=False):
        a_run(newest, source, started, outcome)

    assert asked(newest, source).last_attempt == HOUR[3]


@pytest.mark.parametrize("later", [RUNNING, FAILED, INTERRUPTED])
def test_the_last_success_is_the_newest_run_that_succeeded_whatever_came_after(
    newest: Engine, later: RunOutcome
) -> None:
    source = a_source(newest)
    for started, outcome in zip(HOUR, [SUCCEEDED, SUCCEEDED, later], strict=False):
        a_run(newest, source, started, outcome)

    said = asked(newest, source)

    assert said.last_success == HOUR[1]
    assert said.last_attempt == HOUR[2]


@pytest.mark.parametrize("over", [SUCCEEDED, FAILED, INTERRUPTED])
def test_the_health_is_told_by_the_newest_run_that_is_over(
    newest: Engine, over: RunOutcome
) -> None:
    source = a_source(newest)
    # Before it, a run of each other kind; after it, one that is still running.
    for started, outcome in zip(
        HOUR, [*(other for other in HEALTH_AFTER if other is not over), over, RUNNING], strict=False
    ):
        a_run(newest, source, started, outcome)

    assert asked(newest, source).health is HEALTH_AFTER[over]


def test_the_last_error_is_that_of_the_newest_run_that_failed(newest: Engine) -> None:
    source = a_source(newest)
    for started, outcome in zip(HOUR, [FAILED, SUCCEEDED, FAILED, FAILED], strict=False):
        a_run(newest, source, started, outcome)

    assert asked(newest, source) == SourceStanding(
        last_attempt=HOUR[3],
        last_success=HOUR[1],
        last_error="The feed did not answer at 09:00.",
        health=SourceHealth.FAILING,
    )


def test_the_last_error_is_no_longer_said_once_a_later_run_succeeded(newest: Engine) -> None:
    source = a_source(newest)
    for started, outcome in zip(HOUR, [FAILED, FAILED, SUCCEEDED], strict=False):
        a_run(newest, source, started, outcome)

    assert asked(newest, source) == SourceStanding(
        last_attempt=HOUR[2], last_success=HOUR[2], last_error=None, health=SourceHealth.HEALTHY
    )


@pytest.mark.parametrize("later", [RUNNING, INTERRUPTED])
def test_the_last_error_is_still_said_while_no_later_run_has_succeeded(
    newest: Engine, later: RunOutcome
) -> None:
    source = a_source(newest)
    for started, outcome in zip(HOUR, [SUCCEEDED, FAILED, later], strict=False):
        a_run(newest, source, started, outcome)

    said = asked(newest, source)

    assert said.last_error == "The feed did not answer at 07:00."
    assert said.last_success == HOUR[0]
    assert said.health is (SourceHealth.FAILING if later is RUNNING else SourceHealth.INTERRUPTED)


def test_the_newest_run_is_the_one_that_started_last_not_the_one_stored_last(
    newest: Engine,
) -> None:
    source = a_source(newest)
    # Stored in this order; the run that failed started last.
    a_run(newest, source, HOUR[1], SUCCEEDED)
    a_run(newest, source, HOUR[2], FAILED)
    a_run(newest, source, HOUR[0], SUCCEEDED)

    assert asked(newest, source) == SourceStanding(
        last_attempt=HOUR[2],
        last_success=HOUR[1],
        last_error="The feed did not answer at 08:00.",
        health=SourceHealth.FAILING,
    )


@pytest.mark.parametrize(
    ("stored", "health", "error"),
    [
        ([FAILED, SUCCEEDED], SourceHealth.HEALTHY, None),
        ([SUCCEEDED, FAILED], SourceHealth.FAILING, "The feed did not answer at 06:00."),
    ],
)
def test_of_two_runs_that_started_together_the_one_stored_last_is_the_newer(
    newest: Engine, stored: list[RunOutcome], health: SourceHealth, error: str | None
) -> None:
    source = a_source(newest)
    for outcome in stored:
        a_run(newest, source, HOUR[0], outcome)

    said = asked(newest, source)

    assert said.health is health
    assert said.last_error == error


def test_a_source_is_told_by_its_own_runs_and_not_by_those_of_another(newest: Engine) -> None:
    first = a_source(newest)
    second = a_source(newest, "Example Club")
    third = a_source(newest, "Example Track")
    a_run(newest, first, HOUR[0], SUCCEEDED)
    a_run(newest, second, HOUR[1], FAILED)
    a_run(newest, second, HOUR[2], RUNNING)

    assert asked(newest, first) == SourceStanding(
        last_attempt=HOUR[0], last_success=HOUR[0], last_error=None, health=SourceHealth.HEALTHY
    )
    assert asked(newest, second) == SourceStanding(
        last_attempt=HOUR[2],
        last_success=None,
        last_error="The feed did not answer at 07:00.",
        health=SourceHealth.FAILING,
    )
    assert asked(newest, third) == SourceStanding(
        last_attempt=None,
        last_success=None,
        last_error=None,
        health=SourceHealth.NOT_YET_SCANNED,
    )


def test_the_times_come_back_as_times_in_utc(newest: Engine) -> None:
    source = a_source(newest)
    a_run(newest, source, HOUR[0], SUCCEEDED)

    said = asked(newest, source)

    assert said.last_attempt is not None
    assert said.last_attempt.utcoffset() == timedelta(0)
    assert said.last_success is not None
    assert said.last_success.utcoffset() == timedelta(0)


@pytest.mark.parametrize("key", [2, 0, -1])
def test_a_key_that_no_source_has_is_refused_in_plain_words(newest: Engine, key: int) -> None:
    source = a_source(newest)
    a_run(newest, source, HOUR[0], SUCCEEDED)

    with pytest.raises(LookupError) as refusal:
        asked(newest, key)

    assert str(refusal.value) == f"There is no source with the key {key}."


def test_asking_writes_nothing_to_the_store(newest: Engine, clock: list[datetime]) -> None:
    file = Path(str(newest.url.database))
    source = a_source(newest)
    for started, outcome in zip(HOUR, list(RunOutcome), strict=False):
        a_run(newest, source, started, outcome)
    before = file.read_bytes()
    asked_the_clock = len(clock)

    with unit_of_work(newest) as work:
        standing_of(work, source)
        assert not work.new
        assert not work.dirty
        assert not work.deleted

    assert file.read_bytes() == before
    assert len(clock) == asked_the_clock


@pytest.mark.parametrize("name", ["last_attempt", "last_success", "last_error", "health"])
def test_what_is_said_cannot_be_changed_afterwards(newest: Engine, name: str) -> None:
    source = a_source(newest)
    said = asked(newest, source)

    with pytest.raises(AttributeError):
        setattr(said, name, None)

    assert said == SourceStanding(None, None, None, SourceHealth.NOT_YET_SCANNED)
