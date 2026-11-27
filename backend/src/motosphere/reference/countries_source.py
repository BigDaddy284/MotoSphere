"""The source of the countries, as the store knows it.

The countries of the reference file are from the project iso-codes.
``DATA_SOURCES.md`` says what was found out about it, and the note beside
the file says which release the file is from. This module says the same
to the store: what the row of that source in the table of the sources
holds, and which kind of information it offers.
:func:`source_of_the_countries` gives that row, and stores it first when
the store does not have it.

The pipeline describes the source: its name, its website, its kind, how
it is collected from, where its terms are, its licence and what the
licence asks for. The rest of a source's row is for people: whether a
person has read its terms, whether it is switched on, how often it is
looked at and which country it is of. This module sets none of those
and looks at none of them.
"""

from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from motosphere.db.models.source import (
    CollectionMethod,
    InformationType,
    Source,
    SourceCategory,
    SourceOffer,
)

__all__ = [
    "DESCRIBED",
    "LICENCE",
    "NAME",
    "OFFERS",
    "USAGE_RESTRICTIONS",
    "WEBSITE",
    "CountriesSourceError",
    "source_of_the_countries",
]

# What the source is called in the store. It is the name its makers give it.
NAME: Final = "iso-codes"
# Where the project is at home.
WEBSITE: Final = "https://salsa.debian.org/iso-codes-team/iso-codes"
# The licence of its data files, as its release names it.
LICENCE: Final = "LGPL-2.1-or-later"
# What that licence asks of whoever passes the list on, in plain words.
USAGE_RESTRICTIONS: Final = (
    "Every copy keeps the notice of copyright and comes with the licence. "
    "A changed copy says that it was changed, and when. "
    "A work that takes over the list, or part of it, is passed on under the same licence, "
    "free of charge."
)

# What the pipeline says of the source, column by column, in the order of
# the table. The source has no page of terms of its own: its terms are
# its licence, whose text is beside the file.
DESCRIBED: Final[tuple[tuple[str, object], ...]] = (
    ("website", WEBSITE),
    ("category", SourceCategory.REFERENCE),
    ("collection_method", CollectionMethod.DATASET),
    ("terms_address", None),
    ("licence", LICENCE),
    ("usage_restrictions", USAGE_RESTRICTIONS),
)
# The kinds of information it offers.
OFFERS: Final = (InformationType.REFERENCE,)

# What each described column is called in a sentence.
_IN_WORDS: Final = {
    "website": "website",
    "category": "kind",
    "collection_method": "way of collecting",
    "terms_address": "address of its terms",
    "licence": "licence",
    "usage_restrictions": "restrictions of use",
}


class CountriesSourceError(ValueError):
    """The store has a source of this name that is not the one the pipeline describes."""


def source_of_the_countries(work: Session) -> Source:
    """Give the source of the countries, and store it first when the store does not have it.

    The source is known by its name. When the store has no source of that
    name, one is stored as this module describes it, with what it offers.
    It is switched off, and it says that nobody has read its terms: both
    are for a person to say.

    When the store has one, it is given as it is and nothing is written.
    It must then be as described, and offer what is described; what else
    it offers, and what people have said of it, is not looked at. A
    source of this name that is described otherwise is refused with a
    :class:`CountriesSourceError` that says in what it differs, and it is
    left as it is: which of the two is right is for a person to decide.

    Everything is part of the unit of work ``work``.
    """
    source = work.scalars(select(Source).where(Source.name == NAME)).one_or_none()
    if source is None:
        source = Source(name=NAME, **dict(DESCRIBED))
        work.add(source)
        work.flush()
        work.add_all(SourceOffer(source_id=source.id, information_type=kind) for kind in OFFERS)
        work.flush()
        return source

    different = [
        _IN_WORDS[column] for column, value in DESCRIBED if getattr(source, column) != value
    ]
    offered = set(
        work.scalars(select(SourceOffer.information_type).where(SourceOffer.source_id == source.id))
    )
    different += [f'offer of "{kind}"' for kind in OFFERS if kind not in offered]
    if different:
        raise CountriesSourceError(
            f'The store has a source called "{NAME}" that is not the source of the countries '
            f"as the pipeline describes it. It differs in its {_listed(different)}. "
            "Nothing was changed."
        )
    return source


def _listed(words: list[str]) -> str:
    """Say several things in one breath: "a", "a and b", "a, b and c"."""
    if len(words) == 1:
        return words[0]
    return f"{', '.join(words[:-1])} and {words[-1]}"
