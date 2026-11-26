"""Tests of the table of the changes to records, against a real SQLite file.

The store of every test is built by the migrations, as a real store is.
What the table must refuse is also written past the model.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import IntegrityError

from motosphere.db.models import CollectionRun, RecordChange, Source
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

MOMENT = "2026-11-25T22:00:00.000000+00:00"
BROKEN_KEY = "FOREIGN KEY constraint failed"
NOTHING_CHANGED = "CHECK constraint failed: ck_record_change_new_value_not_old_value"
NO_ONE_CAUSE = "CHECK constraint failed: ck_record_change_caused_by_a_run_or_a_person"
# A row written past the model: every column but the key, in the table's order.
PAST_THE_MODEL = (
    "INSERT INTO record_change (record_table, record_id, field, old_value, new_value, "
    "collection_run_id, decided_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
WHAT_IT_HOLDS = (
    "SELECT record_table, record_id, field, old_value, new_value, collection_run_id, "
    "decided_by FROM record_change ORDER BY id"
)


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def a_run(store: Engine) -> int:
    """Store a source and a run of it, and give the key of the run."""
    source = Source(
        name="Example Federation",
        website="https://federation.example",
        category=SourceCategory.GOVERNING_BODY,
        collection_method=CollectionMethod.RSS,
    )
    with unit_of_work(store) as work:
        work.add(source)
        work.flush()
        run = CollectionRun(source_id=source.id, started_at=datetime(2026, 11, 25, 21, tzinfo=UTC))
        work.add(run)
    return run.id


def write(store: Engine, **given: object) -> None:
    """Write a change past the model, as plain SQL: one a person decided, but for what is given."""
    row: dict[str, object] = {
        "record_table": "track",
        "record_id": 7,
        "field": "name",
        "old_value": "Example Park",
        "new_value": "Example Raceway",
        "collection_run_id": None,
        "decided_by": "Jo Example",
        "created_at": MOMENT,
        "updated_at": MOMENT,
    }
    assert set(given) <= set(row)
    row.update(given)
    with store.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, tuple(row.values()))


def held(store: Engine) -> list[tuple[object, ...]]:
    """What the table holds, as SQLite holds it, by the key, without the two times."""
    with store.connect() as connection:
        return [tuple(row) for row in connection.exec_driver_sql(WHAT_IT_HOLDS)]


def test_in_the_file_the_table_is_as_the_model_says_it(newest: Engine) -> None:
    with newest.connect() as connection:
        columns = [
            (name, kind, bool(must), bool(key))
            for _, name, kind, must, _, key in connection.exec_driver_sql(
                "PRAGMA table_info(record_change)"
            )
        ]
        refers = [
            (to, here, there, on_update, on_delete)
            for _, _, to, here, there, on_update, on_delete, _ in connection.exec_driver_sql(
                "PRAGMA foreign_key_list(record_change)"
            )
        ]
        indexes = connection.exec_driver_sql("PRAGMA index_list(record_change)").all()
        strict = connection.exec_driver_sql(
            "SELECT strict FROM pragma_table_list WHERE name = 'record_change'"
        ).scalar_one()
        written = str(
            connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'record_change'"
            ).scalar_one()
        )

    assert columns == [
        ("id", "INTEGER", True, True),
        ("record_table", "TEXT", True, False),
        ("record_id", "INTEGER", True, False),
        ("field", "TEXT", True, False),
        ("old_value", "TEXT", False, False),
        ("new_value", "TEXT", False, False),
        ("collection_run_id", "INTEGER", False, False),
        ("decided_by", "TEXT", False, False),
        ("created_at", "TEXT", True, False),
        ("updated_at", "TEXT", True, False),
    ]
    assert refers == [("collection_run", "collection_run_id", "id", "NO ACTION", "NO ACTION")]
    assert indexes == []
    assert strict == 1
    assert "AUTOINCREMENT" in written
    in_one_line = " ".join(written.split())
    assert "CONSTRAINT ck_record_change_record_id_positive CHECK (record_id > 0)" in in_one_line
    assert (
        "CONSTRAINT ck_record_change_new_value_not_old_value CHECK (old_value IS NOT new_value)"
        in in_one_line
    )
    assert (
        "CONSTRAINT ck_record_change_caused_by_a_run_or_a_person "
        "CHECK ((collection_run_id IS NULL) != (decided_by IS NULL))" in in_one_line
    )
    assert in_one_line.count("CONSTRAINT ck_record_change_") == 6
    for column in ("record_table", "field", "decided_by"):
        assert f"CONSTRAINT ck_record_change_{column}_not_empty CHECK (trim({column}," in (
            in_one_line
        )


def test_a_change_that_a_run_caused_is_stored_and_read_back(
    newest: Engine, clock: list[datetime]
) -> None:
    run = a_run(newest)

    with unit_of_work(newest) as work:
        work.add(
            RecordChange(
                record_table="track",
                record_id=7,
                field="name",
                old_value="Example Park",
                new_value="Example Raceway",
                collection_run_id=run,
            )
        )

    with unit_of_work(newest) as work:
        found = work.execute(select(RecordChange)).scalar_one()
    assert found.id == 1
    assert (found.record_table, found.record_id, found.field) == ("track", 7, "name")
    assert (found.old_value, found.new_value) == ("Example Park", "Example Raceway")
    assert found.collection_run_id == run
    assert found.decided_by is None
    # When it was changed is when the row was stored, and the store's clock says it.
    assert found.created_at == found.updated_at == clock[-1]
    assert held(newest) == [("track", 7, "name", "Example Park", "Example Raceway", run, None)]


def test_a_change_that_a_person_decided_is_stored_and_read_back(newest: Engine) -> None:
    with unit_of_work(newest) as work:
        work.add(
            RecordChange(
                record_table="track",
                record_id=7,
                field="length_in_metres",
                old_value="1600",
                new_value="1750",
                decided_by="Jo Example",
            )
        )

    with unit_of_work(newest) as work:
        found = work.execute(select(RecordChange)).scalar_one()
    assert found.collection_run_id is None
    assert found.decided_by == "Jo Example"
    assert held(newest) == [("track", 7, "length_in_metres", "1600", "1750", None, "Jo Example")]


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (None, "1600"),
        ("1600", None),
        (None, ""),
        ("", None),
        ("Example Park", "example park"),
        ("Example Park", "Example Park "),
        ("1", "1.0"),
        ("", " "),
    ],
    ids=[
        "from no value to one",
        "from a value to none",
        "from no value to empty text",
        "from empty text to no value",
        "a large letter made small",
        "a space at the end",
        "a number written otherwise",
        "from empty text to a space",
    ],
)
def test_a_value_is_kept_as_the_text_it_was_and_no_value_is_a_value_too(
    newest: Engine, old: str | None, new: str | None
) -> None:
    with unit_of_work(newest) as work:
        work.add(
            RecordChange(
                record_table="track",
                record_id=7,
                field="name",
                old_value=old,
                new_value=new,
                decided_by="Jo Example",
            )
        )
    write(newest, old_value=old, new_value=new)

    assert held(newest) == [("track", 7, "name", old, new, None, "Jo Example")] * 2


@pytest.mark.parametrize(
    "value",
    [None, "Example Park", "", " "],
    ids=["no value", "a text", "empty text", "a space"],
)
def test_a_change_that_changed_nothing_is_refused(newest: Engine, value: str | None) -> None:
    with refused(NOTHING_CHANGED), unit_of_work(newest) as work:
        work.add(
            RecordChange(
                record_table="track",
                record_id=7,
                field="name",
                old_value=value,
                new_value=value,
                decided_by="Jo Example",
            )
        )
    with refused(NOTHING_CHANGED):
        write(newest, old_value=value, new_value=value)

    assert held(newest) == []


def test_a_change_that_nothing_caused_is_refused(newest: Engine) -> None:
    with refused(NO_ONE_CAUSE), unit_of_work(newest) as work:
        work.add(
            RecordChange(
                record_table="track",
                record_id=7,
                field="name",
                old_value="Example Park",
                new_value="Example Raceway",
            )
        )
    with refused(NO_ONE_CAUSE):
        write(newest, decided_by=None)

    assert held(newest) == []


def test_a_change_that_a_run_and_a_person_both_caused_is_refused(newest: Engine) -> None:
    run = a_run(newest)

    with refused(NO_ONE_CAUSE), unit_of_work(newest) as work:
        work.add(
            RecordChange(
                record_table="track",
                record_id=7,
                field="name",
                old_value="Example Park",
                new_value="Example Raceway",
                collection_run_id=run,
                decided_by="Jo Example",
            )
        )
    with refused(NO_ONE_CAUSE):
        write(newest, collection_run_id=run)

    assert held(newest) == []


def test_a_change_is_caused_by_a_run_that_exists(newest: Engine) -> None:
    run = a_run(newest)

    with refused(BROKEN_KEY), unit_of_work(newest) as work:
        work.add(
            RecordChange(
                record_table="track",
                record_id=7,
                field="name",
                old_value="Example Park",
                new_value="Example Raceway",
                collection_run_id=run + 1,
            )
        )
    with refused(BROKEN_KEY):
        write(newest, collection_run_id=run + 1, decided_by=None)

    assert held(newest) == []


def test_a_run_that_caused_a_change_cannot_be_deleted_and_one_that_caused_none_can(
    newest: Engine,
) -> None:
    run = a_run(newest)
    with unit_of_work(newest) as work:
        other = CollectionRun(source_id=1, started_at=datetime(2026, 11, 25, 22, tzinfo=UTC))
        work.add(other)
    write(newest, collection_run_id=run, decided_by=None)

    with refused(BROKEN_KEY), unit_of_work(newest) as work:
        work.execute(delete(CollectionRun).where(CollectionRun.id == run))
    with refused(BROKEN_KEY), newest.begin() as connection:
        connection.exec_driver_sql("DELETE FROM collection_run WHERE id = ?", (run,))
    with refused(BROKEN_KEY), newest.begin() as connection:
        connection.exec_driver_sql("UPDATE collection_run SET id = 99 WHERE id = ?", (run,))
    with unit_of_work(newest) as work:
        work.execute(delete(CollectionRun).where(CollectionRun.id == other.id))

    with newest.connect() as connection:
        assert connection.exec_driver_sql("SELECT id FROM collection_run").all() == [(run,)]
    assert held(newest) == [("track", 7, "name", "Example Park", "Example Raceway", run, None)]


@pytest.mark.parametrize("column", ["record_table", "record_id", "field"])
def test_a_change_names_the_table_the_key_and_the_field_of_its_record(
    newest: Engine, column: str
) -> None:
    said: dict[str, object] = {"record_table": "track", "record_id": 7, "field": "name"}
    del said[column]

    with (
        refused(f"NOT NULL constraint failed: record_change.{column}"),
        unit_of_work(newest) as work,
    ):
        work.add(RecordChange(old_value="a", new_value="b", decided_by="Jo Example", **said))
    with refused(f"NOT NULL constraint failed: record_change.{column}"):
        write(newest, **{column: None})

    assert held(newest) == []


@pytest.mark.parametrize("column", ["record_table", "field", "decided_by"])
@pytest.mark.parametrize("text", ["", " ", "\t\n"], ids=["empty", "a space", "a tab and a line"])
def test_the_name_of_a_table_of_a_field_and_of_a_person_is_not_empty(
    newest: Engine, column: str, text: str
) -> None:
    with refused(f"CHECK constraint failed: ck_record_change_{column}_not_empty"):
        write(newest, **{column: text})

    assert held(newest) == []


@pytest.mark.parametrize("key", [0, -1, -7])
def test_the_key_of_a_record_is_above_nothing(newest: Engine, key: int) -> None:
    with (
        refused("CHECK constraint failed: ck_record_change_record_id_positive"),
        unit_of_work(newest) as work,
    ):
        work.add(
            RecordChange(
                record_table="track",
                record_id=key,
                field="name",
                old_value="a",
                new_value="b",
                decided_by="Jo Example",
            )
        )
    with refused("CHECK constraint failed: ck_record_change_record_id_positive"):
        write(newest, record_id=key)

    assert held(newest) == []


@pytest.mark.parametrize(
    ("column", "given", "why"),
    [
        ("record_id", "seven", "cannot store TEXT value in INTEGER column"),
        ("record_id", 7.5, "cannot store REAL value in INTEGER column"),
        ("collection_run_id", "the first", "cannot store TEXT value in INTEGER column"),
        ("old_value", b"Example Park", "cannot store BLOB value in TEXT column"),
        ("new_value", b"Example Raceway", "cannot store BLOB value in TEXT column"),
        ("record_table", b"track", "cannot store BLOB value in TEXT column"),
    ],
    ids=[
        "a key in words",
        "a key with a fraction",
        "a run in words",
        "an old value of bytes",
        "a new value of bytes",
        "a table of bytes",
    ],
)
def test_the_table_is_strict(newest: Engine, column: str, given: object, why: str) -> None:
    with refused(f"{why} record_change.{column}"):
        write(newest, **{column: given})

    assert held(newest) == []


def test_a_number_given_for_a_value_is_kept_as_its_text(newest: Engine) -> None:
    # A value is text here whatever its field holds: SQLite itself turns a
    # number that is written past the model into its text.
    write(newest, old_value=1600, new_value=1750.5)

    with newest.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT old_value, typeof(old_value), new_value, typeof(new_value) FROM record_change"
        ).all()
    assert found == [("1600", "text", "1750.5", "text")]


def test_the_changes_of_a_record_are_kept_in_the_order_they_were_made(newest: Engine) -> None:
    run = a_run(newest)
    changes = [
        ("name", "Example Park", "Example Raceway", run, None),
        ("length_in_metres", None, "1600", run, None),
        ("name", "Example Raceway", "Example Park", None, "Jo Example"),
        # The same change a second time: nothing says a change is made once.
        ("name", "Example Park", "Example Raceway", run, None),
    ]

    for field, old, new, by_run, by_person in changes:
        with unit_of_work(newest) as work:
            work.add(
                RecordChange(
                    record_table="track",
                    record_id=7,
                    field=field,
                    old_value=old,
                    new_value=new,
                    collection_run_id=by_run,
                    decided_by=by_person,
                )
            )

    with unit_of_work(newest) as work:
        keys = list(work.scalars(select(RecordChange.id).order_by(RecordChange.id)))
    assert keys == [1, 2, 3, 4]
    assert held(newest) == [("track", 7, *change) for change in changes]


def test_the_table_does_not_hold_a_change_to_a_record_that_exists(newest: Engine) -> None:
    # A reference is to one table, and this table keeps the changes of all
    # of them: the code that writes a change is what holds it to its record.
    write(newest, record_table="no such table", record_id=987654321, field="no such column")

    assert held(newest) == [
        (
            "no such table",
            987654321,
            "no such column",
            "Example Park",
            "Example Raceway",
            None,
            "Jo Example",
        )
    ]
