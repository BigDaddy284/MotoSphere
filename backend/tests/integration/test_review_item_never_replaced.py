"""Tests that a decided review item is never replaced, against a real SQLite file.

The store of every test is built by the migrations, as a real store is,
and most tests begin with two sources and four items in it: two items
that are open and two that were decided. A statement that says REPLACE
takes out the row its new row clashes with, and SQLite fires no trigger
for a row it takes out so. What the store must refuse is written past
the model, through the model, and on a connection that the store's code
did not open.
"""

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path

import pytest
from sqlalchemy import Engine, insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from motosphere.db.models import SCHEMA, ReviewItem
from motosphere.db.models.review_item import ReviewKind
from motosphere.db.store import open_store
from motosphere.db.work import unit_of_work

NEVER_REPLACED = "A decided review item (review_item) is never replaced."
NEVER_EDITED = "A decided review item (review_item) is never edited."
FIRST = "2026-11-25T22:00:00.000000+00:00"
# Two sources: what follows INSERT INTO, with the name and the website to be given.
A_SOURCE = (
    "source (name, website, category, collection_method, switched_on, created_at, updated_at) "
    "VALUES (?, ?, 'governing body', 'rss feed', 0, '2026-11-19T08:00:00.000000+00:00', "
    "'2026-11-19T08:00:00.000000+00:00')"
)
# An item with every column of the two indexes to be given, with its key
# or without: what follows INSERT INTO. A possible duplicate is given
# its two records, and a doubt about a field its record, the field, the
# source and what the source says.
COLUMNS = (
    "kind, record_table, record_id, other_record_id, field, source_id, source_address, "
    "source_value, reason, state, decided_by, decided_at, created_at, updated_at"
)
VALUES = (
    "?, ?, ?, ?, ?, ?, ?, ?, 'They may be one.', ?, ?, ?, '2026-11-25T22:00:00.000000+00:00', "
    "'2026-11-25T22:00:00.000000+00:00'"
)
AN_ITEM = f"review_item ({COLUMNS}) VALUES ({VALUES})"
AN_ITEM_WITH_A_KEY = f"review_item (id, {COLUMNS}) VALUES (?, {VALUES})"
OPEN = ("open", None, None)
ACCEPTED = ("accepted", "Jo Example", FIRST)
REJECTED = ("rejected", "Jo Example", FIRST)
AN_ADDRESS = "https://federation.example/tracks/7"


def a_pair(record: object, other: object, table: str = "track") -> tuple[object, ...]:
    """The columns of a possible duplicate of two records, before its state."""
    return ("possible duplicate", table, record, other, None, None, None, None)


def of_a_field(
    record: object,
    table: str = "track",
    field: str = "length_in_metres",
    source: object = 1,
    says: object = "1750",
    kind: str = "sources disagree",
    address: str = AN_ADDRESS,
) -> tuple[object, ...]:
    """The columns of a doubt about a field of a record, before its state."""
    return (kind, table, record, None, field, source, address, says)


