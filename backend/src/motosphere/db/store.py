"""Opening the data store: the one place where the pipeline connects to its SQLite file.

``open_store`` gives the SQLAlchemy engine for a store's file. Every
connection that engine makes enforces foreign keys and uses SQLite's own
transactions, so that work which fails is taken back as a whole, a change
to the schema included. No connection is kept open after it has been used.
"""

import sqlite3
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from motosphere.db.sqlite import missing

__all__ = ["StoreError", "open_store"]


class StoreError(Exception):
    """The store cannot be opened. The message is one plain sentence for the user."""


def _refuse(reason: str) -> StoreError:
    return StoreError(f"The data store cannot be opened: {reason}.")


def _switch_on_foreign_keys(connection: sqlite3.Connection, _record: object) -> None:
    """Make a new connection enforce foreign keys.

    SQLite ignores the statement inside a transaction, and with
    ``autocommit=False`` a connection is always inside one. So the
    connection leaves that mode for this one statement.
    """
    before = connection.autocommit
    connection.autocommit = True
    connection.execute("PRAGMA foreign_keys = ON")
    connection.autocommit = before


def open_store(path: Path, lacking: Callable[[], list[str]] = missing) -> Engine:
    """Open the store kept in the file at ``path`` and return its engine.

    A file that is not there yet is created, empty, with its folder. A
    relative path is taken from the current folder now, so the engine keeps
    pointing at the same file whatever the current folder is later.

    ``lacking`` says what this machine's SQLite lacks for the store; if it
    names anything, the store is refused before anything is written.

    Raises ``StoreError`` when the store cannot be opened.
    """
    problems = lacking()
    if problems:
        raise _refuse("; ".join(problems))
    path = path.resolve()
    if path.is_dir():
        raise _refuse(f"{path} is a folder, not a file")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise _refuse(f"the folder {path.parent} cannot be made ({error.strerror})") from error

    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(path)),
        # No connection is kept: a store that is not in use is a closed file.
        poolclass=NullPool,
        # SQLite's own transactions (Python 3.12 and newer): one is always
        # open, so a change to the schema is taken back like any other.
        connect_args={"autocommit": False},
    )
    event.listen(engine, "connect", _switch_on_foreign_keys)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT count(*) FROM sqlite_master").scalar_one()
    except DBAPIError as error:
        raise _refuse(f"{path} cannot be read as an SQLite database ({error.orig})") from error
    return engine
