"""Tests of the store's own history: the real migrations, against real SQLite files."""

import ast
from pathlib import Path

import pytest
from sqlalchemy import Engine

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


def test_the_history_is_these_migrations_in_this_order() -> None:
    # The list only grows at its end: a new migration adds its name here, last.
    assert [migration.__name__ for migration in MIGRATIONS] == [
        "make_the_sources",
        "make_the_source_offers",
    ]


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
