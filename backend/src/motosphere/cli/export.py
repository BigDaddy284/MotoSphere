"""The ``export`` command: write the published data files into a directory."""

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from motosphere.core.settings import Settings
from motosphere.publish.export import export_published_data

__all__ = ["EXIT_EXPORT_FAILED", "add_parser", "run"]

EXIT_EXPORT_FAILED = 1

_logger = logging.getLogger(__name__)


def _directory(value: str) -> Path:
    if value.strip() == "":
        raise argparse.ArgumentTypeError("the directory must not be empty")
    return Path(value)


def add_parser(commands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register the ``export`` command."""
    parser = commands.add_parser(
        "export",
        help="write the published data files",
        description="Write the published data files into a directory.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--out",
        required=True,
        type=_directory,
        metavar="<directory>",
        help="the directory to write into; it is created if it does not exist",
    )
    parser.set_defaults(handler=run)


def _one_line(text: str) -> str:
    return " ".join(text.split())


def run(arguments: argparse.Namespace, _settings: Settings) -> int:
    """Export into ``--out`` and write the manifest's path to standard output."""
    directory: Path = arguments.out
    try:
        manifest_path = export_published_data(directory, datetime.now(UTC))
    except OSError as error:
        reason = _one_line(error.strerror or str(error))
        sys.stderr.write(f"Export failed: cannot write to {directory}: {reason}\n")
        return EXIT_EXPORT_FAILED

    _logger.info("Exported the published data to %s", directory)
    sys.stdout.write(f"{manifest_path}\n")
    return 0
