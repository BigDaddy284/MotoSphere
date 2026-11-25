"""Tests of the index over the source of a collected record, against a real SQLite file.

An index is there to be used. These tests ask SQLite itself how it will
answer what is asked about the records of one source, in a store that
the migrations built, and hold it to the index. The tables of collected
records are made for the tests, beside the real ones.
"""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, Index, MetaData, delete, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session

from motosphere.db.base import NAMING
from motosphere.db.models import SCHEMA, Source
from motosphere.db.models.provenance import Collected, Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.texts import NotEmpty
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 25, 9, 30, tzinfo=UTC)
OF_THE_RECORDS = "ix_proof_record_source_id"
OF_THE_TRACKS = "ix_proof_track_source_id"
# What SQLite says when it goes straight to the records of one source, when
# it needs the rows and when the index alone answers.
BY_THE_INDEX = f"SEARCH proof_record USING INDEX {OF_THE_RECORDS} (source_id=?)"
BY_THE_INDEX_ALONE = f"SEARCH proof_record USING COVERING INDEX {OF_THE_RECORDS} (source_id=?)"
TRACKS_BY_THE_INDEX_ALONE = f"SEARCH proof_track USING COVERING INDEX {OF_THE_TRACKS} (source_id=?)"
# The second of the three sources of these tests.
THE_SOURCE = 2


