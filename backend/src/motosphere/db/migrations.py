"""Migrations: the one way the data store's schema is built and changed.

A migration is a function that changes the schema of a store. The
migrations stand in one list, oldest first, and the place of a migration in
that list is its number. A store records the number of the last migration
it has had (its schema version), and ``migrate`` gives it those it lacks.

Only a store of MotoSphere's is migrated. Its first migration marks the
file as MotoSphere's, and ``migrate`` refuses a file that has anything in it
and not that mark.
"""

from collections.abc import Callable, Sequence

from sqlalchemy import Connection, Engine

__all__ = [
    "APPLICATION_ID",
    "MIGRATIONS",
    "Migration",
    "SchemaError",
    "migrate",
    "schema_version",
]

type Migration = Callable[[Connection], None]

# The history of the store's schema, oldest first. It only ever grows at
# its end: a migration that has been merged is not changed, moved or taken
# out, because stores and snapshots at its version exist.
MIGRATIONS: tuple[Migration, ...] = ()

# The mark of a store of MotoSphere's: the letters "MoSp" as one number. It
# is kept in the file itself, in the field SQLite gives applications to say
# whose a database is (``application_id``), and it never changes.
APPLICATION_ID = 0x4D6F5370


class SchemaError(Exception):
    """The store's schema cannot be brought up to date. One plain sentence for the user."""


def schema_version(store: Engine) -> int:
    """Say which schema the store has: the number of the last migration it has had.

    A store that has had none is at version 0. The number is kept in the
    file itself, in the field SQLite gives applications for this
    (``user_version``).
    """
    with store.connect() as connection:
        return int(connection.exec_driver_sql("PRAGMA user_version").scalar_one())


def _why_not_ours(store: Engine) -> str | None:
    """Say why the file is not a store of MotoSphere's, or ``None`` when it is one.

    A file with nothing in it is one too: it is new, and its first
    migration marks it.
    """
    with store.connect() as connection:
        mark = int(connection.exec_driver_sql("PRAGMA application_id").scalar_one())
        version = int(connection.exec_driver_sql("PRAGMA user_version").scalar_one())
        holds = int(connection.exec_driver_sql("SELECT count(*) FROM sqlite_master").scalar_one())
    if mark == APPLICATION_ID:
        return None
    if mark != 0:
        return f"it carries the mark of another application, {mark}"
    if version == 0 and holds == 0:
        return None
    return "it is not a new, empty file, and it does not carry MotoSphere's mark"


def migrate(store: Engine, migrations: Sequence[Migration] | None = None) -> list[int]:
    """Give the store every migration it lacks, in order, and return their numbers.

    Each migration is one transaction together with the store's new
    version: it is kept as a whole or not at all. When one fails, the store
    stays at the version before it, those before it stay applied, and the
    error reaches the caller as it was raised. A migration does not commit;
    this function does.

    Only a store of MotoSphere's is migrated: a file that carries
    MotoSphere's mark, or a new file with nothing in it, which gets the mark
    in the transaction of its first migration.

    ``migrations`` is the whole history, oldest first; by default the
    store's own, ``MIGRATIONS``.

    Raises ``SchemaError``, and leaves the file as it is, when the file is
    not a store of MotoSphere's, or when the store's version is not one the
    history knows, as that of a store newer than this code.
    """
    history = MIGRATIONS if migrations is None else migrations
    reason = _why_not_ours(store)
    if reason is not None:
        raise SchemaError(
            f"The data store cannot be brought up to date: {store.url.database} is not a "
            f"store of MotoSphere's ({reason})."
        )
    version = schema_version(store)
    if not 0 <= version <= len(history):
        raise SchemaError(
            f"The data store cannot be brought up to date: its schema is version {version}, "
            f"and this MotoSphere knows only the versions 0 to {len(history)}."
        )
    applied: list[int] = []
    for number, migration in enumerate(history[version:], start=version + 1):
        with store.begin() as connection:
            # A new store becomes MotoSphere's with its first migration. For
            # a store that carries the mark already, this changes nothing.
            connection.exec_driver_sql(f"PRAGMA application_id = {APPLICATION_ID}")
            migration(connection)
            connection.exec_driver_sql(f"PRAGMA user_version = {number}")
        applied.append(number)
    return applied
