"""Tests of the columns every collected record has, against a real SQLite file.

The store of every test is built by the migrations, as a real store is,
so the source a record refers to is the real table of the sources. The
tables of collected records are made for the tests: their models are
subclasses of the real ``Collected``, kept in a schema of their own
(``Proof.metadata``), so the real schema never sees them. What a table
must refuse is also written past the model.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

import pytest
from sqlalchemy import Engine, MetaData, UniqueConstraint, delete, select, update
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Mapped

from motosphere.db.base import NAMING
from motosphere.db.models import SCHEMA, Source
from motosphere.db.models.provenance import Collected, Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.texts import NotEmpty
from motosphere.db.work import unit_of_work

COLLECTED = datetime(2026, 11, 25, 9, 30, tzinfo=UTC)
SEEN_AGAIN = COLLECTED + timedelta(days=7)
# An offset of one hour ahead of UTC, as Paris has it in winter.
IN_PARIS = timezone(timedelta(hours=1))
PUBLISHED = date(2026, 11, 22)
ADDRESS = "https://federation.example/results/2026/round-1"
# The same moments and the same day, as the file holds them.
AT = "2026-11-25T09:30:00.000000+00:00"
JUST_BEFORE = "2026-11-25T09:29:59.999999+00:00"
JUST_AFTER = "2026-11-25T09:30:00.000001+00:00"
A_WEEK_LATER = "2026-12-02T09:30:00.000000+00:00"
ON = "2026-11-22"
MOMENT = "2026-11-25T09:31:00.000000+00:00"
BROKEN_KEY = "FOREIGN KEY constraint failed"
REFUSED = "CHECK constraint failed: ck_proof_record_{}"
THE_TWO_TIMES = "last_verified_at_not_before_collected_at"
# What must be said of every record: the columns of the set that a row
# cannot be without.
MUST_BE_SAID = [
    "source_id",
    "source_address",
    "collected_at",
    "last_verified_at",
    "extraction_method",
    "confidence",
    "verification_status",
]
# A row written with plain SQL: the eight columns of the set in their
# order, and the two times, which only the store's code sets.
PAST_THE_MODEL = (
    "INSERT INTO proof_record (source_id, source_address, collected_at, published_on, "
    "last_verified_at, extraction_method, confidence, verification_status, created_at, "
    "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
A_TRACK_PAST_THE_MODEL = (
    "INSERT INTO proof_track (name, source_id, source_address, collected_at, published_on, "
    "last_verified_at, extraction_method, confidence, verification_status, created_at, "
    "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
# Text that is on none of the three lists, or on another list than the column's.
NOT_ON_ITS_LIST = {
    "extraction_method": ["scraping", "HTML extraction", "html  extraction", "high", ""],
    "confidence": ["certain", "High", "high ", "official", "html extraction", "1", ""],
    "verification_status": ["verified", "Official", "medium", "rss feed", ""],
}


class Proof(Collected):
    """A model of collected records of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=NAMING)


# A record refers to its source, so the schema of the tests knows that
# table too. It is not made from here: the migrations have made it.
SCHEMA.tables["source"].to_metadata(Proof.metadata)


class ProofRecord(Proof):
    """A model that says nothing of its own: its table is the key, the set and the two times."""

    __tablename__ = "proof_record"


class ProofTrack(Proof):
    """A model that says more of its table: a column and a rule of its own."""

    __tablename__ = "proof_track"
    __table_args__ = (UniqueConstraint("name"),)

    name: Mapped[NotEmpty]


@pytest.fixture
def made(newest: Engine) -> Engine:
    """The newest store, with the tables of the tests made in it next to the real ones."""
    with newest.begin() as connection:
        Proof.metadata.create_all(connection)
    return newest


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
        collection_method=CollectionMethod.HTML,
    )
    with unit_of_work(store) as work:
        work.add(source)
    return source.id


