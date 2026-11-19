"""The ``schema`` command: say which schema the data store has, and change nothing."""

import argparse
import sys

from motosphere.cli.migrate import EXIT_STORE_REFUSED
from motosphere.core.settings import Settings
from motosphere.db.migrations import SchemaError, pending, schema_version
from motosphere.db.store import StoreError, open_store

__all__ = ["add_parser", "report", "run"]


def add_parser(commands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register the ``schema`` command."""
    parser = commands.add_parser(
        "schema",
        help="say which schema the data store has",
        description=(
            "Say which schema the data store has, and whether it is the newest. Nothing is "
            "changed, and no file is made. The store is the file the setting "
            "MOTOSPHERE_STORE_PATH names."
        ),
        allow_abbrev=False,
    )
    parser.set_defaults(handler=run)


def report(path: str, version: int | None, lacking: int) -> str:
    """Say in one sentence which schema the store at ``path`` has.

    ``version`` is the store's schema version, or ``None`` where there is
    no file, and ``lacking`` is the number of migrations the store lacks.
    """
    if version is None:
        return f"There is no data store: {path} does not exist."
    if lacking == 0:
        return f"The data store is up to date: {path} is at schema version {version}."
    migrations = "1 migration" if lacking == 1 else f"{lacking} migrations"
    return (
        f"The data store lacks {migrations}: {path} is at schema version {version}, "
        f"and the newest is version {version + lacking}."
    )


def run(_arguments: argparse.Namespace, settings: Settings) -> int:
    """Write which schema the store has to standard output, and write nothing else anywhere.

    Where there is no file, the command says so and makes none. A store
    that ``migrate`` would refuse, or that cannot be opened, gives the same
    sentence on standard error and the same exit code 1 as there.
    """
    path = settings.store_path.resolve()
    if not path.exists():
        # open_store would make the file.
        sys.stdout.write(report(str(path), None, 0) + "\n")
        return 0
    try:
        store = open_store(path)
        lacking = pending(store)
    except (StoreError, SchemaError) as error:
        sys.stderr.write(f"{error}\n")
        return EXIT_STORE_REFUSED

    sys.stdout.write(report(str(path), schema_version(store), len(lacking)) + "\n")
    return 0
