"""Tests that a decided review item keeps its decision, against a real SQLite file.

The store of every test is built by the migrations, as a real store is,
and most tests begin with four items in it: two that are open and two
that were decided. What the store must refuse is written past the model,
through the model, and on a connection that the store's code did not
open.
"""

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path

import pytest
from sqlalchemy import Engine, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from motosphere.db.models import SCHEMA, ReviewItem
from motosphere.db.models.review_item import ReviewKind, ReviewState
from motosphere.db.review import decide
from motosphere.db.store import open_store
from motosphere.db.work import unit_of_work

NEVER_EDITED = "A decided review item (review_item) is never edited."
NEVER_DELETED = "A decided review item (review_item) is never deleted."
NEVER_REPLACED = "A decided review item (review_item) is never replaced."
FIRST = "2026-11-25T22:00:00.000000+00:00"
LATER = "2026-11-26T09:30:00.000000+00:00"
A_SOURCE = (
    "INSERT INTO source (name, website, category, collection_method, switched_on, "
    "created_at, updated_at) VALUES ('Example Federation', 'https://federation.example', "
    "'governing body', 'rss feed', 0, '2026-11-19T08:00:00.000000+00:00', "
    "'2026-11-19T08:00:00.000000+00:00')"
)
# A possible duplicate of two tracks, stored at the first moment: what follows INSERT INTO.
A_PAIR = (
    "review_item (kind, record_table, record_id, other_record_id, reason, state, decided_by, "
    "decided_at, note, created_at, updated_at) VALUES ('possible duplicate', 'track', ?, ?, "
    "'They have one name.', ?, ?, ?, ?, '2026-11-25T22:00:00.000000+00:00', "
    "'2026-11-25T22:00:00.000000+00:00')"
)
# The same with a key that is named.
A_PAIR_WITH_A_KEY = (
    "review_item (id, kind, record_table, record_id, other_record_id, reason, state, "
    "decided_by, decided_at, note, created_at, updated_at) VALUES (?, 'possible duplicate', "
    "'track', ?, ?, 'They have one name.', ?, ?, ?, ?, '2026-11-25T22:00:00.000000+00:00', "
    "'2026-11-25T22:00:00.000000+00:00')"
)
# What the first source says of the length of a track, stored at the first moment.
OF_A_FIELD = (
    "review_item (kind, record_table, record_id, field, source_id, source_address, "
    "source_value, reason, state, decided_by, decided_at, note, created_at, updated_at) VALUES "
    "('sources disagree', 'track', ?, 'length_in_metres', 1, "
    "'https://federation.example/tracks/7', '1750', 'The record says 1600.', ?, ?, ?, ?, "
    "'2026-11-25T22:00:00.000000+00:00', '2026-11-25T22:00:00.000000+00:00')"
)
OPEN = ("open", None, None, None)
ACCEPTED = ("accepted", "Jo Example", FIRST, "Checked on the map.")
REJECTED = ("rejected", "Jo Example", FIRST, None)
THE_TRIGGERS = [
    ("tr_review_item_decided_never_deleted", "review_item"),
    ("tr_review_item_decided_never_edited", "review_item"),
    ("tr_review_item_decided_never_replaced", "review_item"),
    ("tr_review_item_decided_never_replaced_by_another", "review_item"),
]
# Every column of the table with a statement that gives it another value
# than the accepted item, 2, and the rejected one, 3, hold. Each is tried
# on both.
ANOTHER_VALUE = {
    "id": "UPDATE review_item SET id = 30 WHERE id = ?",
    "kind": "UPDATE review_item SET kind = 'value outside its rules' WHERE id = ?",
    "record_table": "UPDATE review_item SET record_table = 'rider' WHERE id = ?",
    "record_id": "UPDATE review_item SET record_id = 70 WHERE id = ?",
    "other_record_id": "UPDATE review_item SET other_record_id = 71 WHERE id = ?",
    "field": "UPDATE review_item SET field = 'name' WHERE id = ?",
    "source_id": "UPDATE review_item SET source_id = 2 WHERE id = ?",
    "source_address": "UPDATE review_item SET source_address = "
    "'https://federation.example/tracks/70' WHERE id = ?",
    "source_value": "UPDATE review_item SET source_value = '1800' WHERE id = ?",
    "reason": "UPDATE review_item SET reason = 'Another reason.' WHERE id = ?",
    "state": "UPDATE review_item SET state = CASE state WHEN 'accepted' THEN 'rejected' "
    "ELSE 'accepted' END WHERE id = ?",
    "decided_by": "UPDATE review_item SET decided_by = 'Sam Example' WHERE id = ?",
    "decided_at": "UPDATE review_item SET decided_at = '2026-11-26T09:30:00.000000+00:00' "
    "WHERE id = ?",
    "note": "UPDATE review_item SET note = 'Looked again.' WHERE id = ?",
    "created_at": "UPDATE review_item SET created_at = '2026-11-26T09:30:00.000000+00:00' "
    "WHERE id = ?",
    "updated_at": "UPDATE review_item SET updated_at = '2026-11-26T09:30:00.000000+00:00' "
    "WHERE id = ?",
}
# Each of these too is tried on both.
EDITS = [
    "UPDATE review_item SET state = 'open', decided_by = NULL, decided_at = NULL WHERE id = ?",
    "UPDATE review_item SET note = NULL WHERE id = ?",
    "UPDATE review_item SET state = state WHERE id = ?",
    "UPDATE OR REPLACE review_item SET id = 1 WHERE id = ?",
    "UPDATE OR IGNORE review_item SET note = 'Looked again.' WHERE id = ?",
]
OF_EVERY_ITEM = [
    "UPDATE review_item SET note = 'Looked again.'",
    "UPDATE review_item SET state = 'open', decided_by = NULL, decided_at = NULL",
    "UPDATE review_item SET note = 'Looked again.' WHERE state != 'open'",
]
DELETES = [
    "DELETE FROM review_item WHERE id = 2",
    "DELETE FROM review_item WHERE id = 3",
    "DELETE FROM review_item WHERE state != 'open'",
    "DELETE FROM review_item",
]


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def everything(store: Engine) -> list[tuple[object, ...]]:
    """Every item with every column, as SQLite holds it, by the key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id")
        return [tuple(row) for row in found]


def states(store: Engine) -> list[tuple[object, ...]]:
    """The key of every item with its state, who decided and its note, by the key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT id, state, decided_by, note FROM review_item ORDER BY id"
        )
        return [tuple(row) for row in found]


