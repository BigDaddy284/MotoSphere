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
    "index_the_record_changes",
    "index_the_runs_of_a_source",
    "let_the_record_changes_only_be_added_to",
    "make_the_collection_runs",
    "make_the_record_changes",
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


MIGRATIONS: tuple[Callable[[Connection], None], ...] = (
    make_the_sources,
    make_the_source_offers,
    make_the_collection_runs,
    index_the_runs_of_a_source,
    make_the_record_changes,
    let_the_record_changes_only_be_added_to,
    index_the_record_changes,
    make_the_review_items,
)
