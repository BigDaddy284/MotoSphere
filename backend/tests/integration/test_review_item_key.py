"""Tests that a key of the review queue is 1 or more, against a real SQLite file.

The store of every test is built by the migrations, as a real store is,
and most tests begin with three items in it: two that are open and one
that was decided. What the store must refuse is written past the model,
through the model, and on a connection that the store's code did not
open.

SQLite has four names for the key of this table: that of its column,
``id``, and three of its own, ``rowid``, ``_rowid_`` and ``oid``. The
rule holds under each of them.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

import pytest
from sqlalchemy import Engine, text, update
from sqlalchemy.exc import IntegrityError

from motosphere.db.history import MIGRATIONS
from motosphere.db.migrations import migrate
from motosphere.db.models import SCHEMA, ReviewItem
from motosphere.db.models.review_item import ReviewKind
from motosphere.db.store import open_store
from motosphere.db.work import unit_of_work

A_KEY_IS_1_OR_MORE = "A key of the review queue (review_item) is 1 or more."
NEVER_EDITED = "A decided review item (review_item) is never edited."
FIRST = "2026-11-25T22:00:00.000000+00:00"
A_SOURCE = (
    "INSERT INTO source (name, website, category, collection_method, switched_on, "
    "created_at, updated_at) VALUES ('Example Federation', 'https://federation.example', "
    "'governing body', 'rss feed', 0, '2026-11-19T08:00:00.000000+00:00', "
    "'2026-11-19T08:00:00.000000+00:00')"
)
# A possible duplicate of two tracks, stored at the first moment: what follows INSERT INTO.
A_PAIR = (
    "review_item (kind, record_table, record_id, other_record_id, reason, state, decided_by, "
    "decided_at, created_at, updated_at) VALUES ('possible duplicate', 'track', ?, ?, "
    "'They have one name.', ?, ?, ?, '2026-11-25T22:00:00.000000+00:00', "
    "'2026-11-25T22:00:00.000000+00:00')"
)
# The same with a key that is named.
A_PAIR_WITH_A_KEY = (
    "review_item (id, kind, record_table, record_id, other_record_id, reason, state, "
    "decided_by, decided_at, created_at, updated_at) VALUES (?, 'possible duplicate', "
    "'track', ?, ?, 'They have one name.', ?, ?, ?, '2026-11-25T22:00:00.000000+00:00', "
    "'2026-11-25T22:00:00.000000+00:00')"
)
# What the first source says of the length of a track, with a key that is named.
OF_A_FIELD_WITH_A_KEY = (
    "review_item (id, kind, record_table, record_id, field, source_id, source_address, "
    "source_value, reason, state, decided_by, decided_at, created_at, updated_at) VALUES "
    "(?, 'sources disagree', 'track', ?, 'length_in_metres', 1, "
    "'https://federation.example/tracks/7', '1750', 'The record says 1600.', ?, ?, ?, "
    "'2026-11-25T22:00:00.000000+00:00', '2026-11-25T22:00:00.000000+00:00')"
)
OPEN = ("open", None, None)
ACCEPTED = ("accepted", "Jo Example", FIRST)
# Every trigger the table of the review queue has, by name. A task that
# gives the table another trigger names it here.
THE_TRIGGERS = [
    ("tr_review_item_decided_never_deleted", "review_item"),
    ("tr_review_item_decided_never_edited", "review_item"),
    ("tr_review_item_decided_never_replaced", "review_item"),
    ("tr_review_item_decided_never_replaced_by_another", "review_item"),
    ("tr_review_item_key_positive", "review_item"),
    ("tr_review_item_key_stays_positive", "review_item"),
]
BELOW_1 = [0, -1, -7, -9223372036854775808]
# The three names SQLite itself has for the key of a table.
SQLITES_OWN = ["rowid", "_rowid_", "oid"]
# Every way a statement can name the key: the column, SQLite's own names,
# and each in other capitals or in the marks SQLite takes around a name.
NAMES_OF_THE_KEY = [
    "id",
    "ID",
    '"id"',
    "rowid",
    "ROWID",
    "RowId",
    '"rowid"',
    "_rowid_",
    "_ROWID_",
    "`_rowid_`",
    "oid",
    "OID",
    "[oid]",
]
NEW_ITEMS = [
    (f"INSERT INTO {A_PAIR_WITH_A_KEY}", (20, 21, *OPEN)),
    (f"INSERT INTO {A_PAIR_WITH_A_KEY}", (20, 21, *ACCEPTED)),
    (f"INSERT INTO {OF_A_FIELD_WITH_A_KEY}", (20, *OPEN)),
    (f"INSERT OR REPLACE INTO {A_PAIR_WITH_A_KEY}", (20, 21, *OPEN)),
    (f"INSERT OR IGNORE INTO {A_PAIR_WITH_A_KEY}", (20, 21, *OPEN)),
]
NEW_ITEMS_SAID = [
    "an open item",
    "a decided item",
    "a doubt about a field",
    "an item told to take the place of what it clashes with",
    "an item told to pass over what is refused",
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


def keys(store: Engine) -> list[tuple[object, ...]]:
    """The key of every item with its state and its first record, by the key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT id, state, record_id FROM review_item ORDER BY id"
        )
        return [tuple(row) for row in found]