# The two triggers of this rule: the first for a new item, the second for
# an open item that is changed.
THE_TRIGGERS = [
    ("tr_review_item_decided_never_replaced", "review_item"),
    ("tr_review_item_decided_never_replaced_by_another", "review_item"),
]
# The four ways a statement says what is done with a row that clashes.
NEW = ["INSERT", "INSERT OR REPLACE", "REPLACE", "INSERT OR IGNORE"]
CHANGED = ["UPDATE", "UPDATE OR REPLACE", "UPDATE OR IGNORE"]
# A new item in the place of a decided one: by the key of the accepted
# item, 2, or of the rejected one, 3, as the two records of the accepted
# item, and as what the rejected one says of a field.
IN_THE_PLACE_OF_A_DECIDED_ITEM = {
    "with the key of the accepted item": (AN_ITEM_WITH_A_KEY, (2, *a_pair(30, 31), *OPEN)),
    "with the key of the rejected item": (AN_ITEM_WITH_A_KEY, (3, *a_pair(30, 31), *OPEN)),
    "a doubt about a field with the key of the accepted item": (
        AN_ITEM_WITH_A_KEY,
        (2, *of_a_field(30), *OPEN),
    ),
    "a decided item with the key of the accepted item": (
        AN_ITEM_WITH_A_KEY,
        (2, *a_pair(30, 31), *REJECTED),
    ),
    "the two records of the accepted item": (AN_ITEM, (*a_pair(8, 9), *OPEN)),
    "the two records of the accepted item, decided": (AN_ITEM, (*a_pair(8, 9), *REJECTED)),
    "the two records of the accepted item, with a key": (
        AN_ITEM_WITH_A_KEY,
        (20, *a_pair(8, 9), *OPEN),
    ),
    "the two records of the accepted item, with the key of an open item": (
        AN_ITEM_WITH_A_KEY,
        (1, *a_pair(8, 9), *OPEN),
    ),
    "what the rejected item says of a field": (AN_ITEM, (*of_a_field(7), *OPEN)),
    "what the rejected item says of a field, of another kind at another address": (
        AN_ITEM,
        (
            *of_a_field(
                7,
                kind="value outside its rules",
                address="https://federation.example/venues/7",
            ),
            *OPEN,
        ),
    ),
    "what the rejected item says of a field, with a key": (
        AN_ITEM_WITH_A_KEY,
        (20, *of_a_field(7), *ACCEPTED),
    ),
}
# An open item put in the place of a decided one. Item 1 is an open
# possible duplicate and item 4 an open doubt about a field.
INTO_THE_PLACE_OF_A_DECIDED_ITEM = {
    "the key of the accepted item": "review_item SET id = 2 WHERE id = 1",
    "the key of the rejected item": "review_item SET id = 3 WHERE id = 4",
    "the two records of the accepted item": (
        "review_item SET record_id = 8, other_record_id = 9 WHERE id = 1"
    ),
    "the two records of the accepted item, and decided": (
        "review_item SET record_id = 8, other_record_id = 9, state = 'rejected', "
        "decided_by = 'Sam Example', decided_at = '2026-11-26T09:30:00.000000+00:00' "
        "WHERE id = 1"
    ),
    "what the rejected item says of a field": "review_item SET record_id = 7 WHERE id = 4",
    "what the rejected item says of a field, of another kind": (
        "review_item SET record_id = 7, kind = 'value outside its rules' WHERE id = 4"
    ),
}
# A new item that is another doubt than each decided item by one column
# of an index, and by no other.
ANOTHER_DOUBT_BY_ONE_COLUMN = {
    "two records of another table": a_pair(8, 9, table="rider"),
    "another first record": a_pair(7, 9),
    "another second record": a_pair(8, 10),
    "a field of a record of another table": of_a_field(7, table="rider"),
    "the field of another record": of_a_field(9),
    "another field": of_a_field(7, field="name"),
    "another source": of_a_field(7, source=2),
    "another thing said": of_a_field(7, says="1800"),
    "the first record of the accepted item and another": a_pair(8, 20),
    "the record of the rejected item and another": a_pair(7, 20),
    "a field of the first record of the accepted item": of_a_field(
        8, field="name", says="Example Park"
    ),
}
# The same for an open item that is changed: item 1 for a possible
# duplicate, item 4 for a doubt about a field.
MADE_ANOTHER_DOUBT_BY_ONE_COLUMN = {
    "two records of another table": (
        "UPDATE OR REPLACE review_item SET record_table = 'rider', record_id = 8, "
        "other_record_id = 9 WHERE id = 1"
    ),
    "another first record": (
        "UPDATE OR REPLACE review_item SET record_id = 7, other_record_id = 9 WHERE id = 1"
    ),
    "another second record": (
        "UPDATE OR REPLACE review_item SET record_id = 8, other_record_id = 10 WHERE id = 1"
    ),
    "a field of a record of another table": (
        "UPDATE OR REPLACE review_item SET record_table = 'rider', record_id = 7 WHERE id = 4"
    ),
    "the field of another record": ("UPDATE OR REPLACE review_item SET record_id = 9 WHERE id = 4"),
    "another field": (
        "UPDATE OR REPLACE review_item SET record_id = 7, field = 'name' WHERE id = 4"
    ),
    "another source": (
        "UPDATE OR REPLACE review_item SET record_id = 7, source_id = 2 WHERE id = 4"
    ),
    "another thing said": (
        "UPDATE OR REPLACE review_item SET record_id = 7, source_value = '1800' WHERE id = 4"
    ),
}


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


