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
        "hold_one_doubt_to_one_review_item",
        "keep_the_decision_of_a_review_item",
        "hold_the_key_of_a_review_item_to_1_or_more",
        "keep_a_decided_review_item_from_being_replaced",
        "make_the_countries",
        "let_a_source_say_its_country",
        "let_a_source_be_a_reference_list",
        "make_the_regions",
        "let_a_region_say_its_code",
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


# A store at version 8 for the tests of the ninth migration: its source,
# and its review items as plain SQL, a possible duplicate and a doubt about
# what the source says of a field.
A_SOURCE_AT_VERSION_8 = (
    "INSERT INTO source (name, website, category, collection_method, switched_on, "
    "created_at, updated_at) VALUES ('Example Federation', 'https://federation.example', "
    "'governing body', 'rss feed', 0, '2026-11-19T08:00:00.000000+00:00', "
    "'2026-11-19T08:00:00.000000+00:00')"
)
AN_ITEM_AT_VERSION_8 = (
    "INSERT INTO review_item (kind, record_table, record_id, other_record_id, field, "
    "source_id, source_address, source_value, reason, state, created_at, updated_at) "
    "VALUES (?, 'track', 7, ?, ?, ?, ?, ?, ?, 'open', '2026-11-26T09:00:00.000000+00:00', "
    "'2026-11-26T09:00:00.000000+00:00')"
)
A_PAIR = ("possible duplicate", 12, None, None, None, None)
OF_A_FIELD = (
    "sources disagree",
    None,
    "length_in_metres",
    1,
    "https://federation.example/tracks/7",
    "1750",
)
OF_A_PAIR = "ix_review_item_record_table_record_id_other_record_id"
OF_WHAT_A_SOURCE_SAYS = "ix_review_item_record_table_record_id_field_source_id_source_value"


def test_the_ninth_migration_makes_the_indexes_of_one_doubt_and_keeps_the_items(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:8])
    with store.begin() as connection:
        connection.exec_driver_sql(A_SOURCE_AT_VERSION_8)
        connection.exec_driver_sql(AN_ITEM_AT_VERSION_8, (*A_PAIR, "They have one name."))
        connection.exec_driver_sql(AN_ITEM_AT_VERSION_8, (*OF_A_FIELD, "The record says 1600."))
    with store.connect() as connection:
        items = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id").all()
    before = (tables(store), indexes(store), triggers(store))

    migrate(store, MIGRATIONS[:9])

    assert tables(store) == before[0]
    assert len(before[1]) == 4
    assert indexes(store) == sorted(
        [*before[1], (OF_A_PAIR, "review_item"), (OF_WHAT_A_SOURCE_SAYS, "review_item")]
    )
    assert len(before[2]) == 4
    assert triggers(store) == before[2]
    with store.connect() as connection:
        after = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id").all()
        the_pair = connection.exec_driver_sql(
            "SELECT id FROM review_item "
            "INDEXED BY ix_review_item_record_table_record_id_other_record_id "
            "WHERE record_table = 'track' AND record_id = 7 AND other_record_id = 12"
        ).all()
        of_the_field = connection.exec_driver_sql(
            "SELECT id FROM review_item "
            "INDEXED BY ix_review_item_record_table_record_id_field_source_id_source_value "
            "WHERE record_table = 'track' AND record_id = 7 AND field = 'length_in_metres'"
        ).all()
    assert len(items) == 2
    assert after == items
    # The items that were there are in the new indexes, each in its own.
    assert the_pair == [(1,)]
    assert of_the_field == [(2,)]


@pytest.mark.parametrize(
    ("doubt", "index"),
    [(A_PAIR, OF_A_PAIR), (OF_A_FIELD, OF_WHAT_A_SOURCE_SAYS)],
    ids=["a possible duplicate", "a doubt about a field"],
)
def test_the_ninth_migration_fails_where_a_doubt_is_there_twice(
    store: Engine, doubt: tuple[object, ...], index: str
) -> None:
    # A store at version 8 could hold the same doubt twice. The migration
    # does not choose which of the two to keep: it fails, and the store is
    # as it was, for a person to look at. Where the second index is the one
    # that cannot be made, the first is taken back with the migration.
    migrate(store, MIGRATIONS[:8])
    with store.begin() as connection:
        connection.exec_driver_sql(A_SOURCE_AT_VERSION_8)
        connection.exec_driver_sql(AN_ITEM_AT_VERSION_8, (*doubt, "Found by the first run."))
        connection.exec_driver_sql(AN_ITEM_AT_VERSION_8, (*doubt, "Found by the second run."))
    before = indexes(store)

    with pytest.raises(IntegrityError) as refusal:
        migrate(store, MIGRATIONS[:9])

    columns = {
        OF_A_PAIR: ("record_table", "record_id", "other_record_id"),
        OF_WHAT_A_SOURCE_SAYS: ("record_table", "record_id", "field", "source_id", "source_value"),
    }[index]
    assert str(refusal.value.orig) == "UNIQUE constraint failed: " + ", ".join(
        f"review_item.{column}" for column in columns
    )
    assert schema_version(store) == 8
    assert indexes(store) == before
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM review_item").scalar_one() == 2


@pytest.mark.parametrize("index", [OF_A_PAIR, OF_WHAT_A_SOURCE_SAYS], ids=["first", "second"])
def test_the_ninth_migration_does_not_pass_over_an_index_of_its_name_that_is_there(
    store: Engine, index: str
) -> None:
    # Where the index that is there has the name of the second of the two,
    # the first is made before it, and taken back with the migration.
    migrate(store, MIGRATIONS[:8])
    with store.begin() as connection:
        connection.exec_driver_sql(f"CREATE INDEX {index} ON review_item (note)")
    before = indexes(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:9])

    assert str(refusal.value.orig) == f"index {index} already exists"
    assert schema_version(store) == 8
    assert len(before) == 5
    assert indexes(store) == before


A_DECIDED_ITEM_AT_VERSION_9 = (
    "INSERT INTO review_item (kind, record_table, record_id, other_record_id, reason, state, "
    "decided_by, decided_at, created_at, updated_at) VALUES ('possible duplicate', 'track', "
    "8, 9, 'They have one name.', 'accepted', 'Jo Example', '2026-11-26T12:30:00.000000+00:00', "
    "'2026-11-26T09:00:00.000000+00:00', '2026-11-26T12:30:00.000000+00:00')"
)
NEVER_EDITED = "tr_review_item_decided_never_edited"
NEVER_DELETED = "tr_review_item_decided_never_deleted"


def test_the_tenth_migration_makes_the_triggers_of_a_kept_decision_and_holds_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:9])
    with store.begin() as connection:
        connection.exec_driver_sql(A_SOURCE_AT_VERSION_8)
        connection.exec_driver_sql(AN_ITEM_AT_VERSION_8, (*A_PAIR, "They have one name."))
        connection.exec_driver_sql(A_DECIDED_ITEM_AT_VERSION_9)
    with store.connect() as connection:
        items = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id").all()
    before = (tables(store), indexes(store), triggers(store))

    migrate(store, MIGRATIONS[:10])

    assert tables(store) == before[0]
    assert indexes(store) == before[1]
    assert len(before[2]) == 4
    assert triggers(store) == sorted(
        [*before[2], (NEVER_DELETED, "review_item"), (NEVER_EDITED, "review_item")]
    )
    # The item that was decided before the triggers is held by them as any
    # other, and the open one is not.
    for statement, why in [
        ("UPDATE review_item SET state = 'open', decided_by = NULL, decided_at = NULL", "edited"),
        ("DELETE FROM review_item", "deleted"),
    ]:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement)
        assert str(refusal.value.orig) == f"A decided review item (review_item) is never {why}."
    with store.connect() as connection:
        after = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id").all()
    assert len(items) == 2
    assert after == items
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE review_item SET note = 'To be looked at.' WHERE id = 1")
    with store.connect() as connection:
        notes = connection.exec_driver_sql("SELECT id, note FROM review_item ORDER BY id").all()
    assert notes == [(1, "To be looked at."), (2, None)]