def triggers(store: Engine) -> list[tuple[str, str]]:
    """Every trigger of the table of the review queue, by name."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name, tbl_name FROM sqlite_master "
            "WHERE type = 'trigger' AND tbl_name = 'review_item' ORDER BY name"
        )
        return [(str(name), str(table)) for name, table in found]


def three_items(store: Engine) -> None:
    """Write a source and the three items past the model.

    Item 1 is an open possible duplicate, item 2 one that was accepted,
    and item 3 an open one.
    """
    with store.begin() as connection:
        connection.exec_driver_sql(A_SOURCE)
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR}", (7, 12, *OPEN))
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR}", (8, 9, *ACCEPTED))
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR}", (10, 11, *OPEN))


AS_THEY_WERE = [(1, "open", 7), (2, "accepted", 8), (3, "open", 10)]


@pytest.fixture
def queue(newest: Engine) -> Engine:
    """The test's own store with the newest schema and the three items in it."""
    three_items(newest)
    assert keys(newest) == AS_THEY_WERE
    return newest


def test_the_table_of_the_review_queue_has_these_triggers_and_no_other(newest: Engine) -> None:
    assert triggers(newest) == THE_TRIGGERS


@pytest.mark.parametrize("key", BELOW_1)
@pytest.mark.parametrize(("statement", "given"), NEW_ITEMS, ids=NEW_ITEMS_SAID)
def test_a_new_item_with_a_key_below_1_is_refused(
    queue: Engine, statement: str, given: tuple[object, ...], key: int
) -> None:
    before = everything(queue)

    with refused(A_KEY_IS_1_OR_MORE), queue.begin() as connection:
        connection.exec_driver_sql(statement, (key, *given))

    assert everything(queue) == before


@pytest.mark.parametrize("key", BELOW_1)
def test_a_new_item_with_a_key_below_1_is_refused_in_a_queue_without_items(
    newest: Engine, key: int
) -> None:
    with refused(A_KEY_IS_1_OR_MORE), newest.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR_WITH_A_KEY}", (key, 20, 21, *OPEN))

    assert everything(newest) == []


@pytest.mark.parametrize("key", [4, 30, 9223372036854775807])
def test_a_new_item_is_stored_with_a_key_of_1_or_more_that_is_named(
    queue: Engine, key: int
) -> None:
    with queue.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR_WITH_A_KEY}", (key, 20, 21, *OPEN))

    assert keys(queue) == [*AS_THEY_WERE, (key, "open", 20)]


def test_a_new_item_is_stored_with_the_key_1_in_a_queue_without_items(newest: Engine) -> None:
    with newest.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR_WITH_A_KEY}", (1, 20, 21, *OPEN))

    assert keys(newest) == [(1, "open", 20)]


def test_a_new_item_that_names_no_key_is_given_the_next_one(queue: Engine) -> None:
    # Before the row is written such an item has no key, and SQLite shows
    # -1 for it. The trigger asks after the row is written, when it has
    # the key the store gave it.
    with queue.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR}", (20, 21, *OPEN))
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR_WITH_A_KEY}", (None, 22, 23, *ACCEPTED))
    with unit_of_work(queue) as work:
        through_the_model = ReviewItem(
            kind=ReviewKind.POSSIBLE_DUPLICATE,
            record_table="track",
            record_id=24,
            other_record_id=25,
            reason="They have one name.",
        )
        work.add(through_the_model)

    assert through_the_model.id == 6
    assert keys(queue) == [*AS_THEY_WERE, (4, "open", 20), (5, "accepted", 22), (6, "open", 24)]


