"""The history of the store's schema: every migration, oldest first.

A migration is a function that is given a connection and changes the
schema with it. ``MIGRATIONS`` is the list of them all, and the place of a
migration in that list is its number (:mod:`motosphere.db.migrations`
gives a store those it lacks).

- The list only ever grows at its end. A migration that has been merged is
  not changed, moved or taken out, because stores and snapshots at its
  version exist. A mistake in one is put right by a new one.
- A migration is plain SQL, written out here. It names no model, no list
  and no type of the store's code, and this module imports nothing of
  MotoSphere's: so a migration builds tomorrow what it builds today,
  whatever becomes of the code. What two migrations both need, each
  writes out for itself.
- A migration writes a table as its model makes it, and one test holds
  the two together (``DATABASE.md``, "The models and the migrations
  agree").
- A migration does not commit. ``migrate`` does, with the store's new
  version.
"""

from collections.abc import Callable

from sqlalchemy import Connection

__all__ = [
    "MIGRATIONS",
    "hold_one_doubt_to_one_review_item",
    "hold_the_code_of_a_region_to_its_country",
    "hold_the_key_of_a_review_item_to_1_or_more",
    "hold_the_key_of_a_review_item_under_every_name",
    "index_the_record_changes",
    "index_the_runs_of_a_source",
    "keep_a_decided_review_item_from_being_replaced",
    "keep_the_decision_of_a_review_item",
    "let_a_region_say_its_code",
    "let_a_source_be_a_reference_list",
    "let_a_source_say_its_country",
    "let_regions_with_codes_share_a_name",
    "let_the_record_changes_only_be_added_to",
    "make_the_collection_runs",
    "make_the_countries",
    "make_the_record_changes",
    "make_the_regions",
    "make_the_review_items",
    "make_the_source_offers",
    "make_the_sources",
]


def make_the_sources(connection: Connection) -> None:
    """1: the table of the information sources, ``source`` (DAT-006)."""
    white_space = (
        "char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, "
        "8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)"
    )

    def not_empty(column: str) -> str:
        return (
            f"CONSTRAINT ck_source_{column}_not_empty CHECK (trim({column}, {white_space}) != '')"
        )

    def web_address(column: str) -> str:
        return (
            f"CONSTRAINT ck_source_{column}_web_address CHECK ("
            f"(({column} GLOB '[Hh][Tt][Tt][Pp][Ss]://[^/?#]*')"
            f" OR ({column} GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*'))"
            f" AND NOT ({column} GLOB '*[' || {white_space} || ']*')"
            f" AND instr({column}, char(0)) = 0)"
        )

    connection.exec_driver_sql(
        f"""
        CREATE TABLE source (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            website TEXT NOT NULL,
            category TEXT NOT NULL,
            collection_method TEXT NOT NULL,
            scan_every_hours INTEGER,
            terms_address TEXT,
            licence TEXT,
            usage_restrictions TEXT,
            terms_read_at TEXT,
            switched_on INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT ck_source_scan_every_hours_positive CHECK (scan_every_hours > 0),
            CONSTRAINT ck_source_switched_on_terms_read
                CHECK (switched_on = 0 OR terms_read_at IS NOT NULL),
            CONSTRAINT uq_source_name UNIQUE (name),
            {not_empty("name")},
            {web_address("website")},
            CONSTRAINT ck_source_category_one_of CHECK (category IN (
                'governing body', 'championship', 'organiser', 'promoter', 'track', 'club',
                'regional organisation', 'results database', 'news publication',
                'community website', 'social media page', 'historical archive'
            )),
            CONSTRAINT ck_source_collection_method_one_of CHECK (collection_method IN (
                'official api', 'structured feed', 'rss feed', 'public dataset',
                'html extraction', 'structured document', 'json endpoint', 'sitemap discovery',
                'search engine discovery', 'human submission'
            )),
            {web_address("terms_address")},
            {not_empty("licence")},
            {not_empty("usage_restrictions")},
            CONSTRAINT ck_source_switched_on_yes_or_no CHECK (switched_on IN (0, 1))
        ) STRICT
        """
    )


def make_the_source_offers(connection: Connection) -> None:
    """2: the table of what the sources offer, ``source_offer`` (DAT-040)."""
    connection.exec_driver_sql(
        """
        CREATE TABLE source_offer (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            information_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT uq_source_offer_source_id_information_type
                UNIQUE (source_id, information_type),
            CONSTRAINT fk_source_offer_source_id_source
                FOREIGN KEY(source_id) REFERENCES source (id),
            CONSTRAINT ck_source_offer_information_type_one_of CHECK (information_type IN (
                'tracks', 'events', 'championships', 'results', 'standings', 'riders', 'teams',
                'news', 'reference data'
            ))
        ) STRICT
        """
    )