@pytest.mark.parametrize("trigger", [NEVER_EDITED, NEVER_DELETED], ids=["first", "second"])
def test_the_tenth_migration_does_not_pass_over_a_trigger_of_its_name_that_is_there(
    store: Engine, trigger: str
) -> None:
    # Where the trigger that is there has the name of the second of the
    # two, the first is made before it, and taken back with the migration.
    migrate(store, MIGRATIONS[:9])
    with store.begin() as connection:
        connection.exec_driver_sql(
            f"CREATE TRIGGER {trigger} AFTER INSERT ON review_item BEGIN SELECT 1; END"
        )
    before = triggers(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:10])

    assert str(refusal.value.orig) == f"trigger {trigger} already exists"
    assert schema_version(store) == 9
    assert len(before) == 5
    assert triggers(store) == before


AN_ITEM_WITH_A_KEY_AT_VERSION_10 = (
    "INSERT INTO review_item (id, kind, record_table, record_id, other_record_id, reason, "
    "state, created_at, updated_at) VALUES (?, 'possible duplicate', 'track', ?, ?, "
    "'They have one name.', 'open', '2026-11-27T05:00:00.000000+00:00', "
    "'2026-11-27T05:00:00.000000+00:00')"
)
KEY_POSITIVE = "tr_review_item_key_positive"
KEY_STAYS_POSITIVE = "tr_review_item_key_stays_positive"
A_KEY_IS_1_OR_MORE = "A key of the review queue (review_item) is 1 or more."


def test_the_eleventh_migration_makes_the_triggers_of_the_keys_and_keeps_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:10])
    with store.begin() as connection:
        connection.exec_driver_sql(AN_ITEM_WITH_A_KEY_AT_VERSION_10, (5, 7, 12))
        connection.exec_driver_sql(AN_ITEM_WITH_A_KEY_AT_VERSION_10, (-3, 8, 9))
    with store.connect() as connection:
        items = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id").all()
    before = (tables(store), indexes(store), triggers(store))

    migrate(store, MIGRATIONS[:11])

    assert tables(store) == before[0]
    assert indexes(store) == before[1]
    assert len(before[2]) == 6
    assert triggers(store) == sorted(
        [*before[2], (KEY_POSITIVE, "review_item"), (KEY_STAYS_POSITIVE, "review_item")]
    )
    # The migration asks nothing of the items that are there and changes
    # none: an item that had a key below 1 before the triggers keeps it.
    # From then on no item is given such a key.
    for statement, given in [
        (AN_ITEM_WITH_A_KEY_AT_VERSION_10, (0, 20, 21)),
        ("UPDATE review_item SET id = -5 WHERE id = 5", ()),
    ]:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement, given)
        assert str(refusal.value.orig) == A_KEY_IS_1_OR_MORE
    with store.connect() as connection:
        after = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id").all()
    assert [item[0] for item in items] == [-3, 5]
    assert after == items
    # Such an item is still given a note, and a key of 1 or more.
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE review_item SET note = 'To be looked at.' WHERE id = -3")
        connection.exec_driver_sql("UPDATE review_item SET id = 3 WHERE id = -3")
    with store.connect() as connection:
        notes = connection.exec_driver_sql("SELECT id, note FROM review_item ORDER BY id").all()
    assert notes == [(3, "To be looked at."), (5, None)]


@pytest.mark.parametrize("trigger", [KEY_POSITIVE, KEY_STAYS_POSITIVE], ids=["first", "second"])
def test_the_eleventh_migration_does_not_pass_over_a_trigger_of_its_name_that_is_there(
    store: Engine, trigger: str
) -> None:
    # Where the trigger that is there has the name of the second of the
    # two, the first is made before it, and taken back with the migration.
    migrate(store, MIGRATIONS[:10])
    with store.begin() as connection:
        connection.exec_driver_sql(
            f"CREATE TRIGGER {trigger} AFTER DELETE ON review_item BEGIN SELECT 1; END"
        )
    before = triggers(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:11])

    assert str(refusal.value.orig) == f"trigger {trigger} already exists"
    assert schema_version(store) == 10
    assert len(before) == 7
    assert triggers(store) == before


# An item of a store at version 10, with its key: what follows INSERT or REPLACE.
AN_ITEM_AT_VERSION_10 = (
    "INTO review_item (id, kind, record_table, record_id, other_record_id, reason, "
    "state, decided_by, decided_at, created_at, updated_at) VALUES (?, 'possible duplicate', "
    "'track', ?, ?, 'They have one name.', ?, ?, ?, '2026-11-27T05:00:00.000000+00:00', "
    "'2026-11-27T05:00:00.000000+00:00')"
)
NOT_YET_DECIDED = ("open", None, None)
DECIDED_AT_VERSION_10 = ("accepted", "Jo Example", "2026-11-27T05:30:00.000000+00:00")
NEVER_REPLACED = "tr_review_item_decided_never_replaced"
NEVER_REPLACED_BY_ANOTHER = "tr_review_item_decided_never_replaced_by_another"
A_DECIDED_ITEM_IS_NEVER_REPLACED = "A decided review item (review_item) is never replaced."


def test_the_twelfth_migration_makes_the_triggers_against_replacing_and_keeps_what_there_was(
    store: Engine,
) -> None:
    # A store at version 10 could give an item a key below 1. This one
    # has a decided item with the key -1, which is what SQLite shows for
    # the key of a new row that names none, before the row is written.
    migrate(store, MIGRATIONS[:10])
    with store.begin() as connection:
        connection.exec_driver_sql(f"INSERT {AN_ITEM_AT_VERSION_10}", (5, 7, 12, *NOT_YET_DECIDED))
        for key, record, other in [(-1, 8, 9), (6, 10, 11)]:
            connection.exec_driver_sql(
                f"INSERT {AN_ITEM_AT_VERSION_10}", (key, record, other, *DECIDED_AT_VERSION_10)
            )
    migrate(store, MIGRATIONS[:11])
    with store.connect() as connection:
        items = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id").all()
    before = (tables(store), indexes(store), triggers(store))

    migrate(store, MIGRATIONS[:12])

    assert tables(store) == before[0]
    assert indexes(store) == before[1]
    assert len(before[2]) == 8
    assert triggers(store) == sorted(
        [*before[2], (NEVER_REPLACED, "review_item"), (NEVER_REPLACED_BY_ANOTHER, "review_item")]
    )
    # The migration asks nothing of the items that are there and changes
    # none. From then on neither decided item is replaced, by its key or
    # as its doubt.
    for statement, given in [
        (f"INSERT OR REPLACE {AN_ITEM_AT_VERSION_10}", (6, 20, 21, *NOT_YET_DECIDED)),
        (f"REPLACE {AN_ITEM_AT_VERSION_10}", (None, 8, 9, *NOT_YET_DECIDED)),
        ("UPDATE OR REPLACE review_item SET id = 6 WHERE id = 5", ()),
        ("UPDATE OR REPLACE review_item SET id = -1 WHERE id = 5", ()),
    ]:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement, given)
        assert str(refusal.value.orig) == A_DECIDED_ITEM_IS_NEVER_REPLACED
    with store.connect() as connection:
        after = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id").all()
    assert [item[0] for item in items] == [-1, 5, 6]
    assert after == items
    # A new item that names no key is stored as ever, though a decided
    # item has the key SQLite shows for it before it is written.
    with store.begin() as connection:
        connection.exec_driver_sql(
            f"INSERT {AN_ITEM_AT_VERSION_10}", (None, 20, 21, *NOT_YET_DECIDED)
        )
    with store.connect() as connection:
        keys = connection.exec_driver_sql("SELECT id, state FROM review_item ORDER BY id").all()
    assert keys == [(-1, "accepted"), (5, "open"), (6, "accepted"), (7, "open")]