@pytest.mark.parametrize("key", BELOW_1)
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE review_item SET id = ? WHERE id = 1",
        "UPDATE review_item SET id = ?, reason = 'They have one name and one gate.' WHERE id = 3",
        "UPDATE OR REPLACE review_item SET id = ? WHERE id = 1",
        "UPDATE OR IGNORE review_item SET id = ? WHERE id = 3",
    ],
    ids=[
        "its key alone",
        "its key and its reason",
        "its key, told to take the place of what it clashes with",
        "its key, told to pass over what is refused",
    ],
)
def test_an_open_item_is_not_given_a_key_below_1(queue: Engine, statement: str, key: int) -> None:
    before = everything(queue)

    with refused(A_KEY_IS_1_OR_MORE), queue.begin() as connection:
        connection.exec_driver_sql(statement, (key,))

    assert everything(queue) == before


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE review_item SET id = id - 3 WHERE state = 'open'",
        "UPDATE review_item SET id = 20 - id * 7 WHERE state = 'open'",
        "UPDATE review_item SET id = id + 30, note = 'To be looked at.' WHERE id = 1; "
        "UPDATE review_item SET id = 0 WHERE id = 3",
    ],
    ids=["the first item it meets", "the second item it meets", "the second statement"],
)
def test_a_statement_that_would_give_one_item_a_key_below_1_changes_no_item(
    queue: Engine, statement: str
) -> None:
    # SQLite stops the statement, and what it had done to another item
    # before it came to this one is taken back with it. In a unit of
    # work the statements before it are taken back too.
    before = everything(queue)

    with refused(A_KEY_IS_1_OR_MORE), queue.begin() as connection:
        for one in statement.split("; "):
            connection.exec_driver_sql(one)

    assert everything(queue) == before


@pytest.mark.parametrize(
    ("statement", "after"),
    [
        (
            "UPDATE review_item SET id = 30 WHERE id = 1",
            [(2, "accepted", 8), (3, "open", 10), (30, "open", 7)],
        ),
        ("UPDATE review_item SET id = id WHERE state = 'open'", AS_THEY_WERE),
        (
            "UPDATE review_item SET id = id + 30 WHERE id = 1",
            [(2, "accepted", 8), (3, "open", 10), (31, "open", 7)],
        ),
    ],
    ids=["another key", "the key it has", "a key counted from its own"],
)
def test_an_open_item_is_given_a_key_of_1_or_more_as_before(
    queue: Engine, statement: str, after: list[tuple[object, ...]]
) -> None:
    with queue.begin() as connection:
        connection.exec_driver_sql(statement)

    assert keys(queue) == after


@pytest.mark.parametrize("key", [0, -1])
def test_of_a_decided_item_the_store_says_first_that_it_is_never_edited(
    queue: Engine, key: int
) -> None:
    # The triggers of a kept decision ask before a row is changed, these
    # after it. So a decided item is refused in the sentence of its own rule.
    before = everything(queue)

    with refused(NEVER_EDITED), queue.begin() as connection:
        connection.exec_driver_sql("UPDATE review_item SET id = ? WHERE id = 2", (key,))

    assert everything(queue) == before


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE review_item SET note = 'To be looked at.' WHERE state = 'open'",
        "UPDATE review_item SET id = -1 WHERE id = 99",
        "DELETE FROM review_item WHERE id = 3",
    ],
    ids=["an edit that names no key", "a key below 1 for no item", "a delete"],
)
def test_a_statement_that_gives_no_item_a_key_below_1_is_not_refused(
    queue: Engine, statement: str
) -> None:
    with queue.begin() as connection:
        connection.exec_driver_sql(statement)

    assert [key for key, *_ in keys(queue)] == ([1, 2] if "DELETE" in statement else [1, 2, 3])


@pytest.mark.parametrize("key", [0, -1])
def test_through_the_model_a_new_item_with_a_key_below_1_is_refused(
    queue: Engine, key: int
) -> None:
    before = everything(queue)

    with refused(A_KEY_IS_1_OR_MORE), unit_of_work(queue) as work:
        work.add(
            ReviewItem(
                id=key,
                kind=ReviewKind.POSSIBLE_DUPLICATE,
                record_table="track",
                record_id=24,
                other_record_id=25,
                reason="They have one name.",
            )
        )

    assert everything(queue) == before