def said(source: int, **given: Any) -> dict[str, Any]:
    """What a collector says of a record it found at this source, but for what is given."""
    record: dict[str, Any] = {
        "source_id": source,
        "source_address": ADDRESS,
        "collected_at": COLLECTED,
        "published_on": PUBLISHED,
        "last_verified_at": COLLECTED,
        "extraction_method": CollectionMethod.HTML,
        "confidence": Confidence.MEDIUM,
        "verification_status": VerificationStatus.OFFICIAL,
    }
    assert set(given) <= set(record)
    record.update(given)
    return record


def collect(store: Engine, source: int, **given: Any) -> int:
    """Store a record through the model, and give its key."""
    record = ProofRecord(**said(source, **given))
    with unit_of_work(store) as work:
        work.add(record)
    return record.id


def as_written(source: object, **given: object) -> dict[str, object]:
    """The same record as plain SQL writes it, past the model, but for what is given."""
    row: dict[str, object] = {
        "source_id": source,
        "source_address": ADDRESS,
        "collected_at": AT,
        "published_on": ON,
        "last_verified_at": AT,
        "extraction_method": "html extraction",
        "confidence": "medium",
        "verification_status": "official",
    }
    assert set(given) <= set(row)
    row.update(given)
    return row


def write(store: Engine, source: object, **given: object) -> None:
    """Write a record past the model."""
    row = as_written(source, **given)
    with store.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (*row.values(), MOMENT, MOMENT))


def held(store: Engine, table: str = "proof_record") -> list[tuple[object, ...]]:
    """What a table of the tests holds of the set, as SQLite holds it, by the key."""
    statements = {
        "proof_record": (
            "SELECT source_id, source_address, collected_at, published_on, last_verified_at, "
            "extraction_method, confidence, verification_status FROM proof_record ORDER BY id"
        ),
        "proof_track": (
            "SELECT source_id, source_address, collected_at, published_on, last_verified_at, "
            "extraction_method, confidence, verification_status FROM proof_track ORDER BY id"
        ),
    }
    with store.connect() as connection:
        return [tuple(row) for row in connection.exec_driver_sql(statements[table])]


def sources(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM source ORDER BY id")
        return [str(name) for (name,) in found]


def test_a_record_is_stored_with_where_it_came_from_and_read_back(made: Engine) -> None:
    source = a_source(made)

    key = collect(made, source)

    assert key == 1
    assert held(made) == [
        (source, ADDRESS, AT, ON, AT, "html extraction", "medium", "official"),
    ]
    with unit_of_work(made) as work:
        found = work.execute(select(ProofRecord)).scalar_one()
    assert found.source_id == source
    assert found.source_address == ADDRESS
    assert found.collected_at == COLLECTED
    assert found.published_on == PUBLISHED
    assert type(found.published_on) is date
    assert found.last_verified_at == COLLECTED
    assert found.extraction_method is CollectionMethod.HTML
    assert found.confidence is Confidence.MEDIUM
    assert found.verification_status is VerificationStatus.OFFICIAL


def test_in_the_file_the_set_is_as_the_model_says_it(made: Engine) -> None:
    with made.connect() as connection:
        columns = [
            (name, declared, bool(required), given, bool(key))
            for _, name, declared, required, given, key in connection.exec_driver_sql(
                "PRAGMA table_info(proof_record)"
            )
        ]
        references = [
            (child, parent, key, on_update, on_delete)
            for _, _, parent, child, key, on_update, on_delete, _ in connection.exec_driver_sql(
                "PRAGMA foreign_key_list(proof_record)"
            )
        ]
        indexes = connection.exec_driver_sql("PRAGMA index_list(proof_record)").all()

    assert columns == [
        ("id", "INTEGER", True, None, True),
        ("source_id", "INTEGER", True, None, False),
        ("source_address", "TEXT", True, None, False),
        ("collected_at", "TEXT", True, None, False),
        ("published_on", "TEXT", False, None, False),
        ("last_verified_at", "TEXT", True, None, False),
        ("extraction_method", "TEXT", True, None, False),
        ("confidence", "TEXT", True, None, False),
        ("verification_status", "TEXT", True, None, False),
        ("created_at", "TEXT", True, None, False),
        ("updated_at", "TEXT", True, None, False),
    ]
    assert references == [("source_id", "source", "id", "NO ACTION", "NO ACTION")]
    assert indexes == []


def test_the_file_has_the_checks_of_the_set_by_name_and_letter_for_letter(made: Engine) -> None:
    with made.connect() as connection:
        (written,) = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE name = 'proof_record'"
        ).one()

    for check in (
        "CONSTRAINT fk_proof_record_source_id_source FOREIGN KEY(source_id) REFERENCES source (id)",
        "CONSTRAINT ck_proof_record_last_verified_at_not_before_collected_at "
        "CHECK (last_verified_at >= collected_at)",
        "CONSTRAINT ck_proof_record_confidence_one_of "
        "CHECK (confidence IN ('high', 'medium', 'low'))",
        "CONSTRAINT ck_proof_record_verification_status_one_of CHECK (verification_status IN "
        "('official', 'independent', 'reconstructed', 'unverified'))",
        "CONSTRAINT ck_proof_record_extraction_method_one_of CHECK (extraction_method IN "
        "('official api', 'structured feed', 'rss feed', 'public dataset', 'html extraction', "
        "'structured document', 'json endpoint', 'sitemap discovery', "
        "'search engine discovery', 'human submission'))",
        "CONSTRAINT ck_proof_record_source_address_web_address CHECK (",
        "CONSTRAINT ck_proof_record_published_on_calendar_day CHECK (",
    ):
        assert written.count(check) == 1, check
    assert written.count("CONSTRAINT ck_") == 6
    assert written.rstrip().endswith("STRICT")