def make_the_collection_runs(connection: Connection) -> None:
    """3: the table of the collection runs, ``collection_run`` (DAT-007)."""
    connection.exec_driver_sql(
        """
        CREATE TABLE collection_run (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            outcome TEXT NOT NULL,
            records_seen INTEGER NOT NULL,
            records_added INTEGER NOT NULL,
            records_changed INTEGER NOT NULL,
            records_unchanged INTEGER NOT NULL,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT ck_collection_run_ended_at_not_before_started_at
                CHECK (ended_at >= started_at),
            CONSTRAINT ck_collection_run_ended_at_when_succeeded_or_failed
                CHECK ((ended_at IS NULL) = (outcome IN ('running', 'interrupted'))),
            CONSTRAINT ck_collection_run_error_when_failed
                CHECK ((error IS NULL) = (outcome != 'failed')),
            CONSTRAINT ck_collection_run_records_seen_not_negative CHECK (records_seen >= 0),
            CONSTRAINT ck_collection_run_records_added_not_negative CHECK (records_added >= 0),
            CONSTRAINT ck_collection_run_records_changed_not_negative
                CHECK (records_changed >= 0),
            CONSTRAINT ck_collection_run_records_unchanged_not_negative
                CHECK (records_unchanged >= 0),
            CONSTRAINT fk_collection_run_source_id_source
                FOREIGN KEY(source_id) REFERENCES source (id),
            CONSTRAINT ck_collection_run_outcome_one_of
                CHECK (outcome IN ('running', 'succeeded', 'failed', 'interrupted')),
            CONSTRAINT ck_collection_run_error_not_empty CHECK (trim(error, char(
                9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195,
                8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288
            )) != '')
        ) STRICT
        """
    )


def index_the_runs_of_a_source(connection: Connection) -> None:
    """4: the index of the runs of one source in the order they started (DAT-042)."""
    connection.exec_driver_sql(
        "CREATE INDEX ix_collection_run_source_id_started_at "
        "ON collection_run (source_id, started_at)"
    )


def make_the_record_changes(connection: Connection) -> None:
    """5: the table of the changes to records, ``record_change`` (DAT-009)."""
    white_space = (
        "char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, "
        "8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)"
    )

    def not_empty(column: str) -> str:
        return (
            f"CONSTRAINT ck_record_change_{column}_not_empty "
            f"CHECK (trim({column}, {white_space}) != '')"
        )

    connection.exec_driver_sql(
        f"""
        CREATE TABLE record_change (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            record_table TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            field TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            collection_run_id INTEGER,
            decided_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT ck_record_change_record_id_positive CHECK (record_id > 0),
            CONSTRAINT ck_record_change_new_value_not_old_value
                CHECK (old_value IS NOT new_value),
            CONSTRAINT ck_record_change_caused_by_a_run_or_a_person
                CHECK ((collection_run_id IS NULL) != (decided_by IS NULL)),
            CONSTRAINT fk_record_change_collection_run_id_collection_run
                FOREIGN KEY(collection_run_id) REFERENCES collection_run (id),
            {not_empty("record_table")},
            {not_empty("field")},
            {not_empty("decided_by")}
        ) STRICT
        """
    )


