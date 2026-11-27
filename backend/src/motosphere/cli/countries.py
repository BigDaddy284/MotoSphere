"""The ``countries`` command: load the countries of the reference file into the data store."""

import argparse
import sys

from motosphere.cli.store import StoreNotReadyError, store_to_work_on
from motosphere.core.settings import Settings
from motosphere.db.work import unit_of_work
from motosphere.reference.countries import CountriesFileError, countries_of_the_project
from motosphere.reference.countries_load import RELEASE, CountriesLoaded, load_countries
from motosphere.reference.countries_source import CountriesSourceError

__all__ = ["EXIT_NOT_LOADED", "add_parser", "report", "run"]

# The exit code when nothing was loaded and the store is as it was.
EXIT_NOT_LOADED = 1


def add_parser(commands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Register the ``countries`` command."""
    parser = commands.add_parser(
        "countries",
        help="load the countries into the data store",
        description=(
            "Load the countries of the reference file that comes with the pipeline into "
            "the data store. A country the store does not have is added. No country is "
            "changed and none is taken out: what the file says otherwise of a country "
            "waits in the review queue. Nothing is fetched. The store is the file the "
            "setting MOTOSPHERE_STORE_PATH names, and it must be at the newest schema."
        ),
        allow_abbrev=False,
    )
    parser.set_defaults(handler=run)


def _so_many(number: int, were: str) -> str:
    if number == 0:
        return f"none was {were}"
    return f"1 was {were}" if number == 1 else f"{number} were {were}"


def report(path: str, loaded: CountriesLoaded) -> str:
    """Say what a loading into the store at ``path`` found, one sentence or two to a line.

    The first line counts the countries of the release, those that were
    added and those that were there already as the release has them. A
    line follows for the countries the store says something else of, and
    one for the countries the release does not have, each only where
    there are such, with their codes of two letters.
    """
    otherwise = len(loaded.said_otherwise)
    of_the_release = len(loaded.added) + len(loaded.as_they_were) + otherwise
    lines = [
        f"Of the {'1 country' if of_the_release == 1 else f'{of_the_release} countries'} "
        f"of release {RELEASE} of iso-codes, {_so_many(len(loaded.added), 'added')} to the "
        f"data store {path} and {_so_many(len(loaded.as_they_were), 'there already')}."
    ]
    if otherwise:
        lines.append(
            f"The data store says something else of {otherwise} of them than the release "
            f"does: {', '.join(loaded.said_otherwise)}. "
            f"{'It was left as it is' if otherwise == 1 else 'They were left as they are'}, "
            "and what the release says waits in the review queue."
        )
    if loaded.not_in_the_file:
        one = len(loaded.not_in_the_file) == 1
        lines.append(
            "The data store has "
            f"{'1 country' if one else f'{len(loaded.not_in_the_file)} countries'} that the "
            f"release does not have: {', '.join(loaded.not_in_the_file)}. "
            f"{'It was left as it is' if one else 'They were left as they are'}."
        )
    return "\n".join(lines)


def run(_arguments: argparse.Namespace, settings: Settings) -> int:
    """Load the countries in one unit of work and write what was found to standard output.

    A store that is not ready gives its one sentence on standard error
    and the exit code 1, and so does a loading that is refused: by a
    countries file that is damaged, or by a source called as the source
    of the countries that is described otherwise. The store is then as
    it was. Countries the store says something else of are no failure:
    they are named, and the exit code is 0.
    """
    try:
        store = store_to_work_on(settings)
    except StoreNotReadyError as error:
        sys.stderr.write(f"{error}\n")
        return EXIT_NOT_LOADED
    try:
        countries = countries_of_the_project()
        with unit_of_work(store) as work:
            loaded = load_countries(work, countries)
    except (CountriesFileError, CountriesSourceError) as error:
        sys.stderr.write(f"{error}\n")
        return EXIT_NOT_LOADED

    sys.stdout.write(report(str(settings.store_path.resolve()), loaded) + "\n")
    return 0
