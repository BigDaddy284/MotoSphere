"""Tests of the store's own history: the real migrations, against real SQLite files."""

import ast
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError, OperationalError

from motosphere.db import history, migrations
from motosphere.db.history import MIGRATIONS
from motosphere.db.migrations import APPLICATION_ID, migrate, pending, schema_version


def tables(store: Engine) -> list[str]:
    """The tables of the store, without those SQLite keeps for itself."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite~_%' ESCAPE '~' ORDER BY name"
        )
        return [str(name) for (name,) in found]


def indexes(store: Engine) -> list[tuple[str, str]]:
    """The indexes a migration made, each with its table, without those SQLite makes by itself."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name, tbl_name FROM sqlite_master "
            "WHERE type = 'index' AND name NOT LIKE 'sqlite~_%' ESCAPE '~' ORDER BY name"
        )
        return [(str(name), str(table)) for name, table in found]


def triggers(store: Engine) -> list[tuple[str, str]]:
    """The triggers of the store, each with its table."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger' ORDER BY name"
        )
        return [(str(name), str(table)) for name, table in found]


def test_the_history_is_these_migrations_in_this_order() -> None:
    # The list only grows at its end: a new migration adds its name here, last.
    assert [migration.__name__ for migration in MIGRATIONS] == [
        "make_the_sources",
        "make_the_source_offers",
        "make_the_collection_runs",
        "index_the_runs_of_a_source",
        "make_the_record_changes",
        "let_the_record_changes_only_be_added_to",
        "index_the_record_changes",
        "make_the_review_items",
    ]


def test_the_module_gives_every_migration_and_their_list_by_name() -> None:
    assert sorted(history.__all__) == sorted(
        ["MIGRATIONS", *(migration.__name__ for migration in MIGRATIONS)]
    )


def test_the_history_is_the_one_the_store_is_migrated_with() -> None:
    assert migrations.MIGRATIONS is MIGRATIONS


@pytest.mark.parametrize("number", range(1, len(MIGRATIONS) + 1))
def test_each_migration_is_taken_by_a_store_at_the_version_before_it(
    store: Engine, number: int
) -> None:
    migrate(store, MIGRATIONS[: number - 1])
    assert schema_version(store) == number - 1

    applied = migrate(store, MIGRATIONS[:number])

    assert applied == [number]
    assert schema_version(store) == number


def test_the_first_migration_makes_the_table_of_the_sources(store: Engine) -> None:
    assert tables(store) == []

    migrate(store, MIGRATIONS[:1])

    assert tables(store) == ["source"]
    with store.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA application_id").scalar_one() == APPLICATION_ID
        assert connection.exec_driver_sql("SELECT count(*) FROM source").scalar_one() == 0


def test_the_second_migration_makes_the_table_of_the_offers_and_keeps_the_sources(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:1])
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "created_at, updated_at) VALUES ('Example Federation', 'https://federation.example', "
            "'governing body', 'rss feed', 0, '2026-11-19T08:00:00.000000+00:00', "
            "'2026-11-19T08:00:00.000000+00:00')"
        )

    migrate(store, MIGRATIONS[:2])

    assert tables(store) == ["source", "source_offer"]
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT id, name FROM source").all() == [
            (1, "Example Federation")
        ]
        assert connection.exec_driver_sql("SELECT count(*) FROM source_offer").scalar_one() == 0


def test_the_third_migration_makes_the_table_of_the_runs_and_keeps_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:2])
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "created_at, updated_at) VALUES ('Example Federation', 'https://federation.example', "
            "'governing body', 'rss feed', 0, '2026-11-19T08:00:00.000000+00:00', "
            "'2026-11-19T08:00:00.000000+00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO source_offer (source_id, information_type, created_at, updated_at) "
            "VALUES (1, 'events', '2026-11-19T08:00:00.000000+00:00', "
            "'2026-11-19T08:00:00.000000+00:00')"
        )

    migrate(store, MIGRATIONS[:3])

    assert tables(store) == ["collection_run", "source", "source_offer"]
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT id, name FROM source").all() == [
            (1, "Example Federation")
        ]
        assert connection.exec_driver_sql(
            "SELECT id, source_id, information_type FROM source_offer"
        ).all() == [(1, 1, "events")]
        assert connection.exec_driver_sql("SELECT count(*) FROM collection_run").scalar_one() == 0


def test_the_fourth_migration_makes_the_index_of_the_runs_and_keeps_the_runs(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:3])
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "created_at, updated_at) VALUES ('Example Federation', 'https://federation.example', "
            "'governing body', 'rss feed', 0, '2026-11-19T08:00:00.000000+00:00', "
            "'2026-11-19T08:00:00.000000+00:00')"
        )
        for started in ("2026-11-24T06:00:00.000000+00:00", "2026-11-23T06:00:00.000000+00:00"):
            connection.exec_driver_sql(
                "INSERT INTO collection_run (source_id, started_at, outcome, records_seen, "
                "records_added, records_changed, records_unchanged, created_at, updated_at) "
                "VALUES (1, ?, 'running', 0, 0, 0, 0, '2026-11-24T06:00:00.000000+00:00', "
                "'2026-11-24T06:00:00.000000+00:00')",
                (started,),
            )
    assert indexes(store) == []

    migrate(store, MIGRATIONS[:4])

    assert tables(store) == ["collection_run", "source", "source_offer"]
    assert indexes(store) == [("ix_collection_run_source_id_started_at", "collection_run")]
    with store.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT id, source_id, started_at, outcome FROM collection_run ORDER BY id"
        ).all() == [
            (1, 1, "2026-11-24T06:00:00.000000+00:00", "running"),
            (2, 1, "2026-11-23T06:00:00.000000+00:00", "running"),
        ]


def test_the_fourth_migration_does_not_pass_over_an_index_of_its_name_that_is_there(
    store: Engine,
) -> None:
    # An index of that name over something else would be taken for the
    # right one ever after. The migration fails instead, and the store is
    # as it was.
    migrate(store, MIGRATIONS[:3])
    with store.begin() as connection:
        connection.exec_driver_sql(
            "CREATE INDEX ix_collection_run_source_id_started_at ON collection_run (outcome)"
        )

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:4])

    assert str(refusal.value.orig) == "index ix_collection_run_source_id_started_at already exists"
    assert schema_version(store) == 3
    with store.connect() as connection:
        columns = connection.exec_driver_sql(
            "PRAGMA index_info(ix_collection_run_source_id_started_at)"
        ).all()
    assert [name for _, _, name in columns] == ["outcome"]


def test_the_fifth_migration_makes_the_table_of_the_changes_and_keeps_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:4])
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "created_at, updated_at) VALUES ('Example Federation', 'https://federation.example', "
            "'governing body', 'rss feed', 0, '2026-11-19T08:00:00.000000+00:00', "
            "'2026-11-19T08:00:00.000000+00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO collection_run (source_id, started_at, outcome, records_seen, "
            "records_added, records_changed, records_unchanged, created_at, updated_at) "
            "VALUES (1, '2026-11-24T06:00:00.000000+00:00', 'running', 0, 0, 0, 0, "
            "'2026-11-24T06:00:00.000000+00:00', '2026-11-24T06:00:00.000000+00:00')"
        )

    migrate(store, MIGRATIONS[:5])

    assert tables(store) == ["collection_run", "record_change", "source", "source_offer"]
    assert indexes(store) == [("ix_collection_run_source_id_started_at", "collection_run")]
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT id, name FROM source").all() == [
            (1, "Example Federation")
        ]
        assert connection.exec_driver_sql(
            "SELECT id, source_id, started_at, outcome FROM collection_run"
        ).all() == [(1, 1, "2026-11-24T06:00:00.000000+00:00", "running")]
        assert connection.exec_driver_sql("SELECT count(*) FROM record_change").scalar_one() == 0


def test_the_fifth_migration_does_not_pass_over_a_table_of_its_name_that_is_there(
    store: Engine,
) -> None:
    # A table of that name with other columns would be taken for the right
    # one ever after. The migration fails instead, and the store is as it
    # was.
    migrate(store, MIGRATIONS[:4])
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE record_change (note TEXT)")
        connection.exec_driver_sql("INSERT INTO record_change (note) VALUES ('kept')")

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:5])

    assert str(refusal.value.orig) == "table record_change already exists"
    assert schema_version(store) == 4
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT * FROM record_change").all() == [("kept",)]


def test_the_sixth_migration_makes_the_triggers_of_the_changes_and_holds_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:5])
    a_change = (
        "INSERT INTO record_change (record_table, record_id, field, old_value, new_value, "
        "decided_by, created_at, updated_at) VALUES ('track', 7, 'name', 'Example Park', "
        "'Example Raceway', 'Jo Example', '2026-11-25T22:00:00.000000+00:00', "
        "'2026-11-25T22:00:00.000000+00:00')"
    )
    with store.begin() as connection:
        connection.exec_driver_sql(a_change)
    with store.connect() as connection:
        before = connection.exec_driver_sql("SELECT * FROM record_change").all()
    assert triggers(store) == []

    migrate(store, MIGRATIONS[:6])

    assert tables(store) == ["collection_run", "record_change", "source", "source_offer"]
    assert indexes(store) == [("ix_collection_run_source_id_started_at", "collection_run")]
    assert triggers(store) == [
        ("tr_record_change_key_positive", "record_change"),
        ("tr_record_change_never_deleted", "record_change"),
        ("tr_record_change_never_edited", "record_change"),
        ("tr_record_change_never_replaced", "record_change"),
    ]
    # The row that was there before the triggers is held by them as any other.
    for statement, why in [
        ("UPDATE record_change SET new_value = 'Example Ring'", "edited"),
        ("DELETE FROM record_change", "deleted"),
    ]:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement)
        assert str(refusal.value.orig) == f"A row of the history (record_change) is never {why}."
    with store.begin() as connection:
        connection.exec_driver_sql(a_change)
    with store.connect() as connection:
        after = connection.exec_driver_sql("SELECT * FROM record_change ORDER BY id").all()
    assert len(before) == 1
    assert after[0] == before[0]
    assert [row[0] for row in after] == [1, 2]


def test_the_sixth_migration_does_not_pass_over_a_trigger_of_its_name_that_is_there(
    store: Engine,
) -> None:
    # The trigger that is there has the name of the last of the four: the
    # three before it are made first, and taken back with the migration.
    migrate(store, MIGRATIONS[:5])
    with store.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TRIGGER tr_record_change_key_positive AFTER INSERT ON record_change "
            "BEGIN SELECT 1; END"
        )

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:6])

    assert str(refusal.value.orig) == "trigger tr_record_change_key_positive already exists"
    assert schema_version(store) == 5
    assert triggers(store) == [("tr_record_change_key_positive", "record_change")]


def test_the_seventh_migration_makes_the_indexes_of_the_changes_and_keeps_the_history(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:6])
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "created_at, updated_at) VALUES ('Example Federation', 'https://federation.example', "
            "'governing body', 'rss feed', 0, '2026-11-19T08:00:00.000000+00:00', "
            "'2026-11-19T08:00:00.000000+00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO collection_run (source_id, started_at, outcome, records_seen, "
            "records_added, records_changed, records_unchanged, created_at, updated_at) "
            "VALUES (1, '2026-11-24T06:00:00.000000+00:00', 'running', 0, 0, 0, 0, "
            "'2026-11-24T06:00:00.000000+00:00', '2026-11-24T06:00:00.000000+00:00')"
        )
        for run, person in ((1, None), (None, "Jo Example")):
            connection.exec_driver_sql(
                "INSERT INTO record_change (record_table, record_id, field, old_value, "
                "new_value, collection_run_id, decided_by, created_at, updated_at) VALUES "
                "('track', 7, 'name', 'Example Park', 'Example Raceway', ?, ?, "
                "'2026-11-25T22:00:00.000000+00:00', '2026-11-25T22:00:00.000000+00:00')",
                (run, person),
            )
    with store.connect() as connection:
        before = connection.exec_driver_sql("SELECT * FROM record_change ORDER BY id").all()
    assert indexes(store) == [("ix_collection_run_source_id_started_at", "collection_run")]

    migrate(store, MIGRATIONS[:7])

    assert tables(store) == ["collection_run", "record_change", "source", "source_offer"]
    assert indexes(store) == [
        ("ix_collection_run_source_id_started_at", "collection_run"),
        ("ix_record_change_collection_run_id", "record_change"),
        ("ix_record_change_record_table_record_id", "record_change"),
    ]
    assert len(triggers(store)) == 4
    with store.connect() as connection:
        after = connection.exec_driver_sql("SELECT * FROM record_change ORDER BY id").all()
        by_the_run = connection.exec_driver_sql(
            "SELECT id FROM record_change INDEXED BY ix_record_change_collection_run_id "
            "WHERE collection_run_id = 1"
        ).all()
        of_the_record = connection.exec_driver_sql(
            "SELECT id FROM record_change INDEXED BY ix_record_change_record_table_record_id "
            "WHERE record_table = 'track' AND record_id = 7 ORDER BY id"
        ).all()
    assert len(before) == 2
    assert after == before
    # The rows that were there are in the new indexes.
    assert by_the_run == [(1,)]
    assert of_the_record == [(1,), (2,)]


def test_the_seventh_migration_does_not_pass_over_an_index_of_its_name_that_is_there(
    store: Engine,
) -> None:
    # The index that is there has the name of the second of the two: the
    # first is made before it, and taken back with the migration.
    migrate(store, MIGRATIONS[:6])
    with store.begin() as connection:
        connection.exec_driver_sql(
            "CREATE INDEX ix_record_change_collection_run_id ON record_change (decided_by)"
        )

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:7])

    assert str(refusal.value.orig) == "index ix_record_change_collection_run_id already exists"
    assert schema_version(store) == 6
    assert indexes(store) == [
        ("ix_collection_run_source_id_started_at", "collection_run"),
        ("ix_record_change_collection_run_id", "record_change"),
    ]
    with store.connect() as connection:
        columns = connection.exec_driver_sql(
            "PRAGMA index_info(ix_record_change_collection_run_id)"
        ).all()
    assert [name for _, _, name in columns] == ["decided_by"]


def test_the_eighth_migration_makes_the_table_of_the_review_queue_and_keeps_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:7])
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "created_at, updated_at) VALUES ('Example Federation', 'https://federation.example', "
            "'governing body', 'rss feed', 0, '2026-11-19T08:00:00.000000+00:00', "
            "'2026-11-19T08:00:00.000000+00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO record_change (record_table, record_id, field, old_value, new_value, "
            "decided_by, created_at, updated_at) VALUES ('track', 7, 'name', 'Example Park', "
            "'Example Raceway', 'Jo Example', '2026-11-25T22:00:00.000000+00:00', "
            "'2026-11-25T22:00:00.000000+00:00')"
        )
    with store.connect() as connection:
        sources = connection.exec_driver_sql("SELECT * FROM source").all()
        changes = connection.exec_driver_sql("SELECT * FROM record_change").all()
    before = (indexes(store), triggers(store))

    migrate(store, MIGRATIONS[:8])

    assert tables(store) == [
        "collection_run",
        "record_change",
        "review_item",
        "source",
        "source_offer",
    ]
    assert len(before[0]) == 3
    assert indexes(store) == sorted([*before[0], ("ix_review_item_source_id", "review_item")])
    assert len(before[1]) == 4
    assert triggers(store) == before[1]
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT * FROM source").all() == sources
        assert connection.exec_driver_sql("SELECT * FROM record_change").all() == changes
        assert connection.exec_driver_sql("SELECT count(*) FROM review_item").scalar_one() == 0
    assert (len(sources), len(changes)) == (1, 1)


def test_the_eighth_migration_does_not_pass_over_a_table_of_its_name_that_is_there(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:7])
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE review_item (note TEXT)")
        connection.exec_driver_sql("INSERT INTO review_item (note) VALUES ('kept')")

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:8])

    assert str(refusal.value.orig) == "table review_item already exists"
    assert schema_version(store) == 7
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT * FROM review_item").all() == [("kept",)]


def test_the_eighth_migration_does_not_pass_over_an_index_of_its_name_that_is_there(
    store: Engine,
) -> None:
    # The index is the second thing the migration makes: its table is made
    # before it, and taken back with the migration.
    migrate(store, MIGRATIONS[:7])
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE INDEX ix_review_item_source_id ON source (name)")

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:8])

    assert str(refusal.value.orig) == "index ix_review_item_source_id already exists"
    assert schema_version(store) == 7
    assert tables(store) == ["collection_run", "record_change", "source", "source_offer"]
    assert ("ix_review_item_source_id", "source") in indexes(store)


def test_a_store_with_the_newest_schema_lacks_no_migration(newest: Engine) -> None:
    assert schema_version(newest) == len(MIGRATIONS)
    assert pending(newest) == []


def test_the_history_names_nothing_of_the_stores_code() -> None:
    # A migration that named a model, a list or a type would build something
    # else once that was changed.
    written = ast.parse(Path(history.__file__).read_text(encoding="utf-8"))
    named: list[str] = []
    for part in ast.walk(written):
        if isinstance(part, ast.Import):
            named.extend(alias.name for alias in part.names)
        elif isinstance(part, ast.ImportFrom):
            named.append("." * part.level + (part.module or ""))

    assert "sqlalchemy" in named
    assert [name for name in named if name.startswith(("motosphere", "."))] == []
