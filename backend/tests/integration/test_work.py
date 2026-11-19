"""Tests of units of work, against a real SQLite file in the test's own folder."""

from collections.abc import Callable
from pathlib import Path

import pytest
from sqlalchemy import Engine, ForeignKey, event, select, text
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from motosphere.db.store import open_store
from motosphere.db.work import unit_of_work

Step = Callable[[Session], object]

BROKEN_KEY = "FOREIGN KEY constraint failed"


class Base(DeclarativeBase):
    pass


class Parent(Base):
    __tablename__ = "parent"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class Child(Base):
    __tablename__ = "child"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parent.id"))


class StoppedFromOutside(BaseException):
    """Like Ctrl+C: an error that is not an ordinary exception."""


def a_store(path: Path) -> Engine:
    store = open_store(path)
    Base.metadata.create_all(store)
    return store


def names(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM parent ORDER BY name")
        return [str(name) for (name,) in found]


def tables(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM sqlite_master ORDER BY name")
        return [str(name) for (name,) in found]


def connections(store: Engine) -> tuple[list[object], list[object]]:
    """The connections the store opens and closes from now on, as two growing lists."""
    opened: list[object] = []
    closed: list[object] = []
    event.listen(store, "connect", lambda connection, _record: opened.append(connection))
    event.listen(store, "close", lambda connection, _record: closed.append(connection))
    return opened, closed


def do(store: Engine, *steps: Step) -> Session:
    """Do the steps as one unit of work and give back its session."""
    with unit_of_work(store) as work:
        for step in steps:
            step(work)
    return work


def write(name: str) -> Step:
    """A row written with a statement, at once."""
    statement = text("INSERT INTO parent (name) VALUES (:name)")
    return lambda work: work.execute(statement, {"name": name})


def add(*rows: Base) -> Step:
    """Rows that are only added: they are written when the work ends."""
    return lambda work: work.add_all(rows)


def fail_with(error: BaseException) -> Step:
    def step(_work: Session) -> None:
        raise error

    return step


def fail() -> Step:
    return fail_with(RuntimeError("the work failed part-way"))


def test_work_that_ends_is_kept_for_the_next_unit_of_work(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")

    do(store, write("first"))

    with unit_of_work(store) as work:
        found = work.scalars(select(Parent.name)).all()
    assert found == ["first"]


def test_work_that_ends_is_there_when_the_store_is_opened_again(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite3"

    do(a_store(path), write("first"))

    assert names(open_store(path)) == ["first"]


def test_rows_that_were_only_added_are_written_when_the_work_ends(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")

    do(store, add(Parent(name="first"), Parent(name="second")))

    assert names(store) == ["first", "second"]


def test_work_that_fails_leaves_no_row(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")

    with pytest.raises(RuntimeError, match="part-way"):
        do(store, write("first"), add(Parent(name="second")), lambda work: work.flush(), fail())

    assert names(store) == []


def test_work_that_fails_leaves_no_new_table(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")
    new_table = text("CREATE TABLE extra (id INTEGER PRIMARY KEY)")

    with pytest.raises(RuntimeError, match="part-way"):
        do(store, lambda work: work.execute(new_table), write("first"), fail())

    assert tables(store) == ["child", "parent"]


def test_the_store_can_be_worked_on_after_work_that_failed(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")
    with pytest.raises(RuntimeError, match="part-way"):
        do(store, write("first"), fail())

    do(store, write("second"))

    assert names(store) == ["second"]


def test_the_error_that_ended_the_work_reaches_the_caller_unchanged(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")
    error = RuntimeError("the work failed part-way")

    with pytest.raises(RuntimeError) as caught:
        do(store, write("first"), fail_with(error))

    assert caught.value is error


def test_work_that_is_stopped_from_outside_is_taken_back_too(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")

    with pytest.raises(StoppedFromOutside):
        do(store, write("first"), fail_with(StoppedFromOutside()))

    assert names(store) == []


def test_a_row_without_its_parent_ends_the_whole_unit_of_work(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")
    an_orphan = text("INSERT INTO child (parent_id) VALUES (7)")

    with pytest.raises(IntegrityError, match=BROKEN_KEY):
        do(store, write("first"), lambda work: work.execute(an_orphan), write("second"))

    assert names(store) == []


def test_a_row_without_its_parent_that_was_only_added_ends_the_unit_when_it_ends(
    tmp_path: Path,
) -> None:
    store = a_store(tmp_path / "store.sqlite3")

    with pytest.raises(IntegrityError, match=BROKEN_KEY):
        do(store, write("first"), add(Child(parent_id=7)))

    assert names(store) == []


def test_a_unit_of_work_uses_one_connection_and_closes_it(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")
    opened, closed = connections(store)

    do(store, write("first"), write("second"), add(Parent(name="third")))

    assert len(opened) == 1
    assert closed == opened


def test_the_connection_is_closed_after_work_that_fails(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")
    opened, closed = connections(store)

    with pytest.raises(RuntimeError, match="part-way"):
        do(store, write("first"), fail())

    assert len(opened) == 1
    assert closed == opened


def test_the_file_can_be_removed_after_units_of_work(tmp_path: Path) -> None:
    path = tmp_path / "store.sqlite3"
    store = a_store(path)
    do(store, write("first"))
    with pytest.raises(RuntimeError, match="part-way"):
        do(store, write("second"), fail())

    path.unlink()

    assert not path.exists()


def test_work_cannot_be_committed_part_way(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")

    with pytest.raises(RuntimeError) as refusal:
        do(store, write("first"), lambda work: work.commit(), write("second"))

    assert str(refusal.value) == (
        "A unit of work is kept as a whole when it ends; it cannot be committed part-way."
    )
    assert names(store) == []


def test_work_that_took_itself_back_cannot_go_on(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")

    with pytest.raises(InvalidRequestError):
        do(store, write("first"), lambda work: work.rollback(), write("second"))

    assert names(store) == []


def test_what_a_unit_of_work_wrote_can_be_read_after_it_has_ended(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")
    opened, _closed = connections(store)
    row = Parent(name="first")

    do(store, add(row))

    assert (row.id, row.name) == (1, "first")
    assert len(opened) == 1


def test_what_a_unit_of_work_read_can_be_read_after_it_has_ended(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")
    do(store, write("first"))
    opened, _closed = connections(store)

    with unit_of_work(store) as work:
        row = work.scalars(select(Parent)).one()

    assert (row.id, row.name) == (1, "first")
    assert len(opened) == 1


def test_a_unit_of_work_cannot_be_used_after_it_has_ended(tmp_path: Path) -> None:
    store = a_store(tmp_path / "store.sqlite3")
    opened, closed = connections(store)
    work = do(store, write("first"))

    try:
        with pytest.raises(InvalidRequestError):
            work.execute(text("SELECT 1"))
    finally:
        work.close()

    assert len(opened) == 1
    assert closed == opened
