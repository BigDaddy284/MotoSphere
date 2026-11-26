"""Tests of the store's own history: the real migrations, against real SQLite files."""

import ast
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

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


def test_the_history_is_these_migrations_in_this_order() -> None:
    # The list only grows at its end: a new migration adds its name here, last.
    assert [migration.__name__ for migration in MIGRATIONS] == [
        "make_the_sources",
        "make_the_source_offers",
        "make_the_collection_runs",
        "index_the_runs_of_a_source",
        "make_the_record_changes",
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