def doubts(store: Engine) -> list[tuple[object, ...]]:
    """The key of every item with its state and what it is about, by the key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT id, state, record_table, record_id, other_record_id, field, source_id, "
            "source_value FROM review_item ORDER BY id"
        )
        return [tuple(row) for row in found]


def triggers(store: Engine) -> list[tuple[str, str]]:
    """The triggers against replacing on the table of the review queue, by name."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger' AND "
            "tbl_name = 'review_item' AND name GLOB 'tr_review_item_decided_never_replaced*' "
            "ORDER BY name"
        )
        return [(str(name), str(table)) for name, table in found]


def four_items(store: Engine) -> None:
    """Write two sources and the four items past the model.

    Item 1 is an open possible duplicate, item 2 one that was accepted,
    item 3 a doubt about a field that was rejected, and item 4 an open one.
    """
    with store.begin() as connection:
        connection.exec_driver_sql(
            f"INSERT INTO {A_SOURCE}", ("Example Federation", "https://federation.example")
        )
        connection.exec_driver_sql(
            f"INSERT INTO {A_SOURCE}", ("Example Club", "https://club.example")
        )
        connection.exec_driver_sql(f"INSERT INTO {AN_ITEM}", (*a_pair(7, 12), *OPEN))
        connection.exec_driver_sql(f"INSERT INTO {AN_ITEM}", (*a_pair(8, 9), *ACCEPTED))
        connection.exec_driver_sql(f"INSERT INTO {AN_ITEM}", (*of_a_field(7), *REJECTED))
        connection.exec_driver_sql(f"INSERT INTO {AN_ITEM}", (*of_a_field(8), *OPEN))


AS_THEY_WERE = [
    (1, "open", "track", 7, 12, None, None, None),
    (2, "accepted", "track", 8, 9, None, None, None),
    (3, "rejected", "track", 7, None, "length_in_metres", 1, "1750"),
    (4, "open", "track", 8, None, "length_in_metres", 1, "1750"),
]


@pytest.fixture
def queue(newest: Engine) -> Engine:
    """The test's own store with the newest schema and the four items in it."""
    four_items(newest)
    assert doubts(newest) == AS_THEY_WERE
    return newest


def test_the_table_of_the_review_queue_has_the_two_triggers_against_replacing(
    newest: Engine,
) -> None:
    assert triggers(newest) == THE_TRIGGERS


def test_a_row_of_the_table_clashes_by_its_key_and_by_two_indexes_and_no_other(
    newest: Engine,
) -> None:
    # The triggers ask about the key and about the two indexes that take
    # one doubt for one item. An index that is added to the table and
    # holds a row to be the only one of its kind is one more way of
    # taking a row out with REPLACE: the triggers are then to ask about
    # it too, and this test is changed with them.
    with newest.connect() as connection:
        indexes = connection.exec_driver_sql(
            "SELECT name, \"unique\", origin, partial FROM pragma_index_list('review_item') "
            'WHERE "unique" ORDER BY name'
        ).all()
        written = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'review_item'"
        ).scalar_one()

    assert [tuple(index) for index in indexes] == [
        ("ix_review_item_record_table_record_id_field_source_id_source_value", 1, "c", 1),
        ("ix_review_item_record_table_record_id_other_record_id", 1, "c", 1),
    ]
    assert "UNIQUE" not in str(written)
    assert str(written).count("PRIMARY KEY") == 1


@pytest.mark.parametrize("told", NEW)
@pytest.mark.parametrize(
    ("item", "given"),
    list(IN_THE_PLACE_OF_A_DECIDED_ITEM.values()),
    ids=list(IN_THE_PLACE_OF_A_DECIDED_ITEM),
)
def test_a_new_item_in_the_place_of_a_decided_item_is_refused(
    queue: Engine, item: str, given: tuple[object, ...], told: str
) -> None:
    # Whatever the statement is told to do with a row that clashes: a
    # trigger cannot tell, and the store stops the statement before the
    # row is written.
    before = everything(queue)

    with refused(NEVER_REPLACED), queue.begin() as connection:
        connection.exec_driver_sql(f"{told} INTO {item}", given)

    assert everything(queue) == before


