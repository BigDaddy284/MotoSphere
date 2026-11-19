"""Argument parsing and start-up shared by every MotoSphere command.

A command is a module with an ``add_parser`` function that registers its
sub-command and names the function that runs it. :func:`main` parses the
arguments, loads the settings, sets up logging and then runs the command.

Results are written to standard output. Log lines and error messages go to
standard error, so output can be piped or saved without them.
"""

import argparse
import sys
from collections.abc import Callable, Sequence

from pydantic import ValidationError

from motosphere.cli import export, version
from motosphere.core.logging_config import configure_logging
from motosphere.core.settings import Settings, get_settings

__all__ = ["EXIT_CONFIGURATION_ERROR", "EXIT_OK", "PROGRAM", "build_parser", "main"]

PROGRAM = "python -m motosphere"
EXIT_OK = 0
# argparse also exits with 2 when the arguments are wrong.
EXIT_CONFIGURATION_ERROR = 2

type CommandHandler = Callable[[argparse.Namespace, Settings], int]


def build_parser() -> argparse.ArgumentParser:
    """Return the parser for ``python -m motosphere`` with every command registered."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="MotoSphere data pipeline.",
        allow_abbrev=False,
    )
    commands = parser.add_subparsers(
        title="commands",
        dest="command",
        metavar="<command>",
        required=True,
    )
    export.add_parser(commands)
    version.add_parser(commands)
    return parser


def _describe_configuration_error(error: ValidationError) -> str:
    """Return one line naming every invalid setting and what is wrong with it."""
    problems = "; ".join(
        f"{'.'.join(str(part) for part in problem['loc'])}: {problem['msg']}"
        for problem in error.errors()
    )
    return f"Configuration error: {problems}"


def main(argv: Sequence[str] | None = None) -> int:
    """Run one MotoSphere command and return the process exit code.

    ``argv`` is the argument list without the program name; ``None`` means the
    arguments of the running process. Wrong arguments, and ``--help``, end the
    process through :class:`SystemExit`, as is usual for argparse. Invalid
    settings give a one-line message on standard error and exit code 2.
    """
    arguments = build_parser().parse_args(argv)

    try:
        settings = get_settings()
    except ValidationError as error:
        sys.stderr.write(_describe_configuration_error(error) + "\n")
        return EXIT_CONFIGURATION_ERROR

    configure_logging(settings)
    handler: CommandHandler = arguments.handler
    return handler(arguments, settings)