def test_the_day_a_record_was_published_may_be_unknown(made: Engine) -> None:
    source = a_source(made)

    collect(made, source, published_on=None)
    write(made, source, published_on=None)

    assert [row[3] for row in held(made)] == [None, None]
    with unit_of_work(made) as work:
        assert list(work.scalars(select(ProofRecord.published_on))) == [None, None]


@pytest.mark.parametrize("column", MUST_BE_SAID)
def test_a_record_that_does_not_say_one_of_the_other_seven_is_refused(
    made: Engine, column: str
) -> None:
    source = a_source(made)
    without = said(source)
    del without[column]

    with refused(f"NOT NULL constraint failed: proof_record.{column}"), unit_of_work(made) as work:
        work.add(ProofRecord(**without))
    with refused(f"NOT NULL constraint failed: proof_record.{column}"):
        collect(made, source, **{column: None})
    with refused(f"NOT NULL constraint failed: proof_record.{column}"):
        write(made, source, **{column: None})

    assert held(made) == []


def test_a_record_belongs_to_a_source_that_exists(made: Engine) -> None:
    source = a_source(made)

    with refused(BROKEN_KEY):
        collect(made, source + 1)
    with refused(BROKEN_KEY):
        write(made, source + 1)

    assert held(made) == []


def test_a_source_that_records_came_from_cannot_be_deleted(made: Engine) -> None:
    source = a_source(made)
    other = a_source(made, "Example Club")
    collect(made, source)

    with refused(BROKEN_KEY), unit_of_work(made) as work:
        work.execute(delete(Source).where(Source.id == source))
    with refused(BROKEN_KEY), made.begin() as connection:
        connection.exec_driver_sql("DELETE FROM source WHERE id = ?", (source,))
    with refused(BROKEN_KEY), made.begin() as connection:
        connection.exec_driver_sql("UPDATE source SET id = 99 WHERE id = ?", (source,))

    assert sources(made) == ["Example Federation", "Example Club"]
    assert [row[0] for row in held(made)] == [source]

    # A source nothing came from is deleted as before.
    with unit_of_work(made) as work:
        work.execute(delete(Source).where(Source.id == other))

    assert sources(made) == ["Example Federation"]


