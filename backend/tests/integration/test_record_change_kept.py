"""Tests that the history is only added to, against a real SQLite file.

The store of every test is built by the migrations, as a real store is,
and most tests begin with two rows of history in it. What the store must
refuse is written past the model, through the model, and on a connection
that the store's code did not open.
"""

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path

import pytest
from sqlalchemy import Engine, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from motosphere.db.models import SCHEMA, RecordChange
from motosphere.db.store import open_store
from motosphere.db.work import unit_of_work

NEVER_EDITED = "A row of the history (record_change) is never edited."
NEVER_DELETED = "A row of the history (record_change) is never deleted."
NEVER_REPLACED = "A row of the history (record_change) is never replaced."
KEY_BELOW_ONE = "A key of the history (record_change) is 1 or more."
FIRST = "2026-11-25T22:00:00.000000+00:00"
LATER = "2026-11-26T09:30:00.000000+00:00"
# A row of history that names no key: a person decided it, at the first moment.
A_ROW = (
    "INSERT INTO record_change (record_table, record_id, field, old_value, new_value, "
    "decided_by, created_at, updated_at) VALUES ('track', 7, ?, ?, ?, 'Jo Example', "
    "'2026-11-25T22:00:00.000000+00:00', '2026-11-25T22:00:00.000000+00:00')"
)
# The two rows every test of the fixture ``history`` begins with, as SQLite holds them.
AS_IT_WAS = [
    (1, "track", 7, "name", "Example Park", "Example Raceway", None, "Jo Example", FIRST, FIRST),
    (2, "track", 7, "length_in_metres", None, "1600", None, "Jo Example", FIRST, FIRST),
]
# A whole row that names its key, at the later moment: what follows INSERT INTO.
WITH_A_KEY = (
    "record_change (id, record_table, record_id, field, old_value, new_value, decided_by, "
    "created_at, updated_at) VALUES (?, 'track', 7, 'name', 'Example Raceway', 'Example Ring', "
    "'Jo Example', '2026-11-26T09:30:00.000000+00:00', '2026-11-26T09:30:00.000000+00:00')"
)
THE_TRIGGERS = [
    ("tr_record_change_key_positive", "record_change"),
    ("tr_record_change_never_deleted", "record_change"),
    ("tr_record_change_never_edited", "record_change"),
    ("tr_record_change_never_replaced", "record_change"),
]
EDITS = [
    "UPDATE record_change SET new_value = 'Example Ring' WHERE id = 1",
    "UPDATE record_change SET new_value = 'Example Ring'",
    "UPDATE record_change SET new_value = new_value WHERE id = 2",
    "UPDATE record_change SET updated_at = '2026-11-26T09:30:00.000000+00:00' WHERE id = 1",
    "UPDATE record_change SET id = 3 WHERE id = 2",
    "UPDATE OR REPLACE record_change SET id = 1 WHERE id = 2",
    "UPDATE OR IGNORE record_change SET new_value = 'Example Ring' WHERE id = 1",
]
DELETES = [
    "DELETE FROM record_change WHERE id = 1",
    "DELETE FROM record_change WHERE id = 2",
    "DELETE FROM record_change",
]
ONTO_A_ROW = [
    f"INSERT OR REPLACE INTO {WITH_A_KEY}",
    f"REPLACE INTO {WITH_A_KEY}",
    f"INSERT INTO {WITH_A_KEY}",
    f"INSERT OR IGNORE INTO {WITH_A_KEY}",
    f"INSERT INTO {WITH_A_KEY} ON CONFLICT (id) DO UPDATE SET new_value = excluded.new_value",
    f"INSERT INTO {WITH_A_KEY} ON CONFLICT (id) DO NOTHING",
]


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def everything(store: Engine) -> list[tuple[object, ...]]:
    """Every row of the table with every column, as SQLite holds it, by the key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT * FROM record_change ORDER BY id")
        return [tuple(row) for row in found]


def triggers(store: Engine) -> list[tuple[str, str]]:
    """Every trigger of the store with its table, by name."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger' ORDER BY name"
        )
        return [(str(name), str(table)) for name, table in found]


def two_rows(store: Engine) -> None:
    """Write the two rows of ``AS_IT_WAS`` past the model."""
    with store.begin() as connection:
        connection.exec_driver_sql(A_ROW, ("name", "Example Park", "Example Raceway"))
        connection.exec_driver_sql(A_ROW, ("length_in_metres", None, "1600"))


@pytest.fixture
def history(newest: Engine) -> Engine:
    """The test's own store with the newest schema and two rows of history in it."""
    two_rows(newest)
    assert everything(newest) == AS_IT_WAS
    return newest


