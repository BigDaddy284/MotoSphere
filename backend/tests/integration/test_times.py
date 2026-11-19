"""Tests of times in the data store, with a table made in a real SQLite file.

The model here is made for the tests. It is a subclass of the real ``Base``,
so it proves what a model gets for a time, but it is kept in a schema of its
own (``Proof.metadata``), so the real schema never sees it.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import Engine, MetaData, func, select
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base, broken_rules
from motosphere.db.times import UtcDateTime
from motosphere.db.work import unit_of_work

A_TIME = datetime(2026, 11, 19, 8, 26, 4, 123456, tzinfo=UTC)
ITS_TEXT = "2026-11-19T08:26:04.123456+00:00"
NO_OFFSET = "A time without an offset is not stored"


def offset(hours: int, minutes: int = 0) -> timezone:
    """A zone that is always this far from UTC."""
    return timezone(timedelta(hours=hours, minutes=minutes))


class Proof(Base):
    """Models of the tests' own: what ``Base`` gives a time, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofVisit(Proof):
    __tablename__ = "proof_visit"

    id: Mapped[int] = mapped_column(primary_key=True)
    seen_at: Mapped[datetime]
    checked_at: Mapped[datetime | None]


@pytest.fixture
def made(store: Engine) -> Engine:
    """The store, with the table of the tests made in it."""
    with store.begin() as connection:
        Proof.metadata.create_all(connection)
    return store


def stored_texts(made: Engine) -> list[tuple[str, str | None]]:
    """What the file itself holds, read without the model."""
    with made.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT seen_at, checked_at FROM proof_visit ORDER BY id"
        ).all()
    return [(seen_at, checked_at) for seen_at, checked_at in rows]


def test_a_models_time_is_the_stores_own_type_and_text_in_a_strict_table(made: Engine) -> None:
    assert isinstance(ProofVisit.__table__.c.seen_at.type, UtcDateTime)
    assert isinstance(ProofVisit.__table__.c.checked_at.type, UtcDateTime)
    assert broken_rules(Proof.metadata) == []

    with made.connect() as connection:
        columns = {
            name: (declared, bool(required))
            for _, name, declared, required, _, _ in connection.exec_driver_sql(
                "PRAGMA table_info(proof_visit)"
            )
        }

    assert columns == {
        "id": ("INTEGER", True),
        "seen_at": ("TEXT", True),
        "checked_at": ("TEXT", False),
    }


@pytest.mark.parametrize(
    "zone",
    [UTC, offset(2), offset(-5, -30), offset(14), offset(-12)],
    ids=["UTC", "two hours east", "five and a half hours west", "the day after", "the day before"],
)
def test_a_time_is_stored_as_text_in_utc_and_comes_back_as_an_aware_utc_time(
    made: Engine, zone: timezone
) -> None:
    with unit_of_work(made) as work:
        work.add(ProofVisit(seen_at=A_TIME.astimezone(zone), checked_at=A_TIME.astimezone(zone)))

    assert stored_texts(made) == [(ITS_TEXT, ITS_TEXT)]
    with unit_of_work(made) as work:
        visit = work.scalars(select(ProofVisit)).one()
    assert (visit.seen_at, visit.checked_at) == (A_TIME, A_TIME)
    assert visit.seen_at.utcoffset() == timedelta(0)
    assert visit.seen_at.tzinfo == UTC


def test_no_time_is_stored_as_nothing_and_comes_back_as_nothing(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofVisit(seen_at=A_TIME))

    assert stored_texts(made) == [(ITS_TEXT, None)]
    with unit_of_work(made) as work:
        assert work.scalars(select(ProofVisit)).one().checked_at is None


def test_a_time_without_an_offset_is_refused_and_nothing_is_stored(made: Engine) -> None:
    naive = A_TIME.replace(tzinfo=None)

    with pytest.raises(StatementError, match=NO_OFFSET) as refused, unit_of_work(made) as work:
        work.add_all([ProofVisit(seen_at=A_TIME), ProofVisit(seen_at=naive)])

    assert isinstance(refused.value.orig, ValueError)
    assert stored_texts(made) == []


def test_rows_sorted_by_a_time_come_in_the_order_of_the_times(made: Engine) -> None:
    in_order = [
        datetime(2026, 11, 19, 23, 0, tzinfo=offset(9)),
        datetime(2026, 11, 19, 8, 26, 4, tzinfo=offset(-8)),
        datetime(2026, 11, 19, 8, 26, 4, 1, tzinfo=offset(-8)),
        datetime(2026, 11, 20, 0, 30, tzinfo=offset(5, 30)),
        datetime(2026, 11, 20, tzinfo=UTC),
    ]
    assert sorted(in_order) == in_order
    with unit_of_work(made) as work:
        work.add_all(ProofVisit(seen_at=moment) for moment in reversed(in_order))

    with unit_of_work(made) as work:
        found = work.scalars(select(ProofVisit.seen_at).order_by(ProofVisit.seen_at)).all()

    assert found == in_order


def test_rows_are_found_by_a_time_whatever_offset_the_question_has(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all(ProofVisit(seen_at=A_TIME + timedelta(hours=hours)) for hours in (-1, 0, 1))
    asked = A_TIME.astimezone(offset(9))

    with unit_of_work(made) as work:
        at = work.scalars(select(ProofVisit.seen_at).where(ProofVisit.seen_at == asked)).all()
        after = work.scalars(select(ProofVisit.seen_at).where(ProofVisit.seen_at > asked)).all()
        number_before = work.scalar(
            select(func.count()).select_from(ProofVisit).where(ProofVisit.seen_at < asked)
        )

    assert at == [A_TIME]
    assert after == [A_TIME + timedelta(hours=1)]
    assert number_before == 1


def test_a_question_with_a_time_without_an_offset_is_refused(made: Engine) -> None:
    naive = A_TIME.replace(tzinfo=None)

    with pytest.raises(StatementError, match=NO_OFFSET), unit_of_work(made) as work:
        work.scalars(select(ProofVisit).where(ProofVisit.seen_at > naive)).all()


def test_sqlite_itself_reads_the_stored_text_as_that_moment(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofVisit(seen_at=A_TIME.astimezone(offset(2))))

    with made.connect() as connection:
        seconds, said = connection.exec_driver_sql(
            "SELECT unixepoch(seen_at), strftime('%Y-%m-%d %H:%M:%f', seen_at) FROM proof_visit"
        ).one()

    assert seconds == int(A_TIME.timestamp())
    assert said == "2026-11-19 08:26:04.123"


@pytest.mark.parametrize(
    "text",
    ["2026-11-19 08:26:04", "2026-11-19T10:26:04.123456+02:00", "yesterday"],
    ids=["SQLite's own form", "another offset", "a word"],
)
def test_text_put_into_the_store_in_another_form_is_refused_when_it_is_read(
    made: Engine, text: str
) -> None:
    with made.begin() as connection:
        connection.exec_driver_sql("INSERT INTO proof_visit (seen_at) VALUES (?)", (text,))

    with (
        pytest.raises(ValueError, match="in the store's form") as refused,
        unit_of_work(made) as work,
    ):
        work.scalars(select(ProofVisit)).all()

    assert str(refused.value) == (
        f"The store holds a time that is not in the store's form: {text!r}."
    )