def triggers(store: Engine) -> list[tuple[str, str]]:
    """The triggers of a kept decision on the table of the review queue, by name."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger' "
            "AND tbl_name = 'review_item' AND name GLOB 'tr_review_item_decided_*' ORDER BY name"
        )
        return [(str(name), str(table)) for name, table in found]


def four_items(store: Engine) -> None:
    """Write a source and the four items past the model.

    Item 1 is an open possible duplicate, item 2 one that was accepted,
    item 3 a doubt about a field that was rejected, and item 4 an open one.
    """
    with store.begin() as connection:
        connection.exec_driver_sql(A_SOURCE)
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR}", (7, 12, *OPEN))
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR}", (8, 9, *ACCEPTED))
        connection.exec_driver_sql(f"INSERT INTO {OF_A_FIELD}", (7, *REJECTED))
        connection.exec_driver_sql(f"INSERT INTO {OF_A_FIELD}", (8, *OPEN))


AS_THEY_WERE = [
    (1, "open", None, None),
    (2, "accepted", "Jo Example", "Checked on the map."),
    (3, "rejected", "Jo Example", None),
    (4, "open", None, None),
]


@pytest.fixture
def queue(newest: Engine) -> Engine:
    """The test's own store with the newest schema and the four items in it."""
    four_items(newest)
    assert states(newest) == AS_THEY_WERE
    return newest


def test_the_table_of_the_review_queue_has_the_four_triggers_of_a_kept_decision(
    newest: Engine,
) -> None:
    assert triggers(newest) == THE_TRIGGERS


def test_every_column_of_the_table_is_one_of_those_given_another_value(newest: Engine) -> None:
    # A column that a later task gives the table must get its statement here.
    with newest.connect() as connection:
        columns = connection.exec_driver_sql("SELECT name FROM pragma_table_info('review_item')")
        assert sorted(ANOTHER_VALUE) == sorted(name for (name,) in columns)