def test_through_the_model_an_open_item_is_not_given_a_key_below_1(queue: Engine) -> None:
    before = everything(queue)

    with refused(A_KEY_IS_1_OR_MORE), unit_of_work(queue) as work:
        work.get_one(ReviewItem, 3).note = "To be looked at."
        work.flush()
        work.execute(update(ReviewItem).where(ReviewItem.id == 1).values(id=0))

    # The note that was written before the refusal is taken back with the
    # unit of work.
    assert everything(queue) == before


@pytest.mark.parametrize(
    ("statement", "given"),
    [
        (f"INSERT INTO {A_PAIR_WITH_A_KEY}", (0, 20, 21, *OPEN)),
        (f"INSERT INTO {A_PAIR_WITH_A_KEY}", (-1, 20, 21, *ACCEPTED)),
        ("UPDATE review_item SET id = ? WHERE id = 1", (0,)),
        ("UPDATE review_item SET id = id - 3 WHERE state = 'open'", ()),
    ],
    ids=[
        "a new item",
        "a new decided item",
        "the key of an open item",
        "the keys of the open items",
    ],
)
def test_the_refusal_holds_on_a_connection_the_stores_code_did_not_open(
    queue: Engine, statement: str, given: tuple[object, ...]
) -> None:
    # The store's code switches foreign keys on for every connection it
    # opens. The triggers are in the file, and need no one to switch them on.
    before = everything(queue)
    with closing(sqlite3.connect(str(queue.url.database))) as bare:
        assert bare.execute("PRAGMA foreign_keys").fetchone() == (0,)

        with pytest.raises(sqlite3.IntegrityError) as refusal:
            bare.execute(statement, given)
        bare.commit()

    assert str(refusal.value) == A_KEY_IS_1_OR_MORE
    assert everything(queue) == before


@pytest.mark.parametrize(
    ("statement", "given"),
    [
        (f"INSERT INTO {A_PAIR_WITH_A_KEY}", (0, 20, 21, *OPEN)),
        ("UPDATE review_item SET id = id - 3 WHERE state = 'open'", ()),
    ],
    ids=["a new item", "the keys of the open items"],
)
def test_a_refusal_stops_the_statement_and_not_the_work_before_it(
    queue: Engine, statement: str, given: tuple[object, ...]
) -> None:
    # Whoever catches the refusal can go on and keep what was done before
    # it: the store stops the statement, and does not end the work.
    with closing(sqlite3.connect(str(queue.url.database))) as bare:
        bare.execute(f"INSERT INTO {A_PAIR_WITH_A_KEY}", (30, 40, 41, *OPEN))

        with pytest.raises(sqlite3.IntegrityError) as refusal:
            bare.execute(statement, given)
        bare.execute(f"INSERT INTO {A_PAIR_WITH_A_KEY}", (31, 42, 43, *OPEN))
        bare.commit()

    assert str(refusal.value) == A_KEY_IS_1_OR_MORE
    assert keys(queue) == [*AS_THEY_WERE, (30, "open", 40), (31, "open", 42)]


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
    three_items(from_the_models)
    before = everything(from_the_models)

    assert triggers(from_the_models) == THE_TRIGGERS
    for statement, given in [
        (f"INSERT INTO {A_PAIR_WITH_A_KEY}", (0, 20, 21, *OPEN)),
        (f"INSERT INTO {A_PAIR_WITH_A_KEY}", (-1, 20, 21, *ACCEPTED)),
        ("UPDATE review_item SET id = ? WHERE id = 1", (0,)),
    ]:
        with refused(A_KEY_IS_1_OR_MORE), from_the_models.begin() as connection:
            connection.exec_driver_sql(statement, given)
    assert everything(from_the_models) == before


def under(name: str, statement: str) -> str:
    """The statement with this name of the key wherever it says ``{name}``."""
    return statement.format(name=name)


@pytest.mark.parametrize("key", BELOW_1)
@pytest.mark.parametrize("name", NAMES_OF_THE_KEY)
def test_an_open_item_is_not_given_a_key_below_1_under_any_name_of_the_key(
    queue: Engine, name: str, key: int
) -> None:
    before = everything(queue)

    with refused(A_KEY_IS_1_OR_MORE), queue.begin() as connection:
        connection.exec_driver_sql(
            under(name, "UPDATE review_item SET {name} = ? WHERE id = 1"), (key,)
        )

    assert everything(queue) == before