@pytest.mark.parametrize(
    "trigger", [NEVER_REPLACED, NEVER_REPLACED_BY_ANOTHER], ids=["first", "second"]
)
def test_the_twelfth_migration_does_not_pass_over_a_trigger_of_its_name_that_is_there(
    store: Engine, trigger: str
) -> None:
    # Where the trigger that is there has the name of the second of the
    # two, the first is made before it, and taken back with the migration.
    migrate(store, MIGRATIONS[:11])
    with store.begin() as connection:
        connection.exec_driver_sql(
            f"CREATE TRIGGER {trigger} AFTER DELETE ON review_item BEGIN SELECT 1; END"
        )
    before = triggers(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:12])

    assert str(refusal.value.orig) == f"trigger {trigger} already exists"
    assert schema_version(store) == 11
    assert len(before) == 9
    assert triggers(store) == before


A_COUNTRY = (
    "INSERT INTO country (alpha_2, alpha_3, name, source_id, source_address, collected_at, "
    "last_verified_at, extraction_method, confidence, verification_status, created_at, "
    "updated_at) VALUES ('NZ', 'NZL', 'New Zealand', 1, "
    "'https://standards.example/countries.csv', '2026-11-27T09:00:00.000000+00:00', "
    "'2026-11-27T09:00:00.000000+00:00', 'public dataset', 'high', 'official', "
    "'2026-11-27T09:00:05.000000+00:00', '2026-11-27T09:00:05.000000+00:00')"
)


def test_the_thirteenth_migration_makes_the_table_of_the_countries_and_keeps_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:12])
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "created_at, updated_at) VALUES ('Example Standards Body', "
            "'https://standards.example', 'governing body', 'public dataset', 0, "
            "'2026-11-19T08:00:00.000000+00:00', '2026-11-19T08:00:00.000000+00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO review_item (kind, record_table, record_id, other_record_id, reason, "
            "state, created_at, updated_at) VALUES ('possible duplicate', 'track', 7, 8, "
            "'The two are 40 metres apart.', 'open', '2026-11-26T20:00:00.000000+00:00', "
            "'2026-11-26T20:00:00.000000+00:00')"
        )
    with store.connect() as connection:
        sources = connection.exec_driver_sql("SELECT * FROM source").all()
        items = connection.exec_driver_sql("SELECT * FROM review_item").all()
    before = (tables(store), indexes(store), triggers(store))

    migrate(store, MIGRATIONS[:13])

    assert schema_version(store) == 13
    assert len(before[0]) == 5
    assert tables(store) == sorted([*before[0], "country"])
    assert len(before[1]) == 6
    assert indexes(store) == sorted([*before[1], ("ix_country_source_id", "country")])
    assert len(before[2]) == 10
    assert triggers(store) == before[2]
    with store.begin() as connection:
        assert connection.exec_driver_sql("SELECT * FROM source").all() == sources
        assert connection.exec_driver_sql("SELECT * FROM review_item").all() == items
        assert connection.exec_driver_sql("SELECT count(*) FROM country").scalar_one() == 0
        # The new table refers to the sources that were there.
        connection.exec_driver_sql(A_COUNTRY)
    assert (len(sources), len(items)) == (1, 1)
    with store.connect() as connection:
        columns = connection.exec_driver_sql("PRAGMA index_info(ix_country_source_id)").all()
        assert connection.exec_driver_sql("SELECT alpha_2, source_id FROM country").all() == [
            ("NZ", 1)
        ]
    assert [name for _, _, name in columns] == ["source_id"]


def test_the_thirteenth_migration_does_not_pass_over_a_table_of_its_name_that_is_there(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:12])
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE country (note TEXT)")
        connection.exec_driver_sql("INSERT INTO country (note) VALUES ('kept')")

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:13])

    assert str(refusal.value.orig) == "table country already exists"
    assert schema_version(store) == 12
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT * FROM country").all() == [("kept",)]


def test_the_thirteenth_migration_does_not_pass_over_an_index_of_its_name_that_is_there(
    store: Engine,
) -> None:
    # The index is the second thing the migration makes: its table is made
    # before it, and taken back with the migration.
    migrate(store, MIGRATIONS[:12])
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE INDEX ix_country_source_id ON source (name)")
    before = (tables(store), indexes(store))

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:13])

    assert str(refusal.value.orig) == "index ix_country_source_id already exists"
    assert schema_version(store) == 12
    assert "country" not in tables(store)
    assert (tables(store), indexes(store)) == before


# The columns a source had before the fourteenth migration, in their order.
OF_A_SOURCE_AT_VERSION_13 = [
    "id",
    "name",
    "website",
    "category",
    "collection_method",
    "scan_every_hours",
    "terms_address",
    "licence",
    "usage_restrictions",
    "terms_read_at",
    "switched_on",
    "created_at",
    "updated_at",
]
# What a store at version 13 holds of its sources: every row of the four
# tables whose rows point to a source, the sources themselves with the
# columns they had then, and the highest key each table gave.
HELD_AT_VERSION_13 = {
    "source_offer": "SELECT * FROM source_offer ORDER BY id",
    "collection_run": "SELECT * FROM collection_run ORDER BY id",
    "review_item": "SELECT * FROM review_item ORDER BY id",
    "country": "SELECT * FROM country ORDER BY id",
    "source": (
        "SELECT id, name, website, category, collection_method, scan_every_hours, "
        "terms_address, licence, usage_restrictions, terms_read_at, switched_on, created_at, "
        "updated_at FROM source ORDER BY id"
    ),
    "the highest key of each table": "SELECT name, seq FROM sqlite_sequence ORDER BY name",
}


def sources_and_what_points_to_them(store: Engine) -> None:
    """Fill a store at version 13: two sources, two that were deleted, and what they have.

    Four sources are stored, with the keys 1 to 4, and the second and the
    fourth are deleted again: so the keys of the sources have a gap, and
    the highest key the table gave is above that of every source that is
    there. The first source has only what a source cannot be without. The
    third has everything a source can have. Each of the four tables whose
    rows point to a source has a row that does.
    """
    with store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "created_at, updated_at) VALUES ('Example Standards Body', "
            "'https://standards.example', 'governing body', 'public dataset', 0, "
            "'2026-11-19T08:00:00.000000+00:00', '2026-11-19T08:00:00.000000+00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "created_at, updated_at) VALUES ('Example Club', 'https://club.example', 'club', "
            "'html extraction', 0, '2026-11-19T08:00:02.000000+00:00', "
            "'2026-11-19T08:00:02.000000+00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, scan_every_hours, "
            "terms_address, licence, usage_restrictions, terms_read_at, switched_on, "
            "created_at, updated_at) VALUES ('Example Federation', "
            "'https://federation.example', 'championship', 'rss feed', 24, "
            "'https://federation.example/terms', 'CC BY 4.0', "
            "'Name the federation wherever its calendar is shown.', "
            "'2026-11-18T21:30:00.000000+00:00', 1, '2026-11-19T08:00:01.000000+00:00', "
            "'2026-11-20T08:00:00.000000+00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO source (name, website, category, collection_method, switched_on, "
            "created_at, updated_at) VALUES ('Example Promoter', 'https://promoter.example', "
            "'promoter', 'html extraction', 0, '2026-11-19T08:00:03.000000+00:00', "
            "'2026-11-19T08:00:03.000000+00:00')"
        )
        connection.exec_driver_sql(
            "DELETE FROM source WHERE name IN ('Example Club', 'Example Promoter')"
        )
        connection.exec_driver_sql(
            "INSERT INTO source_offer (source_id, information_type, created_at, updated_at) "
            "VALUES (1, 'reference data', '2026-11-19T08:00:00.000000+00:00', "
            "'2026-11-19T08:00:00.000000+00:00'), (3, 'events', "
            "'2026-11-19T08:00:01.000000+00:00', '2026-11-19T08:00:01.000000+00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO collection_run (source_id, started_at, outcome, records_seen, "
            "records_added, records_changed, records_unchanged, created_at, updated_at) "
            "VALUES (3, '2026-11-24T06:00:00.000000+00:00', 'running', 0, 0, 0, 0, "
            "'2026-11-24T06:00:00.000000+00:00', '2026-11-24T06:00:00.000000+00:00')"
        )
        connection.exec_driver_sql(
            "INSERT INTO review_item (kind, record_table, record_id, field, source_id, "
            "source_address, source_value, reason, state, created_at, updated_at) VALUES ("
            "'sources disagree', 'track', 7, 'length_in_metres', 3, "
            "'https://federation.example/tracks/7', '1750', 'The record says 1600.', 'open', "
            "'2026-11-26T09:00:00.000000+00:00', '2026-11-26T09:00:00.000000+00:00')"
        )
        connection.exec_driver_sql(A_COUNTRY)


