"""Migrations: the one way the data store's schema is built and changed.

A migration is a function that changes the schema of a store. The
migrations stand in one list, oldest first, and the place of a migration in
that list is its number. A store records the number of the last migration
it has had (its schema version), and ``migrate`` gives it those it lacks.
"""

from collections.abc import Callable, Sequence

from sqlalchemy import Connection, Engine

__all__ = ["MIGRATIONS", "Migration", "SchemaError", "migrate", "schema_version"]

type Migration = Callable[[Connection], None]

# The history of the store's schema, oldest first. It only ever grows at
# its end: a migration that has been merged is not changed, moved or taken
# out, because stores and snapshots at its version exist.
MIGRATIONS: tuple[Migration, ...] = ()


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


def migrate(store: Engine, migrations: Sequence[Migration] | None = None) -> list[int]:
    """Give the store every migration it lacks, in order, and return their numbers.

    Each migration is one transaction together with the store's new
    version: it is kept as a whole or not at all. When one fails, the store
    stays at the version before it, those before it stay applied, and the
    error reaches the caller as it was raised. A migration does not commit;
    this function does.

    ``migrations`` is the whole history, oldest first; by default the
    store's own, ``MIGRATIONS``.

    Raises ``SchemaError``, and leaves the store as it is, when the store's
    version is not one the history knows: the store is newer than this
    code, or it is not a store of MotoSphere's.
    """
    history = MIGRATIONS if migrations is None else migrations
    version = schema_version(store)
    if not 0 <= version <= len(history):
        raise SchemaError(
            f"The data store cannot be brought up to date: its schema is version {version}, "
            f"and this MotoSphere knows only the versions 0 to {len(history)}."
        )
    applied: list[int] = []
    for number, migration in enumerate(history[version:], start=version + 1):
        with store.begin() as connection:
            migration(connection)
            connection.exec_driver_sql(f"PRAGMA user_version = {number}")
        applied.append(number)
    return applied