@pytest.mark.parametrize("name", SQLITES_OWN)
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE review_item SET note = 'To be looked at.', {name} = 0 WHERE id = 3",
        "UPDATE review_item SET ({name}, note) = (-1, 'To be looked at.') WHERE id = 3",
        "UPDATE OR REPLACE review_item SET {name} = 0 WHERE id = 1",
        "UPDATE OR IGNORE review_item SET {name} = -1 WHERE id = 3",
        "UPDATE review_item SET {name} = {name} - 3 WHERE state = 'open'",
        "UPDATE review_item SET {name} = v.below FROM (SELECT -4 AS below) AS v "
        "WHERE review_item.id = 1",
        "UPDATE review_item SET id = 30, {name} = -5 WHERE id = 1",
        "UPDATE review_item SET {name} = 30, id = -5 WHERE id = 1",
    ],
    ids=[
        "after another column",
        "in one list with another column",
        "told to take the place of what it clashes with",
        "told to pass over what is refused",
        "counted from its own, for every open item",
        "from a query",
        "after the column, which says a key of 1 or more",
        "before the column, which says a key below 1",
    ],
)
def test_no_statement_gives_an_open_item_a_key_below_1_by_one_of_sqlites_own_names(
    queue: Engine, statement: str, name: str
) -> None:
    before = everything(queue)

    with refused(A_KEY_IS_1_OR_MORE), queue.begin() as connection:
        connection.exec_driver_sql(under(name, statement))

    assert everything(queue) == before


@pytest.mark.parametrize("name", NAMES_OF_THE_KEY)
def test_an_open_item_is_given_a_key_of_1_or_more_under_any_name_of_the_key(
    queue: Engine, name: str
) -> None:
    with queue.begin() as connection:
        connection.exec_driver_sql(under(name, "UPDATE review_item SET {name} = 30 WHERE id = 1"))

    assert keys(queue) == [(2, "accepted", 8), (3, "open", 10), (30, "open", 7)]


@pytest.mark.parametrize("name", SQLITES_OWN)
def test_where_a_statement_names_the_key_twice_the_store_asks_about_the_key_the_item_got(
    queue: Engine, name: str
) -> None:
    # SQLite takes the last of the two. The trigger asks after the row is
    # written, so it sees that one and no other.
    with queue.begin() as connection:
        connection.exec_driver_sql(
            under(name, "UPDATE review_item SET {name} = -5, id = 30 WHERE id = 1")
        )

    assert keys(queue) == [(2, "accepted", 8), (3, "open", 10), (30, "open", 7)]


@pytest.mark.parametrize("name", SQLITES_OWN)
def test_an_open_item_that_is_given_the_key_it_has_is_not_refused(queue: Engine, name: str) -> None:
    with queue.begin() as connection:
        connection.exec_driver_sql(
            under(
                name,
                "UPDATE review_item SET {name} = {name}, note = 'To be looked at.' "
                "WHERE state = 'open'",
            )
        )

    assert keys(queue) == AS_THEY_WERE


@pytest.mark.parametrize("key", [0, -1])
@pytest.mark.parametrize("name", SQLITES_OWN)
def test_a_new_item_whose_key_is_named_by_one_of_sqlites_own_names_is_held_too(
    queue: Engine, name: str, key: int
) -> None:
    before = everything(queue)
    a_pair = A_PAIR_WITH_A_KEY.replace("review_item (id, ", f"review_item ({name}, ")
    assert a_pair != A_PAIR_WITH_A_KEY

    with refused(A_KEY_IS_1_OR_MORE), queue.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {a_pair}", (key, 20, 21, *OPEN))
    assert everything(queue) == before

    with queue.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {a_pair}", (30, 20, 21, *OPEN))
    assert keys(queue) == [*AS_THEY_WERE, (30, "open", 20)]


@pytest.mark.parametrize("name", NAMES_OF_THE_KEY)
def test_an_item_that_is_stored_again_is_not_given_a_key_below_1_in_the_same_statement(
    queue: Engine, name: str
) -> None:
    # A statement can say what is done where the new item clashes with
    # one that is there: here, that the item that is there gets another
    # key. That is a change of the item, and it is held like any other.
    before = everything(queue)

    with refused(A_KEY_IS_1_OR_MORE), queue.begin() as connection:
        connection.exec_driver_sql(
            f"INSERT INTO {A_PAIR_WITH_A_KEY} ON CONFLICT (id) DO UPDATE SET {name} = -9",
            (1, 20, 21, *OPEN),
        )

    assert everything(queue) == before