@pytest.mark.parametrize("key", [2, 3], ids=["an accepted item", "a rejected item"])
@pytest.mark.parametrize("column", list(ANOTHER_VALUE))
def test_no_column_of_a_decided_item_is_given_another_value(
    queue: Engine, column: str, key: int
) -> None:
    before = everything(queue)

    with refused(NEVER_EDITED), queue.begin() as connection:
        connection.exec_driver_sql(ANOTHER_VALUE[column], (key,))

    assert everything(queue) == before


@pytest.mark.parametrize("key", [2, 3], ids=["an accepted item", "a rejected item"])
@pytest.mark.parametrize(
    "statement",
    EDITS,
    ids=[
        "put back to open",
        "no note",
        "its state to what it holds already",
        "its key to that of an open item, to take its place",
        "a note, told to pass over what is refused",
    ],
)
def test_a_decided_item_is_not_edited(queue: Engine, statement: str, key: int) -> None:
    before = everything(queue)

    with refused(NEVER_EDITED), queue.begin() as connection:
        connection.exec_driver_sql(statement, (key,))

    assert everything(queue) == before


@pytest.mark.parametrize(
    "statement",
    OF_EVERY_ITEM,
    ids=["a note for every item", "every item put back to open", "a note for every decided item"],
)
def test_a_statement_that_would_edit_a_decided_item_changes_no_item(
    queue: Engine, statement: str
) -> None:
    # SQLite stops the statement, and what it had done to the open items
    # before it came to a decided one is taken back with it.
    before = everything(queue)

    with refused(NEVER_EDITED), queue.begin() as connection:
        connection.exec_driver_sql(statement)

    assert everything(queue) == before


@pytest.mark.parametrize(
    "statement",
    DELETES,
    ids=["the accepted item", "the rejected item", "every decided item", "every item"],
)
def test_a_decided_item_is_not_deleted(queue: Engine, statement: str) -> None:
    before = everything(queue)

    with refused(NEVER_DELETED), queue.begin() as connection:
        connection.exec_driver_sql(statement)

    assert everything(queue) == before


@pytest.mark.parametrize("decision", ["accepted", "rejected"])
@pytest.mark.parametrize("key", [1, 4], ids=["a possible duplicate", "a doubt about a field"])
def test_an_open_item_is_decided_with_plain_sql_and_is_kept_from_then_on(
    queue: Engine, key: int, decision: str
) -> None:
    with queue.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE review_item SET state = ?, decided_by = 'Sam Example', decided_at = ?, "
            "note = 'Seen on site.', updated_at = ? WHERE id = ?",
            (decision, LATER, LATER, key),
        )
    decided = everything(queue)
    assert states(queue)[key - 1] == (key, decision, "Sam Example", "Seen on site.")

    with refused(NEVER_EDITED), queue.begin() as connection:
        connection.exec_driver_sql(EDITS[0], (key,))
    with refused(NEVER_DELETED), queue.begin() as connection:
        connection.exec_driver_sql("DELETE FROM review_item WHERE id = ?", (key,))

    assert everything(queue) == decided


@pytest.mark.parametrize("decision", [ReviewState.ACCEPTED, ReviewState.REJECTED])
def test_an_item_decided_through_the_function_is_kept_from_then_on(
    queue: Engine, decision: ReviewState
) -> None:
    with unit_of_work(queue) as work:
        decide(work, work.get_one(ReviewItem, 4), decision, by="Sam Example")
    decided = everything(queue)
    assert states(queue)[3] == (4, str(decision), "Sam Example", None)

    with refused(NEVER_EDITED), queue.begin() as connection:
        connection.exec_driver_sql(EDITS[0], (4,))
    with refused(NEVER_DELETED), queue.begin() as connection:
        connection.exec_driver_sql("DELETE FROM review_item WHERE id = 4")

    assert everything(queue) == decided


def test_an_open_item_is_edited_and_deleted_as_before(queue: Engine) -> None:
    # The triggers ask what the item was before the statement. An open
    # item is not kept by them: it can get a note, another reason, and it
    # can be deleted.
    with queue.begin() as connection:
        connection.exec_driver_sql("UPDATE review_item SET note = 'To be looked at.' WHERE id = 1")
        connection.exec_driver_sql(
            "UPDATE review_item SET reason = 'They have one name and one gate.' "
            "WHERE state = 'open'"
        )
        connection.exec_driver_sql("DELETE FROM review_item WHERE id = 4")

    assert states(queue) == [(1, "open", None, "To be looked at."), *AS_THEY_WERE[1:3]]
    with queue.connect() as connection:
        reasons = connection.exec_driver_sql("SELECT id, reason FROM review_item ORDER BY id")
        assert [tuple(row) for row in reasons] == [
            (1, "They have one name and one gate."),
            (2, "They have one name."),
            (3, "The record says 1600."),
        ]