@pytest.mark.parametrize(
    "what_then",
    [
        "ON CONFLICT DO NOTHING",
        "ON CONFLICT (record_table, record_id, other_record_id) "
        "WHERE other_record_id IS NOT NULL DO UPDATE SET reason = 'Found again.'",
    ],
    ids=["to do nothing", "to change the item that is there"],
)
def test_a_new_item_that_says_what_to_do_on_a_clash_with_a_decided_item_is_refused(
    queue: Engine, what_then: str
) -> None:
    before = everything(queue)

    with refused(NEVER_REPLACED), queue.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {AN_ITEM} {what_then}", (*a_pair(8, 9), *OPEN))

    assert everything(queue) == before


@pytest.mark.parametrize(
    ("item", "given"),
    [
        (AN_ITEM_WITH_A_KEY, ("2", *a_pair(30, 31), *OPEN)),
        (AN_ITEM_WITH_A_KEY, (2.0, *a_pair(30, 31), *OPEN)),
        (AN_ITEM, (*a_pair("8", "9"), *OPEN)),
        (AN_ITEM, (*of_a_field("7", source="1", says=1750), *OPEN)),
    ],
    ids=[
        "the key as text",
        "the key as a number with a point",
        "the two records as text",
        "the record and the source as text, and what is said as a number",
    ],
)
def test_a_value_written_another_way_is_the_value_the_table_would_hold(
    queue: Engine, item: str, given: tuple[object, ...]
) -> None:
    # SQLite makes of each value what the column holds before it asks the
    # trigger, as it does before it looks into an index.
    before = everything(queue)

    with refused(NEVER_REPLACED), queue.begin() as connection:
        connection.exec_driver_sql(f"REPLACE INTO {item}", given)

    assert everything(queue) == before


@pytest.mark.parametrize("told", CHANGED)
@pytest.mark.parametrize(
    "change",
    list(INTO_THE_PLACE_OF_A_DECIDED_ITEM.values()),
    ids=list(INTO_THE_PLACE_OF_A_DECIDED_ITEM),
)
def test_an_open_item_is_not_put_in_the_place_of_a_decided_item(
    queue: Engine, change: str, told: str
) -> None:
    before = everything(queue)

    with refused(NEVER_REPLACED), queue.begin() as connection:
        connection.exec_driver_sql(f"{told} {change}")

    assert everything(queue) == before


OVER_SEVERAL_ITEMS = pytest.mark.parametrize(
    ("statement", "given"),
    [
        (
            f"INSERT OR REPLACE INTO {AN_ITEM} , ({VALUES})",
            (*a_pair(50, 51), *OPEN, *a_pair(8, 9), *OPEN),
        ),
        (
            f"INSERT OR REPLACE INTO {AN_ITEM} , ({VALUES})",
            (*a_pair(50, 51), *ACCEPTED, *a_pair(50, 51), *OPEN),
        ),
        (
            "INSERT OR REPLACE INTO review_item SELECT 2, kind, record_table, 90, 91, field, "
            "source_id, source_address, source_value, reason, state, decided_by, decided_at, "
            "note, created_at, updated_at FROM review_item WHERE id = 1",
            (),
        ),
        ("UPDATE OR REPLACE review_item SET id = id + 1 WHERE state = 'open'", ()),
        (
            "UPDATE OR REPLACE review_item SET kind = 'possible duplicate', record_id = 70, "
            "other_record_id = 71, field = NULL, source_id = NULL, source_address = NULL, "
            "source_value = NULL, state = 'accepted', decided_by = 'Sam Example', "
            "decided_at = '2026-11-26T09:30:00.000000+00:00' WHERE state = 'open'",
            (),
        ),
    ],
    ids=[
        "two new items, the second in the place of a decided one",
        "a new decided item and then the same doubt again",
        "a copy of an open item with the key of a decided one",
        "the open items each given the next key",
        "the open items decided and made one doubt",
    ],
)