def held_at_version_13(store: Engine) -> dict[str, list[tuple[object, ...]]]:
    """Every row of the sources and of the tables that point to them, each table by its key."""
    with store.connect() as connection:
        return {
            what: [tuple(row) for row in connection.exec_driver_sql(asked)]
            for what, asked in HELD_AT_VERSION_13.items()
        }


def columns_of_the_sources(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM pragma_table_info('source')")
        return [str(name) for (name,) in found]


A_NEW_SOURCE = (
    "INSERT INTO source (name, website, category, collection_method, switched_on, "
    "created_at, updated_at) VALUES ('Example Union', 'https://union.example', "
    "'governing body', 'rss feed', 0, '2026-11-27T12:00:00.000000+00:00', "
    "'2026-11-27T12:00:00.000000+00:00') RETURNING id"
)


def test_the_fourteenth_migration_gives_the_sources_the_column_and_keeps_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:13])
    sources_and_what_points_to_them(store)
    held = held_at_version_13(store)
    before = (tables(store), indexes(store), triggers(store))

    migrate(store, MIGRATIONS[:14])

    assert schema_version(store) == 14
    # The copies the migration works with are gone again.
    assert len(before[0]) == 6
    assert tables(store) == before[0]
    assert len(before[1]) == 7
    assert indexes(store) == sorted([*before[1], ("ix_source_country_id", "source")])
    assert len(before[2]) == 10
    assert triggers(store) == before[2]
    assert columns_of_the_sources(store) == [
        *OF_A_SOURCE_AT_VERSION_13[:11],
        "country_id",
        "created_at",
        "updated_at",
    ]
    # Every source has what it had, its key too, and every row that
    # pointed to a source points to the same one.
    assert {what: len(rows) for what, rows in held.items()} == {
        "source_offer": 2,
        "collection_run": 1,
        "review_item": 1,
        "country": 1,
        "source": 2,
        "the highest key of each table": 5,
    }
    # The highest key of the sources is above that of every source that
    # is there, and the migration leaves those of the other tables alone.
    assert held["the highest key of each table"] == [
        ("collection_run", 1),
        ("country", 1),
        ("review_item", 1),
        ("source", 4),
        ("source_offer", 2),
    ]
    assert [key for key, *_ in held["source"]] == [1, 3]
    assert held_at_version_13(store) == held
    with store.connect() as connection:
        countries = connection.exec_driver_sql("SELECT id, country_id FROM source").all()
        broken = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
        index = connection.exec_driver_sql("PRAGMA index_info(ix_source_country_id)").all()
    # No source that was there is of a country: nobody has said of which.
    assert [tuple(row) for row in countries] == [(1, None), (3, None)]
    assert broken == []
    assert [name for _, _, name in index] == ["country_id"]


def test_after_the_fourteenth_migration_the_key_of_a_deleted_source_is_not_given_again(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:13])
    sources_and_what_points_to_them(store)

    migrate(store, MIGRATIONS[:14])

    with store.begin() as connection:
        key = connection.exec_driver_sql(A_NEW_SOURCE).scalar_one()
        highest = connection.exec_driver_sql(
            "SELECT name, seq FROM sqlite_sequence WHERE name = 'source'"
        ).all()
    # The fourth source was deleted before the migration. Its key stays its own.
    assert key == 5
    assert [tuple(row) for row in highest] == [("source", 5)]


@pytest.mark.parametrize("ever", [0, 2], ids=["never a source", "two sources, both deleted"])
def test_the_fourteenth_migration_keeps_the_highest_key_of_a_table_without_sources(
    store: Engine, ever: int
) -> None:
    migrate(store, MIGRATIONS[:13])
    with store.begin() as connection:
        for number in range(ever):
            connection.exec_driver_sql(
                "INSERT INTO source (name, website, category, collection_method, switched_on, "
                "created_at, updated_at) VALUES (?, 'https://club.example', 'club', "
                "'html extraction', 0, '2026-11-19T08:00:00.000000+00:00', "
                "'2026-11-19T08:00:00.000000+00:00')",
                (f"Example Club {number}",),
            )
        connection.exec_driver_sql("DELETE FROM source")

    migrate(store, MIGRATIONS[:14])

    with store.begin() as connection:
        kept = connection.exec_driver_sql(
            "SELECT seq FROM sqlite_sequence WHERE name = 'source'"
        ).all()
        key = connection.exec_driver_sql(A_NEW_SOURCE).scalar_one()
    # A table that never gave a key has no highest one, before and after.
    assert [tuple(row) for row in kept] == ([(2,)] if ever else [])
    assert key == ever + 1


def test_after_the_fourteenth_migration_the_rows_are_held_to_their_sources_again(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:13])
    sources_and_what_points_to_them(store)

    migrate(store, MIGRATIONS[:14])

    with pytest.raises(IntegrityError) as no_such_source, store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source_offer (source_id, information_type, created_at, updated_at) "
            "VALUES (2, 'news', '2026-11-27T12:00:00.000000+00:00', "
            "'2026-11-27T12:00:00.000000+00:00')"
        )
    with pytest.raises(IntegrityError) as still_needed, store.begin() as connection:
        connection.exec_driver_sql("DELETE FROM source WHERE id = 1")
    with pytest.raises(IntegrityError) as no_such_country, store.begin() as connection:
        connection.exec_driver_sql("UPDATE source SET country_id = 2 WHERE id = 3")
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE source SET country_id = 1 WHERE id = 3")
        of = connection.exec_driver_sql(
            "SELECT country.alpha_2 FROM source JOIN country ON country.id = source.country_id"
        ).all()

    refusals = (no_such_source, still_needed, no_such_country)
    assert [str(refusal.value.orig) for refusal in refusals] == [
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
    ]
    assert [tuple(row) for row in of] == [("NZ",)]


# A table that is there under the name of one of the two copies the
# migration works with: how it is made, filled and read.
IN_THE_PLACE_OF_A_COPY = {
    "source_before": (
        "CREATE TABLE source_before (note TEXT)",
        "INSERT INTO source_before (note) VALUES ('kept')",
        "SELECT * FROM source_before",
    ),
    "source_key_before": (
        "CREATE TABLE source_key_before (note TEXT)",
        "INSERT INTO source_key_before (note) VALUES ('kept')",
        "SELECT * FROM source_key_before",
    ),
}