def test_a_new_item_is_still_stored_open_or_decided(queue: Engine) -> None:
    # An item can be stored as decided in one statement, as before: the
    # triggers are for an item that is there.
    with queue.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR}", (20, 21, *OPEN))
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR}", (22, 23, *ACCEPTED))
    with unit_of_work(queue) as work:
        through_the_model = ReviewItem(
            kind=ReviewKind.POSSIBLE_DUPLICATE,
            record_table="track",
            record_id=24,
            other_record_id=25,
            reason="They have one name.",
        )
        work.add(through_the_model)

    assert through_the_model.id == 7
    assert states(queue) == [
        *AS_THEY_WERE,
        (5, "open", None, None),
        (6, "accepted", "Jo Example", "Checked on the map."),
        (7, "open", None, None),
    ]


def put_back_to_open(work: Session) -> None:
    item = work.get_one(ReviewItem, 2)
    item.state = ReviewState.OPEN
    item.decided_by = None
    item.decided_at = None


def give_a_note(work: Session) -> None:
    work.get_one(ReviewItem, 3).note = "Looked again."


def give_every_item_a_note(work: Session) -> None:
    work.execute(update(ReviewItem).values(note="Looked again."))


def merge_onto_a_decided_item(work: Session) -> None:
    work.merge(
        ReviewItem(
            id=2,
            kind=ReviewKind.POSSIBLE_DUPLICATE,
            record_table="track",
            record_id=8,
            other_record_id=9,
            reason="They have one name and one gate.",
        )
    )


def delete_a_decided_item(work: Session) -> None:
    work.delete(work.get_one(ReviewItem, 3))


def delete_every_item(work: Session) -> None:
    work.execute(delete(ReviewItem))


@pytest.mark.parametrize(
    ("the_work", "why"),
    [
        (put_back_to_open, NEVER_EDITED),
        (give_a_note, NEVER_EDITED),
        (give_every_item_a_note, NEVER_EDITED),
        (merge_onto_a_decided_item, NEVER_EDITED),
        (delete_a_decided_item, NEVER_DELETED),
        (delete_every_item, NEVER_DELETED),
    ],
    ids=[
        "a decided item that was read is put back to open",
        "a decided item that was read is given a note",
        "every item is given a note in one statement",
        "an item with another reason is merged onto a decided one",
        "a decided item that was read is deleted",
        "every item is deleted in one statement",
    ],
)
def test_through_the_model_a_decided_item_is_kept(
    queue: Engine, the_work: Callable[[Session], None], why: str
) -> None:
    before = everything(queue)

    with refused(why), unit_of_work(queue) as work:
        the_work(work)

    assert everything(queue) == before


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE review_item SET note = 'Looked again.' WHERE id = 99",
        "DELETE FROM review_item WHERE id = 99",
        "UPDATE review_item SET note = note WHERE state = 'open'",
    ],
    ids=["an edit of no item", "a delete of no item", "an edit of the open items"],
)
def test_a_statement_that_meets_no_decided_item_is_not_refused(
    queue: Engine, statement: str
) -> None:
    before = everything(queue)

    with queue.begin() as connection:
        connection.exec_driver_sql(statement)

    assert everything(queue) == before


@pytest.mark.parametrize(
    "statement",
    ["UPDATE review_item SET note = 'Looked again.'", "DELETE FROM review_item"],
    ids=["an edit", "a delete"],
)
def test_in_a_queue_without_items_there_is_nothing_to_refuse(
    newest: Engine, statement: str
) -> None:
    with newest.begin() as connection:
        connection.exec_driver_sql(statement)

    assert everything(newest) == []


def test_a_refusal_takes_back_the_whole_unit_of_work(queue: Engine) -> None:
    before = everything(queue)

    with refused(NEVER_EDITED), unit_of_work(queue) as work:
        decide(work, work.get_one(ReviewItem, 1), ReviewState.ACCEPTED, by="Sam Example")
        give_a_note(work)
    with refused(NEVER_DELETED), queue.begin() as connection:
        connection.exec_driver_sql("UPDATE review_item SET note = 'To be looked at.' WHERE id = 4")
        connection.exec_driver_sql("DELETE FROM review_item WHERE id = 2")

    assert everything(queue) == before