@OVER_SEVERAL_ITEMS
def test_a_statement_that_would_replace_a_decided_item_on_its_way_changes_no_item(
    queue: Engine, statement: str, given: tuple[object, ...]
) -> None:
    # SQLite stops the statement, and what it had done before it came to
    # the decided item is taken back with it. An item the statement
    # itself stored or made decided is a decided item from then on.
    before = everything(queue)

    with refused(NEVER_REPLACED), queue.begin() as connection:
        connection.exec_driver_sql(statement, given)

    assert everything(queue) == before


def test_a_refusal_takes_back_the_whole_unit_of_work(queue: Engine) -> None:
    before = everything(queue)

    with refused(NEVER_REPLACED), queue.begin() as connection:
        connection.exec_driver_sql("UPDATE review_item SET note = 'To be looked at.' WHERE id = 4")
        connection.exec_driver_sql(f"REPLACE INTO {AN_ITEM}", (*a_pair(8, 9), *OPEN))

    assert everything(queue) == before


@pytest.mark.parametrize("told", ["INSERT", "REPLACE"])
@pytest.mark.parametrize(
    "columns",
    list(ANOTHER_DOUBT_BY_ONE_COLUMN.values()),
    ids=list(ANOTHER_DOUBT_BY_ONE_COLUMN),
)
def test_a_new_item_that_is_another_doubt_than_every_decided_item_is_stored(
    queue: Engine, columns: tuple[object, ...], told: str
) -> None:
    with queue.begin() as connection:
        connection.exec_driver_sql(f"{told} INTO {AN_ITEM}", (*columns, *OPEN))

    _, table, record, other, field, source, _, says = columns
    assert doubts(queue) == [*AS_THEY_WERE, (5, "open", table, record, other, field, source, says)]


@pytest.mark.parametrize(
    "statement",
    list(MADE_ANOTHER_DOUBT_BY_ONE_COLUMN.values()),
    ids=list(MADE_ANOTHER_DOUBT_BY_ONE_COLUMN),
)
def test_an_open_item_is_made_another_doubt_than_every_decided_item(
    queue: Engine, statement: str
) -> None:
    with queue.begin() as connection:
        connection.exec_driver_sql(statement)

    after = doubts(queue)
    assert [item[:2] for item in after] == [item[:2] for item in AS_THEY_WERE]
    assert after[1:3] == AS_THEY_WERE[1:3]
    assert after != AS_THEY_WERE


@pytest.mark.parametrize(
    ("statement", "given", "after"),
    [
        (
            f"INSERT OR REPLACE INTO {AN_ITEM_WITH_A_KEY}",
            (1, *a_pair(30, 31), *OPEN),
            [(1, "open", 30), (2, "accepted", 8), (3, "rejected", 7), (4, "open", 8)],
        ),
        (
            f"REPLACE INTO {AN_ITEM}",
            (*a_pair(7, 12), *ACCEPTED),
            [(2, "accepted", 8), (3, "rejected", 7), (4, "open", 8), (5, "accepted", 7)],
        ),
        (
            f"REPLACE INTO {AN_ITEM}",
            (*of_a_field(8), *OPEN),
            [(1, "open", 7), (2, "accepted", 8), (3, "rejected", 7), (5, "open", 8)],
        ),
        (
            "UPDATE OR REPLACE review_item SET id = 1 WHERE id = 4",
            (),
            [(1, "open", 8), (2, "accepted", 8), (3, "rejected", 7)],
        ),
        (
            "UPDATE OR REPLACE review_item SET kind = 'possible duplicate', record_id = 7, "
            "other_record_id = 12, field = NULL, source_id = NULL, source_address = NULL, "
            "source_value = NULL WHERE id = 4",
            (),
            [(2, "accepted", 8), (3, "rejected", 7), (4, "open", 7)],
        ),
    ],
    ids=[
        "a new item with its key",
        "the same two records again, decided",
        "the same thing said of the field again",
        "another open item given its key",
        "another open item made the same doubt",
    ],
)
def test_an_open_item_is_replaced_as_before(
    queue: Engine, statement: str, given: tuple[object, ...], after: list[tuple[object, ...]]
) -> None:
    # An open item is edited and deleted as before, and a statement that
    # says REPLACE takes it out as before.
    with queue.begin() as connection:
        connection.exec_driver_sql(statement, given)

    assert [(item[0], item[1], item[3]) for item in doubts(queue)] == after


