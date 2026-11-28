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
        "hold_the_key_of_a_review_item_under_every_name",
        "hold_the_code_of_a_region_to_its_country",
        "let_regions_with_codes_share_a_name",
        "let_a_region_be_a_part_of_another",
        "let_parts_of_different_regions_share_a_name",
        "keep_a_region_out_of_its_own_parts",
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


# A statement that gives an item another key, by each of the three names
# SQLite itself has for the key of a table.
BY_SQLITES_OWN_NAMES_OF_THE_KEY = [
    "UPDATE review_item SET rowid = ? WHERE id = ?",
    "UPDATE review_item SET _rowid_ = ? WHERE id = ?",
    "UPDATE review_item SET oid = ? WHERE id = ?",
]


def the_second_trigger_of_the_keys(store: Engine) -> str:
    """The trigger as SQLite holds it: the statement that made it."""
    with store.connect() as connection:
        return str(
            connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?",
                (KEY_STAYS_POSITIVE,),
            ).scalar_one()
        )


def review_items(store: Engine) -> list[tuple[object, ...]]:
    """Every item of the review queue with every column, by the key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql("SELECT * FROM review_item ORDER BY id")
        return [tuple(row) for row in found]


def a_queue_at_version_17(store: Engine) -> None:
    """Bring the store to version 17 with three open items in its review queue.

    The item with the key -3 was stored before the eleventh migration,
    which asks nothing of the items that are there. The others have the
    keys 5 and 6.
    """
    migrate(store, MIGRATIONS[:10])
    with store.begin() as connection:
        connection.exec_driver_sql(AN_ITEM_WITH_A_KEY_AT_VERSION_10, (-3, 8, 9))
        connection.exec_driver_sql(AN_ITEM_WITH_A_KEY_AT_VERSION_10, (5, 7, 12))
        connection.exec_driver_sql(AN_ITEM_WITH_A_KEY_AT_VERSION_10, (6, 10, 11))
    migrate(store, MIGRATIONS[:17])


def test_the_eighteenth_migration_makes_the_second_trigger_of_the_keys_anew_and_keeps_the_rest(
    store: Engine,
) -> None:
    a_queue_at_version_17(store)
    items = review_items(store)
    before = (tables(store), indexes(store), triggers(store), as_written(store))
    old = the_second_trigger_of_the_keys(store)

    migrate(store, MIGRATIONS[:18])

    assert schema_version(store) == 18
    # The same tables, indexes and triggers by name, and the tables and
    # indexes as they were written.
    assert (tables(store), indexes(store), triggers(store), as_written(store)) == before
    assert (KEY_STAYS_POSITIVE, "review_item") in before[2]
    new = the_second_trigger_of_the_keys(store)
    assert "AFTER UPDATE OF id ON review_item" in old
    assert "AFTER UPDATE ON review_item" in new
    assert "NEW.id < 1 AND NEW.id != OLD.id" in new
    assert A_KEY_IS_1_OR_MORE in new
    # The migration asks nothing of the items that are there and changes none.
    assert [item[0] for item in items] == [-3, 5, 6]
    assert review_items(store) == items


@pytest.mark.parametrize(
    "statement", BY_SQLITES_OWN_NAMES_OF_THE_KEY, ids=["rowid", "_rowid_", "oid"]
)
def test_the_eighteenth_migration_holds_the_key_under_the_names_the_store_passed_over_before(
    store: Engine, statement: str
) -> None:
    # Before the migration a statement that sets the key by one of
    # SQLite's own names is taken, which is the defect; after it the same
    # statement is refused. What was taken before is left as it is.
    a_queue_at_version_17(store)
    with store.begin() as connection:
        connection.exec_driver_sql(statement, (-5, 5))
    assert [item[0] for item in review_items(store)] == [-5, -3, 6]
    items = review_items(store)

    migrate(store, MIGRATIONS[:18])

    with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
        connection.exec_driver_sql(statement, (-6, 6))
    assert str(refusal.value.orig) == A_KEY_IS_1_OR_MORE
    assert review_items(store) == items


def test_after_the_eighteenth_migration_the_column_is_held_as_before(store: Engine) -> None:
    a_queue_at_version_17(store)
    migrate(store, MIGRATIONS[:18])
    items = review_items(store)

    for statement, given in [
        (AN_ITEM_WITH_A_KEY_AT_VERSION_10, (0, 20, 21)),
        ("UPDATE review_item SET id = -5 WHERE id = 5", ()),
        ("UPDATE review_item SET id = -7 WHERE id = -3", ()),
    ]:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement, given)
        assert str(refusal.value.orig) == A_KEY_IS_1_OR_MORE
    assert review_items(store) == items
    # An item with a key below 1 is still given a note, and a key of 1 or
    # more; an item is still given another key of 1 or more.
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE review_item SET note = 'To be looked at.' WHERE id = -3")
        connection.exec_driver_sql("UPDATE review_item SET id = 3 WHERE id = -3")
        connection.exec_driver_sql("UPDATE review_item SET id = 50 WHERE id = 5")
    with store.connect() as connection:
        notes = connection.exec_driver_sql("SELECT id, note FROM review_item ORDER BY id").all()
    assert [tuple(row) for row in notes] == [(3, "To be looked at."), (6, None), (50, None)]


def test_the_eighteenth_migration_is_refused_where_the_trigger_it_makes_anew_is_not_there(
    store: Engine,
) -> None:
    # A store whose trigger was taken out is not what the migrations
    # built. The migration does not make the trigger as if nothing had
    # happened: it is refused, and the store is left as it was found.
    a_queue_at_version_17(store)
    with store.begin() as connection:
        connection.exec_driver_sql("DROP TRIGGER tr_review_item_key_stays_positive")
    items = review_items(store)
    before = triggers(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:18])

    assert str(refusal.value.orig) == "no such trigger: tr_review_item_key_stays_positive"
    assert schema_version(store) == 17
    assert len(before) == 9
    assert triggers(store) == before
    assert review_items(store) == items


THE_CODE_IS_OF_THE_COUNTRY = [
    ("tr_country_code_of_its_regions", "country"),
    ("tr_country_code_stays_of_its_regions", "country"),
    ("tr_region_code_of_its_country", "region"),
    ("tr_region_code_stays_of_its_country", "region"),
]
A_CODE_BEGINS_WITH_ITS_COUNTRY = (
    "The code of a region (region) begins with the code of its country (country)."
)
THE_CODES_BEGIN_WITH_THEIR_COUNTRY = (
    "The codes of the regions of a country (region) begin with its code (country)."
)


def regions_with_codes_at_version_18(store: Engine) -> None:
    """Bring a store to version 18 with its two regions given codes, one of them wrong.

    The country of both is New Zealand, "NZ". Canterbury, with the key 1,
    is given "NZ-CAN". Otago, with the key 3, is given "AU-OTA", which
    nothing refuses until the nineteenth migration.
    """
    migrate(store, MIGRATIONS[:16])
    regions_and_what_they_point_to(store)
    migrate(store, MIGRATIONS[:18])
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET iso_3166_2 = 'NZ-CAN' WHERE id = 1")
        connection.exec_driver_sql("UPDATE region SET iso_3166_2 = 'AU-OTA' WHERE id = 3")


def held_at_version_18(store: Engine) -> dict[str, list[tuple[object, ...]]]:
    """Every row of the regions with every column, and of the tables they point to."""
    with store.connect() as connection:
        return {
            what: [tuple(row) for row in connection.exec_driver_sql(asked)]
            for what, asked in {
                **HELD_AT_VERSION_14,
                "region": "SELECT * FROM region ORDER BY id",
            }.items()
        }


def as_the_triggers_are_written(store: Engine) -> dict[str, str]:
    """How SQLite holds each trigger of the store: its name and its statement."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT name, sql FROM sqlite_master WHERE type = 'trigger' ORDER BY name"
        )
        return {str(name): str(statement) for name, statement in found}


