"""Tests of how the source of the countries is described, without a store."""

from importlib import resources

from motosphere.db.models import Source
from motosphere.db.models.source import CollectionMethod, InformationType, SourceCategory
from motosphere.db.texts import WHITE_SPACE
from motosphere.reference.countries import ORIGIN_FOLDER
from motosphere.reference.countries_source import (
    DESCRIBED,
    LICENCE,
    NAME,
    OFFERS,
    USAGE_RESTRICTIONS,
    WEBSITE,
    CountriesSourceError,
)

# The columns of a source that are for people to fill, and its name, which
# is what it is known by.
NOT_DESCRIBED = ["name", "scan_every_hours", "terms_read_at", "switched_on", "country_id"]


def _beside_the_file(file: str) -> str:
    folder = resources.files("motosphere.reference").joinpath(ORIGIN_FOLDER)
    return folder.joinpath(file).read_bytes().decode("utf-8")


def test_the_source_is_called_what_its_makers_call_it() -> None:
    assert NAME == "iso-codes"
    # The folder that holds what was taken from it has the same name.
    assert NAME == ORIGIN_FOLDER


def test_the_source_is_a_reference_list_read_as_a_public_dataset() -> None:
    described = dict(DESCRIBED)

    assert described["category"] is SourceCategory.REFERENCE
    assert described["collection_method"] is CollectionMethod.DATASET
    assert described["terms_address"] is None


def test_the_source_offers_reference_data_and_nothing_else() -> None:
    assert OFFERS == (InformationType.REFERENCE,)


def test_the_description_has_its_three_texts() -> None:
    described = dict(DESCRIBED)

    assert described["website"] is WEBSITE
    assert described["licence"] is LICENCE
    assert described["usage_restrictions"] is USAGE_RESTRICTIONS


def test_the_description_names_columns_of_a_source_in_the_order_of_the_table() -> None:
    columns = [column.name for column in Source.__table__.columns]
    described = [column for column, _ in DESCRIBED]

    assert described == [
        "website",
        "category",
        "collection_method",
        "terms_address",
        "licence",
        "usage_restrictions",
    ]
    assert described == [column for column in columns if column in described]


def test_what_is_for_people_to_say_is_not_described() -> None:
    columns = [column.name for column in Source.__table__.columns]
    described = [column for column, _ in DESCRIBED]

    # Every column of a source is described, or it is one of these, or it
    # is one of the three that are the store's own.
    assert sorted(described + NOT_DESCRIBED + ["id", "created_at", "updated_at"]) == sorted(columns)


def test_the_website_is_one_address_without_white_space() -> None:
    assert WEBSITE == "https://salsa.debian.org/iso-codes-team/iso-codes"
    assert not any(chr(number) in WEBSITE for number in WHITE_SPACE)


def test_the_licence_is_named_as_the_release_names_it() -> None:
    assert LICENCE == "LGPL-2.1-or-later"


def test_the_restrictions_say_what_the_licence_asks_in_plain_words() -> None:
    assert USAGE_RESTRICTIONS == (
        "Every copy keeps the notice of copyright and comes with the licence. "
        "A changed copy says that it was changed, and when. "
        "A work that takes over the list, or part of it, is passed on under the same "
        "licence, free of charge."
    )


def test_what_is_written_beside_the_file_names_the_same_website_and_licence() -> None:
    written = _beside_the_file("README.md")

    assert f"(<{WEBSITE}>)" in written
    assert f'SPDX-License-Identifier = "{LICENCE}"' in written


def test_the_text_of_the_licence_is_beside_the_file_under_its_name() -> None:
    text = _beside_the_file(f"{LICENCE}.txt")

    assert "GNU LESSER GENERAL PUBLIC LICENSE" in text
    assert "Version 2.1, February 1999" in text


def test_the_refusal_is_an_error_of_its_own_kind_and_a_value_error() -> None:
    assert issubclass(CountriesSourceError, ValueError)
    assert CountriesSourceError is not ValueError