def let_the_record_changes_only_be_added_to(connection: Connection) -> None:
    """6: the triggers by which ``record_change`` is only added to (DAT-048)."""
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_record_change_never_edited BEFORE UPDATE ON record_change
        BEGIN
            SELECT RAISE(ABORT, 'A row of the history (record_change) is never edited.');
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_record_change_never_deleted BEFORE DELETE ON record_change
        BEGIN
            SELECT RAISE(ABORT, 'A row of the history (record_change) is never deleted.');
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_record_change_never_replaced BEFORE INSERT ON record_change
        WHEN EXISTS (SELECT 1 FROM record_change WHERE id = NEW.id)
        BEGIN
            SELECT RAISE(ABORT, 'A row of the history (record_change) is never replaced.');
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_record_change_key_positive AFTER INSERT ON record_change
        WHEN NEW.id < 1
        BEGIN
            SELECT RAISE(ABORT, 'A key of the history (record_change) is 1 or more.');
        END
        """
    )


def index_the_record_changes(connection: Connection) -> None:
    """7: the indexes of the changes of one record and of the changes one run caused (DAT-049)."""
    connection.exec_driver_sql(
        "CREATE INDEX ix_record_change_record_table_record_id "
        "ON record_change (record_table, record_id)"
    )
    connection.exec_driver_sql(
        "CREATE INDEX ix_record_change_collection_run_id ON record_change (collection_run_id)"
    )


def make_the_review_items(connection: Connection) -> None:
    """8: the table of the review queue, ``review_item``, and the index of its sources (DAT-010)."""
    white_space = (
        "char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, "
        "8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)"
    )

    def not_empty(column: str) -> str:
        return (
            f"CONSTRAINT ck_review_item_{column}_not_empty "
            f"CHECK (trim({column}, {white_space}) != '')"
        )

    def unless_possible_duplicate(column: str) -> str:
        return (
            f"CONSTRAINT ck_review_item_{column}_unless_possible_duplicate "
            f"CHECK (({column} IS NULL) = (kind = 'possible duplicate'))"
        )

    connection.exec_driver_sql(
        f"""
        CREATE TABLE review_item (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            record_table TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            other_record_id INTEGER,
            field TEXT,
            source_id INTEGER,
            source_address TEXT,
            source_value TEXT,
            reason TEXT NOT NULL,
            state TEXT NOT NULL,
            decided_by TEXT,
            decided_at TEXT,
            note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT ck_review_item_record_id_positive CHECK (record_id > 0),
            CONSTRAINT ck_review_item_other_record_id_after_record_id
                CHECK (other_record_id > record_id),
            CONSTRAINT ck_review_item_other_record_id_when_possible_duplicate
                CHECK ((other_record_id IS NULL) = (kind != 'possible duplicate')),
            {unless_possible_duplicate("field")},
            {unless_possible_duplicate("source_id")},
            {unless_possible_duplicate("source_address")},
            {unless_possible_duplicate("source_value")},
            CONSTRAINT ck_review_item_decided_by_when_decided
                CHECK ((decided_by IS NULL) = (state = 'open')),
            CONSTRAINT ck_review_item_decided_at_when_decided
                CHECK ((decided_at IS NULL) = (state = 'open')),
            CONSTRAINT fk_review_item_source_id_source
                FOREIGN KEY(source_id) REFERENCES source (id),
            CONSTRAINT ck_review_item_kind_one_of CHECK (kind IN (
                'possible duplicate', 'sources disagree', 'value outside its rules'
            )),
            {not_empty("record_table")},
            {not_empty("field")},
            CONSTRAINT ck_review_item_source_address_web_address CHECK (
                ((source_address GLOB '[Hh][Tt][Tt][Pp][Ss]://[^/?#]*')
                 OR (source_address GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*'))
                AND NOT (source_address GLOB '*[' || {white_space} || ']*')
                AND instr(source_address, char(0)) = 0
            ),
            {not_empty("reason")},
            CONSTRAINT ck_review_item_state_one_of
                CHECK (state IN ('open', 'accepted', 'rejected')),
            {not_empty("decided_by")},
            {not_empty("note")}
        ) STRICT
        """
    )
    connection.exec_driver_sql("CREATE INDEX ix_review_item_source_id ON review_item (source_id)")


def hold_one_doubt_to_one_review_item(connection: Connection) -> None:
    """9: the two indexes by which one doubt is one review item (DAT-050)."""
    connection.exec_driver_sql(
        "CREATE UNIQUE INDEX ix_review_item_record_table_record_id_other_record_id "
        "ON review_item (record_table, record_id, other_record_id) "
        "WHERE other_record_id IS NOT NULL"
    )
    connection.exec_driver_sql(
        "CREATE UNIQUE INDEX ix_review_item_record_table_record_id_field_source_id_source_value "
        "ON review_item (record_table, record_id, field, source_id, source_value) "
        "WHERE field IS NOT NULL"
    )


def keep_the_decision_of_a_review_item(connection: Connection) -> None:
    """10: the triggers by which a decided review item is neither edited nor deleted (DAT-054)."""
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_review_item_decided_never_edited BEFORE UPDATE ON review_item
        WHEN OLD.state != 'open'
        BEGIN
            SELECT RAISE(ABORT, 'A decided review item (review_item) is never edited.');
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_review_item_decided_never_deleted BEFORE DELETE ON review_item
        WHEN OLD.state != 'open'
        BEGIN
            SELECT RAISE(ABORT, 'A decided review item (review_item) is never deleted.');
        END
        """
    )


def hold_the_key_of_a_review_item_to_1_or_more(connection: Connection) -> None:
    """11: the triggers by which a key of the review queue is 1 or more (DAT-056)."""
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_review_item_key_positive AFTER INSERT ON review_item
        WHEN NEW.id < 1
        BEGIN
            SELECT RAISE(ABORT, 'A key of the review queue (review_item) is 1 or more.');
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_review_item_key_stays_positive AFTER UPDATE OF id ON review_item
        WHEN NEW.id < 1
        BEGIN
            SELECT RAISE(ABORT, 'A key of the review queue (review_item) is 1 or more.');
        END
        """
    )


def keep_a_decided_review_item_from_being_replaced(connection: Connection) -> None:
    """12: the triggers by which a decided review item is never replaced (DAT-055)."""
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_review_item_decided_never_replaced BEFORE INSERT ON review_item
        WHEN EXISTS (
            SELECT 1 FROM review_item WHERE state != 'open' AND (
                (NEW.id >= 1 AND id = NEW.id)
                OR (record_table = NEW.record_table AND record_id = NEW.record_id
                    AND other_record_id = NEW.other_record_id)
                OR (record_table = NEW.record_table AND record_id = NEW.record_id
                    AND field = NEW.field AND source_id = NEW.source_id
                    AND source_value = NEW.source_value)
            )
        )
        BEGIN
            SELECT RAISE(ABORT, 'A decided review item (review_item) is never replaced.');
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_review_item_decided_never_replaced_by_another
        BEFORE UPDATE ON review_item
        WHEN OLD.state = 'open' AND EXISTS (
            SELECT 1 FROM review_item WHERE state != 'open' AND (
                id = NEW.id
                OR (record_table = NEW.record_table AND record_id = NEW.record_id
                    AND other_record_id = NEW.other_record_id)
                OR (record_table = NEW.record_table AND record_id = NEW.record_id
                    AND field = NEW.field AND source_id = NEW.source_id
                    AND source_value = NEW.source_value)
            )
        )
        BEGIN
            SELECT RAISE(ABORT, 'A decided review item (review_item) is never replaced.');
        END
        """
    )