def test_a_source_can_be_deleted_once_its_records_are_gone(made: Engine) -> None:
    source = a_source(made)
    collect(made, source)
    collect(made, source)

    with unit_of_work(made) as work:
        work.execute(delete(ProofRecord).where(ProofRecord.id == 1))
    with refused(BROKEN_KEY), unit_of_work(made) as work:
        work.execute(delete(Source).where(Source.id == source))
    with unit_of_work(made) as work:
        work.execute(delete(ProofRecord).where(ProofRecord.source_id == source))
        work.execute(delete(Source).where(Source.id == source))

    assert sources(made) == []
    assert held(made) == []


def test_every_table_of_collected_records_holds_its_source(made: Engine) -> None:
    source = a_source(made)
    with unit_of_work(made) as work:
        work.add(ProofTrack(name="Example Park", **said(source)))

    with refused(BROKEN_KEY), unit_of_work(made) as work:
        work.execute(delete(Source).where(Source.id == source))

    assert sources(made) == ["Example Federation"]
    assert held(made) == []
    assert held(made, "proof_track") == [
        (source, ADDRESS, AT, ON, AT, "html extraction", "medium", "official"),
    ]


def test_a_record_can_be_given_to_another_source_that_exists_and_to_no_other(
    made: Engine,
) -> None:
    first = a_source(made)
    second = a_source(made, "Example Club")
    collect(made, first)

    with unit_of_work(made) as work:
        work.execute(update(ProofRecord).values(source_id=second))

    assert [row[0] for row in held(made)] == [second]

    with refused(BROKEN_KEY), unit_of_work(made) as work:
        work.execute(update(ProofRecord).values(source_id=second + 1))

    assert [row[0] for row in held(made)] == [second]


@pytest.mark.parametrize(
    "text",
    ["federation.example/results", "ftp://federation.example/results.csv", "https://", ""],
    ids=["no scheme", "another scheme", "a scheme and nothing after it", "empty text"],
)
def test_an_address_that_is_not_a_web_address_is_refused(made: Engine, text: str) -> None:
    source = a_source(made)

    with refused(REFUSED.format("source_address_web_address")):
        collect(made, source, source_address=text)
    with refused(REFUSED.format("source_address_web_address")):
        write(made, source, source_address=text)

    assert held(made) == []


@pytest.mark.parametrize(
    ("column", "text"),
    [(column, text) for column, texts in NOT_ON_ITS_LIST.items() for text in texts],
)
def test_text_that_is_not_on_the_list_of_its_column_is_refused(
    made: Engine, column: str, text: str
) -> None:
    source = a_source(made)

    with refused(REFUSED.format(f"{column}_one_of")):
        write(made, source, **{column: text})

    assert held(made) == []


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("extraction_method", Confidence.HIGH),
        ("extraction_method", "html extraction"),
        ("confidence", VerificationStatus.OFFICIAL),
        ("confidence", "high"),
        ("verification_status", Confidence.LOW),
        ("verification_status", "official"),
    ],
)
def test_a_value_that_is_not_of_the_list_of_its_column_is_refused_before_it_is_written(
    made: Engine, column: str, value: object
) -> None:
    source = a_source(made)

    with pytest.raises(StatementError, match="Only a value of the list") as refusal:
        collect(made, source, **{column: value})

    assert isinstance(refusal.value.orig, TypeError)
    assert held(made) == []


@pytest.mark.parametrize(
    ("column", "the_list"),
    [
        ("extraction_method", CollectionMethod),
        ("confidence", Confidence),
        ("verification_status", VerificationStatus),
    ],
)
def test_every_value_of_the_list_of_its_column_is_stored_as_its_text_and_read_back(
    made: Engine, column: str, the_list: type[StrEnum]
) -> None:
    source = a_source(made)
    place = list(as_written(source)).index(column)

    for value in the_list:
        collect(made, source, **{column: value})

    assert [row[place] for row in held(made)] == [value.value for value in the_list]
    with unit_of_work(made) as work:
        found = list(work.scalars(select(getattr(ProofRecord, column)).order_by(ProofRecord.id)))
    assert found == list(the_list)
    assert all(type(value) is the_list for value in found)