def a_change(**given: object) -> RecordChange:
    """A change a person decided, as the model says it, but for what is given."""
    return RecordChange(
        **{
            "record_table": "track",
            "record_id": 7,
            "field": "name",
            "old_value": "Example Raceway",
            "new_value": "Example Ring",
            "decided_by": "Jo Example",
            **given,
        }
    )


def test_the_store_has_the_four_triggers_of_the_history_and_no_other(newest: Engine) -> None:
    assert triggers(newest) == THE_TRIGGERS


@pytest.mark.parametrize(
    "statement",
    EDITS,
    ids=[
        "a value of one row",
        "a value of every row",
        "a value to what it holds already",
        "only the moment it says it was last changed",
        "its key",
        "its key to that of another row, to take its place",
        "a value, told to pass over what is refused",
    ],
)
def test_a_row_is_not_edited(history: Engine, statement: str) -> None:
    with refused(NEVER_EDITED), history.begin() as connection:
        connection.exec_driver_sql(statement)

    assert everything(history) == AS_IT_WAS


@pytest.mark.parametrize("statement", DELETES, ids=["the first row", "the newest row", "every row"])
def test_a_row_is_not_deleted(history: Engine, statement: str) -> None:
    with refused(NEVER_DELETED), history.begin() as connection:
        connection.exec_driver_sql(statement)

    assert everything(history) == AS_IT_WAS


@pytest.mark.parametrize("key", [1, 2], ids=["the first row", "the newest row"])
@pytest.mark.parametrize(
    "statement",
    ONTO_A_ROW,
    ids=[
        "INSERT OR REPLACE",
        "REPLACE",
        "a plain INSERT",
        "INSERT OR IGNORE",
        "an INSERT that edits the row when its key is taken",
        "an INSERT that does nothing when its key is taken",
    ],
)
def test_a_new_row_is_not_put_in_the_place_of_a_row(
    history: Engine, statement: str, key: int
) -> None:
    # REPLACE takes the old row out and fires no trigger for it, so the
    # store asks before every new row whether its key is taken. It cannot
    # tell what the statement would have done then, and refuses them all.
    with refused(NEVER_REPLACED), history.begin() as connection:
        connection.exec_driver_sql(statement, (key,))

    assert everything(history) == AS_IT_WAS


@pytest.mark.parametrize("key", [0, -1, -7])
def test_a_row_has_a_key_of_one_or_more_and_the_history_goes_on_after_one_that_had_not(
    history: Engine, key: int
) -> None:
    # A new row that names no key shows SQLite's -1 to the trigger that
    # asks whether its key is taken. No row may have that key, or no new
    # row could be stored again.
    with refused(KEY_BELOW_ONE), history.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {WITH_A_KEY}", (key,))
    assert everything(history) == AS_IT_WAS

    with history.begin() as connection:
        connection.exec_driver_sql(A_ROW, ("name", "Example Raceway", "Example Ring"))

    assert [row[0] for row in everything(history)] == [1, 2, 3]


def edit_a_row(work: Session) -> None:
    row = work.get_one(RecordChange, 1)
    row.new_value = "Example Ring"


def edit_every_row(work: Session) -> None:
    work.execute(update(RecordChange).values(new_value="Example Ring"))


def merge_onto_a_row(work: Session) -> None:
    work.merge(a_change(id=1))


def delete_a_row(work: Session) -> None:
    work.delete(work.get_one(RecordChange, 2))


def delete_every_row(work: Session) -> None:
    work.execute(delete(RecordChange))


def add_a_row_with_a_key_that_is_taken(work: Session) -> None:
    work.add(a_change(id=2))


def add_a_row_with_a_key_below_one(work: Session) -> None:
    work.add(a_change(id=-1))


@pytest.mark.parametrize(
    ("the_work", "why"),
    [
        (edit_a_row, NEVER_EDITED),
        (edit_every_row, NEVER_EDITED),
        (merge_onto_a_row, NEVER_EDITED),
        (delete_a_row, NEVER_DELETED),
        (delete_every_row, NEVER_DELETED),
        (add_a_row_with_a_key_that_is_taken, NEVER_REPLACED),
        (add_a_row_with_a_key_below_one, KEY_BELOW_ONE),
    ],
    ids=[
        "a row that was read is given another value",
        "every row is given another value in one statement",
        "a row is merged onto one that is there",
        "a row that was read is deleted",
        "every row is deleted in one statement",
        "a row is added with a key that is taken",
        "a row is added with a key below one",
    ],
)
def test_through_the_model_the_history_is_only_added_to(
    history: Engine, the_work: Callable[[Session], None], why: str
) -> None:
    with refused(why), unit_of_work(history) as work:
        the_work(work)

    assert everything(history) == AS_IT_WAS