def make_the_countries(connection: Connection) -> None:
    """13: the table of the countries, ``country``, and the index over their source (DAT-011)."""
    white_space = (
        "char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, "
        "8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)"
    )
    connection.exec_driver_sql(
        f"""
        CREATE TABLE country (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            alpha_2 TEXT NOT NULL,
            alpha_3 TEXT NOT NULL,
            name TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            source_address TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            published_on TEXT,
            last_verified_at TEXT NOT NULL,
            extraction_method TEXT NOT NULL,
            confidence TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT ck_country_alpha_2_two_capitals
                CHECK ((alpha_2 GLOB '[A-Z][A-Z]') AND instr(alpha_2, char(0)) = 0),
            CONSTRAINT ck_country_alpha_3_three_capitals
                CHECK ((alpha_3 GLOB '[A-Z][A-Z][A-Z]') AND instr(alpha_3, char(0)) = 0),
            CONSTRAINT uq_country_alpha_2 UNIQUE (alpha_2),
            CONSTRAINT uq_country_alpha_3 UNIQUE (alpha_3),
            CONSTRAINT fk_country_source_id_source
                FOREIGN KEY(source_id) REFERENCES source (id),
            CONSTRAINT ck_country_name_not_empty CHECK (trim(name, {white_space}) != ''),
            CONSTRAINT ck_country_source_address_web_address CHECK (
                ((source_address GLOB '[Hh][Tt][Tt][Pp][Ss]://[^/?#]*')
                 OR (source_address GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*'))
                AND NOT (source_address GLOB '*[' || {white_space} || ']*')
                AND instr(source_address, char(0)) = 0),
            CONSTRAINT ck_country_published_on_calendar_day CHECK (
                (published_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
                AND date(published_on) IS published_on AND published_on >= '0001-01-01'),
            CONSTRAINT ck_country_extraction_method_one_of CHECK (extraction_method IN (
                'official api', 'structured feed', 'rss feed', 'public dataset',
                'html extraction', 'structured document', 'json endpoint', 'sitemap discovery',
                'search engine discovery', 'human submission'
            )),
            CONSTRAINT ck_country_confidence_one_of
                CHECK (confidence IN ('high', 'medium', 'low')),
            CONSTRAINT ck_country_verification_status_one_of CHECK (verification_status IN (
                'official', 'independent', 'reconstructed', 'unverified'
            )),
            CONSTRAINT ck_country_last_verified_at_not_before_collected_at
                CHECK (last_verified_at >= collected_at)
        ) STRICT
        """
    )
    connection.exec_driver_sql("CREATE INDEX ix_country_source_id ON country (source_id)")


def let_a_source_say_its_country(connection: Connection) -> None:
    """14: the column ``country_id`` of ``source``, and the index over it (DAT-057).

    SQLite puts a new column of a table that is there after all the
    others, and cannot give it a foreign key with a name. So the table is
    built anew: its rows are copied aside, the table is dropped, made
    again with the column and filled from the copy, every row with the
    key it had. Other tables point to the sources. Their foreign keys stay
    on and are checked when the migration ends, when every source is
    there again. The highest key the table has given is kept too: without
    it the key of a source that was deleted would be given a second time.
    """
    white_space = (
        "char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, "
        "8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)"
    )

    def not_empty(column: str) -> str:
        return (
            f"CONSTRAINT ck_source_{column}_not_empty CHECK (trim({column}, {white_space}) != '')"
        )

    def web_address(column: str) -> str:
        return (
            f"CONSTRAINT ck_source_{column}_web_address CHECK ("
            f"(({column} GLOB '[Hh][Tt][Tt][Pp][Ss]://[^/?#]*')"
            f" OR ({column} GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*'))"
            f" AND NOT ({column} GLOB '*[' || {white_space} || ']*')"
            f" AND instr({column}, char(0)) = 0)"
        )

    connection.exec_driver_sql("PRAGMA defer_foreign_keys = ON")
    connection.exec_driver_sql("CREATE TABLE source_before AS SELECT * FROM source")
    connection.exec_driver_sql(
        "CREATE TABLE source_key_before AS SELECT seq FROM sqlite_sequence WHERE name = 'source'"
    )
    connection.exec_driver_sql("DROP TABLE source")
    connection.exec_driver_sql(
        f"""
        CREATE TABLE source (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            website TEXT NOT NULL,
            category TEXT NOT NULL,
            collection_method TEXT NOT NULL,
            scan_every_hours INTEGER,
            terms_address TEXT,
            licence TEXT,
            usage_restrictions TEXT,
            terms_read_at TEXT,
            switched_on INTEGER NOT NULL,
            country_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT ck_source_scan_every_hours_positive CHECK (scan_every_hours > 0),
            CONSTRAINT ck_source_switched_on_terms_read
                CHECK (switched_on = 0 OR terms_read_at IS NOT NULL),
            CONSTRAINT uq_source_name UNIQUE (name),
            CONSTRAINT fk_source_country_id_country
                FOREIGN KEY(country_id) REFERENCES country (id),
            {not_empty("name")},
            {web_address("website")},
            CONSTRAINT ck_source_category_one_of CHECK (category IN (
                'governing body', 'championship', 'organiser', 'promoter', 'track', 'club',
                'regional organisation', 'results database', 'news publication',
                'community website', 'social media page', 'historical archive'
            )),
            CONSTRAINT ck_source_collection_method_one_of CHECK (collection_method IN (
                'official api', 'structured feed', 'rss feed', 'public dataset',
                'html extraction', 'structured document', 'json endpoint', 'sitemap discovery',
                'search engine discovery', 'human submission'
            )),
            {web_address("terms_address")},
            {not_empty("licence")},
            {not_empty("usage_restrictions")},
            CONSTRAINT ck_source_switched_on_yes_or_no CHECK (switched_on IN (0, 1))
        ) STRICT
        """
    )
    # Every source gets what it had before, its key too. The new column
    # gets no value.
    connection.exec_driver_sql(
        """
        INSERT INTO source (
            id, name, website, category, collection_method, scan_every_hours, terms_address,
            licence, usage_restrictions, terms_read_at, switched_on, created_at, updated_at
        )
        SELECT
            id, name, website, category, collection_method, scan_every_hours, terms_address,
            licence, usage_restrictions, terms_read_at, switched_on, created_at, updated_at
        FROM source_before ORDER BY id
        """
    )
    # Filling the table set its highest key to that of the rows that are
    # there. The one it had before is put back.
    connection.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name = 'source'")
    connection.exec_driver_sql(
        "INSERT INTO sqlite_sequence (name, seq) SELECT 'source', seq FROM source_key_before"
    )
    connection.exec_driver_sql("DROP TABLE source_key_before")
    connection.exec_driver_sql("DROP TABLE source_before")
    connection.exec_driver_sql("CREATE INDEX ix_source_country_id ON source (country_id)")