@pytest.mark.parametrize(
    "text",
    ["2026-02-30", "22/11/2026", "2026-11-22T00:00:00.000000+00:00", "November 2026", "2026", ""],
    ids=[
        "a day no calendar has",
        "day first",
        "a time",
        "a month",
        "a year",
        "empty text",
    ],
)
def test_a_day_of_publishing_that_is_not_a_day_is_refused(made: Engine, text: str) -> None:
    source = a_source(made)

    with refused(REFUSED.format("published_on_calendar_day")):
        write(made, source, published_on=text)

    assert held(made) == []


def test_a_time_is_not_taken_for_the_day_a_record_was_published(made: Engine) -> None:
    source = a_source(made)

    with pytest.raises(StatementError, match="A time is not stored as a day") as refusal:
        collect(made, source, published_on=COLLECTED)

    assert isinstance(refusal.value.orig, TypeError)
    assert held(made) == []


def test_a_record_may_be_published_after_the_day_it_was_collected_in_utc(made: Engine) -> None:
    # A page dated the 26th in New Zealand is read on the 25th by the clock of UTC.
    source = a_source(made)

    collect(made, source, published_on=date(2026, 11, 26))

    assert [(row[2], row[3]) for row in held(made)] == [(AT, "2026-11-26")]


@pytest.mark.parametrize(
    ("last_verified", "taken"),
    [(JUST_BEFORE, False), (AT, True), (JUST_AFTER, True), (A_WEEK_LATER, True)],
    ids=["a moment before", "the same moment", "a moment after", "a week later"],
)
def test_a_record_is_not_last_seen_at_its_source_before_it_was_collected(
    made: Engine, last_verified: str, taken: bool
) -> None:
    source = a_source(made)

    if taken:
        write(made, source, last_verified_at=last_verified)
    else:
        with refused(REFUSED.format(THE_TWO_TIMES)):
            write(made, source, last_verified_at=last_verified)

    assert [(row[2], row[4]) for row in held(made)] == ([(AT, last_verified)] if taken else [])


def test_the_model_cannot_store_a_record_last_seen_before_it_was_collected(made: Engine) -> None:
    source = a_source(made)

    with refused(REFUSED.format(THE_TWO_TIMES)):
        collect(made, source, last_verified_at=COLLECTED - timedelta(microseconds=1))

    assert held(made) == []


def test_the_two_times_are_compared_as_moments_whatever_offset_they_were_given_in(
    made: Engine,
) -> None:
    source = a_source(made)
    # 10:29 in Paris is 09:29 in UTC, a minute before the record was collected,
    # and 10:31 in Paris is a minute after it.
    before = datetime(2026, 11, 25, 10, 29, tzinfo=IN_PARIS)
    after = datetime(2026, 11, 25, 10, 31, tzinfo=IN_PARIS)

    with refused(REFUSED.format(THE_TWO_TIMES)):
        collect(made, source, last_verified_at=before)
    collect(made, source, last_verified_at=after)

    assert [(row[2], row[4]) for row in held(made)] == [(AT, "2026-11-25T09:31:00.000000+00:00")]


def test_a_record_that_is_seen_again_says_when_and_keeps_when_it_was_collected(
    made: Engine, clock: list[datetime]
) -> None:
    source = a_source(made)
    key = collect(made, source)

    with unit_of_work(made) as work:
        record = work.get_one(ProofRecord, key)
        record.last_verified_at = SEEN_AGAIN

    assert [(row[2], row[4]) for row in held(made)] == [(AT, A_WEEK_LATER)]
    with unit_of_work(made) as work:
        found = work.get_one(ProofRecord, key)
        assert found.collected_at == COLLECTED
        assert found.last_verified_at == SEEN_AGAIN
        # Seeing it again is a change to the row, and the row says so.
        assert found.updated_at > found.created_at