@pytest.mark.parametrize(
    ("statement", "after"),
    [
        (
            "UPDATE review_item SET state = 'accepted', decided_by = 'Sam Example', "
            "decided_at = '2026-11-26T09:30:00.000000+00:00' WHERE id = 1",
            [(1, "accepted"), (2, "accepted"), (3, "rejected"), (4, "open")],
        ),
        (
            "UPDATE review_item SET id = 30, note = 'To be looked at.' WHERE id = 4",
            [(1, "open"), (2, "accepted"), (3, "rejected"), (30, "open")],
        ),
        (
            "UPDATE review_item SET note = 'To be looked at.' WHERE state = 'open'",
            [(1, "open"), (2, "accepted"), (3, "rejected"), (4, "open")],
        ),
        (
            "DELETE FROM review_item WHERE state = 'open'",
            [(2, "accepted"), (3, "rejected")],
        ),
    ],
    ids=["decided", "given another key and a note", "each given a note", "deleted"],
)
def test_an_open_item_is_changed_as_before(
    queue: Engine, statement: str, after: list[tuple[object, ...]]
) -> None:
    with queue.begin() as connection:
        connection.exec_driver_sql(statement)

    assert [item[:2] for item in doubts(queue)] == after


def test_a_new_item_that_names_no_key_is_stored_open_or_decided(queue: Engine) -> None:
    # Before the row is written such an item has no key, and SQLite shows
    # -1 for it: the trigger asks about a key from 1 on.
    with queue.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {AN_ITEM}", (*a_pair(30, 31), *OPEN))
        connection.exec_driver_sql(
            f"INSERT INTO {AN_ITEM_WITH_A_KEY}", (None, *of_a_field(30), *ACCEPTED)
        )

    assert [item[:2] for item in doubts(queue)] == [
        (1, "open"),
        (2, "accepted"),
        (3, "rejected"),
        (4, "open"),
        (5, "open"),
        (6, "accepted"),
    ]


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE OR REPLACE review_item SET id = 3 WHERE id = 2",
        "UPDATE OR REPLACE review_item SET id = 2 WHERE id = 2",
        "UPDATE review_item SET note = 'Looked again.' WHERE id = 3",
        "UPDATE OR REPLACE review_item SET record_id = 7, other_record_id = 12 WHERE id = 2",
    ],
    ids=[
        "given the key of the other decided item",
        "given its own key",
        "given a note",
        "made the doubt of an open item",
    ],
)
def test_of_a_decided_item_the_store_says_that_it_is_never_edited(
    queue: Engine, statement: str
) -> None:
    # The trigger of this rule asks of an open item only. A decided item
    # that is changed is refused in the sentence of its own rule.
    before = everything(queue)

    with refused(NEVER_EDITED), queue.begin() as connection:
        connection.exec_driver_sql(statement)

    assert everything(queue) == before


def test_in_a_queue_without_items_there_is_nothing_to_refuse(newest: Engine) -> None:
    with newest.begin() as connection:
        connection.exec_driver_sql(
            f"INSERT INTO {A_SOURCE}", ("Example Federation", "https://federation.example")
        )
        connection.exec_driver_sql(
            f"REPLACE INTO {AN_ITEM_WITH_A_KEY}", (2, *a_pair(8, 9), *ACCEPTED)
        )
        connection.exec_driver_sql(f"REPLACE INTO {AN_ITEM}", (*of_a_field(7), *OPEN))
        connection.exec_driver_sql("UPDATE OR REPLACE review_item SET id = 1 WHERE id = 3")

    assert [item[:2] for item in doubts(newest)] == [(1, "open"), (2, "accepted")]