def let_a_source_be_a_reference_list(connection: Connection) -> None:
    """15: one more kind of source, ``reference list`` (DAT-058).

    The check of the column ``category`` names the texts it takes, and
    SQLite cannot change a check of a table that is there. So the table
    is built anew, as the fourteenth migration built it: its rows are
    copied aside, the table is dropped, made again with the check that
    names the new text too, and filled from the copy, every row with all
    it had, its key and its country too. Other tables point to the
    sources. Their foreign keys stay on and are checked when the
    migration ends, when every source is there again. The highest key the
    table has given is kept, and the index over the countries of the
    sources, which went with the table, is made again.
    """
    white_space = (
        "char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, "
        "8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)"
    )

    def not_empty(column: str) -> str:
        return (
            f"CONSTRAINT ck_source_{column}_not_empty CHECK (trim({column}, {white_space}) != '')"
        )

    def web_address(column: str) -> str:
        return (
            f"CONSTRAINT ck_source_{column}_web_address CHECK ("
            f"(({column} GLOB '[Hh][Tt][Tt][Pp][Ss]://[^/?#]*')"
            f" OR ({column} GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*'))"
            f" AND NOT ({column} GLOB '*[' || {white_space} || ']*')"
            f" AND instr({column}, char(0)) = 0)"
        )

    connection.exec_driver_sql("PRAGMA defer_foreign_keys = ON")
    connection.exec_driver_sql("CREATE TABLE source_before AS SELECT * FROM source")
    connection.exec_driver_sql(
        "CREATE TABLE source_key_before AS SELECT seq FROM sqlite_sequence WHERE name = 'source'"
    )
    connection.exec_driver_sql("DROP TABLE source")
    connection.exec_driver_sql(
        f"""
        CREATE TABLE source (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            website TEXT NOT NULL,
            category TEXT NOT NULL,
            collection_method TEXT NOT NULL,
            scan_every_hours INTEGER,
            terms_address TEXT,
            licence TEXT,
            usage_restrictions TEXT,
            terms_read_at TEXT,
            switched_on INTEGER NOT NULL,
            country_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT ck_source_scan_every_hours_positive CHECK (scan_every_hours > 0),
            CONSTRAINT ck_source_switched_on_terms_read
                CHECK (switched_on = 0 OR terms_read_at IS NOT NULL),
            CONSTRAINT uq_source_name UNIQUE (name),
            CONSTRAINT fk_source_country_id_country
                FOREIGN KEY(country_id) REFERENCES country (id),
            {not_empty("name")},
            {web_address("website")},
            CONSTRAINT ck_source_category_one_of CHECK (category IN (
                'governing body', 'championship', 'organiser', 'promoter', 'track', 'club',
                'regional organisation', 'results database', 'news publication',
                'community website', 'social media page', 'historical archive',
                'reference list'
            )),
            CONSTRAINT ck_source_collection_method_one_of CHECK (collection_method IN (
                'official api', 'structured feed', 'rss feed', 'public dataset',
                'html extraction', 'structured document', 'json endpoint', 'sitemap discovery',
                'search engine discovery', 'human submission'
            )),
            {web_address("terms_address")},
            {not_empty("licence")},
            {not_empty("usage_restrictions")},
            CONSTRAINT ck_source_switched_on_yes_or_no CHECK (switched_on IN (0, 1))
        ) STRICT
        """
    )
    # Every source gets all it had before, column for column.
    connection.exec_driver_sql(
        """
        INSERT INTO source (
            id, name, website, category, collection_method, scan_every_hours, terms_address,
            licence, usage_restrictions, terms_read_at, switched_on, country_id, created_at,
            updated_at
        )
        SELECT
            id, name, website, category, collection_method, scan_every_hours, terms_address,
            licence, usage_restrictions, terms_read_at, switched_on, country_id, created_at,
            updated_at
        FROM source_before ORDER BY id
        """
    )
    # Filling the table set its highest key to that of the rows that are
    # there. The one it had before is put back.
    connection.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name = 'source'")
    connection.exec_driver_sql(
        "INSERT INTO sqlite_sequence (name, seq) SELECT 'source', seq FROM source_key_before"
    )
    connection.exec_driver_sql("DROP TABLE source_key_before")
    connection.exec_driver_sql("DROP TABLE source_before")
    # The index went with the table it was over.
    connection.exec_driver_sql("CREATE INDEX ix_source_country_id ON source (country_id)")