@pytest.mark.parametrize(
    ("change", "value", "why"),
    [
        # Last seen before it was collected.
        ("UPDATE proof_record SET last_verified_at = ?", JUST_BEFORE, "ck_" + THE_TWO_TIMES),
        # Collected after it was last seen.
        ("UPDATE proof_record SET collected_at = ?", JUST_AFTER, "ck_" + THE_TWO_TIMES),
        ("UPDATE proof_record SET confidence = ?", "certain", "ck_confidence_one_of"),
        ("UPDATE proof_record SET published_on = ?", "2026-02-30", "ck_published_on_calendar_day"),
        ("UPDATE proof_record SET source_address = ?", "nowhere", "ck_source_address_web_address"),
        ("UPDATE proof_record SET source_address = ?", None, "source_address"),
        ("UPDATE proof_record SET source_id = ?", 99, None),
    ],
    ids=[
        "last seen before it was collected",
        "collected after it was last seen",
        "a confidence that is not on the list",
        "a day no calendar has",
        "an address that is none",
        "no address",
        "a source that is not there",
    ],
)
def test_a_change_that_breaks_the_set_is_refused_and_the_row_stays_as_it_was(
    made: Engine, change: str, value: object, why: str | None
) -> None:
    source = a_source(made)
    collect(made, source)
    before = held(made)
    if why is None:
        said_by_sqlite = BROKEN_KEY
    elif why.startswith("ck_"):
        said_by_sqlite = REFUSED.format(why.removeprefix("ck_"))
    else:
        said_by_sqlite = f"NOT NULL constraint failed: proof_record.{why}"

    with refused(said_by_sqlite), made.begin() as connection:
        connection.exec_driver_sql(change, (value,))

    assert held(made) == before


@pytest.mark.parametrize(
    ("name", "given", "why"),
    [
        (
            "Example Hill",
            {"last_verified_at": JUST_BEFORE},
            "CHECK constraint failed: ck_proof_track_" + THE_TWO_TIMES,
        ),
        (
            "Example Hill",
            {"confidence": "certain"},
            "CHECK constraint failed: ck_proof_track_confidence_one_of",
        ),
        (
            "Example Hill",
            {"collected_at": None},
            "NOT NULL constraint failed: proof_track.collected_at",
        ),
        ("Example Hill", {"source_id": 99}, BROKEN_KEY),
        # What the model said of its own table holds as well.
        ("Example Park", {}, "UNIQUE constraint failed: proof_track.name"),
        ("Example Hill", {}, None),
    ],
    ids=[
        "last seen before it was collected",
        "a confidence that is not on the list",
        "no moment of collecting",
        "a source that is not there",
        "a name another track has",
        "nothing wrong",
    ],
)
def test_a_table_with_columns_of_its_own_keeps_the_set_and_what_its_model_said(
    made: Engine, name: str, given: dict[str, object], why: str | None
) -> None:
    source = a_source(made)
    with unit_of_work(made) as work:
        work.add(ProofTrack(name="Example Park", **said(source)))
    row = (name, *as_written(source, **given).values(), MOMENT, MOMENT)

    if why is None:
        with made.begin() as connection:
            connection.exec_driver_sql(A_TRACK_PAST_THE_MODEL, row)
    else:
        with refused(why), made.begin() as connection:
            connection.exec_driver_sql(A_TRACK_PAST_THE_MODEL, row)

    assert len(held(made, "proof_track")) == (2 if why is None else 1)


def test_the_real_tables_are_as_the_migrations_made_them(made: Engine) -> None:
    with made.connect() as connection:
        tables = [
            str(name)
            for (name,) in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'proof%' "
                "ORDER BY name"
            )
        ]
        (sources_made,) = connection.exec_driver_sql(
            "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = 'source'"
        ).one()

    assert tables == ["proof_record", "proof_track"]
    assert sources_made == 1