@pytest.mark.parametrize("copy", list(IN_THE_PLACE_OF_A_COPY))
def test_the_fourteenth_migration_does_not_pass_over_a_table_of_the_name_of_a_copy(
    store: Engine, copy: str
) -> None:
    make, fill, read = IN_THE_PLACE_OF_A_COPY[copy]
    migrate(store, MIGRATIONS[:13])
    sources_and_what_points_to_them(store)
    with store.begin() as connection:
        connection.exec_driver_sql(make)
        connection.exec_driver_sql(fill)
    held = held_at_version_13(store)
    before = (tables(store), indexes(store), triggers(store), columns_of_the_sources(store))

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:14])

    assert str(refusal.value.orig) == f"table {copy} already exists"
    assert schema_version(store) == 13
    assert (
        tables(store),
        indexes(store),
        triggers(store),
        columns_of_the_sources(store),
    ) == before
    assert "country_id" not in before[3]
    assert held_at_version_13(store) == held
    with store.connect() as connection:
        assert connection.exec_driver_sql(read).all() == [("kept",)]


def test_the_fourteenth_migration_that_fails_at_its_end_leaves_the_sources_as_they_were(
    store: Engine,
) -> None:
    # The index is the last thing the migration makes. By then the table
    # of the sources was dropped, made anew and filled, and all of that is
    # taken back with the migration.
    migrate(store, MIGRATIONS[:13])
    sources_and_what_points_to_them(store)
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE INDEX ix_source_country_id ON country (name)")
    held = held_at_version_13(store)
    before = (tables(store), indexes(store), triggers(store), columns_of_the_sources(store))

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:14])

    assert str(refusal.value.orig) == "index ix_source_country_id already exists"
    assert schema_version(store) == 13
    assert (
        tables(store),
        indexes(store),
        triggers(store),
        columns_of_the_sources(store),
    ) == before
    assert "country_id" not in before[3]
    assert held_at_version_13(store) == held
    with store.begin() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        # The key of the deleted source is still not given again.
        assert connection.exec_driver_sql(A_NEW_SOURCE).scalar_one() == 5


# What a store at version 14 holds of its sources: as at version 13, and
# of each source its country too.
HELD_AT_VERSION_14 = {
    **HELD_AT_VERSION_13,
    "source": "SELECT * FROM source ORDER BY id",
}
# The twelve kinds of source a store at version 14 takes, as the first
# migration wrote them, and the one the fifteenth adds.
KINDS_AT_VERSION_14 = [
    "governing body",
    "championship",
    "organiser",
    "promoter",
    "track",
    "club",
    "regional organisation",
    "results database",
    "news publication",
    "community website",
    "social media page",
    "historical archive",
]
THE_NEW_KIND = "reference list"
A_SOURCE_OF_A_KIND = (
    "INSERT INTO source (name, website, category, collection_method, switched_on, "
    "created_at, updated_at) VALUES (?, 'https://lists.example', ?, 'public dataset', 0, "
    "'2026-11-27T12:00:00.000000+00:00', '2026-11-27T12:00:00.000000+00:00') RETURNING id"
)


def sources_with_a_country_and_what_points_to_them(store: Engine) -> None:
    """Fill a store at version 14: as at version 13, and the third source is of the country."""
    sources_and_what_points_to_them(store)
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE source SET country_id = 1 WHERE id = 3")


def held_at_version_14(store: Engine) -> dict[str, list[tuple[object, ...]]]:
    """Every row of the sources and of the tables that point to them, each table by its key."""
    with store.connect() as connection:
        return {
            what: [tuple(row) for row in connection.exec_driver_sql(asked)]
            for what, asked in HELD_AT_VERSION_14.items()
        }


