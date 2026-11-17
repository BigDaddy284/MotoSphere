"""The ``version`` command: print the installed MotoSphere version."""

import argparse
import sys

import motosphere
from motosphere.core.settings import Settings

__all__ = ["add_parser", "run"]


def add_parser(commands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register the ``version`` command."""
    parser = commands.add_parser(
        "version",
        help="print the MotoSphere version",
        description="Print the installed MotoSphere version.",
        allow_abbrev=False,
    )
    parser.set_defaults(handler=run)


def run(_arguments: argparse.Namespace, _settings: Settings) -> int:
    """Write ``motosphere <version>`` to standard output."""
    sys.stdout.write(f"motosphere {motosphere.__version__}\n")
    return 0