@pytest.mark.parametrize("name", SQLITES_OWN)
def test_of_a_decided_item_the_store_says_that_it_is_never_edited_under_these_names_too(
    queue: Engine, name: str
) -> None:
    before = everything(queue)

    with refused(NEVER_EDITED), queue.begin() as connection:
        connection.exec_driver_sql(under(name, "UPDATE review_item SET {name} = 0 WHERE id = 2"))

    assert everything(queue) == before


def test_in_a_unit_of_work_a_key_below_1_by_another_name_takes_the_work_back(
    queue: Engine,
) -> None:
    before = everything(queue)

    with refused(A_KEY_IS_1_OR_MORE), unit_of_work(queue) as work:
        work.get_one(ReviewItem, 3).note = "To be looked at."
        work.flush()
        work.execute(text("UPDATE review_item SET rowid = 0 WHERE id = 1"))

    assert everything(queue) == before


@pytest.mark.parametrize("name", SQLITES_OWN)
def test_the_refusal_of_these_names_holds_on_a_connection_the_stores_code_did_not_open(
    queue: Engine, name: str
) -> None:
    before = everything(queue)
    with closing(sqlite3.connect(str(queue.url.database))) as bare:
        with pytest.raises(sqlite3.IntegrityError) as refusal:
            bare.execute(under(name, "UPDATE review_item SET {name} = 0 WHERE id = 1"))
        bare.commit()

    assert str(refusal.value) == A_KEY_IS_1_OR_MORE
    assert everything(queue) == before


@pytest.mark.parametrize("name", SQLITES_OWN)
def test_a_store_made_from_the_models_refuses_these_names_too(
    from_the_models: Engine, name: str
) -> None:
    three_items(from_the_models)
    before = everything(from_the_models)

    with refused(A_KEY_IS_1_OR_MORE), from_the_models.begin() as connection:
        connection.exec_driver_sql(under(name, "UPDATE review_item SET {name} = 0 WHERE id = 1"))

    assert everything(from_the_models) == before


@pytest.fixture
def with_a_key_from_before(store: Engine) -> Engine:
    """The test's own store with the newest schema and an item whose key is -3.

    The item was stored before the store had the rule of the keys, by
    the first ten migrations, and kept its key through the ones after.
    Beside it is an open item with the key 5.
    """
    migrate(store, MIGRATIONS[:10])
    with store.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR_WITH_A_KEY}", (-3, 8, 9, *OPEN))
        connection.exec_driver_sql(f"INSERT INTO {A_PAIR_WITH_A_KEY}", (5, 7, 12, *OPEN))
    migrate(store)
    assert keys(store) == [(-3, "open", 8), (5, "open", 7)]
    return store


def test_an_item_that_had_a_key_below_1_before_the_rule_keeps_it_and_is_given_a_note(
    with_a_key_from_before: Engine,
) -> None:
    with with_a_key_from_before.begin() as connection:
        connection.exec_driver_sql("UPDATE review_item SET note = 'To be looked at.'")
        notes = connection.exec_driver_sql("SELECT id, note FROM review_item ORDER BY id").all()

    assert [tuple(row) for row in notes] == [(-3, "To be looked at."), (5, "To be looked at.")]


@pytest.mark.parametrize("key", [-7, 0])
@pytest.mark.parametrize("name", ["id", *SQLITES_OWN])
def test_an_item_that_had_a_key_below_1_before_the_rule_is_not_given_another_such_key(
    with_a_key_from_before: Engine, name: str, key: int
) -> None:
    before = everything(with_a_key_from_before)

    with refused(A_KEY_IS_1_OR_MORE), with_a_key_from_before.begin() as connection:
        connection.exec_driver_sql(
            under(name, "UPDATE review_item SET {name} = ? WHERE id = -3"), (key,)
        )

    assert everything(with_a_key_from_before) == before


@pytest.mark.parametrize("name", ["id", *SQLITES_OWN])
def test_an_item_that_had_a_key_below_1_before_the_rule_is_given_a_key_of_1_or_more_for_good(
    with_a_key_from_before: Engine, name: str
) -> None:
    with with_a_key_from_before.begin() as connection:
        connection.exec_driver_sql(under(name, "UPDATE review_item SET {name} = 3 WHERE id = -3"))
    assert keys(with_a_key_from_before) == [(3, "open", 8), (5, "open", 7)]

    with refused(A_KEY_IS_1_OR_MORE), with_a_key_from_before.begin() as connection:
        connection.exec_driver_sql(under(name, "UPDATE review_item SET {name} = -3 WHERE id = 3"))
    assert keys(with_a_key_from_before) == [(3, "open", 8), (5, "open", 7)]