def make_the_regions(connection: Connection) -> None:
    """16: the table of the regions, ``region``, and the index over their source (DAT-013)."""
    white_space = (
        "char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, "
        "8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)"
    )
    connection.exec_driver_sql(
        f"""
        CREATE TABLE region (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            country_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            source_address TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            published_on TEXT,
            last_verified_at TEXT NOT NULL,
            extraction_method TEXT NOT NULL,
            confidence TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT uq_region_country_id_name UNIQUE (country_id, name),
            CONSTRAINT fk_region_country_id_country
                FOREIGN KEY(country_id) REFERENCES country (id),
            CONSTRAINT fk_region_source_id_source
                FOREIGN KEY(source_id) REFERENCES source (id),
            CONSTRAINT ck_region_name_not_empty CHECK (trim(name, {white_space}) != ''),
            CONSTRAINT ck_region_source_address_web_address CHECK (
                ((source_address GLOB '[Hh][Tt][Tt][Pp][Ss]://[^/?#]*')
                 OR (source_address GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*'))
                AND NOT (source_address GLOB '*[' || {white_space} || ']*')
                AND instr(source_address, char(0)) = 0),
            CONSTRAINT ck_region_published_on_calendar_day CHECK (
                (published_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
                AND date(published_on) IS published_on AND published_on >= '0001-01-01'),
            CONSTRAINT ck_region_extraction_method_one_of CHECK (extraction_method IN (
                'official api', 'structured feed', 'rss feed', 'public dataset',
                'html extraction', 'structured document', 'json endpoint', 'sitemap discovery',
                'search engine discovery', 'human submission'
            )),
            CONSTRAINT ck_region_confidence_one_of
                CHECK (confidence IN ('high', 'medium', 'low')),
            CONSTRAINT ck_region_verification_status_one_of CHECK (verification_status IN (
                'official', 'independent', 'reconstructed', 'unverified'
            )),
            CONSTRAINT ck_region_last_verified_at_not_before_collected_at
                CHECK (last_verified_at >= collected_at)
        ) STRICT
        """
    )
    connection.exec_driver_sql("CREATE INDEX ix_region_source_id ON region (source_id)")


def let_a_region_say_its_code(connection: Connection) -> None:
    """17: the column ``iso_3166_2`` of ``region``, its form, and one region to a code (DAT-064).

    SQLite puts a new column of a table that is there after all the
    others, and cannot give it the rule that no two rows have one value.
    So the table is built anew, as the fourteenth migration built the
    sources: its rows are copied aside, the table is dropped, made again
    with the column and filled from the copy, every row with all it had
    and its key. No region gets a code: none is known. The highest key
    the table has given is kept: without it the key of a region that was
    deleted would be given a second time. The index over the sources of
    the regions, which went with the table, is made again. No table of
    a store at this version points to a region, so no check of what
    points where has to wait for the end of the migration.
    """
    white_space = (
        "char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, "
        "8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)"
    )
    connection.exec_driver_sql("CREATE TABLE region_before AS SELECT * FROM region")
    connection.exec_driver_sql(
        "CREATE TABLE region_key_before AS SELECT seq FROM sqlite_sequence WHERE name = 'region'"
    )
    connection.exec_driver_sql("DROP TABLE region")
    connection.exec_driver_sql(
        f"""
        CREATE TABLE region (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            country_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            iso_3166_2 TEXT,
            source_id INTEGER NOT NULL,
            source_address TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            published_on TEXT,
            last_verified_at TEXT NOT NULL,
            extraction_method TEXT NOT NULL,
            confidence TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT uq_region_country_id_name UNIQUE (country_id, name),
            CONSTRAINT ck_region_iso_3166_2_form CHECK (
                ((iso_3166_2 GLOB '[A-Z][A-Z]-[A-Z0-9]')
                 OR (iso_3166_2 GLOB '[A-Z][A-Z]-[A-Z0-9][A-Z0-9]')
                 OR (iso_3166_2 GLOB '[A-Z][A-Z]-[A-Z0-9][A-Z0-9][A-Z0-9]'))
                AND instr(iso_3166_2, char(0)) = 0),
            CONSTRAINT fk_region_country_id_country
                FOREIGN KEY(country_id) REFERENCES country (id),
            CONSTRAINT uq_region_iso_3166_2 UNIQUE (iso_3166_2),
            CONSTRAINT fk_region_source_id_source
                FOREIGN KEY(source_id) REFERENCES source (id),
            CONSTRAINT ck_region_name_not_empty CHECK (trim(name, {white_space}) != ''),
            CONSTRAINT ck_region_source_address_web_address CHECK (
                ((source_address GLOB '[Hh][Tt][Tt][Pp][Ss]://[^/?#]*')
                 OR (source_address GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*'))
                AND NOT (source_address GLOB '*[' || {white_space} || ']*')
                AND instr(source_address, char(0)) = 0),
            CONSTRAINT ck_region_published_on_calendar_day CHECK (
                (published_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
                AND date(published_on) IS published_on AND published_on >= '0001-01-01'),
            CONSTRAINT ck_region_extraction_method_one_of CHECK (extraction_method IN (
                'official api', 'structured feed', 'rss feed', 'public dataset',
                'html extraction', 'structured document', 'json endpoint', 'sitemap discovery',
                'search engine discovery', 'human submission'
            )),
            CONSTRAINT ck_region_confidence_one_of
                CHECK (confidence IN ('high', 'medium', 'low')),
            CONSTRAINT ck_region_verification_status_one_of CHECK (verification_status IN (
                'official', 'independent', 'reconstructed', 'unverified'
            )),
            CONSTRAINT ck_region_last_verified_at_not_before_collected_at
                CHECK (last_verified_at >= collected_at)
        ) STRICT
        """
    )
    # Every region gets what it had before, its key too. The new column
    # gets no value.
    connection.exec_driver_sql(
        """
        INSERT INTO region (
            id, country_id, name, source_id, source_address, collected_at, published_on,
            last_verified_at, extraction_method, confidence, verification_status, created_at,
            updated_at
        )
        SELECT
            id, country_id, name, source_id, source_address, collected_at, published_on,
            last_verified_at, extraction_method, confidence, verification_status, created_at,
            updated_at
        FROM region_before ORDER BY id
        """
    )
    # Filling the table set its highest key to that of the rows that are
    # there. The one it had before is put back.
    connection.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name = 'region'")
    connection.exec_driver_sql(
        "INSERT INTO sqlite_sequence (name, seq) SELECT 'region', seq FROM region_key_before"
    )
    connection.exec_driver_sql("DROP TABLE region_key_before")
    connection.exec_driver_sql("DROP TABLE region_before")
    connection.exec_driver_sql("CREATE INDEX ix_region_source_id ON region (source_id)")


