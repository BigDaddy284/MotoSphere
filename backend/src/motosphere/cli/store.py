"""The data store as a command that works on it is given it.

``migrate`` makes the store and brings it to the newest schema, and
``schema`` says which schema it has. Every other command that reads or
writes the store works on it as it is, and :func:`store_to_work_on` is
where such a command gets it: the store the settings name, and only when
it is there and at the newest schema.

Nothing is put right here. Where there is no file, none is made, and a
store that lacks migrations is not given them: that stays with
``migrate``, so that a command that was asked for one thing does not do
another as well. What is wrong is said in one sentence, and where
``migrate`` puts it right, the sentence says so.
"""

from typing import Final

from sqlalchemy import Engine

from motosphere.cli.schema import report
from motosphere.core.settings import Settings
from motosphere.db.migrations import SchemaError, pending, schema_version
from motosphere.db.store import StoreError, open_store

__all__ = ["MIGRATE_FIRST", "StoreNotReadyError", "store_to_work_on"]

# What a person does about a store that is not there or lacks migrations.
MIGRATE_FIRST: Final = "Run `python -m motosphere migrate` first."


class StoreNotReadyError(Exception):
    """The store cannot be worked on as it is. The message is one plain sentence for the user."""


def store_to_work_on(settings: Settings) -> Engine:
    """Give the store the settings name, when it is there and at the newest schema.

    The store is opened the way every store is opened
    (:func:`motosphere.db.store.open_store`), and no connection to it is
    left open.

    Raises :class:`StoreNotReadyError` when there is no file, when the
    store lacks migrations, and when ``migrate`` would refuse the store
    or it cannot be opened: then in the words ``migrate`` has for it.
    Nothing is written either way, and no file is made.
    """
    path = settings.store_path.resolve()
    if not path.exists():
        # open_store would make the file.
        raise StoreNotReadyError(f"{report(str(path), None, 0)} {MIGRATE_FIRST}")
    try:
        store = open_store(path)
        lacking = pending(store)
    except (StoreError, SchemaError) as error:
        raise StoreNotReadyError(str(error)) from error
    if lacking:
        said = report(str(path), schema_version(store), len(lacking))
        raise StoreNotReadyError(f"{said} {MIGRATE_FIRST}")
    return store
