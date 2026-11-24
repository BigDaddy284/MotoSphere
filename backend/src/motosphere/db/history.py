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

__all__ = ["MIGRATIONS", "make_the_collection_runs", "make_the_source_offers", "make_the_sources"]


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


MIGRATIONS: tuple[Callable[[Connection], None], ...] = (
    make_the_sources,
    make_the_source_offers,
    make_the_collection_runs,
)