class Proof(Collected):
    """A model of collected records of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=NAMING)


# A record refers to its source, so the schema of the tests knows that
# table too. It is not made from here: the migrations have made it.
SCHEMA.tables["source"].to_metadata(Proof.metadata)


class ProofRecord(Proof):
    """A model that says nothing of its own."""

    __tablename__ = "proof_record"


class ProofTrack(Proof):
    """A model that gives its table an index of its own."""

    __tablename__ = "proof_track"
    __table_args__ = (Index(None, "name"),)

    name: Mapped[NotEmpty]


# What is asked about the records of one source, as the store's code will
# ask it: each question with what SQLite says of how it answers.
QUESTIONS: dict[str, tuple[Callable[[Session], Any], str]] = {
    "which records came from it": (
        lambda work: work.scalars(
            select(ProofRecord).where(ProofRecord.source_id == THE_SOURCE)
        ).all(),
        BY_THE_INDEX,
    ),
    "how many records came from it": (
        lambda work: work.scalar(
            select(func.count()).select_from(ProofRecord).where(ProofRecord.source_id == THE_SOURCE)
        ),
        BY_THE_INDEX_ALONE,
    ),
    "whether any record came from it": (
        lambda work: work.scalar(
            select(ProofRecord.id).where(ProofRecord.source_id == THE_SOURCE).limit(1)
        ),
        BY_THE_INDEX_ALONE,
    ),
    "which of its records were not seen since a moment": (
        lambda work: work.scalars(
            select(ProofRecord).where(
                ProofRecord.source_id == THE_SOURCE, ProofRecord.last_verified_at < COLLECTED
            )
        ).all(),
        BY_THE_INDEX,
    ),
    "take its records away": (
        lambda work: work.execute(delete(ProofRecord).where(ProofRecord.source_id == THE_SOURCE)),
        BY_THE_INDEX_ALONE,
    ),
}
EACH_QUESTION = pytest.mark.parametrize("question", list(QUESTIONS))


@pytest.fixture
def made(newest: Engine) -> Engine:
    """The newest store, with the tables of the tests in it and records of three sources."""
    with newest.begin() as connection:
        Proof.metadata.create_all(connection)
    with unit_of_work(newest) as work:
        for name in ("Example Federation", "Example Club", "Example Track"):
            source = Source(
                name=name,
                website="https://federation.example",
                category=SourceCategory.GOVERNING_BODY,
                collection_method=CollectionMethod.HTML,
            )
            work.add(source)
            work.flush()
            said = {
                "source_id": source.id,
                "collected_at": COLLECTED,
                "last_verified_at": COLLECTED,
                "extraction_method": CollectionMethod.HTML,
                "confidence": Confidence.MEDIUM,
                "verification_status": VerificationStatus.OFFICIAL,
            }
            for number in range(1, 4):
                address = f"https://federation.example/{source.id}/{number}"
                work.add(ProofRecord(source_address=address, **said))
            work.add(ProofTrack(name=name, source_address="https://federation.example", **said))
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
                with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
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
        connection.exec_driver_sql(f"DROP INDEX {OF_THE_RECORDS}")
        connection.exec_driver_sql(f"DROP INDEX {OF_THE_TRACKS}")


def to_delete_the_source(work: Session) -> None:
    """Delete a source that records came from, which SQLite refuses when it has looked."""
    work.execute(delete(Source).where(Source.id == THE_SOURCE))


def test_in_the_file_every_table_of_collected_records_has_the_index(made: Engine) -> None:
    with made.connect() as connection:
        listed = {
            table: sorted(
                (name, bool(unique), made_by, bool(partial))
                for _, name, unique, made_by, partial in connection.exec_driver_sql(
                    f"PRAGMA index_list({table})"
                )
            )
            for table in ("proof_record", "proof_track")
        }
        indexed = {
            index: [
                name for _, _, name in connection.exec_driver_sql(f"PRAGMA index_info({index})")
            ]
            for index in (OF_THE_RECORDS, OF_THE_TRACKS)
        }
        written = [
            str(sql)
            for (sql,) in connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type = 'index' AND name LIKE "
                "'ix_proof%source_id' ORDER BY name"
            )
        ]

    # Its name, that two rows can be alike in it, that a statement made it,
    # and that it is over all rows. A model's own index is there as well.
    assert listed == {
        "proof_record": [(OF_THE_RECORDS, False, "c", False)],
        "proof_track": [
            ("ix_proof_track_name", False, "c", False),
            (OF_THE_TRACKS, False, "c", False),
        ],
    }
    assert indexed == {OF_THE_RECORDS: ["source_id"], OF_THE_TRACKS: ["source_id"]}
    assert written == [
        "CREATE INDEX ix_proof_record_source_id ON proof_record (source_id)",
        "CREATE INDEX ix_proof_track_source_id ON proof_track (source_id)",
    ]


@EACH_QUESTION
def test_what_is_asked_about_the_records_of_one_source_is_answered_by_the_index(
    made: Engine, question: str
) -> None:
    ask, answered = QUESTIONS[question]

    ((statement, given),) = sent_by(made, ask)

    assert "proof_record" in statement
    assert plan_of(made, statement, given) == [answered]


@EACH_QUESTION
def test_without_the_index_the_whole_table_is_read(made: Engine, question: str) -> None:
    # What the index is for: the same statement, in the same store without it.
    ask, _ = QUESTIONS[question]
    ((statement, given),) = sent_by(made, ask)
    without_the_indexes(made)

    assert plan_of(made, statement, given) == ["SCAN proof_record"]


def test_sqlite_looks_for_the_records_of_a_source_by_the_index_when_the_source_is_deleted(
    made: Engine,
) -> None:
    ((statement, given),) = sent_by(made, to_delete_the_source, refused=True)

    plan = plan_of(made, statement, given)

    assert statement.startswith("DELETE FROM source")
    assert [step for step in plan if "proof_" in step] == sorted(
        [BY_THE_INDEX_ALONE, TRACKS_BY_THE_INDEX_ALONE], reverse=True
    )
    # Nor does it read the whole of any other table that refers to a source.
    assert [step for step in plan if step.startswith("SCAN")] == []


def test_without_the_index_every_table_of_collected_records_is_read_to_delete_a_source(
    made: Engine,
) -> None:
    ((statement, given),) = sent_by(made, to_delete_the_source, refused=True)
    without_the_indexes(made)

    plan = plan_of(made, statement, given)

    assert sorted(step for step in plan if "proof_" in step) == [
        "SCAN proof_record",
        "SCAN proof_track",
    ]


def answers(store: Engine) -> list[Any]:
    """What the store answers about the records of each source, and whether a source can go."""
    said: list[Any] = []
    with unit_of_work(store) as work:
        for source in (1, 2, 3, 4):
            of_it = ProofRecord.source_id == source
            said.append(list(work.scalars(select(ProofRecord.id).where(of_it).order_by("id"))))
            said.append(work.scalar(select(func.count()).select_from(ProofRecord).where(of_it)))
    try:
        with unit_of_work(store) as work:
            to_delete_the_source(work)
    except IntegrityError as refusal:
        said.append(str(refusal.orig))
    return said


def test_the_index_changes_no_answer(made: Engine) -> None:
    with_it = answers(made)
    without_the_indexes(made)

    without_it = answers(made)

    assert with_it == without_it
    assert with_it == [
        [1, 2, 3],
        3,
        [4, 5, 6],
        3,
        [7, 8, 9],
        3,
        [],
        0,
        "FOREIGN KEY constraint failed",
    ]