def test_a_decided_item_with_the_key_1_is_not_replaced(newest: Engine) -> None:
    # The first key the store gives is 1, and it is the least key the
    # first trigger asks about.
    with newest.begin() as connection:
        connection.exec_driver_sql(f"INSERT INTO {AN_ITEM}", (*a_pair(8, 9), *ACCEPTED))
        connection.exec_driver_sql(f"INSERT INTO {AN_ITEM}", (*a_pair(7, 12), *OPEN))
    before = everything(newest)
    assert [item[:2] for item in doubts(newest)] == [(1, "accepted"), (2, "open")]

    for statement, given in [
        (f"INSERT OR REPLACE INTO {AN_ITEM_WITH_A_KEY}", (1, *a_pair(30, 31), *OPEN)),
        ("UPDATE OR REPLACE review_item SET id = 1 WHERE id = 2", ()),
    ]:
        with refused(NEVER_REPLACED), newest.begin() as connection:
            connection.exec_driver_sql(statement, given)

    assert everything(newest) == before


def a_new_item_with_the_key_of_a_decided_one(work: Session) -> None:
    work.add(
        ReviewItem(
            id=2,
            kind=ReviewKind.POSSIBLE_DUPLICATE,
            record_table="track",
            record_id=30,
            other_record_id=31,
            reason="They have one name.",
        )
    )


def a_new_item_that_is_the_doubt_of_a_decided_one(work: Session) -> None:
    work.add(
        ReviewItem(
            kind=ReviewKind.POSSIBLE_DUPLICATE,
            record_table="track",
            record_id=8,
            other_record_id=9,
            reason="They have one name.",
        )
    )


def a_new_item_told_to_take_the_place_of_a_decided_one(work: Session) -> None:
    work.execute(
        insert(ReviewItem)
        .prefix_with("OR REPLACE")
        .values(
            kind=ReviewKind.SOURCES_DISAGREE,
            record_table="track",
            record_id=7,
            field="length_in_metres",
            source_id=1,
            source_address=AN_ADDRESS,
            source_value="1750",
            reason="The record says 1600.",
        )
    )


def an_open_item_that_was_read_is_given_the_two_records_of_a_decided_one(work: Session) -> None:
    item = work.get_one(ReviewItem, 1)
    item.record_id = 8
    item.other_record_id = 9


def an_open_item_told_to_take_the_key_of_a_decided_one(work: Session) -> None:
    work.execute(
        update(ReviewItem).prefix_with("OR REPLACE").where(ReviewItem.id == 4).values(id=3)
    )


@pytest.mark.parametrize(
    "the_work",
    [
        a_new_item_with_the_key_of_a_decided_one,
        a_new_item_that_is_the_doubt_of_a_decided_one,
        a_new_item_told_to_take_the_place_of_a_decided_one,
        an_open_item_that_was_read_is_given_the_two_records_of_a_decided_one,
        an_open_item_told_to_take_the_key_of_a_decided_one,
    ],
)
def test_through_the_model_a_decided_item_is_not_replaced(
    queue: Engine, the_work: Callable[[Session], None]
) -> None:
    before = everything(queue)

    with refused(NEVER_REPLACED), unit_of_work(queue) as work:
        work.get_one(ReviewItem, 4).note = "To be looked at."
        work.flush()
        the_work(work)

    # The note that was written before the refusal is taken back with the
    # unit of work.
    assert everything(queue) == before


@pytest.mark.parametrize("recursive", [0, 1], ids=["as SQLite opens it", "recursive triggers on"])
@pytest.mark.parametrize(
    ("statement", "given"),
    [
        (f"INSERT OR REPLACE INTO {AN_ITEM_WITH_A_KEY}", (2, *a_pair(30, 31), *OPEN)),
        (f"REPLACE INTO {AN_ITEM}", (*a_pair(8, 9), *OPEN)),
        (f"REPLACE INTO {AN_ITEM}", (*of_a_field(7), *OPEN)),
        ("UPDATE OR REPLACE review_item SET id = 2 WHERE id = 1", ()),
        ("UPDATE OR REPLACE review_item SET record_id = 8, other_record_id = 9 WHERE id = 1", ()),
        ("UPDATE OR REPLACE review_item SET record_id = 7 WHERE id = 4", ()),
    ],
    ids=[
        "a new item with its key",
        "the same two records again",
        "the same thing said of the field again",
        "an open item given its key",
        "an open item given its two records",
        "an open item made what it says of the field",
    ],
)
def test_the_refusal_holds_on_a_connection_the_stores_code_did_not_open(
    queue: Engine, statement: str, given: tuple[object, ...], recursive: int
) -> None:
    # The store's code switches foreign keys on for every connection it
    # opens. The triggers are in the file, and need no one to switch them
    # on. Where a connection has SQLite fire the triggers of a delete for
    # a row that REPLACE takes out, the store has said no before that.
    before = everything(queue)
    with closing(sqlite3.connect(str(queue.url.database))) as bare:
        assert bare.execute("PRAGMA foreign_keys").fetchone() == (0,)
        bare.execute(f"PRAGMA recursive_triggers = {recursive}")
        assert bare.execute("PRAGMA recursive_triggers").fetchone() == (recursive,)

        with pytest.raises(sqlite3.IntegrityError) as refusal:
            bare.execute(statement, given)
        bare.commit()

    assert str(refusal.value) == NEVER_REPLACED
    assert everything(queue) == before


