"""Bringing the countries of the reference file into the store.

:func:`load_countries` is handed the countries the reference file says
and adds to the store every one of them the store does not have. Each
new row says where it came from: the source of the countries
(:mod:`motosphere.reference.countries_source`), the address the release
was fetched from, the day the release was published and the moment of
the loading.

The loading adds, and it does nothing else. A country the store has is
left as it is, also when the file says something else of it, and no
country is ever taken out. What the loading found and did not put right
is told to whoever called it: which countries of the file the store says
otherwise of, and which countries of the store the file does not have.
Which of the two is right there is for a person to decide.

Nothing is fetched. The file was fetched once, by hand, and is part of
the project; the note beside it says from where and when. That is why a
loading is not a collection run of the source, and why the source need
not be switched on for it.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from motosphere.db import times
from motosphere.db.models.country import Country
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod
from motosphere.reference.countries import ReferenceCountry
from motosphere.reference.countries_source import source_of_the_countries

__all__ = [
    "ADDRESS",
    "PUBLISHED_ON",
    "RELEASE",
    "CountriesLoaded",
    "load_countries",
]

# The release of iso-codes the reference file is from, as the note beside
# the file names it.
RELEASE: Final = "4.20.1"
# The day its makers published that release.
PUBLISHED_ON: Final = date(2026, 1, 1)
# The address the release was fetched from: the file that says what the
# rows say, not the front page of a site.
ADDRESS: Final = (
    "https://archive.ubuntu.com/ubuntu/pool/main/i/iso-codes/iso-codes_4.20.1.orig.tar.xz"
)


@dataclass(frozen=True, slots=True)
class CountriesLoaded:
    """What one loading found and did, each country by its code of two letters."""

    # The countries of the file that the store did not have, and has now.
    # In the order of the file.
    added: tuple[str, ...]
    # The countries of the file that the store had already, with the same
    # two codes and the same name. In the order of the file.
    as_they_were: tuple[str, ...]
    # The countries of the file that the store says something else of: it
    # has the code of two letters with another code of three or another
    # name, or it has the code of three letters under another code of
    # two. Nothing was done about them. In the order of the file.
    said_otherwise: tuple[str, ...]
    # The countries of the store whose code of two letters the file does
    # not have. Nothing was done about them. In the order of their codes.
    not_in_the_file: tuple[str, ...]


def load_countries(work: Session, countries: Iterable[ReferenceCountry]) -> CountriesLoaded:
    """Add the countries of the reference file that the store does not have, and say what was found.

    ``countries`` is what the file says, as
    :func:`motosphere.reference.countries.countries_of_the_project` gives
    it. A country is known by its code of two letters. One the store
    does not have is added, with the source of the countries as its
    source, which is stored first when the store does not have it. One
    the store has with the same code of three letters and the same name
    is left alone. One the store says something else of is left alone
    too, and so is a country of the store that the file does not have:
    both are named in what is given back, and nothing is changed and
    nothing deleted.

    All rows of one loading say one moment, for when they were collected
    and when they were last seen: the clock is read once. A loading
    that finds nothing to add writes no country, and nothing at all
    when the store has the source already.

    Everything is part of the unit of work ``work`` and is written to it
    before the function returns, so what the store refuses is refused
    here: a source called as the source of the countries that is
    described otherwise
    (:class:`motosphere.reference.countries_source.CountriesSourceError`),
    and a list that has one code twice.
    """
    source = source_of_the_countries(work)
    moment = times.now()
    stored = work.execute(select(Country.alpha_2, Country.alpha_3, Country.name)).all()
    by_code = {row.alpha_2: (row.alpha_3, row.name) for row in stored}
    codes_of_three = {row.alpha_3 for row in stored}

    new: list[Country] = []
    as_they_were: list[str] = []
    said_otherwise: list[str] = []
    in_the_file: set[str] = set()
    for country in countries:
        in_the_file.add(country.alpha_2)
        there = by_code.get(country.alpha_2)
        if there == (country.alpha_3, country.name):
            as_they_were.append(country.alpha_2)
        elif there is not None or country.alpha_3 in codes_of_three:
            said_otherwise.append(country.alpha_2)
        else:
            new.append(
                Country(
                    alpha_2=country.alpha_2,
                    alpha_3=country.alpha_3,
                    name=country.name,
                    source_id=source.id,
                    source_address=ADDRESS,
                    collected_at=moment,
                    published_on=PUBLISHED_ON,
                    last_verified_at=moment,
                    extraction_method=CollectionMethod.DATASET,
                    # The file gives each value in a field made for it.
                    confidence=Confidence.HIGH,
                    # iso-codes is not the body that keeps the standard.
                    verification_status=VerificationStatus.INDEPENDENT,
                )
            )
    work.add_all(new)
    work.flush()
    return CountriesLoaded(
        added=tuple(country.alpha_2 for country in new),
        as_they_were=tuple(as_they_were),
        said_otherwise=tuple(said_otherwise),
        not_in_the_file=tuple(sorted(code for code in by_code if code not in in_the_file)),
    )