@pytest.mark.parametrize(
    ("statement", "given", "why"),
    [
        (EDITS[0], (2,), NEVER_EDITED),
        (ANOTHER_VALUE["note"], (3,), NEVER_EDITED),
        (OF_EVERY_ITEM[0], (), NEVER_EDITED),
        (DELETES[0], (), NEVER_DELETED),
        (DELETES[3], (), NEVER_DELETED),
    ],
    ids=[
        "put back to open",
        "a note",
        "a note for every item",
        "a delete",
        "a delete of every item",
    ],
)
def test_the_refusal_holds_on_a_connection_the_stores_code_did_not_open(
    queue: Engine, statement: str, given: tuple[int, ...], why: str
) -> None:
    # The store's code switches foreign keys on for every connection it
    # opens. The triggers are in the file, and need no one to switch them on.
    # What the connection keeps afterwards is nothing: a statement that
    # is refused had changed or deleted the first, open item before it
    # came to a decided one, and that is taken back with it.
    before = everything(queue)
    with closing(sqlite3.connect(str(queue.url.database))) as bare:
        assert bare.execute("PRAGMA foreign_keys").fetchone() == (0,)

        with pytest.raises(sqlite3.IntegrityError) as refusal:
            bare.execute(statement, given)
        bare.commit()

    assert str(refusal.value) == why
    assert everything(queue) == before


@pytest.mark.parametrize(
    ("statement", "why"),
    [(OF_EVERY_ITEM[2], NEVER_EDITED), (DELETES[2], NEVER_DELETED)],
    ids=["an edit", "a delete"],
)
def test_a_refusal_stops_the_statement_and_not_the_work_before_it(
    queue: Engine, statement: str, why: str
) -> None:
    # Whoever catches the refusal can go on and keep what was done before
    # it: the store stops the statement, and does not end the work.
    with closing(sqlite3.connect(str(queue.url.database))) as bare:
        bare.execute("UPDATE review_item SET note = 'To be looked at.' WHERE id = 1")

        with pytest.raises(sqlite3.IntegrityError) as refusal:
            bare.execute(statement)
        bare.execute("UPDATE review_item SET note = 'This one too.' WHERE id = 4")
        bare.commit()

    assert str(refusal.value) == why
    assert states(queue) == [
        (1, "open", None, "To be looked at."),
        *AS_THEY_WERE[1:3],
        (4, "open", None, "This one too."),
    ]


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
    four_items(from_the_models)
    before = everything(from_the_models)

    assert triggers(from_the_models) == THE_TRIGGERS
    for statement, given, why in [
        (EDITS[0], (2,), NEVER_EDITED),
        (ANOTHER_VALUE["note"], (3,), NEVER_EDITED),
        (DELETES[0], (), NEVER_DELETED),
    ]:
        with refused(why), from_the_models.begin() as connection:
            connection.exec_driver_sql(statement, given)
    assert everything(from_the_models) == before


@pytest.mark.parametrize(
    ("statement", "given"),
    [
        (f"INSERT OR REPLACE INTO {A_PAIR_WITH_A_KEY}", (2, 30, 31, *OPEN)),
        (f"REPLACE INTO {A_PAIR}", (8, 9, *OPEN)),
        ("UPDATE OR REPLACE review_item SET id = 2 WHERE id = 1", ()),
        ("UPDATE OR REPLACE review_item SET record_id = 8, other_record_id = 9 WHERE id = 1", ()),
    ],
    ids=[
        "a new item with its key",
        "the same doubt again",
        "an open item given its key",
        "an open item made the same doubt",
    ],
)
def test_the_table_keeps_a_decided_item_from_being_replaced(
    queue: Engine, statement: str, given: tuple[object, ...]
) -> None:
    # A statement that says REPLACE takes the item it clashes with out and
    # fires no trigger for it. Two triggers of their own ask before the
    # new row is written (DAT-055), and the accepted item, 2, is as it was.
    before = everything(queue)

    with refused(NEVER_REPLACED), queue.begin() as connection:
        connection.exec_driver_sql(statement, given)

    assert everything(queue) == before
