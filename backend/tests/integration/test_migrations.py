"""Tests of the migration runner, against a real SQLite file of the test's own."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import Connection, Engine, event
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from motosphere.db import migrations
from motosphere.db.migrations import (
    APPLICATION_ID,
    Migration,
    SchemaError,
    migrate,
    schema_version,
)
from motosphere.db.store import open_store

# The mark of another application: that of an OGC GeoPackage file.
GEOPACKAGE = 0x47504B47


def tables(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM sqlite_master ORDER BY name")
        return [str(name) for (name,) in found]


def file_of(store: Engine) -> Path:
    return Path(str(store.url.database))


def with_sqlite_alone(store: Engine, *statements: str) -> bytes:
    """Change the store's file as another program would, and return the file as it then is."""
    with closing(sqlite3.connect(file_of(store), autocommit=True)) as connection:
        for statement in statements:
            connection.execute(statement)
    return file_of(store).read_bytes()


def make(table: str) -> Migration:
    """A migration that makes a table. It fails when it is applied a second time."""

    def migration(connection: Connection) -> None:
        connection.exec_driver_sql(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")

    return migration


def rename(old: str, new: str) -> Migration:
    """A migration that needs the one before it."""

    def migration(connection: Connection) -> None:
        connection.exec_driver_sql(f"ALTER TABLE {old} RENAME TO {new}")

    return migration


def make_and_fail(table: str, error: BaseException) -> Migration:
    def migration(connection: Connection) -> None:
        connection.exec_driver_sql(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
        raise error

    return migration


def make_and_commit(table: str) -> Migration:
    def migration(connection: Connection) -> None:
        connection.exec_driver_sql(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
        connection.commit()

    return migration


THREE = [make("first"), rename("first", "second"), rename("second", "third")]


def a_parent_and_its_children(connection: Connection) -> None:
    """A migration that makes a table, another that points to it, and rows in both."""
    connection.exec_driver_sql("CREATE TABLE parent (id INTEGER PRIMARY KEY, name TEXT) STRICT")
    connection.exec_driver_sql(
        "CREATE TABLE child (id INTEGER PRIMARY KEY,"
        " parent_id INTEGER NOT NULL REFERENCES parent (id)) STRICT"
    )
    connection.exec_driver_sql("INSERT INTO parent VALUES (1, 'one'), (2, 'two')")
    connection.exec_driver_sql("INSERT INTO child VALUES (10, 1), (11, 2)")


EVERY_ROW = "INSERT INTO parent (id, name) SELECT id, name FROM parent_before"
ALL_BUT_ONE_ROW = "INSERT INTO parent (id, name) SELECT id, name FROM parent_before WHERE id = 1"


def build_parent_anew(fill_it_again: str) -> Migration:
    """A migration that makes a change SQLite cannot make in place.

    The table is copied aside, dropped, made anew under its own name and
    filled again, while other rows point to it. Foreign keys stay on; they
    are only checked later, when the transaction ends.
    """

    def migration(connection: Connection) -> None:
        connection.exec_driver_sql("PRAGMA defer_foreign_keys = ON")
        connection.exec_driver_sql("CREATE TABLE parent_before AS SELECT * FROM parent")
        connection.exec_driver_sql("DROP TABLE parent")
        connection.exec_driver_sql(
            "CREATE TABLE parent (id INTEGER PRIMARY KEY, name TEXT NOT NULL, added TEXT) STRICT"
        )
        connection.exec_driver_sql(fill_it_again)
        connection.exec_driver_sql("DROP TABLE parent_before")

    return migration


def columns_of_parent(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM pragma_table_info('parent')")
        return [str(name) for (name,) in found]


def test_a_new_store_is_at_version_zero(store: Engine) -> None:
    assert schema_version(store) == 0


def test_migrating_applies_every_migration_in_order(store: Engine) -> None:
    applied = migrate(store, THREE)

    assert applied == [1, 2, 3]
    assert schema_version(store) == 3
    assert tables(store) == ["third"]


def test_migrating_twice_changes_nothing(store: Engine) -> None:
    migrate(store, THREE)

    applied = migrate(store, THREE)

    assert applied == []
    assert schema_version(store) == 3
    assert tables(store) == ["third"]


def test_only_the_migrations_a_store_lacks_are_applied(store: Engine) -> None:
    migrate(store, THREE[:1])

    applied = migrate(store, THREE)

    assert applied == [2, 3]
    assert schema_version(store) == 3
    assert tables(store) == ["third"]


def test_the_version_is_there_when_the_store_is_opened_again(store: Engine) -> None:
    migrate(store, THREE[:2])

    opened_again = open_store(Path(str(store.url.database)))

    assert schema_version(opened_again) == 2
    assert migrate(opened_again, THREE) == [3]


@pytest.mark.parametrize(
    "error",
    [RuntimeError("the migration failed part-way"), KeyboardInterrupt()],
    ids=["an error", "Ctrl+C"],
)
def test_a_migration_that_fails_leaves_the_store_at_the_version_before_it(
    store: Engine, error: BaseException
) -> None:
    with pytest.raises(type(error)) as caught:
        migrate(store, [make("first"), make_and_fail("second", error), make("third")])

    assert caught.value is error
    assert schema_version(store) == 1
    assert tables(store) == ["first"]


def test_a_store_goes_on_from_where_a_migration_failed(store: Engine) -> None:
    error = RuntimeError("the migration failed part-way")
    with pytest.raises(RuntimeError):
        migrate(store, [make("first"), make_and_fail("second", error), make("third")])

    applied = migrate(store, [make("first"), make("second"), make("third")])

    assert applied == [2, 3]
    assert tables(store) == ["first", "second", "third"]


def test_each_migration_is_one_transaction_with_its_version(store: Engine) -> None:
    commits: list[object] = []
    event.listen(store, "commit", commits.append)

    migrate(store, THREE)

    assert len(commits) == 3


def test_a_store_newer_than_the_history_is_refused_and_left_as_it_is(store: Engine) -> None:
    migrate(store, THREE)

    with pytest.raises(SchemaError) as refusal:
        migrate(store, THREE[:2])

    assert str(refusal.value) == (
        "The data store cannot be brought up to date: its schema is version 3, "
        "and this MotoSphere knows only the versions 0 to 2."
    )
    assert schema_version(store) == 3
    assert tables(store) == ["third"]


def test_a_version_no_migration_gave_is_refused_and_the_store_left_as_it_is(store: Engine) -> None:
    with store.begin() as connection:
        connection.exec_driver_sql(f"PRAGMA application_id = {APPLICATION_ID}")
        connection.exec_driver_sql("PRAGMA user_version = -1")

    with pytest.raises(SchemaError) as refusal:
        migrate(store, THREE)

    assert str(refusal.value) == (
        "The data store cannot be brought up to date: its schema is version -1, "
        "and this MotoSphere knows only the versions 0 to 3."
    )
    assert schema_version(store) == -1
    assert tables(store) == []


def test_a_migration_that_commits_by_itself_fails(store: Engine) -> None:
    with pytest.raises(InvalidRequestError):
        migrate(store, [make_and_commit("first"), make("second")])

    assert schema_version(store) == 0
    assert tables(store) == ["first"]


def test_the_stores_own_history_is_used_when_none_is_given(
    store: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(migrations, "MIGRATIONS", tuple(THREE))

    applied = migrate(store)

    assert applied == [1, 2, 3]
    assert tables(store) == ["third"]


def test_the_stores_own_history_brings_an_empty_store_to_the_newest_schema(store: Engine) -> None:
    newest = len(migrations.MIGRATIONS)

    applied = migrate(store)

    assert applied == list(range(1, newest + 1))
    assert schema_version(store) == newest
    assert migrate(store) == []


def test_a_migration_can_build_anew_a_table_that_rows_point_to(store: Engine) -> None:
    applied = migrate(store, [a_parent_and_its_children, build_parent_anew(EVERY_ROW)])

    assert applied == [1, 2]
    assert tables(store) == ["child", "parent"]
    assert columns_of_parent(store) == ["id", "name", "added"]
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT id, parent_id FROM child").all() == [
            (10, 1),
            (11, 2),
        ]
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_foreign_keys_are_enforced_again_after_such_a_migration(store: Engine) -> None:
    migrate(store, [a_parent_and_its_children, build_parent_anew(EVERY_ROW)])

    with pytest.raises(IntegrityError), store.begin() as connection:
        connection.exec_driver_sql("INSERT INTO child VALUES (12, 99)")


def test_such_a_migration_is_refused_when_it_loses_a_row_that_is_pointed_to(store: Engine) -> None:
    with pytest.raises(IntegrityError):
        migrate(store, [a_parent_and_its_children, build_parent_anew(ALL_BUT_ONE_ROW)])

    assert schema_version(store) == 1
    assert tables(store) == ["child", "parent"]
    assert columns_of_parent(store) == ["id", "name"]
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT id FROM parent").all() == [(1,), (2,)]


def test_the_first_migration_marks_the_file_as_a_store_of_motospheres(store: Engine) -> None:
    migrate(store, THREE[:1])

    # Where SQLite keeps an application's mark: four bytes of the file's header.
    assert file_of(store).read_bytes()[68:72] == b"MoSp"


def test_a_new_store_that_lacks_no_migration_is_not_written_to(store: Engine) -> None:
    before = file_of(store).read_bytes()

    applied = migrate(store, [])

    assert applied == []
    assert file_of(store).read_bytes() == before


def test_a_first_migration_that_fails_leaves_the_file_as_it_was(store: Engine) -> None:
    before = file_of(store).read_bytes()
    error = RuntimeError("the migration failed part-way")

    with pytest.raises(RuntimeError):
        migrate(store, [make_and_fail("first", error)])

    assert file_of(store).read_bytes() == before
    assert migrate(store, [make("first")]) == [1]


@pytest.mark.parametrize(
    "theirs",
    [
        ["CREATE TABLE theirs (id INTEGER PRIMARY KEY)", "INSERT INTO theirs VALUES (1)"],
        ["CREATE VIEW theirs AS SELECT 1 AS one"],
        ["PRAGMA user_version = 9"],
    ],
    ids=["a table", "a view", "a version"],
)
def test_a_file_that_is_not_new_and_carries_no_mark_is_refused_and_left_as_it_is(
    store: Engine, theirs: list[str]
) -> None:
    before = with_sqlite_alone(store, *theirs)

    with pytest.raises(SchemaError) as refusal:
        migrate(store, THREE)

    assert str(refusal.value) == (
        f"The data store cannot be brought up to date: {file_of(store)} is not a store of "
        "MotoSphere's (it is not a new, empty file, and it does not carry MotoSphere's mark)."
    )
    assert file_of(store).read_bytes() == before


def test_a_file_with_the_mark_of_another_application_is_refused_and_left_as_it_is(
    store: Engine,
) -> None:
    before = with_sqlite_alone(store, f"PRAGMA application_id = {GEOPACKAGE}")

    with pytest.raises(SchemaError) as refusal:
        migrate(store, THREE)

    assert str(refusal.value) == (
        f"The data store cannot be brought up to date: {file_of(store)} is not a store of "
        "MotoSphere's (it carries the mark of another application, 1196444487)."
    )
    assert file_of(store).read_bytes() == before