def test_a_new_row_is_still_stored_and_gets_the_next_key(history: Engine) -> None:
    with unit_of_work(history) as work:
        through_the_model = a_change()
        work.add(through_the_model)
    with history.begin() as connection:
        connection.exec_driver_sql(A_ROW, ("name", "Example Ring", "Example Raceway"))
        # A key that is free may be named, and the next row follows it.
        connection.exec_driver_sql(f"INSERT INTO {WITH_A_KEY}", (10,))
        connection.exec_driver_sql(f"INSERT OR REPLACE INTO {WITH_A_KEY}", (20,))
        connection.exec_driver_sql(A_ROW, ("name", "Example Ring", "Example Park"))

    held = everything(history)
    assert through_the_model.id == 3
    assert held[:2] == AS_IT_WAS
    assert [(row[0], row[4], row[5]) for row in held[2:]] == [
        (3, "Example Raceway", "Example Ring"),
        (4, "Example Ring", "Example Raceway"),
        (10, "Example Raceway", "Example Ring"),
        (20, "Example Raceway", "Example Ring"),
        (21, "Example Ring", "Example Park"),
    ]


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE record_change SET new_value = 'Example Ring' WHERE id = 99",
        "DELETE FROM record_change WHERE id = 99",
    ],
    ids=["an edit", "a delete"],
)
def test_a_statement_that_meets_no_row_is_not_refused_and_changes_nothing(
    history: Engine, statement: str
) -> None:
    # The store refuses for the row that would be changed. Where there is
    # none, nothing is changed and nothing is refused.
    with history.begin() as connection:
        connection.exec_driver_sql(statement)

    assert everything(history) == AS_IT_WAS


@pytest.mark.parametrize(
    "statement",
    ["UPDATE record_change SET new_value = 'Example Ring'", "DELETE FROM record_change"],
    ids=["an edit", "a delete"],
)
def test_in_a_history_without_rows_there_is_nothing_to_refuse(
    newest: Engine, statement: str
) -> None:
    with newest.begin() as connection:
        connection.exec_driver_sql(statement)

    assert everything(newest) == []


def test_a_refusal_takes_back_the_whole_unit_of_work(history: Engine) -> None:
    with refused(NEVER_EDITED), unit_of_work(history) as work:
        work.add(a_change())
        work.flush()
        edit_a_row(work)
    with refused(NEVER_DELETED), history.begin() as connection:
        connection.exec_driver_sql(A_ROW, ("name", "Example Raceway", "Example Ring"))
        connection.exec_driver_sql("DELETE FROM record_change WHERE id = 3")

    assert everything(history) == AS_IT_WAS


@pytest.mark.parametrize(
    ("statement", "given", "why"),
    [
        (EDITS[0], (), NEVER_EDITED),
        (DELETES[0], (), NEVER_DELETED),
        (ONTO_A_ROW[1], (1,), NEVER_REPLACED),
        (ONTO_A_ROW[2], (-1,), KEY_BELOW_ONE),
    ],
    ids=["an edit", "a delete", "a row in the place of a row", "a key below one"],
)
def test_the_refusal_holds_on_a_connection_the_stores_code_did_not_open(
    history: Engine, statement: str, given: tuple[int, ...], why: str
) -> None:
    # The store's code switches foreign keys on for every connection it
    # opens. The triggers are in the file, and need no one to switch them on.
    with closing(sqlite3.connect(str(history.url.database))) as bare:
        assert bare.execute("PRAGMA foreign_keys").fetchone() == (0,)

        with pytest.raises(sqlite3.IntegrityError) as refusal:
            bare.execute(statement, given)
        bare.commit()

    assert str(refusal.value) == why
    assert everything(history) == AS_IT_WAS


@pytest.fixture
def from_the_models(tmp_path: Path) -> Iterator[Engine]:
    """A second store of the test's own, with every table made from the models."""
    engine = open_store(tmp_path / "models.sqlite3")
    with engine.begin() as connection:
        SCHEMA.create_all(connection)
    yield engine
    engine.dispose()


def test_a_store_made_from_the_models_has_the_triggers_and_refuses_the_same(
    from_the_models: Engine,
) -> None:
    two_rows(from_the_models)

    assert triggers(from_the_models) == THE_TRIGGERS
    for statement, given, why in [
        (EDITS[0], (), NEVER_EDITED),
        (DELETES[0], (), NEVER_DELETED),
        (ONTO_A_ROW[1], (1,), NEVER_REPLACED),
        (ONTO_A_ROW[2], (-1,), KEY_BELOW_ONE),
    ]:
        with refused(why), from_the_models.begin() as connection:
            connection.exec_driver_sql(statement, given)
    assert everything(from_the_models) == AS_IT_WAS