def hold_the_key_of_a_review_item_under_every_name(connection: Connection) -> None:
    """18: the second trigger of the keys of the review queue, made anew (DAT-068).

    The eleventh migration made it fire for a change of the column
    ``id``. SQLite has three more names for the key of a table,
    ``rowid``, ``_rowid_`` and ``oid``, and a statement that sets the key
    by one of them did not fire it. The trigger now fires after every
    change of an item and asks whether the key is another than it was.
    """
    connection.exec_driver_sql("DROP TRIGGER tr_review_item_key_stays_positive")
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_review_item_key_stays_positive AFTER UPDATE ON review_item
        WHEN NEW.id < 1 AND NEW.id != OLD.id
        BEGIN
            SELECT RAISE(ABORT, 'A key of the review queue (review_item) is 1 or more.');
        END
        """
    )


def hold_the_code_of_a_region_to_its_country(connection: Connection) -> None:
    """19: the code of a region begins with the code of its country (DAT-067).

    Four triggers: two on the regions, for a new region and for one that
    is changed, and two on the countries, for a new country and for one
    that is changed. They change no table, no index and no row.

    A store can hold a region whose code begins with the letters of
    another country: until this migration nothing refused one. Which of
    the two is wrong, the code or the country, the migration cannot
    know, so it puts nothing right and such a region stays as it is.
    From then on it can be put right or deleted and nothing else: every
    other change of it is refused, and so is every change of its country.
    """
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_region_code_of_its_country AFTER INSERT ON region
        WHEN substr(NEW.iso_3166_2, 1, 2) != (SELECT alpha_2 FROM country WHERE id = NEW.country_id)
        BEGIN
            SELECT RAISE(ABORT,
                'The code of a region (region) begins with the code of its country (country).');
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_region_code_stays_of_its_country AFTER UPDATE ON region
        WHEN substr(NEW.iso_3166_2, 1, 2) != (SELECT alpha_2 FROM country WHERE id = NEW.country_id)
        BEGIN
            SELECT RAISE(ABORT,
                'The code of a region (region) begins with the code of its country (country).');
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_country_code_of_its_regions AFTER INSERT ON country
        WHEN EXISTS (SELECT 1 FROM region WHERE country_id = NEW.id
            AND substr(iso_3166_2, 1, 2) != NEW.alpha_2)
        BEGIN
            SELECT RAISE(ABORT,
                'The codes of the regions of a country (region) begin with its code (country).');
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_country_code_stays_of_its_regions AFTER UPDATE ON country
        WHEN EXISTS (SELECT 1 FROM region WHERE country_id = NEW.id
            AND substr(iso_3166_2, 1, 2) != NEW.alpha_2)
        BEGIN
            SELECT RAISE(ABORT,
                'The codes of the regions of a country (region) begin with its code (country).');
        END
        """
    )


