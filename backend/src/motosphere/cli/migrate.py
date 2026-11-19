"""The ``migrate`` command: bring the data store to the newest schema."""

import argparse
import sys
from collections.abc import Sequence

from motosphere.core.settings import Settings
from motosphere.db.migrations import SchemaError, migrate, schema_version
from motosphere.db.store import StoreError, open_store

__all__ = ["EXIT_STORE_REFUSED", "add_parser", "report", "run"]

EXIT_STORE_REFUSED = 1


def add_parser(commands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register the ``migrate`` command."""
    parser = commands.add_parser(
        "migrate",
        help="bring the data store to the newest schema",
        description=(
            "Bring the data store to the newest schema. The store is the file the setting "
            "MOTOSPHERE_STORE_PATH names; it is made if it is not there."
        ),
        allow_abbrev=False,
    )
    parser.set_defaults(handler=run)


def report(path: str, made: bool, applied: Sequence[int], version: int) -> str:
    """Say in one sentence what the command did to the store at ``path``.

    ``made`` says that there was no file before, ``applied`` holds the
    numbers of the migrations the store was given, and ``version`` is the
    schema version the store has now.
    """
    if made:
        return f"A new data store was made: {path} is at schema version {version}."
    if applied:
        return (
            f"The data store was brought up to date: {path} went from schema version "
            f"{version - len(applied)} to {version}."
        )
    return f"The data store is up to date: {path} is at schema version {version}."


def run(_arguments: argparse.Namespace, settings: Settings) -> int:
    """Give the store the migrations it lacks and write what was done to standard output.

    A store that cannot be opened, or that is refused, gives its one
    sentence on standard error and the exit code 1, and is left as it is.
    An error inside a migration is not caught: it is a fault in the code,
    and the store stays at the version before that migration.
    """
    path = settings.store_path.resolve()
    made = not path.exists()
    try:
        store = open_store(path)
        applied = migrate(store)
    except (StoreError, SchemaError) as error:
        sys.stderr.write(f"{error}\n")
        return EXIT_STORE_REFUSED

    sys.stdout.write(report(str(path), made, applied, schema_version(store)) + "\n")
    return 0