def test_the_nineteenth_migration_makes_four_triggers_and_keeps_what_there_was(
    store: Engine,
) -> None:
    regions_with_codes_at_version_18(store)
    held = held_at_version_18(store)
    before = (tables(store), indexes(store), triggers(store), as_written(store))
    written = as_the_triggers_are_written(store)

    migrate(store, MIGRATIONS[:19])

    assert schema_version(store) == 19
    # The same tables and indexes, written as they were, and every trigger
    # that was there, written as it was.
    assert (tables(store), indexes(store), as_written(store)) == (before[0], before[1], before[3])
    assert len(before[2]) == 10
    assert triggers(store) == sorted([*before[2], *THE_CODE_IS_OF_THE_COUNTRY])
    now = as_the_triggers_are_written(store)
    assert {name: now[name] for name in written} == written
    # The migration asks nothing of the regions that are there and changes
    # no row: the region whose code is of another country keeps it.
    with store.connect() as connection:
        assert connection.exec_driver_sql("SELECT id, alpha_2 FROM country").all() == [(1, "NZ")]
        codes = connection.exec_driver_sql("SELECT id, iso_3166_2 FROM region ORDER BY id").all()
    assert [tuple(row) for row in codes] == [(1, "NZ-CAN"), (3, "AU-OTA")]
    assert held_at_version_18(store) == held


SOUTHLAND_WITH_A_CODE_OF_AUSTRALIA = (
    "INSERT INTO region (country_id, name, iso_3166_2, source_id, source_address, collected_at, "
    "last_verified_at, extraction_method, confidence, verification_status, created_at, "
    "updated_at) VALUES (1, 'Southland', 'AU-STL', 1, 'https://standards.example/regions.csv', "
    "'2026-11-27T09:00:00.000000+00:00', '2026-11-27T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-27T09:00:05.000000+00:00', '2026-11-27T09:00:05.000000+00:00')"
)


@pytest.mark.parametrize(
    ("statement", "why"),
    [
        (SOUTHLAND_WITH_A_CODE_OF_AUSTRALIA, A_CODE_BEGINS_WITH_ITS_COUNTRY),
        ("UPDATE region SET iso_3166_2 = 'AT-CAN' WHERE id = 1", A_CODE_BEGINS_WITH_ITS_COUNTRY),
        ("UPDATE region SET name = 'Otakou' WHERE id = 3", A_CODE_BEGINS_WITH_ITS_COUNTRY),
        ("UPDATE country SET alpha_2 = 'NX' WHERE id = 1", THE_CODES_BEGIN_WITH_THEIR_COUNTRY),
    ],
    ids=[
        "a new region",
        "a region that is given a code",
        "a region whose code was wrong, another name",
        "a country that is given other letters",
    ],
)
def test_the_nineteenth_migration_holds_what_the_store_took_before(
    store: Engine, statement: str, why: str
) -> None:
    # Before the migration the statement is taken: it is tried and taken
    # back, so the store is as it was. After it the same statement is
    # refused.
    regions_with_codes_at_version_18(store)
    held = held_at_version_18(store)
    with store.connect() as connection:
        assert connection.exec_driver_sql(statement).rowcount == 1
        connection.rollback()
    assert held_at_version_18(store) == held

    migrate(store, MIGRATIONS[:19])

    with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
        connection.exec_driver_sql(statement)
    assert str(refusal.value.orig) == why
    assert held_at_version_18(store) == held


@pytest.mark.parametrize("trigger", [name for name, _ in THE_CODE_IS_OF_THE_COUNTRY])
def test_the_nineteenth_migration_does_not_pass_over_a_trigger_of_its_name_that_is_there(
    store: Engine, trigger: str
) -> None:
    # Whichever of the four is there already, the triggers made before it
    # are taken back with the migration.
    regions_with_codes_at_version_18(store)
    with store.begin() as connection:
        connection.exec_driver_sql(
            f"CREATE TRIGGER {trigger} AFTER DELETE ON region BEGIN SELECT 1; END"
        )
    before = triggers(store)
    held = held_at_version_18(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:19])

    assert str(refusal.value.orig) == f"trigger {trigger} already exists"
    assert schema_version(store) == 18
    assert len(before) == 11
    assert triggers(store) == before
    assert held_at_version_18(store) == held


THE_RULE_OF_THE_NAMES_IN_THE_TABLE = (
    "CONSTRAINT uq_region_country_id_name UNIQUE (country_id, name),\n            "
)
ONE_NAME_TWICE = "UNIQUE constraint failed: region.country_id, region.name"
THE_INDEXES_OF_THE_TWENTIETH = [
    ("ix_region_country_id", "region"),
    ("ix_region_country_id_name", "region"),
]
MOZAMBIQUE = (
    "INSERT INTO country (alpha_2, alpha_3, name, source_id, source_address, collected_at, "
    "last_verified_at, extraction_method, confidence, verification_status, created_at, "
    "updated_at) VALUES ('MZ', 'MOZ', 'Mozambique', 1, "
    "'https://standards.example/countries.csv', '2026-11-27T09:00:00.000000+00:00', "
    "'2026-11-27T09:00:00.000000+00:00', 'public dataset', 'high', 'official', "
    "'2026-11-27T09:00:05.000000+00:00', '2026-11-27T09:00:05.000000+00:00')"
)
# A region of the second country of the store, with its name and its code.
A_REGION_OF_THE_SECOND_COUNTRY = (
    "INSERT INTO region (country_id, name, iso_3166_2, source_id, source_address, "
    "collected_at, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) VALUES (2, ?, ?, 1, 'https://standards.example/regions.csv', "
    "'2026-11-28T09:00:00.000000+00:00', '2026-11-28T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-28T09:00:05.000000+00:00', "
    "'2026-11-28T09:00:05.000000+00:00')"
)


def regions_at_version_19(store: Engine) -> None:
    """Bring a store to version 19 with regions of two countries.

    New Zealand has Canterbury, with the key 1 and the code "NZ-CAN",
    and Otago, with the key 3 and the code "AU-OTA", which was stored
    before the nineteenth migration and is not of its country. Two
    regions were deleted, so the highest key the table gave when the
    nineteenth migration ran was 4. Mozambique, the second country, has
    Maputo the province, with the key 5 and the code "MZ-L", and Gaza,
    with the key 6 and no code.
    """
    regions_with_codes_at_version_18(store)
    migrate(store, MIGRATIONS[:19])
    with store.begin() as connection:
        connection.exec_driver_sql(MOZAMBIQUE)
        connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, ("Maputo", "MZ-L"))
        connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, ("Gaza", None))