def let_regions_with_codes_share_a_name(connection: Connection) -> None:
    """20: one name among the regions of a country that say no code, not among all (DAT-066).

    Until now no two regions of one country had one name. The standard's
    own list has such pairs, each region with its code, so the rule now
    holds among the regions that say no code, and an index over those
    regions only holds it. A second index, over the country, finds the
    regions of one country, which the index of the old rule did.

    The old rule was written into the table, and SQLite cannot take a
    rule out of a table that is there. So the table is built anew, as
    the seventeenth migration built it: its rows are copied aside, the
    table is dropped, made again without the rule and filled from the
    copy, every row with all it had and its key. The highest key the
    table has given is kept. What went with the table is made again: the
    index over the sources of the regions, and the two triggers of the
    nineteenth migration that are on the regions. They are made after
    the table is filled, so a region whose code is not of its country,
    which the nineteenth migration left as it was, is left as it is here
    too. The two triggers on the countries stay: they are not the
    table's. No table of a store at this version points to a region.

    No region can be in the way of the new rule: every store kept the
    old one, which asked for more.
    """
    white_space = (
        "char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, "
        "8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)"
    )
    connection.exec_driver_sql("CREATE TABLE region_before AS SELECT * FROM region")
    connection.exec_driver_sql(
        "CREATE TABLE region_key_before AS SELECT seq FROM sqlite_sequence WHERE name = 'region'"
    )
    connection.exec_driver_sql("DROP TABLE region")
    connection.exec_driver_sql(
        f"""
        CREATE TABLE region (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            country_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            iso_3166_2 TEXT,
            source_id INTEGER NOT NULL,
            source_address TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            published_on TEXT,
            last_verified_at TEXT NOT NULL,
            extraction_method TEXT NOT NULL,
            confidence TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT ck_region_iso_3166_2_form CHECK (
                ((iso_3166_2 GLOB '[A-Z][A-Z]-[A-Z0-9]')
                 OR (iso_3166_2 GLOB '[A-Z][A-Z]-[A-Z0-9][A-Z0-9]')
                 OR (iso_3166_2 GLOB '[A-Z][A-Z]-[A-Z0-9][A-Z0-9][A-Z0-9]'))
                AND instr(iso_3166_2, char(0)) = 0),
            CONSTRAINT fk_region_country_id_country
                FOREIGN KEY(country_id) REFERENCES country (id),
            CONSTRAINT uq_region_iso_3166_2 UNIQUE (iso_3166_2),
            CONSTRAINT fk_region_source_id_source
                FOREIGN KEY(source_id) REFERENCES source (id),
            CONSTRAINT ck_region_name_not_empty CHECK (trim(name, {white_space}) != ''),
            CONSTRAINT ck_region_source_address_web_address CHECK (
                ((source_address GLOB '[Hh][Tt][Tt][Pp][Ss]://[^/?#]*')
                 OR (source_address GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*'))
                AND NOT (source_address GLOB '*[' || {white_space} || ']*')
                AND instr(source_address, char(0)) = 0),
            CONSTRAINT ck_region_published_on_calendar_day CHECK (
                (published_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
                AND date(published_on) IS published_on AND published_on >= '0001-01-01'),
            CONSTRAINT ck_region_extraction_method_one_of CHECK (extraction_method IN (
                'official api', 'structured feed', 'rss feed', 'public dataset',
                'html extraction', 'structured document', 'json endpoint', 'sitemap discovery',
                'search engine discovery', 'human submission'
            )),
            CONSTRAINT ck_region_confidence_one_of
                CHECK (confidence IN ('high', 'medium', 'low')),
            CONSTRAINT ck_region_verification_status_one_of CHECK (verification_status IN (
                'official', 'independent', 'reconstructed', 'unverified'
            )),
            CONSTRAINT ck_region_last_verified_at_not_before_collected_at
                CHECK (last_verified_at >= collected_at)
        ) STRICT
        """
    )
    # Every region gets what it had before, its key and its code too.
    connection.exec_driver_sql(
        """
        INSERT INTO region (
            id, country_id, name, iso_3166_2, source_id, source_address, collected_at,
            published_on, last_verified_at, extraction_method, confidence, verification_status,
            created_at, updated_at
        )
        SELECT
            id, country_id, name, iso_3166_2, source_id, source_address, collected_at,
            published_on, last_verified_at, extraction_method, confidence, verification_status,
            created_at, updated_at
        FROM region_before ORDER BY id
        """
    )
    # Filling the table set its highest key to that of the rows that are
    # there. The one it had before is put back.
    connection.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name = 'region'")
    connection.exec_driver_sql(
        "INSERT INTO sqlite_sequence (name, seq) SELECT 'region', seq FROM region_key_before"
    )
    connection.exec_driver_sql("DROP TABLE region_key_before")
    connection.exec_driver_sql("DROP TABLE region_before")
    connection.exec_driver_sql("CREATE INDEX ix_region_source_id ON region (source_id)")
    connection.exec_driver_sql("CREATE INDEX ix_region_country_id ON region (country_id)")
    connection.exec_driver_sql(
        "CREATE UNIQUE INDEX ix_region_country_id_name ON region (country_id, name) "
        "WHERE iso_3166_2 IS NULL"
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_region_code_of_its_country AFTER INSERT ON region
        WHEN substr(NEW.iso_3166_2, 1, 2) != (SELECT alpha_2 FROM country WHERE id = NEW.country_id)
        BEGIN
            SELECT RAISE(ABORT,
                'The code of a region (region) begins with the code of its country (country).');
        END
        """
    )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER tr_region_code_stays_of_its_country AFTER UPDATE ON region
        WHEN substr(NEW.iso_3166_2, 1, 2) != (SELECT alpha_2 FROM country WHERE id = NEW.country_id)
        BEGIN
            SELECT RAISE(ABORT,
                'The code of a region (region) begins with the code of its country (country).');
        END
        """
    )


MIGRATIONS: tuple[Callable[[Connection], None], ...] = (
    make_the_sources,
    make_the_source_offers,
    make_the_collection_runs,
    index_the_runs_of_a_source,
    make_the_record_changes,
    let_the_record_changes_only_be_added_to,
    index_the_record_changes,
    make_the_review_items,
    hold_one_doubt_to_one_review_item,
    keep_the_decision_of_a_review_item,
    hold_the_key_of_a_review_item_to_1_or_more,
    keep_a_decided_review_item_from_being_replaced,
    make_the_countries,
    let_a_source_say_its_country,
    let_a_source_be_a_reference_list,
    make_the_regions,
    let_a_region_say_its_code,
    hold_the_key_of_a_review_item_under_every_name,
    hold_the_code_of_a_region_to_its_country,
    let_regions_with_codes_share_a_name,
)