@pytest.mark.parametrize(
    ("statement", "given"),
    [
        (f"REPLACE INTO {AN_ITEM}", (*a_pair(8, 9), *OPEN)),
        ("UPDATE OR REPLACE review_item SET id = 2 WHERE id = 1", ()),
    ],
    ids=["a new item", "an open item"],
)
def test_a_refusal_stops_the_statement_and_not_the_work_before_it(
    queue: Engine, statement: str, given: tuple[object, ...]
) -> None:
    # Whoever catches the refusal can go on and keep what was done before
    # it: the store stops the statement, and does not end the work.
    with closing(sqlite3.connect(str(queue.url.database))) as bare:
        bare.execute(f"INSERT INTO {AN_ITEM}", (*a_pair(40, 41), *OPEN))

        with pytest.raises(sqlite3.IntegrityError) as refusal:
            bare.execute(statement, given)
        bare.execute(f"INSERT INTO {AN_ITEM}", (*a_pair(42, 43), *OPEN))
        bare.commit()

    assert str(refusal.value) == NEVER_REPLACED
    assert doubts(queue) == [
        *AS_THEY_WERE,
        (5, "open", "track", 40, 41, None, None, None),
        (6, "open", "track", 42, 43, None, None, None),
    ]


@OVER_SEVERAL_ITEMS
def test_a_refusal_takes_back_what_the_statement_did_and_not_the_work_before_it(
    queue: Engine, statement: str, given: tuple[object, ...]
) -> None:
    # The same statements as above, where nothing takes the work back: what
    # the statement had stored or changed before it came to the decided item
    # is gone when the refusal is caught, and by the store's own doing.
    with closing(sqlite3.connect(str(queue.url.database))) as bare:
        bare.execute(f"INSERT INTO {AN_ITEM}", (*a_pair(40, 41), *OPEN))

        with pytest.raises(sqlite3.IntegrityError) as refusal:
            bare.execute(statement, given)
        bare.commit()

    assert str(refusal.value) == NEVER_REPLACED
    assert doubts(queue) == [*AS_THEY_WERE, (5, "open", "track", 40, 41, None, None, None)]


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
    for statement, given in [
        (f"INSERT OR REPLACE INTO {AN_ITEM_WITH_A_KEY}", (2, *a_pair(30, 31), *OPEN)),
        (f"REPLACE INTO {AN_ITEM}", (*a_pair(8, 9), *OPEN)),
        (f"REPLACE INTO {AN_ITEM}", (*of_a_field(7), *OPEN)),
        ("UPDATE OR REPLACE review_item SET id = 2 WHERE id = 1", ()),
        ("UPDATE OR REPLACE review_item SET record_id = 8, other_record_id = 9 WHERE id = 1", ()),
        ("UPDATE OR REPLACE review_item SET record_id = 7 WHERE id = 4", ()),
    ]:
        with refused(NEVER_REPLACED), from_the_models.begin() as connection:
            connection.exec_driver_sql(statement, given)
    assert everything(from_the_models) == before
    # An open item is replaced in a store made from the models too.
    with from_the_models.begin() as connection:
        connection.exec_driver_sql(f"REPLACE INTO {AN_ITEM}", (*a_pair(7, 12), *ACCEPTED))
    assert [item[:2] for item in doubts(from_the_models)] == [
        (2, "accepted"),
        (3, "rejected"),
        (4, "open"),
        (5, "accepted"),
    ]