def regions_as_they_are(store: Engine) -> list[tuple[object, ...]]:
    """The key, the country, the name and the code of every region, by their key."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT id, country_id, name, iso_3166_2 FROM region ORDER BY id"
        )
        return [tuple(row) for row in found]


def test_the_twentieth_migration_takes_the_rule_of_the_names_out_of_the_table_and_keeps_the_rest(
    store: Engine,
) -> None:
    regions_at_version_19(store)
    held = held_at_version_18(store)
    before = (tables(store), indexes(store), triggers(store))
    written = as_written(store)
    triggers_written = as_the_triggers_are_written(store)

    migrate(store, MIGRATIONS[:20])

    assert schema_version(store) == 20
    # The copies the migration works with are gone again. The index that
    # went with the table is there again, and two are new.
    assert len(before[0]) == 7
    assert tables(store) == before[0]
    assert len(before[1]) == 9
    assert indexes(store) == sorted([*before[1], *THE_INDEXES_OF_THE_TWENTIETH])
    # The two triggers that went with the table are there again, written
    # as they were, and so is every other.
    assert len(before[2]) == 14
    assert triggers(store) == before[2]
    assert as_the_triggers_are_written(store) == triggers_written
    # Every other table and every index that was there is written as it
    # was, and the table of the regions as it was but for the one rule.
    now = as_written(store)
    new = [name for name, _ in THE_INDEXES_OF_THE_TWENTIETH]
    assert sorted(now) == sorted([*written, *new])
    assert [name for name in written if now[name] != written[name]] == ["region"]
    assert written["region"].count(THE_RULE_OF_THE_NAMES_IN_THE_TABLE) == 1
    assert now["region"] == written["region"].replace(THE_RULE_OF_THE_NAMES_IN_THE_TABLE, "")
    assert {name: now[name] for name in new} == {
        "ix_region_country_id": "CREATE INDEX ix_region_country_id ON region (country_id)",
        "ix_region_country_id_name": (
            "CREATE UNIQUE INDEX ix_region_country_id_name ON region (country_id, name) "
            "WHERE iso_3166_2 IS NULL"
        ),
    }
    # Every region has what it had, its key and its code too: also the
    # one whose code is not of its country, which no migration puts
    # right. And so has every row a region points to.
    assert regions_as_they_are(store) == [
        (1, 1, "Canterbury", "NZ-CAN"),
        (3, 1, "Otago", "AU-OTA"),
        (5, 2, "Maputo", "MZ-L"),
        (6, 2, "Gaza", None),
    ]
    assert held_at_version_18(store) == held
    assert ("region", 6) in held["the highest key of each table"]
    with store.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        kept_by_sqlite = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'region' "
            "AND sql IS NULL"
        ).all()
        of_the_codes = connection.exec_driver_sql(
            "PRAGMA index_info(sqlite_autoindex_region_1)"
        ).all()
    # The one index SQLite keeps for a rule written into the table is
    # that of the codes now.
    assert [tuple(row) for row in kept_by_sqlite] == [("sqlite_autoindex_region_1",)]
    assert [name for _, _, name in of_the_codes] == ["iso_3166_2"]


@pytest.mark.parametrize(
    ("name", "code"),
    [("Maputo", "MZ-MPM"), ("Maputo", None), ("Gaza", "MZ-G")],
    ids=[
        "the city beside the province, each with its code",
        "one without a code beside one with a code",
        "one with a code beside one without",
    ],
)
def test_the_twentieth_migration_lets_in_a_region_the_store_refused_before(
    store: Engine, name: str, code: str | None
) -> None:
    regions_at_version_19(store)
    before = regions_as_they_are(store)
    with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
        connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, (name, code))
    assert str(refusal.value.orig) == ONE_NAME_TWICE
    assert regions_as_they_are(store) == before

    migrate(store, MIGRATIONS[:20])

    with store.begin() as connection:
        connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, (name, code))
    assert regions_as_they_are(store) == [*before, (7, 2, name, code)]


def test_after_the_twentieth_migration_two_regions_without_a_code_still_cannot_share_a_name(
    store: Engine,
) -> None:
    regions_at_version_19(store)
    before = regions_as_they_are(store)

    migrate(store, MIGRATIONS[:20])

    with pytest.raises(IntegrityError) as a_new_one, store.begin() as connection:
        connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, ("Gaza", None))
    # A second Gaza that says a code is taken, and cannot lose it again.
    with store.begin() as connection:
        connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, ("Gaza", "MZ-G"))
    with pytest.raises(IntegrityError) as one_that_loses_its_code, store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET iso_3166_2 = NULL WHERE id = 7")
    assert [str(refusal.value.orig) for refusal in (a_new_one, one_that_loses_its_code)] == [
        ONE_NAME_TWICE,
        ONE_NAME_TWICE,
    ]
    assert regions_as_they_are(store) == [*before, (7, 2, "Gaza", "MZ-G")]


def test_after_the_twentieth_migration_the_regions_are_held_to_their_other_rules_again(
    store: Engine,
) -> None:
    regions_at_version_19(store)
    before = regions_as_they_are(store)

    migrate(store, MIGRATIONS[:20])

    statements = [
        "UPDATE region SET country_id = 9 WHERE id = 5",
        "UPDATE region SET source_id = 9 WHERE id = 5",
        "DELETE FROM country WHERE id = 2",
        "DELETE FROM source WHERE id = 3",
        "UPDATE region SET name = ' ' WHERE id = 5",
        "UPDATE region SET iso_3166_2 = 'mz-l' WHERE id = 5",
        "UPDATE region SET iso_3166_2 = 'MZ-L' WHERE id = 6",
        "UPDATE region SET iso_3166_2 = 'NZ-GAZ' WHERE id = 6",
        "UPDATE region SET name = 'Otakou' WHERE id = 3",
        "UPDATE country SET alpha_2 = 'MX' WHERE id = 2",
    ]
    said = []
    for statement in statements:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement)
        said.append(str(refusal.value.orig))

    assert said == [
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "CHECK constraint failed: ck_region_name_not_empty",
        "CHECK constraint failed: ck_region_iso_3166_2_form",
        "UNIQUE constraint failed: region.iso_3166_2",
        A_CODE_BEGINS_WITH_ITS_COUNTRY,
        A_CODE_BEGINS_WITH_ITS_COUNTRY,
        THE_CODES_BEGIN_WITH_THEIR_COUNTRY,
    ]
    assert regions_as_they_are(store) == before
    # The region whose code is not of its country can still be put right.
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET iso_3166_2 = 'NZ-OTA' WHERE id = 3")
    assert regions_as_they_are(store)[1] == (3, 1, "Otago", "NZ-OTA")


def test_after_the_twentieth_migration_the_key_of_a_deleted_region_is_not_given_again(
    store: Engine,
) -> None:
    regions_at_version_19(store)
    with store.begin() as connection:
        connection.exec_driver_sql("DELETE FROM region WHERE id = 6")

    migrate(store, MIGRATIONS[:20])

    with store.begin() as connection:
        connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, ("Gaza", None))
        highest = connection.exec_driver_sql(
            "SELECT name, seq FROM sqlite_sequence WHERE name = 'region'"
        ).all()
    # The sixth region was deleted before the migration. Its key stays its own.
    assert regions_as_they_are(store)[-1] == (7, 2, "Gaza", None)
    assert [tuple(row) for row in highest] == [("region", 7)]


@pytest.mark.parametrize("ever", [0, 2], ids=["never a region", "two regions, both deleted"])
def test_the_twentieth_migration_keeps_the_highest_key_of_a_table_without_regions(
    store: Engine, ever: int
) -> None:
    migrate(store, MIGRATIONS[:16])
    sources_with_a_country_and_what_points_to_them(store)
    migrate(store, MIGRATIONS[:19])
    with store.begin() as connection:
        for number in range(ever):
            connection.exec_driver_sql(A_NEW_REGION, (f"Example Region {number}", None))
        connection.exec_driver_sql("DELETE FROM region")

    migrate(store, MIGRATIONS[:20])

    with store.begin() as connection:
        kept = connection.exec_driver_sql(
            "SELECT seq FROM sqlite_sequence WHERE name = 'region'"
        ).all()
        key = connection.exec_driver_sql(A_NEW_REGION, ("Southland", "NZ-STL")).scalar_one()
    # A table that never gave a key has no highest one, before and after.
    assert [tuple(row) for row in kept] == ([(2,)] if ever else [])
    assert key == ever + 1


@pytest.mark.parametrize("copy", list(IN_THE_PLACE_OF_A_COPY_OF_THE_REGIONS))
def test_the_twentieth_migration_does_not_pass_over_a_table_of_the_name_of_a_copy(
    store: Engine, copy: str
) -> None:
    make, fill, read = IN_THE_PLACE_OF_A_COPY_OF_THE_REGIONS[copy]
    regions_at_version_19(store)
    with store.begin() as connection:
        connection.exec_driver_sql(make)
        connection.exec_driver_sql(fill)
    held = held_at_version_18(store)
    written = as_written(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:20])

    assert str(refusal.value.orig) == f"table {copy} already exists"
    assert schema_version(store) == 19
    assert as_written(store) == written
    assert THE_RULE_OF_THE_NAMES_IN_THE_TABLE in written["region"]
    assert held_at_version_18(store) == held
    with store.connect() as connection:
        assert connection.exec_driver_sql(read).all() == [("kept",)]


# What the twentieth migration makes after it has built the table anew
# and filled it, in the order in which it makes it: how a thing of that
# name is put in its way, and what SQLite then says. An index that goes
# with the table, and a trigger that is on it, is taken away first: the
# migration drops it with the table.
IN_THE_WAY_OF_THE_TWENTIETH = {
    "ix_region_source_id": (
        "DROP INDEX ix_region_source_id",
        "CREATE INDEX ix_region_source_id ON country (name)",
        "index ix_region_source_id already exists",
    ),
    "ix_region_country_id": (
        "SELECT 1",
        "CREATE INDEX ix_region_country_id ON country (name)",
        "index ix_region_country_id already exists",
    ),
    "ix_region_country_id_name": (
        "SELECT 1",
        "CREATE INDEX ix_region_country_id_name ON country (name)",
        "index ix_region_country_id_name already exists",
    ),
    "tr_region_code_of_its_country": (
        "DROP TRIGGER tr_region_code_of_its_country",
        "CREATE TRIGGER tr_region_code_of_its_country AFTER DELETE ON country BEGIN SELECT 1; END",
        "trigger tr_region_code_of_its_country already exists",
    ),
    "tr_region_code_stays_of_its_country": (
        "DROP TRIGGER tr_region_code_stays_of_its_country",
        "CREATE TRIGGER tr_region_code_stays_of_its_country AFTER DELETE ON country "
        "BEGIN SELECT 1; END",
        "trigger tr_region_code_stays_of_its_country already exists",
    ),
}


@pytest.mark.parametrize("name", list(IN_THE_WAY_OF_THE_TWENTIETH))
def test_the_twentieth_migration_that_fails_after_the_table_leaves_the_regions_as_they_were(
    store: Engine, name: str
) -> None:
    # By the time the migration makes the thing, the table of the regions
    # was dropped, made anew and filled, and all of that is taken back
    # with the migration. The last of the five is the last statement of
    # the migration.
    first, then, why = IN_THE_WAY_OF_THE_TWENTIETH[name]
    regions_at_version_19(store)
    with store.begin() as connection:
        connection.exec_driver_sql(first)
        connection.exec_driver_sql(then)
    held = held_at_version_18(store)
    written = as_written(store)
    before = (indexes(store), triggers(store), as_the_triggers_are_written(store))

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:20])

    assert str(refusal.value.orig) == why
    assert schema_version(store) == 19
    assert as_written(store) == written
    assert THE_RULE_OF_THE_NAMES_IN_THE_TABLE in written["region"]
    assert (indexes(store), triggers(store), as_the_triggers_are_written(store)) == before
    assert held_at_version_18(store) == held
    with store.begin() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        # The old rule is in force again, and the next key is the next.
        with pytest.raises(IntegrityError) as one_name_twice:
            connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, ("Maputo", "MZ-MPM"))
        connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, ("Tete", "MZ-T"))
    assert str(one_name_twice.value.orig) == ONE_NAME_TWICE
    assert regions_as_they_are(store)[-1] == (7, 2, "Tete", "MZ-T")


# What the twenty-first migration adds to the statement of the table: the
# column after the country, and three rules after the check of the code.
THE_COLUMN_OF_THE_PARENT = (
    "country_id INTEGER NOT NULL,\n            ",
    "parent_id INTEGER,\n            ",
)
THE_RULES_OF_THE_PARENT = (
    "AND instr(iso_3166_2, char(0)) = 0),\n            ",
    "CONSTRAINT uq_region_id_country_id UNIQUE (id, country_id),\n            "
    "CONSTRAINT fk_region_parent_id_country_id_region\n                "
    "FOREIGN KEY(parent_id, country_id) REFERENCES region (id, country_id),\n            "
    "CONSTRAINT ck_region_parent_id_not_itself CHECK (parent_id != id),\n            ",
)
POINTS_NOWHERE = "FOREIGN KEY constraint failed"
A_PART_OF_ITSELF = "CHECK constraint failed: ck_region_parent_id_not_itself"
# A region of the second country of the store that is a part of another:
# the region it is a part of, its name and its code.
A_PART_IN_THE_SECOND_COUNTRY = (
    "INSERT INTO region (country_id, parent_id, name, iso_3166_2, source_id, source_address, "
    "collected_at, last_verified_at, extraction_method, confidence, verification_status, "
    "created_at, updated_at) VALUES (2, ?, ?, ?, 1, 'https://standards.example/regions.csv', "
    "'2026-11-28T09:00:00.000000+00:00', '2026-11-28T09:00:00.000000+00:00', 'public dataset', "
    "'high', 'official', '2026-11-28T09:00:05.000000+00:00', "
    "'2026-11-28T09:00:05.000000+00:00')"
)


def regions_at_version_20(store: Engine) -> None:
    """Bring a store to version 20 with regions of two countries.

    As at version 19, and one region more that the twentieth migration
    let in: Mozambique has Maputo the city too, with the key 7 and the
    code "MZ-MPM", beside Maputo the province, with the key 5.
    """
    regions_at_version_19(store)
    migrate(store, MIGRATIONS[:20])
    with store.begin() as connection:
        connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, ("Maputo", "MZ-MPM"))


AT_VERSION_20: list[tuple[object, ...]] = [
    (1, 1, "Canterbury", "NZ-CAN"),
    (3, 1, "Otago", "AU-OTA"),
    (5, 2, "Maputo", "MZ-L"),
    (6, 2, "Gaza", None),
    (7, 2, "Maputo", "MZ-MPM"),
]


def regions_and_their_parents(store: Engine) -> list[tuple[object, ...]]:
    """The key, the country, the region it is a part of, the name and the code of every region."""
    with store.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT id, country_id, parent_id, name, iso_3166_2 FROM region ORDER BY id"
        )
        return [tuple(row) for row in found]


def with_no_parent(regions: list[tuple[object, ...]]) -> list[tuple[object, ...]]:
    """The rows of the regions as they are after the migration: a part of no region."""
    return [(*region[:2], None, *region[2:]) for region in regions]


def test_the_twenty_first_migration_gives_the_regions_the_column_and_keeps_the_rest(
    store: Engine,
) -> None:
    regions_at_version_20(store)
    held = held_at_version_18(store)
    before = (tables(store), indexes(store), triggers(store))
    written = as_written(store)
    triggers_written = as_the_triggers_are_written(store)
    assert regions_as_they_are(store) == AT_VERSION_20

    migrate(store, MIGRATIONS[:21])

    assert schema_version(store) == 21
    # The copies the migration works with are gone again. The three
    # indexes that went with the table are there again, and one is new.
    assert len(before[0]) == 7
    assert tables(store) == before[0]
    assert len(before[1]) == 11
    assert indexes(store) == sorted([*before[1], ("ix_region_parent_id", "region")])
    # The two triggers that went with the table are there again, written
    # as they were, and so is every other.
    assert len(before[2]) == 14
    assert triggers(store) == before[2]
    assert as_the_triggers_are_written(store) == triggers_written
    # Every other table and every index that was there is written as it
    # was, and the table of the regions as it was but for the column and
    # its three rules.
    now = as_written(store)
    assert sorted(now) == sorted([*written, "ix_region_parent_id"])
    assert [name for name in written if now[name] != written[name]] == ["region"]
    expected = written["region"]
    for after, added in (THE_COLUMN_OF_THE_PARENT, THE_RULES_OF_THE_PARENT):
        assert expected.count(after) == 1
        assert added not in expected
        expected = expected.replace(after, after + added)
    assert now["region"] == expected
    assert now["ix_region_parent_id"] == "CREATE INDEX ix_region_parent_id ON region (parent_id)"
    # Every region has what it had, its key and its code too: also the
    # one whose code is not of its country, which no migration puts
    # right. Each is a part of no region. And every row a region points
    # to has what it had.
    assert regions_and_their_parents(store) == with_no_parent(AT_VERSION_20)
    held_now = held_at_version_18(store)
    assert held_now["region"] == with_no_parent(held["region"])
    assert {what: rows for what, rows in held_now.items() if what != "region"} == {
        what: rows for what, rows in held.items() if what != "region"
    }
    assert ("region", 7) in held["the highest key of each table"]
    with store.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        kept_by_sqlite = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'region' "
            "AND sql IS NULL ORDER BY name"
        ).all()
        of_the_key_and_the_country = connection.exec_driver_sql(
            "PRAGMA index_info(sqlite_autoindex_region_1)"
        ).all()
        of_the_codes = connection.exec_driver_sql(
            "PRAGMA index_info(sqlite_autoindex_region_2)"
        ).all()
    # SQLite keeps an index for each of the two rules of that kind that
    # are written into the table, in the order in which they are written.
    assert [tuple(row) for row in kept_by_sqlite] == [
        ("sqlite_autoindex_region_1",),
        ("sqlite_autoindex_region_2",),
    ]
    assert [name for _, _, name in of_the_key_and_the_country] == ["id", "country_id"]
    assert [name for _, _, name in of_the_codes] == ["iso_3166_2"]


def test_the_twenty_first_migration_lets_a_region_be_a_part_of_one_that_was_there(
    store: Engine,
) -> None:
    regions_at_version_20(store)
    with pytest.raises(OperationalError) as refusal, store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET parent_id = 5 WHERE id = 7")
    assert str(refusal.value.orig) == "no such column: parent_id"

    migrate(store, MIGRATIONS[:21])

    with store.begin() as connection:
        # The city, which was there, and a region that is new.
        connection.exec_driver_sql("UPDATE region SET parent_id = 5 WHERE id = 7")
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (5, "Matola", None))
    assert regions_and_their_parents(store) == [
        *with_no_parent(AT_VERSION_20)[:4],
        (7, 2, 5, "Maputo", "MZ-MPM"),
        (8, 2, 5, "Matola", None),
    ]


def test_after_the_twenty_first_migration_a_region_is_held_to_the_rules_of_a_part(
    store: Engine,
) -> None:
    regions_at_version_20(store)

    migrate(store, MIGRATIONS[:21])

    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET parent_id = 5 WHERE id = 7")
    before = regions_and_their_parents(store)
    refusals = [
        # A region that is not there, one of another country, itself.
        ("UPDATE region SET parent_id = 99 WHERE id = 6", (), POINTS_NOWHERE),
        ("UPDATE region SET parent_id = 1 WHERE id = 6", (), POINTS_NOWHERE),
        ("UPDATE region SET parent_id = 6 WHERE id = 6", (), A_PART_OF_ITSELF),
        (A_PART_IN_THE_SECOND_COUNTRY, (99, "Matola", None), POINTS_NOWHERE),
        (A_PART_IN_THE_SECOND_COUNTRY, (1, "Matola", None), POINTS_NOWHERE),
        (A_PART_IN_THE_SECOND_COUNTRY, (8, "Matola", None), A_PART_OF_ITSELF),
        # A region that has a part stays, with its key and in its country.
        ("DELETE FROM region WHERE id = 5", (), POINTS_NOWHERE),
        ("UPDATE region SET id = 50 WHERE id = 5", (), POINTS_NOWHERE),
        ("UPDATE region SET country_id = 1, iso_3166_2 = NULL WHERE id = 5", (), POINTS_NOWHERE),
        ("UPDATE region SET country_id = 1, iso_3166_2 = NULL WHERE id = 7", (), POINTS_NOWHERE),
    ]
    said = []
    for statement, given, _ in refusals:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement, given)
        said.append(str(refusal.value.orig))

    assert said == [why for _, _, why in refusals]
    assert regions_and_their_parents(store) == before
    with store.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_after_the_twenty_first_migration_the_regions_are_held_to_their_other_rules_again(
    store: Engine,
) -> None:
    regions_at_version_20(store)

    migrate(store, MIGRATIONS[:21])

    before = regions_and_their_parents(store)
    statements = [
        "UPDATE region SET country_id = 9 WHERE id = 5",
        "UPDATE region SET source_id = 9 WHERE id = 5",
        "DELETE FROM country WHERE id = 2",
        "DELETE FROM source WHERE id = 3",
        "UPDATE region SET name = ' ' WHERE id = 5",
        "UPDATE region SET iso_3166_2 = 'mz-l' WHERE id = 5",
        "UPDATE region SET iso_3166_2 = 'MZ-L' WHERE id = 6",
        "UPDATE region SET iso_3166_2 = 'NZ-GAZ' WHERE id = 6",
        "UPDATE region SET name = 'Otakou' WHERE id = 3",
        "UPDATE country SET alpha_2 = 'MX' WHERE id = 2",
        "INSERT INTO region SELECT NULL, country_id, NULL, name, NULL, source_id, source_address, "
        "collected_at, published_on, last_verified_at, extraction_method, confidence, "
        "verification_status, created_at, updated_at FROM region WHERE id = 6",
        "UPDATE region SET iso_3166_2 = NULL WHERE id = 5 OR id = 7",
    ]
    said = []
    for statement in statements:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement)
        said.append(str(refusal.value.orig))

    assert said == [
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "FOREIGN KEY constraint failed",
        "CHECK constraint failed: ck_region_name_not_empty",
        "CHECK constraint failed: ck_region_iso_3166_2_form",
        "UNIQUE constraint failed: region.iso_3166_2",
        A_CODE_BEGINS_WITH_ITS_COUNTRY,
        A_CODE_BEGINS_WITH_ITS_COUNTRY,
        THE_CODES_BEGIN_WITH_THEIR_COUNTRY,
        ONE_NAME_TWICE,
        ONE_NAME_TWICE,
    ]
    assert regions_and_their_parents(store) == before
    # The two regions of one name that each say a code are both there
    # still, and the region whose code is not of its country can still be
    # put right.
    assert [region for region in before if region[3] == "Maputo"] == [
        (5, 2, None, "Maputo", "MZ-L"),
        (7, 2, None, "Maputo", "MZ-MPM"),
    ]
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET iso_3166_2 = 'NZ-OTA' WHERE id = 3")
    assert regions_and_their_parents(store)[1] == (3, 1, None, "Otago", "NZ-OTA")


def test_after_the_twenty_first_migration_the_key_of_a_deleted_region_is_not_given_again(
    store: Engine,
) -> None:
    regions_at_version_20(store)
    with store.begin() as connection:
        connection.exec_driver_sql("DELETE FROM region WHERE id = 7")

    migrate(store, MIGRATIONS[:21])

    with store.begin() as connection:
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (5, "Matola", None))
        highest = connection.exec_driver_sql(
            "SELECT name, seq FROM sqlite_sequence WHERE name = 'region'"
        ).all()
    # The seventh region was deleted before the migration. Its key stays its own.
    assert regions_and_their_parents(store)[-1] == (8, 2, 5, "Matola", None)
    assert [tuple(row) for row in highest] == [("region", 8)]


@pytest.mark.parametrize("ever", [0, 2], ids=["never a region", "two regions, both deleted"])
def test_the_twenty_first_migration_keeps_the_highest_key_of_a_table_without_regions(
    store: Engine, ever: int
) -> None:
    migrate(store, MIGRATIONS[:16])
    sources_with_a_country_and_what_points_to_them(store)
    migrate(store, MIGRATIONS[:20])
    with store.begin() as connection:
        for number in range(ever):
            connection.exec_driver_sql(A_NEW_REGION, (f"Example Region {number}", None))
        connection.exec_driver_sql("DELETE FROM region")

    migrate(store, MIGRATIONS[:21])

    with store.begin() as connection:
        kept = connection.exec_driver_sql(
            "SELECT seq FROM sqlite_sequence WHERE name = 'region'"
        ).all()
        key = connection.exec_driver_sql(A_NEW_REGION, ("Southland", "NZ-STL")).scalar_one()
    # A table that never gave a key has no highest one, before and after.
    assert [tuple(row) for row in kept] == ([(2,)] if ever else [])
    assert key == ever + 1


@pytest.mark.parametrize("copy", list(IN_THE_PLACE_OF_A_COPY_OF_THE_REGIONS))
def test_the_twenty_first_migration_does_not_pass_over_a_table_of_the_name_of_a_copy(
    store: Engine, copy: str
) -> None:
    make, fill, read = IN_THE_PLACE_OF_A_COPY_OF_THE_REGIONS[copy]
    regions_at_version_20(store)
    with store.begin() as connection:
        connection.exec_driver_sql(make)
        connection.exec_driver_sql(fill)
    held = held_at_version_18(store)
    written = as_written(store)

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:21])

    assert str(refusal.value.orig) == f"table {copy} already exists"
    assert schema_version(store) == 20
    assert as_written(store) == written
    assert "parent_id" not in written["region"]
    assert held_at_version_18(store) == held
    with store.connect() as connection:
        assert connection.exec_driver_sql(read).all() == [("kept",)]


# What the twenty-first migration makes after it has built the table anew
# and filled it, in the order in which it makes it: how a thing of that
# name is put in its way, and what SQLite then says. An index that goes
# with the table, and a trigger that is on it, is taken away first: the
# migration drops it with the table.
IN_THE_WAY_OF_THE_TWENTY_FIRST = {
    "ix_region_source_id": (
        "DROP INDEX ix_region_source_id",
        "CREATE INDEX ix_region_source_id ON country (name)",
        "index ix_region_source_id already exists",
    ),
    "ix_region_country_id": (
        "DROP INDEX ix_region_country_id",
        "CREATE INDEX ix_region_country_id ON country (name)",
        "index ix_region_country_id already exists",
    ),
    "ix_region_parent_id": (
        "SELECT 1",
        "CREATE INDEX ix_region_parent_id ON country (name)",
        "index ix_region_parent_id already exists",
    ),
    "ix_region_country_id_name": (
        "DROP INDEX ix_region_country_id_name",
        "CREATE INDEX ix_region_country_id_name ON country (name)",
        "index ix_region_country_id_name already exists",
    ),
    "tr_region_code_of_its_country": (
        "DROP TRIGGER tr_region_code_of_its_country",
        "CREATE TRIGGER tr_region_code_of_its_country AFTER DELETE ON country BEGIN SELECT 1; END",
        "trigger tr_region_code_of_its_country already exists",
    ),
    "tr_region_code_stays_of_its_country": (
        "DROP TRIGGER tr_region_code_stays_of_its_country",
        "CREATE TRIGGER tr_region_code_stays_of_its_country AFTER DELETE ON country "
        "BEGIN SELECT 1; END",
        "trigger tr_region_code_stays_of_its_country already exists",
    ),
}


@pytest.mark.parametrize("name", list(IN_THE_WAY_OF_THE_TWENTY_FIRST))
def test_the_twenty_first_migration_that_fails_after_the_table_leaves_the_regions_as_they_were(
    store: Engine, name: str
) -> None:
    # By the time the migration makes the thing, the table of the regions
    # was dropped, made anew and filled, and all of that is taken back
    # with the migration. The last of the six is the last statement of
    # the migration.
    first, then, why = IN_THE_WAY_OF_THE_TWENTY_FIRST[name]
    regions_at_version_20(store)
    with store.begin() as connection:
        connection.exec_driver_sql(first)
        connection.exec_driver_sql(then)
    held = held_at_version_18(store)
    written = as_written(store)
    before = (indexes(store), triggers(store), as_the_triggers_are_written(store))

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:21])

    assert str(refusal.value.orig) == why
    assert schema_version(store) == 20
    assert as_written(store) == written
    assert "parent_id" not in written["region"]
    assert (indexes(store), triggers(store), as_the_triggers_are_written(store)) == before
    assert held_at_version_18(store) == held
    with store.begin() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        # The table has no such column still, and the next key is the next.
        with pytest.raises(OperationalError) as no_column:
            connection.exec_driver_sql("UPDATE region SET parent_id = 5 WHERE id = 7")
        connection.exec_driver_sql(A_REGION_OF_THE_SECOND_COUNTRY, ("Tete", "MZ-T"))
    assert str(no_column.value.orig) == "no such column: parent_id"
    assert regions_as_they_are(store)[-1] == (8, 2, "Tete", "MZ-T")


# The rule of the names as the twentieth migration made it, and the two
# rules the twenty-second makes of it.
THE_RULE_OF_THE_NAMES_AT_VERSION_20 = (
    "CREATE UNIQUE INDEX ix_region_country_id_name ON region (country_id, name) "
    "WHERE iso_3166_2 IS NULL"
)
THE_RULE_OF_THE_NAMES_OF_THE_PARTS_OF_NONE = (
    "CREATE UNIQUE INDEX ix_region_country_id_name ON region (country_id, name) "
    "WHERE iso_3166_2 IS NULL AND parent_id IS NULL"
)
THE_RULE_OF_THE_NAMES_OF_THE_PARTS_OF_A_REGION = (
    "CREATE UNIQUE INDEX ix_region_parent_id_name ON region (parent_id, name) "
    "WHERE iso_3166_2 IS NULL AND parent_id IS NOT NULL"
)
ONE_NAME_TWICE_IN_A_REGION = "UNIQUE constraint failed: region.parent_id, region.name"


def regions_at_version_21(store: Engine) -> None:
    """Bring a store to version 21 with regions that are parts of others.

    As at version 20, and then: Maputo the city, with the key 7, is a
    part of Maputo the province, with the key 5. The province has one
    part more, Matola, with the key 8 and no code, and Gaza, with the
    key 6, has a part with the key 9 and no code, Xai-Xai.
    """
    regions_at_version_20(store)
    migrate(store, MIGRATIONS[:21])
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET parent_id = 5 WHERE id = 7")
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (5, "Matola", None))
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (6, "Xai-Xai", None))


AT_VERSION_21: list[tuple[object, ...]] = [
    (1, 1, None, "Canterbury", "NZ-CAN"),
    (3, 1, None, "Otago", "AU-OTA"),
    (5, 2, None, "Maputo", "MZ-L"),
    (6, 2, None, "Gaza", None),
    (7, 2, 5, "Maputo", "MZ-MPM"),
    (8, 2, 5, "Matola", None),
    (9, 2, 6, "Xai-Xai", None),
]


def how_the_indexes_of_the_regions_are(store: Engine) -> list[tuple[object, ...]]:
    """Each index a migration made on the regions: its name, whether it holds
    a thing to be there once, and whether it is over some of the regions only."""
    with store.connect() as connection:
        found = connection.exec_driver_sql("PRAGMA index_list(region)").all()
    return sorted(
        (str(name), unique, partial) for _, name, unique, origin, partial in found if origin == "c"
    )


def test_the_twenty_second_migration_makes_two_rules_of_the_rule_of_the_names_and_keeps_the_rest(
    store: Engine,
) -> None:
    regions_at_version_21(store)
    held = held_at_version_18(store)
    before = (tables(store), indexes(store), triggers(store))
    written = as_written(store)
    triggers_written = as_the_triggers_are_written(store)
    assert regions_and_their_parents(store) == AT_VERSION_21
    assert written["ix_region_country_id_name"] == THE_RULE_OF_THE_NAMES_AT_VERSION_20

    migrate(store, MIGRATIONS[:22])

    assert schema_version(store) == 22
    # No table is made or taken away, and no trigger. One index is new.
    assert len(before[0]) == 7
    assert tables(store) == before[0]
    assert len(before[1]) == 12
    assert indexes(store) == sorted([*before[1], ("ix_region_parent_id_name", "region")])
    assert len(before[2]) == 14
    assert triggers(store) == before[2]
    assert as_the_triggers_are_written(store) == triggers_written
    # Every table, the one of the regions too, and every other index is
    # written as it was.
    now = as_written(store)
    assert sorted(now) == sorted([*written, "ix_region_parent_id_name"])
    assert [name for name in written if now[name] != written[name]] == ["ix_region_country_id_name"]
    assert now["ix_region_country_id_name"] == THE_RULE_OF_THE_NAMES_OF_THE_PARTS_OF_NONE
    assert now["ix_region_parent_id_name"] == THE_RULE_OF_THE_NAMES_OF_THE_PARTS_OF_A_REGION
    assert how_the_indexes_of_the_regions_are(store) == [
        ("ix_region_country_id", 0, 0),
        ("ix_region_country_id_name", 1, 1),
        ("ix_region_parent_id", 0, 0),
        ("ix_region_parent_id_name", 1, 1),
        ("ix_region_source_id", 0, 0),
    ]
    # Every region has what it had, the region it is a part of too, and
    # every row a region points to has what it had. The highest key the
    # table gave is the same.
    assert regions_and_their_parents(store) == AT_VERSION_21
    assert held_at_version_18(store) == held
    assert ("region", 9) in held["the highest key of each table"]
    with store.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


# A region of the second country of the store that says no code: what
# it is a part of, and its name.
NAMES_THE_OLD_RULE_REFUSED: list[tuple[int | None, str]] = [
    # The name of a part of the province, for a part of Gaza.
    (6, "Matola"),
    # The name of a part of Gaza, for a part of the province.
    (5, "Xai-Xai"),
    # The name of a region that is a part of none, for a part of another
    # region and for a part of that region itself.
    (5, "Gaza"),
    (6, "Gaza"),
    # The name of a part, for a region that is a part of none.
    (None, "Matola"),
]


def test_the_twenty_second_migration_lets_in_what_the_old_rule_of_the_names_refused(
    store: Engine,
) -> None:
    regions_at_version_21(store)
    said = []
    for part_of, name in NAMES_THE_OLD_RULE_REFUSED:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (part_of, name, None))
        said.append(str(refusal.value.orig))
    assert said == [ONE_NAME_TWICE] * 5
    assert regions_and_their_parents(store) == AT_VERSION_21

    migrate(store, MIGRATIONS[:22])

    with store.begin() as connection:
        for part_of, name in NAMES_THE_OLD_RULE_REFUSED:
            connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (part_of, name, None))
    # What was refused before the migration was taken back with its key.
    assert regions_and_their_parents(store) == [
        *AT_VERSION_21,
        (10, 2, 6, "Matola", None),
        (11, 2, 5, "Xai-Xai", None),
        (12, 2, 5, "Gaza", None),
        (13, 2, 6, "Gaza", None),
        (14, 2, None, "Matola", None),
    ]


def test_after_the_twenty_second_migration_a_name_is_there_once_where_it_is(
    store: Engine,
) -> None:
    regions_at_version_21(store)

    migrate(store, MIGRATIONS[:22])

    with store.begin() as connection:
        # The tenth region: a second Matola, a part of Gaza.
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (6, "Matola", None))
    before = regions_and_their_parents(store)
    refusals = [
        # Among the parts of one region: a new region, a region that gets
        # the name, and a region that becomes a part of that region.
        (A_PART_IN_THE_SECOND_COUNTRY, (5, "Matola", None), ONE_NAME_TWICE_IN_A_REGION),
        (A_PART_IN_THE_SECOND_COUNTRY, (6, "Xai-Xai", None), ONE_NAME_TWICE_IN_A_REGION),
        ("UPDATE region SET name = 'Matola' WHERE id = 9", (), ONE_NAME_TWICE_IN_A_REGION),
        ("UPDATE region SET parent_id = 5 WHERE id = 10", (), ONE_NAME_TWICE_IN_A_REGION),
        # Among the parts of none: a new region, a region that gets the
        # name, and a part that becomes a part of none.
        (A_PART_IN_THE_SECOND_COUNTRY, (None, "Gaza", None), ONE_NAME_TWICE),
        ("UPDATE region SET name = 'Gaza', iso_3166_2 = NULL WHERE id = 5", (), ONE_NAME_TWICE),
        ("UPDATE region SET name = 'Gaza', parent_id = NULL WHERE id = 9", (), ONE_NAME_TWICE),
    ]
    said = []
    for statement, given, _ in refusals:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement, given)
        said.append(str(refusal.value.orig))

    assert said == [why for _, _, why in refusals]
    assert regions_and_their_parents(store) == before
    # A region that says a code is held to neither rule: the city can
    # have the name of a part of the province it is a part of, and the
    # province the name of a region that is a part of none.
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET name = 'Matola' WHERE id = 7")
        connection.exec_driver_sql("UPDATE region SET name = 'Gaza' WHERE id = 5")
    assert [region for region in regions_and_their_parents(store) if region[0] in (5, 7)] == [
        (5, 2, None, "Gaza", "MZ-L"),
        (7, 2, 5, "Matola", "MZ-MPM"),
    ]


def test_after_the_twenty_second_migration_the_regions_are_held_to_their_other_rules_still(
    store: Engine,
) -> None:
    regions_at_version_21(store)

    migrate(store, MIGRATIONS[:22])

    before = regions_and_their_parents(store)
    refusals = [
        ("UPDATE region SET parent_id = 99 WHERE id = 6", POINTS_NOWHERE),
        ("UPDATE region SET parent_id = 1 WHERE id = 6", POINTS_NOWHERE),
        ("UPDATE region SET parent_id = 6 WHERE id = 6", A_PART_OF_ITSELF),
        ("DELETE FROM region WHERE id = 5", POINTS_NOWHERE),
        ("DELETE FROM country WHERE id = 2", POINTS_NOWHERE),
        (
            "UPDATE region SET name = ' ' WHERE id = 8",
            "CHECK constraint failed: ck_region_name_not_empty",
        ),
        (
            "UPDATE region SET iso_3166_2 = 'MZ-L' WHERE id = 8",
            "UNIQUE constraint failed: region.iso_3166_2",
        ),
        ("UPDATE region SET iso_3166_2 = 'NZ-MAT' WHERE id = 8", A_CODE_BEGINS_WITH_ITS_COUNTRY),
    ]
    said = []
    for statement, _ in refusals:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement)
        said.append(str(refusal.value.orig))

    assert said == [why for _, why in refusals]
    assert regions_and_their_parents(store) == before


# What can be in the way of the twenty-second migration: how the store is
# changed by hand before it, and what SQLite then says.
IN_THE_WAY_OF_THE_TWENTY_SECOND = {
    "the index of the old rule is not there": (
        "DROP INDEX ix_region_country_id_name",
        "no such index: ix_region_country_id_name",
    ),
    "an index of the name of the second rule is there": (
        "CREATE INDEX ix_region_parent_id_name ON country (name)",
        "index ix_region_parent_id_name already exists",
    ),
}


@pytest.mark.parametrize("what", list(IN_THE_WAY_OF_THE_TWENTY_SECOND))
def test_the_twenty_second_migration_that_fails_leaves_the_rule_of_the_names_as_it_was(
    store: Engine, what: str
) -> None:
    # The second of the two fails at the last statement of the migration,
    # when the index of the old rule was taken away and made anew: that
    # is taken back with the migration.
    by_hand, why = IN_THE_WAY_OF_THE_TWENTY_SECOND[what]
    regions_at_version_21(store)
    with store.begin() as connection:
        connection.exec_driver_sql(by_hand)
    held = held_at_version_18(store)
    written = as_written(store)
    before = (indexes(store), triggers(store), as_the_triggers_are_written(store))

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:22])

    assert str(refusal.value.orig) == why
    assert schema_version(store) == 21
    assert as_written(store) == written
    assert (indexes(store), triggers(store), as_the_triggers_are_written(store)) == before
    assert held_at_version_18(store) == held
    assert regions_and_their_parents(store) == AT_VERSION_21


def test_the_twenty_second_migration_takes_no_region_for_one_too_many(store: Engine) -> None:
    # The old rule asked for more than the two new ones together: what it
    # let in, they let in. Here the store holds as many regions of one
    # name as the old rule allowed: one that says no code, and one that
    # says a code beside it wherever a region can be.
    regions_at_version_21(store)
    with store.begin() as connection:
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (None, "Matola", "MZ-MA1"))
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (5, "Matola", "MZ-MA2"))
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (6, "Matola", "MZ-MA3"))
    before = regions_and_their_parents(store)
    assert len(before) == 10

    assert migrate(store, MIGRATIONS[:22]) == [22]

    assert regions_and_their_parents(store) == before


A_RING_OF_REGIONS = "A region (region) is not a part of itself through other regions."
# The question both triggers of the twenty-third migration ask, with the
# white space of the migration made one space.
ABOVE_A_REGION = (
    "EXISTS ( WITH RECURSIVE above(id) AS ( SELECT NEW.parent_id UNION "
    "SELECT region.parent_id FROM region JOIN above ON region.id = above.id "
    "WHERE region.parent_id IS NOT NULL) SELECT 1 FROM above WHERE id = NEW.id)"
)
THE_TRIGGERS_OF_THE_TWENTY_THIRD = {
    "tr_region_parent_id_not_below_itself": (
        "CREATE TRIGGER tr_region_parent_id_not_below_itself AFTER INSERT ON region "
        f"WHEN NEW.parent_id IS NOT NULL AND {ABOVE_A_REGION} "
        f"BEGIN SELECT RAISE(ABORT, '{A_RING_OF_REGIONS}'); END"
    ),
    "tr_region_parent_id_stays_not_below_itself": (
        "CREATE TRIGGER tr_region_parent_id_stays_not_below_itself AFTER UPDATE ON region "
        "WHEN NEW.parent_id IS NOT NULL "
        "AND (NEW.parent_id IS NOT OLD.parent_id OR NEW.id != OLD.id) "
        f"AND {ABOVE_A_REGION} "
        f"BEGIN SELECT RAISE(ABORT, '{A_RING_OF_REGIONS}'); END"
    ),
}


def regions_at_version_22(store: Engine) -> None:
    """Bring a store to version 22 with regions three deep.

    As at version 21, and one region more: Machava, with the key 10 and
    no code, is a part of Matola, which is a part of Maputo the province.
    """
    regions_at_version_21(store)
    migrate(store, MIGRATIONS[:22])
    with store.begin() as connection:
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (8, "Machava", None))


AT_VERSION_22: list[tuple[object, ...]] = [*AT_VERSION_21, (10, 2, 8, "Machava", None)]
# Statements that close a ring in the store at version 22: the province
# made a part of the city that is a part of it, and of Machava, two
# below it; Machava given the key of the province, two above it; and
# the province put in its own place as a part of Matola.
CLOSES_A_RING = [
    "UPDATE region SET parent_id = 7 WHERE id = 5",
    "UPDATE region SET parent_id = 10 WHERE id = 5",
    "UPDATE OR REPLACE region SET id = 5 WHERE id = 10",
    "UPDATE OR REPLACE region SET rowid = 5 WHERE id = 10",
    "INSERT OR REPLACE INTO region SELECT id, country_id, 8, name, iso_3166_2, source_id, "
    "source_address, collected_at, published_on, last_verified_at, extraction_method, "
    "confidence, verification_status, created_at, updated_at FROM region WHERE id = 5",
]


def test_the_twenty_third_migration_makes_two_triggers_and_keeps_what_there_was(
    store: Engine,
) -> None:
    regions_at_version_22(store)
    held = held_at_version_18(store)
    before = (tables(store), indexes(store), triggers(store))
    written = as_written(store)
    triggers_written = as_the_triggers_are_written(store)
    assert regions_and_their_parents(store) == AT_VERSION_22

    migrate(store, MIGRATIONS[:23])

    assert schema_version(store) == 23
    # No table and no index is made, taken away or written otherwise.
    assert len(before[0]) == 7
    assert tables(store) == before[0]
    assert len(before[1]) == 13
    assert indexes(store) == before[1]
    assert as_written(store) == written
    # Two triggers are new, both on the regions, and the fourteen that
    # were there are written as they were.
    assert len(before[2]) == 14
    assert triggers(store) == sorted(
        [*before[2], *((name, "region") for name in THE_TRIGGERS_OF_THE_TWENTY_THIRD)]
    )
    now = as_the_triggers_are_written(store)
    assert {name: now[name] for name in triggers_written} == triggers_written
    assert {
        name: " ".join(now[name].split()) for name in THE_TRIGGERS_OF_THE_TWENTY_THIRD
    } == THE_TRIGGERS_OF_THE_TWENTY_THIRD
    # Every region has what it had, and every row a region points to.
    assert regions_and_their_parents(store) == AT_VERSION_22
    assert held_at_version_18(store) == held
    with store.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


@pytest.mark.parametrize("statement", CLOSES_A_RING)
def test_before_the_twenty_third_migration_the_store_took_a_ring_that_it_refuses_after(
    store: Engine, statement: str
) -> None:
    regions_at_version_22(store)
    # Taken, and seen to close a ring: the province has a region above
    # it then. It is taken back before the migration.
    with store.connect() as connection:
        connection.exec_driver_sql(statement)
        above = connection.exec_driver_sql("SELECT parent_id FROM region WHERE id = 5").scalar_one()
        connection.rollback()
    assert above is not None
    assert regions_and_their_parents(store) == AT_VERSION_22

    migrate(store, MIGRATIONS[:23])

    with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
        connection.exec_driver_sql(statement)
    assert str(refusal.value.orig) == A_RING_OF_REGIONS
    assert regions_and_their_parents(store) == AT_VERSION_22


def test_after_the_twenty_third_migration_what_closes_no_ring_is_taken_as_before(
    store: Engine,
) -> None:
    regions_at_version_22(store)

    migrate(store, MIGRATIONS[:23])

    with store.begin() as connection:
        # Machava a part of the province itself, a new part below it, the
        # name of a region that has parts and is a part, and Matola a
        # part of none and of the province again.
        connection.exec_driver_sql("UPDATE region SET parent_id = 5 WHERE id = 10")
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (10, "Machava Sede", None))
        connection.exec_driver_sql("UPDATE region SET name = 'Cidade da Matola' WHERE id = 8")
        connection.exec_driver_sql("UPDATE region SET parent_id = NULL WHERE id = 8")
        connection.exec_driver_sql("UPDATE region SET parent_id = 5 WHERE id = 8")
    assert regions_and_their_parents(store)[5:] == [
        (8, 2, 5, "Cidade da Matola", None),
        (9, 2, 6, "Xai-Xai", None),
        (10, 2, 5, "Machava", None),
        (11, 2, 10, "Machava Sede", None),
    ]
    # The other rules of a part hold as before, each in its own words.
    refusals = [
        ("UPDATE region SET parent_id = 99 WHERE id = 6", POINTS_NOWHERE),
        ("UPDATE region SET parent_id = 1 WHERE id = 6", POINTS_NOWHERE),
        ("UPDATE region SET parent_id = 6 WHERE id = 6", A_PART_OF_ITSELF),
        ("DELETE FROM region WHERE id = 5", POINTS_NOWHERE),
        ("UPDATE region SET name = 'Machava' WHERE id = 8", ONE_NAME_TWICE_IN_A_REGION),
    ]
    said = []
    for statement, _ in refusals:
        with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
            connection.exec_driver_sql(statement)
        said.append(str(refusal.value.orig))
    assert said == [why for _, why in refusals]


@pytest.mark.parametrize(
    ("undone", "then"),
    [
        ("UPDATE region SET parent_id = NULL WHERE id = 5", (5, 2, None, "Maputo", "MZ-L")),
        ("UPDATE region SET parent_id = 6 WHERE id = 5", (5, 2, 6, "Maputo", "MZ-L")),
    ],
    ids=["made a part of none", "made a part of a region outside the ring"],
)
def test_the_twenty_third_migration_leaves_a_ring_that_was_there_until_it_is_undone(
    store: Engine, undone: str, then: tuple[object, ...]
) -> None:
    # The province and the city, each a part of the other: nothing
    # refused that before the migration, and the migration cannot know
    # which of the two names the wrong region.
    regions_at_version_22(store)
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET parent_id = 7 WHERE id = 5")
    in_a_ring = regions_and_their_parents(store)
    assert in_a_ring[2] == (5, 2, 7, "Maputo", "MZ-L")
    assert in_a_ring[4] == (7, 2, 5, "Maputo", "MZ-MPM")

    assert migrate(store, MIGRATIONS[:23]) == [23]

    assert regions_and_their_parents(store) == in_a_ring
    with store.begin() as connection:
        # A region of the ring is changed in another way, a region below
        # the ring is changed and moved within it, and a new one is
        # stored there: the question ends where it has been before.
        connection.exec_driver_sql("UPDATE region SET name = 'Maputo Cidade' WHERE id = 7")
        connection.exec_driver_sql("UPDATE region SET parent_id = 7 WHERE id = 8")
        connection.exec_driver_sql(A_PART_IN_THE_SECOND_COUNTRY, (10, "Machava Sede", None))
    # A region of the ring cannot be given another place in it or below it.
    with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET parent_id = 10 WHERE id = 5")
    assert str(refusal.value.orig) == A_RING_OF_REGIONS
    # The ring is undone by making one of its regions a part of none or
    # of a region outside it, and cannot be closed again.
    with store.begin() as connection:
        connection.exec_driver_sql(undone)
    with pytest.raises(IntegrityError) as refusal, store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET parent_id = 7 WHERE id = 5")
    assert str(refusal.value.orig) == A_RING_OF_REGIONS
    assert regions_and_their_parents(store)[2:] == [
        then,
        (6, 2, None, "Gaza", None),
        (7, 2, 5, "Maputo Cidade", "MZ-MPM"),
        (8, 2, 7, "Matola", None),
        (9, 2, 6, "Xai-Xai", None),
        (10, 2, 8, "Machava", None),
        (11, 2, 10, "Machava Sede", None),
    ]


@pytest.mark.parametrize("name", list(THE_TRIGGERS_OF_THE_TWENTY_THIRD))
def test_the_twenty_third_migration_fails_where_a_trigger_of_its_name_is_there(
    store: Engine, name: str
) -> None:
    # The second of the two is made by the last statement of the
    # migration: the first, made by then, is taken back with it.
    regions_at_version_22(store)
    with store.begin() as connection:
        connection.exec_driver_sql(
            f"CREATE TRIGGER {name} AFTER DELETE ON country BEGIN SELECT 1; END"
        )
    held = held_at_version_18(store)
    before = (as_written(store), triggers(store), as_the_triggers_are_written(store))

    with pytest.raises(OperationalError) as refusal:
        migrate(store, MIGRATIONS[:23])

    assert str(refusal.value.orig) == f"trigger {name} already exists"
    assert schema_version(store) == 22
    assert (as_written(store), triggers(store), as_the_triggers_are_written(store)) == before
    assert len(before[1]) == 15
    assert held_at_version_18(store) == held
    # A ring is taken still.
    with store.begin() as connection:
        connection.exec_driver_sql("UPDATE region SET parent_id = 7 WHERE id = 5")
    assert regions_and_their_parents(store)[2] == (5, 2, 7, "Maputo", "MZ-L")
