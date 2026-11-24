"""Tests of the index of the runs of one source, against a real SQLite file.

An index is there to be used. These tests ask SQLite itself how it will
answer the statements the store's code really sends, in a store that the
migrations built, and hold it to the index.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection, Engine, event

from motosphere.db.models import CollectionRun, Source
from motosphere.db.models.collection_run import RunOutcome
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.source_health import SourceHealth, standing_of
from motosphere.db.work import unit_of_work

INDEX = "ix_collection_run_source_id_started_at"
STARTED = datetime(2026, 11, 24, 6, 0, tzinfo=UTC)
# What SQLite says when it goes straight to the runs of one source.
BY_THE_INDEX = f"SEARCH collection_run USING INDEX {INDEX} (source_id=?)"


def some_runs(store: Engine) -> None:
    """Store three sources, each with a run of every outcome, an hour apart."""
    with unit_of_work(store) as work:
        for name in ("Example Federation", "Example Club", "Example Track"):
            source = Source(
                name=name,
                website="https://federation.example",
                category=SourceCategory.GOVERNING_BODY,
                collection_method=CollectionMethod.RSS,
            )
            work.add(source)
            work.flush()
            for hours, outcome in enumerate(RunOutcome):
                started = STARTED + timedelta(hours=hours)
                over = outcome in (RunOutcome.SUCCEEDED, RunOutcome.FAILED)
                work.add(
                    CollectionRun(
                        source_id=source.id,
                        started_at=started,
                        ended_at=started + timedelta(minutes=4) if over else None,
                        outcome=outcome,
                        error="The feed did not answer." if outcome is RunOutcome.FAILED else None,
                    )
                )


def statements_of_standing_of(store: Engine, source: int) -> list[tuple[str, Sequence[object]]]:
    """Every statement ``standing_of`` sends for this source, with what it is given."""
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
        with unit_of_work(store) as work:
            standing_of(work, source)
    finally:
        event.remove(store, "before_cursor_execute", remember)
    return sent


def plan_of(store: Engine, statement: str, given: Sequence[object]) -> list[str]:
    """SQLite's own account of how it will answer a statement, step by step."""
    with store.connect() as connection:
        steps = connection.exec_driver_sql("EXPLAIN QUERY PLAN " + statement, tuple(given))
        return [str(step[3]) for step in steps]


def test_the_newest_schema_has_the_index_over_the_source_and_the_start(newest: Engine) -> None:
    with newest.connect() as connection:
        columns = connection.exec_driver_sql(f"PRAGMA index_info({INDEX})").all()
        listed = connection.exec_driver_sql("PRAGMA index_list(collection_run)").all()

    assert [name for _, _, name in columns] == ["source_id", "started_at"]
    # Its name, that two rows can be alike in it, that a statement made it,
    # and that it is over all rows.
    assert [(name, unique, origin, partial) for _, name, unique, origin, partial in listed] == [
        (INDEX, 0, "c", 0)
    ]


def test_every_question_about_the_runs_of_a_source_is_answered_by_the_index(
    newest: Engine,
) -> None:
    some_runs(newest)

    about_the_runs = [
        (statement, given)
        for statement, given in statements_of_standing_of(newest, 2)
        if "FROM collection_run" in statement
    ]

    assert len(about_the_runs) == 4
    for statement, given in about_the_runs:
        # One step: the runs of the source are found by the index, and
        # nothing is sorted afterwards.
        assert plan_of(newest, statement, given) == [BY_THE_INDEX]


def test_without_the_index_the_whole_table_is_read_and_sorted(newest: Engine) -> None:
    # What the index is for: the same statements, in the same store without it.
    some_runs(newest)
    statements = [
        (statement, given)
        for statement, given in statements_of_standing_of(newest, 2)
        if "FROM collection_run" in statement
    ]
    with newest.begin() as connection:
        connection.exec_driver_sql(f"DROP INDEX {INDEX}")

    for statement, given in statements:
        assert plan_of(newest, statement, given) == [
            "SCAN collection_run",
            "USE TEMP B-TREE FOR ORDER BY",
        ]


def test_the_index_changes_no_answer(newest: Engine) -> None:
    some_runs(newest)
    with unit_of_work(newest) as work:
        with_it = [standing_of(work, source) for source in (1, 2, 3)]
    with newest.begin() as connection:
        connection.exec_driver_sql(f"DROP INDEX {INDEX}")

    with unit_of_work(newest) as work:
        without_it = [standing_of(work, source) for source in (1, 2, 3)]

    assert with_it == without_it
    assert [said.health for said in with_it] == [SourceHealth.INTERRUPTED] * 3
    assert {said.last_attempt for said in with_it} == {STARTED + timedelta(hours=3)}
    assert {said.last_success for said in with_it} == {STARTED + timedelta(hours=1)}