def as_written(store: Engine) -> dict[str, str]:
    """How SQLite holds each table and index of the store: its name and its statement."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name, sql FROM sqlite_master WHERE type IN ('table', 'index') "
            "AND sql IS NOT NULL ORDER BY name"
        )
        return {str(name): str(statement) for name, statement in found}


def test_the_fifteenth_migration_lets_a_source_be_a_reference_list_and_keeps_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:14])
    sources_with_a_country_and_what_points_to_them(store)
    held = held_at_version_14(store)
    before = (tables(store), indexes(store), triggers(store), columns_of_the_sources(store))
    written = as_written(store)
    with pytest.raises(IntegrityError) as not_yet, store.begin() as connection:
        connection.exec_driver_sql(A_SOURCE_OF_A_KIND, ("Example Lists", THE_NEW_KIND))

    migrate(store, MIGRATIONS[:15])

    assert str(not_yet.value.orig) == "CHECK constraint failed: ck_source_category_one_of"
    assert schema_version(store) == 15
    # The copies the migration works with are gone again, and nothing is
    # there that was not: the index of the sources of a country, which
    # went with the table, is back.
    assert len(before[0]) == 6
    assert len(before[1]) == 8
    assert len(before[2]) == 10
    assert len(before[3]) == 14
    assert (
        tables(store),
        indexes(store),
        triggers(store),
        columns_of_the_sources(store),
    ) == before
    # Every source has what it had, its key and its country too, and
    # every row that pointed to a source points to the same one.
    assert {what: len(rows) for what, rows in held.items()} == {
        "source_offer": 2,
        "collection_run": 1,
        "review_item": 1,
        "country": 1,
        "source": 2,
        "the highest key of each table": 5,
    }
    assert held["the highest key of each table"] == [
        ("collection_run", 1),
        ("country", 1),
        ("review_item", 1),
        ("source", 4),
        ("source_offer", 2),
    ]
    assert [(row[0], row[11]) for row in held["source"]] == [(1, None), (3, 1)]
    assert held_at_version_14(store) == held
    # Of all the tables and indexes, only the table of the sources is
    # written otherwise than it was, and only in the one text more that
    # its check names.
    after = as_written(store)
    assert sorted(after) == sorted(written)
    assert [name for name in after if after[name] != written[name]] == ["source"]
    assert "'historical archive'" in written["source"]
    assert THE_NEW_KIND not in written["source"]
    with_the_new_kind = written["source"].replace(
        "'historical archive'", f"'historical archive', '{THE_NEW_KIND}'"
    )
    assert after["source"].split() == with_the_new_kind.split()
    with store.connect() as connection:
        broken = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
        index = connection.exec_driver_sql("PRAGMA index_info(ix_source_country_id)").all()
    assert broken == []
    assert [name for _, _, name in index] == ["country_id"]


def test_after_the_fifteenth_migration_a_source_is_of_one_of_the_thirteen_kinds(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:15])

    with store.begin() as connection:
        for kind in [*KINDS_AT_VERSION_14, THE_NEW_KIND]:
            connection.exec_driver_sql(A_SOURCE_OF_A_KIND, (f"Example of the kind {kind}", kind))
        kinds = connection.exec_driver_sql("SELECT category FROM source ORDER BY id").all()

    assert len(KINDS_AT_VERSION_14) == 12
    assert [kind for (kind,) in kinds] == [*KINDS_AT_VERSION_14, THE_NEW_KIND]


@pytest.mark.parametrize(
    "text",
    [
        "Reference list",
        "reference list ",
        "reference  list",
        "reference",
        "reference data",
        "reference lists",
        "",
        "public dataset",
    ],
)
def test_after_the_fifteenth_migration_a_text_that_is_not_of_the_list_is_still_refused(
    store: Engine, text: str
) -> None:
    migrate(store, MIGRATIONS[:15])

    with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
        connection.exec_driver_sql(A_SOURCE_OF_A_KIND, ("Example Lists", text))

    assert str(refusal.value.orig) == "CHECK constraint failed: ck_source_category_one_of"
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM source").scalar_one() == 0


def test_after_the_fifteenth_migration_the_key_of_a_deleted_source_is_not_given_again(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:14])
    sources_with_a_country_and_what_points_to_them(store)

    migrate(store, MIGRATIONS[:15])

    with store.begin() as connection:
        key = connection.exec_driver_sql(
            A_SOURCE_OF_A_KIND, ("Example Lists", THE_NEW_KIND)
        ).scalar_one()
        highest = connection.exec_driver_sql(
            "SELECT name, seq FROM sqlite_sequence WHERE name = 'source'"
        ).all()
    # The fourth source was deleted before the migration. Its key stays its own.
    assert key == 5
    assert [tuple(row) for row in highest] == [("source", 5)]


@pytest.mark.parametrize("ever", [0, 2], ids=["never a source", "two sources, both deleted"])
def test_the_fifteenth_migration_keeps_the_highest_key_of_a_table_without_sources(
    store: Engine, ever: int
) -> None:
    migrate(store, MIGRATIONS[:14])
    with store.begin() as connection:
        for number in range(ever):
            connection.exec_driver_sql(
                "INSERT INTO source (name, website, category, collection_method, switched_on, "
                "created_at, updated_at) VALUES (?, 'https://club.example', 'club', "
                "'html extraction', 0, '2026-11-19T08:00:00.000000+00:00', "
                "'2026-11-19T08:00:00.000000+00:00')",
                (f"Example Club {number}",),
            )
        connection.exec_driver_sql("DELETE FROM source")

    migrate(store, MIGRATIONS[:15])

    with store.begin() as connection:
        kept = connection.exec_driver_sql(
            "SELECT seq FROM sqlite_sequence WHERE name = 'source'"
        ).all()
        key = connection.exec_driver_sql(A_NEW_SOURCE).scalar_one()
    # A table that never gave a key has no highest one, before and after.
    assert [tuple(row) for row in kept] == ([(2,)] if ever else [])
    assert key == ever + 1


def test_after_the_fifteenth_migration_the_rows_are_held_to_their_sources_again(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:14])
    sources_with_a_country_and_what_points_to_them(store)

    migrate(store, MIGRATIONS[:15])

    with pytest.raises(IntegrityError) as no_such_source, store.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO source_offer (source_id, information_type, created_at, updated_at) "
            "VALUES (2, 'news', '2026-11-27T12:00:00.000000+00:00', "
            "'2026-11-27T12:00:00.000000+00:00')"
        )
    with pytest.raises(IntegrityError) as still_needed, store.begin() as connection:
        connection.exec_driver_sql("DELETE FROM source WHERE id = 1")
    with pytest.raises(IntegrityError) as no_such_country, store.begin() as connection:
        connection.exec_driver_sql("UPDATE source SET country_id = 2 WHERE id = 1")
    with pytest.raises(IntegrityError) as a_source_is_of_it, store.begin() as connection:
        connection.exec_driver_sql("DELETE FROM country WHERE id = 1")
    with store.begin() as connection:
        of = connection.exec_driver_sql(
            "SELECT source.id, country.alpha_2 FROM source "
            "JOIN country ON country.id = source.country_id"
        ).all()

    refusals = (no_such_source, still_needed, no_such_country, a_source_is_of_it)
    assert [str(refusal.value.orig) for refusal in refusals] == [
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
    ]
    assert [tuple(row) for row in of] == [(3, "NZ")]


@pytest.mark.parametrize("copy", list(IN_THE_PLACE_OF_A_COPY))
def test_the_fifteenth_migration_does_not_pass_over_a_table_of_the_name_of_a_copy(
    store: Engine, copy: str
) -> None:
    make, fill, read = IN_THE_PLACE_OF_A_COPY[copy]
    migrate(store, MIGRATIONS[:14])
    sources_with_a_country_and_what_points_to_them(store)
    with store.begin() as connection:
        connection.exec_driver_sql(make)
        connection.exec_driver_sql(fill)
    held = held_at_version_14(store)
    written = as_written(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:15])

    assert str(refusal.value.orig) == f"table {copy} already exists"
    assert schema_version(store) == 14
    assert as_written(store) == written
    assert THE_NEW_KIND not in written["source"]
    assert held_at_version_14(store) == held
    with store.connect() as connection:
        assert connection.exec_driver_sql(read).all() == [("kept",)]


def test_the_fifteenth_migration_that_fails_at_its_end_leaves_the_sources_as_they_were(
    store: Engine,
) -> None:
    # The index is the last thing the migration makes. By then the table
    # of the sources was dropped, made anew and filled, and all of that is
    # taken back with the migration. So that the index cannot be made, the
    # store has a table of its name where the index was.
    migrate(store, MIGRATIONS[:14])
    sources_with_a_country_and_what_points_to_them(store)
    with store.begin() as connection:
        connection.exec_driver_sql("DROP INDEX ix_source_country_id")
        connection.exec_driver_sql("CREATE TABLE ix_source_country_id (note TEXT)")
    held = held_at_version_14(store)
    written = as_written(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:15])

    assert str(refusal.value.orig) == "there is already a table named ix_source_country_id"
    assert schema_version(store) == 14
    assert as_written(store) == written
    assert THE_NEW_KIND not in written["source"]
    assert held_at_version_14(store) == held
    with pytest.raises(IntegrityError) as still_not, store.begin() as connection:
        connection.exec_driver_sql(A_SOURCE_OF_A_KIND, ("Example Lists", THE_NEW_KIND))
    assert str(still_not.value.orig) == "CHECK constraint failed: ck_source_category_one_of"
    with store.begin() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        # The key of the deleted source is still not given again.
        assert connection.exec_driver_sql(A_NEW_SOURCE).scalar_one() == 5


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


A_REGION = (
    "INSERT INTO region (country_id, name, source_id, source_address, collected_at, "
    "last_verified_at, extraction_method, confidence, verification_status, created_at, "
    "updated_at) VALUES (1, 'Canterbury', 1, 'https://standards.example/regions.csv', "
    "'2026-11-27T09:00:00.000000+00:00', '2026-11-27T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-27T09:00:05.000000+00:00', '2026-11-27T09:00:05.000000+00:00')"
)


def test_the_sixteenth_migration_makes_the_table_of_the_regions_and_keeps_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:15])
    sources_with_a_country_and_what_points_to_them(store)
    held = held_at_version_14(store)
    before = (tables(store), indexes(store), triggers(store))
    written = as_written(store)

    migrate(store, MIGRATIONS[:16])

    assert schema_version(store) == 16
    assert len(before[0]) == 6
    assert tables(store) == sorted([*before[0], "region"])
    assert len(before[1]) == 8
    assert indexes(store) == sorted([*before[1], ("ix_region_source_id", "region")])
    assert len(before[2]) == 10
    assert triggers(store) == before[2]
    # Every table and index that was there is written as it was, and
    # holds what it held.
    now = as_written(store)
    assert {name: statement for name, statement in now.items() if name in written} == written
    assert sorted(set(now) - set(written)) == ["ix_region_source_id", "region"]
    assert held_at_version_14(store) == held
    with store.begin() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM region").scalar_one() == 0
        # The new table refers to the countries and the sources that were there.
        connection.exec_driver_sql(A_REGION)
    with store.connect() as connection:
        columns = connection.exec_driver_sql("PRAGMA index_info(ix_region_source_id)").all()
        rule = connection.exec_driver_sql("PRAGMA index_info(sqlite_autoindex_region_1)").all()
        assert connection.exec_driver_sql(
            "SELECT country.alpha_2, region.name, source.name FROM region "
            "JOIN country ON country.id = region.country_id "
            "JOIN source ON source.id = region.source_id"
        ).all() == [("NZ", "Canterbury", "Example Standards Body")]
    assert [name for _, _, name in columns] == ["source_id"]
    assert [name for _, _, name in rule] == ["country_id", "name"]


def test_the_sixteenth_migration_does_not_pass_over_a_table_of_its_name_that_is_there(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:15])
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE region (note TEXT)")
        connection.exec_driver_sql("INSERT INTO region (note) VALUES ('kept')")

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:16])

    assert str(refusal.value.orig) == "table region already exists"
    assert schema_version(store) == 15
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT * FROM region").all() == [("kept",)]


def test_the_sixteenth_migration_does_not_pass_over_an_index_of_its_name_that_is_there(
    store: Engine,
) -> None:
    # The index is the second thing the migration makes: its table is made
    # before it, and taken back with the migration.
    migrate(store, MIGRATIONS[:15])
    with store.begin() as connection:
        connection.exec_driver_sql("CREATE INDEX ix_region_source_id ON source (name)")
    before = (tables(store), indexes(store))

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:16])

    assert str(refusal.value.orig) == "index ix_region_source_id already exists"
    assert schema_version(store) == 15
    assert "region" not in tables(store)
    assert (tables(store), indexes(store)) == before


# What a store at version 16 holds of its regions: every region with the
# columns it had then, what a region points to, and the highest key each
# table gave.
OF_A_REGION_AT_VERSION_16 = [
    "id",
    "country_id",
    "name",
    "source_id",
    "source_address",
    "collected_at",
    "published_on",
    "last_verified_at",
    "extraction_method",
    "confidence",
    "verification_status",
    "created_at",
    "updated_at",
]
HELD_AT_VERSION_16 = {
    **HELD_AT_VERSION_14,
    "region": (
        "SELECT id, country_id, name, source_id, source_address, collected_at, published_on, "
        "last_verified_at, extraction_method, confidence, verification_status, created_at, "
        "updated_at FROM region ORDER BY id"
    ),
}
A_REGION_NAMED = (
    "INSERT INTO region (country_id, name, source_id, source_address, collected_at, "
    "published_on, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) VALUES (?, ?, ?, 'https://standards.example/regions.csv', "
    "'2026-11-27T09:00:00.000000+00:00', ?, ?, 'public dataset', 'high', 'official', "
    "'2026-11-27T09:00:05.000000+00:00', ?) RETURNING id"
)
NOT_SEEN_AGAIN = (None, "2026-11-27T09:00:00.000000+00:00", "2026-11-27T09:00:05.000000+00:00")
SEEN_AGAIN = ("2026-11-02", "2026-11-28T09:00:00.000000+00:00", "2026-11-28T09:00:05.000000+00:00")


def regions_and_what_they_point_to(store: Engine) -> None:
    """Fill a store at version 16: as at version 14, and two regions and two that were deleted.

    Four regions of the one country are stored, with the keys 1 to 4, and
    the second and the fourth are deleted again: so the keys of the
    regions have a gap, and the highest key the table gave is above that
    of every region that is there. The first region came from the first
    source and has only what a region cannot be without. The third came
    from the third source and has everything a region could have then.
    """
    sources_with_a_country_and_what_points_to_them(store)
    with store.begin() as connection:
        connection.exec_driver_sql(A_REGION_NAMED, (1, "Canterbury", 1, *NOT_SEEN_AGAIN))
        connection.exec_driver_sql(A_REGION_NAMED, (1, "Example Region", 1, *NOT_SEEN_AGAIN))
        connection.exec_driver_sql(A_REGION_NAMED, (1, "Otago", 3, *SEEN_AGAIN))
        connection.exec_driver_sql(A_REGION_NAMED, (1, "Example District", 3, *NOT_SEEN_AGAIN))
        connection.exec_driver_sql(
            "DELETE FROM region WHERE name IN ('Example Region', 'Example District')"
        )


def held_at_version_16(store: Engine) -> dict[str, list[tuple[object, ...]]]:
    """Every row of the regions and of the tables they point to, each table by its key."""
    with store.connect() as connection:
        return {
            what: [tuple(row) for row in connection.exec_driver_sql(asked)]
            for what, asked in HELD_AT_VERSION_16.items()
        }


def columns_of_the_regions(store: Engine) -> list[str]:
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT name FROM pragma_table_info('region')")
        return [str(name) for (name,) in found]


def test_the_seventeenth_migration_gives_the_regions_the_column_and_keeps_what_there_was(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:16])
    regions_and_what_they_point_to(store)
    held = held_at_version_16(store)
    before = (tables(store), indexes(store), triggers(store))
    written = as_written(store)

    migrate(store, MIGRATIONS[:17])

    assert schema_version(store) == 17
    # The copies the migration works with are gone again, and the index
    # that went with the table is there again.
    assert len(before[0]) == 7
    assert tables(store) == before[0]
    assert len(before[1]) == 9
    assert indexes(store) == before[1]
    assert len(before[2]) == 10
    assert triggers(store) == before[2]
    assert columns_of_the_regions(store) == [
        *OF_A_REGION_AT_VERSION_16[:3],
        "iso_3166_2",
        *OF_A_REGION_AT_VERSION_16[3:],
    ]
    # Every other table and every index is written as it was.
    now = as_written(store)
    assert sorted(now) == sorted(written)
    assert [name for name in now if now[name] != written[name]] == ["region"]
    # Every region has what it had, its key too, and so has every row a
    # region points to.
    assert {what: len(rows) for what, rows in held.items()} == {
        "source_offer": 2,
        "collection_run": 1,
        "review_item": 1,
        "country": 1,
        "source": 2,
        "the highest key of each table": 6,
        "region": 2,
    }
    # The highest key of the regions is above that of every region that
    # is there, and the migration leaves those of the other tables alone.
    assert held["the highest key of each table"] == [
        ("collection_run", 1),
        ("country", 1),
        ("region", 4),
        ("review_item", 1),
        ("source", 4),
        ("source_offer", 2),
    ]
    assert [(key, name, source) for key, _, name, source, *_ in held["region"]] == [
        (1, "Canterbury", 1),
        (3, "Otago", 3),
    ]
    assert held_at_version_16(store) == held
    with store.connect() as connection:
        codes = connection.exec_driver_sql("SELECT id, iso_3166_2 FROM region ORDER BY id").all()
        broken = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
        of_the_sources = connection.exec_driver_sql("PRAGMA index_info(ix_region_source_id)").all()
        of_the_names = connection.exec_driver_sql(
            "PRAGMA index_info(sqlite_autoindex_region_1)"
        ).all()
        of_the_codes = connection.exec_driver_sql(
            "PRAGMA index_info(sqlite_autoindex_region_2)"
        ).all()
    # No region that was there has a code: nobody has said which.
    assert [tuple(row) for row in codes] == [(1, None), (3, None)]
    assert broken == []
    assert [name for _, _, name in of_the_sources] == ["source_id"]
    assert [name for _, _, name in of_the_names] == ["country_id", "name"]
    assert [name for _, _, name in of_the_codes] == ["iso_3166_2"]


A_NEW_REGION = (
    "INSERT INTO region (country_id, name, iso_3166_2, source_id, source_address, "
    "collected_at, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) VALUES (1, ?, ?, 1, 'https://standards.example/regions.csv', "
    "'2026-11-28T09:00:00.000000+00:00', '2026-11-28T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-28T09:00:05.000000+00:00', "
    "'2026-11-28T09:00:05.000000+00:00') RETURNING id"
)


ANOTHER_COUNTRY = (
    "INSERT INTO country (alpha_2, alpha_3, name, source_id, source_address, collected_at, "
    "last_verified_at, extraction_method, confidence, verification_status, created_at, "
    "updated_at) VALUES ('AU', 'AUS', 'Australia', 1, "
    "'https://standards.example/countries.csv', '2026-11-27T09:00:00.000000+00:00', "
    "'2026-11-27T09:00:00.000000+00:00', 'public dataset', 'high', 'official', "
    "'2026-11-27T09:00:05.000000+00:00', '2026-11-27T09:00:05.000000+00:00')"
)


def test_after_the_seventeenth_migration_the_key_of_a_deleted_region_is_not_given_again(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:16])
    regions_and_what_they_point_to(store)

    migrate(store, MIGRATIONS[:17])

    with store.begin() as connection:
        key = connection.exec_driver_sql(A_NEW_REGION, ("Southland", "NZ-STL")).scalar_one()
        highest = connection.exec_driver_sql(
            "SELECT name, seq FROM sqlite_sequence WHERE name = 'region'"
        ).all()
    # The fourth region was deleted before the migration. Its key stays its own.
    assert key == 5
    assert [tuple(row) for row in highest] == [("region", 5)]


@pytest.mark.parametrize("ever", [0, 2], ids=["never a region", "two regions, both deleted"])
def test_the_seventeenth_migration_keeps_the_highest_key_of_a_table_without_regions(
    store: Engine, ever: int
) -> None:
    migrate(store, MIGRATIONS[:16])
    sources_with_a_country_and_what_points_to_them(store)
    with store.begin() as connection:
        for number in range(ever):
            connection.exec_driver_sql(
                A_REGION_NAMED, (1, f"Example Region {number}", 1, *NOT_SEEN_AGAIN)
            )
        connection.exec_driver_sql("DELETE FROM region")

    migrate(store, MIGRATIONS[:17])

    with store.begin() as connection:
        kept = connection.exec_driver_sql(
            "SELECT seq FROM sqlite_sequence WHERE name = 'region'"
        ).all()
        key = connection.exec_driver_sql(A_NEW_REGION, ("Southland", "NZ-STL")).scalar_one()
    # A table that never gave a key has no highest one, before and after.
    assert [tuple(row) for row in kept] == ([(2,)] if ever else [])
    assert key == ever + 1


def test_after_the_seventeenth_migration_the_regions_are_held_to_their_rules_again(
    store: Engine,
) -> None:
    migrate(store, MIGRATIONS[:16])
    regions_and_what_they_point_to(store)

    migrate(store, MIGRATIONS[:17])

    with pytest.raises(IntegrityError) as no_such_country, store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET country_id = 2 WHERE id = 1")
    with pytest.raises(IntegrityError) as no_such_source, store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET source_id = 2 WHERE id = 1")
    # A source and a country that nothing but a region points to.
    with store.begin() as connection:
        connection.exec_driver_sql(A_NEW_SOURCE)
        connection.exec_driver_sql(ANOTHER_COUNTRY)
        connection.exec_driver_sql(A_REGION_NAMED, (2, "Western Australia", 1, *NOT_SEEN_AGAIN))
        connection.exec_driver_sql(A_REGION_NAMED, (1, "Southland", 5, *NOT_SEEN_AGAIN))
    with pytest.raises(IntegrityError) as a_region_came_from_it, store.begin() as connection:
        connection.exec_driver_sql("DELETE FROM source WHERE id = 5")
    with pytest.raises(IntegrityError) as a_region_is_of_it, store.begin() as connection:
        connection.exec_driver_sql("DELETE FROM country WHERE id = 2")
    with pytest.raises(IntegrityError) as one_name_twice, store.begin() as connection:
        connection.exec_driver_sql(A_NEW_REGION, ("Otago", None))
    with pytest.raises(IntegrityError) as without_a_name, store.begin() as connection:
        connection.exec_driver_sql(A_NEW_REGION, (" ", None))
    with pytest.raises(IntegrityError) as not_a_code, store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET iso_3166_2 = 'nz-can' WHERE id = 1")
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET iso_3166_2 = 'NZ-CAN' WHERE id = 1")
    with pytest.raises(IntegrityError) as one_code_twice, store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET iso_3166_2 = 'NZ-CAN' WHERE id = 3")
    with store.connect() as connection:
        of = connection.exec_driver_sql(
            "SELECT region.id, country.alpha_2, region.name, region.iso_3166_2, source.name "
            "FROM region JOIN country ON country.id = region.country_id "
            "JOIN source ON source.id = region.source_id ORDER BY region.id"
        ).all()

    refusals = (
        no_such_country,
        no_such_source,
        a_region_came_from_it,
        a_region_is_of_it,
        one_name_twice,
        without_a_name,
        not_a_code,
        one_code_twice,
    )
    assert [str(refusal.value.orig) for refusal in refusals] == [
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "UNIQUE constraint failed: region.country_id, region.name",
        "CHECK constraint failed: ck_region_name_not_empty",
        "CHECK constraint failed: ck_region_iso_3166_2_form",
        "UNIQUE constraint failed: region.iso_3166_2",
    ]
    assert [tuple(row) for row in of] == [
        (1, "NZ", "Canterbury", "NZ-CAN", "Example Standards Body"),
        (3, "NZ", "Otago", None, "Example Federation"),
        (5, "AU", "Western Australia", None, "Example Standards Body"),
        (6, "NZ", "Southland", None, "Example Union"),
    ]


# A table that is there under the name of one of the two copies the
# seventeenth migration works with: how it is made, filled and read.
IN_THE_PLACE_OF_A_COPY_OF_THE_REGIONS = {
    "region_before": (
        "CREATE TABLE region_before (note TEXT)",
        "INSERT INTO region_before (note) VALUES ('kept')",
        "SELECT * FROM region_before",
    ),
    "region_key_before": (
        "CREATE TABLE region_key_before (note TEXT)",
        "INSERT INTO region_key_before (note) VALUES ('kept')",
        "SELECT * FROM region_key_before",
    ),
}


@pytest.mark.parametrize("copy", list(IN_THE_PLACE_OF_A_COPY_OF_THE_REGIONS))
def test_the_seventeenth_migration_does_not_pass_over_a_table_of_the_name_of_a_copy(
    store: Engine, copy: str
) -> None:
    make, fill, read = IN_THE_PLACE_OF_A_COPY_OF_THE_REGIONS[copy]
    migrate(store, MIGRATIONS[:16])
    regions_and_what_they_point_to(store)
    with store.begin() as connection:
        connection.exec_driver_sql(make)
        connection.exec_driver_sql(fill)
    held = held_at_version_16(store)
    written = as_written(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:17])

    assert str(refusal.value.orig) == f"table {copy} already exists"
    assert schema_version(store) == 16
    assert as_written(store) == written
    assert "iso_3166_2" not in written["region"]
    assert held_at_version_16(store) == held
    with store.connect() as connection:
        assert connection.exec_driver_sql(read).all() == [("kept",)]


def test_the_seventeenth_migration_that_fails_at_its_end_leaves_the_regions_as_they_were(
    store: Engine,
) -> None:
    # The index is the last thing the migration makes. By then the table
    # of the regions was dropped, made anew and filled, and all of that is
    # taken back with the migration. So that the index cannot be made, the
    # store has an index of its name over another table where it was.
    migrate(store, MIGRATIONS[:16])
    regions_and_what_they_point_to(store)
    with store.begin() as connection:
        connection.exec_driver_sql("DROP INDEX ix_region_source_id")
        connection.exec_driver_sql("CREATE INDEX ix_region_source_id ON country (name)")
    held = held_at_version_16(store)
    written = as_written(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:17])

    assert str(refusal.value.orig) == "index ix_region_source_id already exists"
    assert schema_version(store) == 16
    assert as_written(store) == written
    assert "iso_3166_2" not in written["region"]
    assert columns_of_the_regions(store) == OF_A_REGION_AT_VERSION_16
    assert held_at_version_16(store) == held
    with store.begin() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        # The key of the deleted region is still not given again.
        assert (
            connection.exec_driver_sql(
                A_REGION_NAMED, (1, "Southland", 1, *NOT_SEEN_AGAIN)
            ).scalar_one()
            == 5
        )
