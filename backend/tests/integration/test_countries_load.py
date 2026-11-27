"""Tests of the loading of the countries, against a real SQLite file.

The store of every test is built the way a real store is built: by the
migrations. What the loading stores is read as SQLite holds it, and what
it must leave alone is written the way a person or another program would
have written it. The statements the loading sends to SQLite are listened
to where a test holds that nothing was written.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import Engine, event
from sqlalchemy.exc import IntegrityError

from motosphere.db.models import Country, Source, SourceOffer
from motosphere.db.models.provenance import Confidence, VerificationStatus
from motosphere.db.models.source import CollectionMethod, InformationType, SourceCategory
from motosphere.db.work import unit_of_work
from motosphere.reference.countries import ReferenceCountry, countries_of_the_project
from motosphere.reference.countries_load import (
    ADDRESS,
    PUBLISHED_ON,
    CountriesLoaded,
    load_countries,
)
from motosphere.reference.countries_source import (
    LICENCE,
    NAME,
    USAGE_RESTRICTIONS,
    WEBSITE,
    CountriesSourceError,
)

RELEASE_ADDRESS = (
    "https://archive.ubuntu.com/ubuntu/pool/main/i/iso-codes/iso-codes_4.20.1.orig.tar.xz"
)
# Three countries as the reference file has them, in its order.
NEW_ZEALAND = ReferenceCountry("NZ", "NZL", "New Zealand")
SWEDEN = ReferenceCountry("SE", "SWE", "Sweden")
TURKIYE = ReferenceCountry("TR", "TUR", "T\u00fcrkiye")
THREE = (NEW_ZEALAND, SWEDEN, TURKIYE)
# When a person put a country in by hand, and where they had it from.
BY_HAND = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)
BY_HAND_AS_KEPT = "2026-11-02T14:00:00.000000+00:00"
BY_HAND_ADDRESS = "https://federation.example/members"
# The tables a loading has nothing to do with, each with how its rows are counted.
COUNT_OF = {
    "collection_run": "SELECT count(*) FROM collection_run",
    "record_change": "SELECT count(*) FROM record_change",
    "review_item": "SELECT count(*) FROM review_item",
}


def said(seconds: int) -> str:
    """What the set clock says so many askings after the first, as the store keeps it."""
    return f"2026-11-19T08:00:{seconds:02d}.000000+00:00"


def countries(store: Engine) -> list[tuple[object, ...]]:
    """Every row of the table of the countries, as SQLite holds it, by its key."""
    with store.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT id, alpha_2, alpha_3, name, source_id, source_address, collected_at, "
            "published_on, last_verified_at, extraction_method, confidence, "
            "verification_status, created_at, updated_at FROM country ORDER BY id"
        )
        return [tuple(row) for row in rows]


def known(store: Engine) -> list[tuple[object, ...]]:
    """The two codes and the name of every country SQLite holds, by its key."""
    return [row[1:4] for row in countries(store)]


def sources(store: Engine) -> list[tuple[object, ...]]:
    """Every source SQLite holds: its key, its name, whether it is on, and its two times."""
    with store.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT id, name, switched_on, terms_read_at, created_at, updated_at "
            "FROM source ORDER BY id"
        )
        return [tuple(row) for row in rows]


def offers(store: Engine) -> list[tuple[object, ...]]:
    """Every offer SQLite holds: its source and its kind, by its key."""
    with store.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT source_id, information_type FROM source_offer ORDER BY id"
        )
        return [tuple(row) for row in rows]


def rows_in(store: Engine, table: str) -> int:
    """How many rows SQLite holds in one of the tables a loading has nothing to do with."""
    with store.connect() as connection:
        (count,) = connection.exec_driver_sql(COUNT_OF[table]).one()
    return int(count)


@contextmanager
def written(store: Engine) -> Iterator[list[str]]:
    """Give the statements that write, as they are sent to SQLite while the block runs."""
    sent: list[str] = []

    def listen(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _many: bool,
    ) -> None:
        if statement.split(maxsplit=1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE"}:
            sent.append(statement)

    event.listen(store, "before_cursor_execute", listen)
    try:
        yield sent
    finally:
        event.remove(store, "before_cursor_execute", listen)


def by_hand(store: Engine, *those: ReferenceCountry) -> int:
    """Store these countries as a person had them from a federation, and give that source's key."""
    with unit_of_work(store) as work:
        federation = Source(
            name="Example Federation",
            website="https://federation.example",
            category=SourceCategory.GOVERNING_BODY,
            collection_method=CollectionMethod.SUBMITTED,
        )
        work.add(federation)
        work.flush()
        work.add_all(
            Country(
                alpha_2=country.alpha_2,
                alpha_3=country.alpha_3,
                name=country.name,
                source_id=federation.id,
                source_address=BY_HAND_ADDRESS,
                collected_at=BY_HAND,
                last_verified_at=BY_HAND,
                extraction_method=CollectionMethod.SUBMITTED,
                confidence=Confidence.MEDIUM,
                verification_status=VerificationStatus.OFFICIAL,
            )
            for country in those
        )
    return federation.id


def loaded(store: Engine, *those: ReferenceCountry) -> CountriesLoaded:
    """Load these countries in a unit of work of its own."""
    with unit_of_work(store) as work:
        return load_countries(work, those)


# ------------------------------------------------------------ what is stored


def test_the_countries_of_the_project_are_loaded_into_an_empty_store(newest: Engine) -> None:
    of_the_file = countries_of_the_project()

    found = loaded(newest, *of_the_file)

    assert len(of_the_file) == 249
    assert known(newest) == [(one.alpha_2, one.alpha_3, one.name) for one in of_the_file]
    assert [row[0] for row in countries(newest)] == list(range(1, 250))
    assert found == CountriesLoaded(
        added=tuple(one.alpha_2 for one in of_the_file),
        as_they_were=(),
        said_otherwise=(),
        not_in_the_file=(),
    )


def test_a_name_is_stored_as_the_file_writes_it(newest: Engine) -> None:
    loaded(newest, *countries_of_the_project())

    names = {row[1]: row[3] for row in countries(newest)}
    assert names["AX"] == "\u00c5land Islands"
    assert names["CI"] == "C\u00f4te d'Ivoire"
    assert names["TR"] == "T\u00fcrkiye"
    assert names["BO"] == "Bolivia, Plurinational State of"


@pytest.mark.usefixtures("clock")
def test_every_new_row_says_where_it_came_from(newest: Engine) -> None:
    loaded(newest, *THREE)

    # The clock was asked once for each of the source and its offer, then
    # once for the loading, then once for each row as it was stored.
    where = (1, RELEASE_ADDRESS, said(2), "2026-01-01", said(2))
    how = ("public dataset", "high", "independent")
    assert countries(newest) == [
        (1, "NZ", "NZL", "New Zealand", *where, *how, said(3), said(3)),
        (2, "SE", "SWE", "Sweden", *where, *how, said(4), said(4)),
        (3, "TR", "TUR", "T\u00fcrkiye", *where, *how, said(5), said(5)),
    ]


def test_what_the_module_says_is_what_the_tests_expect() -> None:
    # The address and the day are written out a second time here, so that
    # a change to what the rows say is made in two places and seen.
    assert ADDRESS == RELEASE_ADDRESS
    assert date(2026, 1, 1) == PUBLISHED_ON


@pytest.mark.usefixtures("clock")
def test_all_rows_of_one_loading_say_one_moment(newest: Engine) -> None:
    loaded(newest, *countries_of_the_project())

    rows = countries(newest)
    assert {(row[6], row[8]) for row in rows} == {(said(2), said(2))}
    # Each row was stored at a moment of its own, after that one.
    assert len({row[12] for row in rows}) == 249
    assert min(str(row[12]) for row in rows) == said(3)


def test_the_source_is_stored_with_the_countries_as_it_is_described(newest: Engine) -> None:
    loaded(newest, *THREE)

    with unit_of_work(newest) as work:
        (source,) = work.query(Source).all()
        assert (source.id, source.name, source.website) == (1, NAME, WEBSITE)
        assert (source.licence, source.usage_restrictions) == (LICENCE, USAGE_RESTRICTIONS)
        assert source.switched_on is False
        assert source.terms_read_at is None
    assert offers(newest) == [(1, "reference data")]
    assert {row[4] for row in countries(newest)} == {1}


def test_a_source_of_the_countries_that_is_there_is_the_one_the_rows_name(newest: Engine) -> None:
    by_hand(newest)
    with unit_of_work(newest) as work:
        source = Source(
            name=NAME,
            website=WEBSITE,
            category=SourceCategory.REFERENCE,
            collection_method=CollectionMethod.DATASET,
            licence=LICENCE,
            usage_restrictions=USAGE_RESTRICTIONS,
        )
        work.add(source)
        work.flush()
        work.add(SourceOffer(source_id=source.id, information_type=InformationType.REFERENCE))
    before = sources(newest)

    with written(newest) as sent:
        loaded(newest, *THREE)

    assert sources(newest) == before
    assert offers(newest) == [(2, "reference data")]
    assert {row[4] for row in countries(newest)} == {2}
    assert all(statement.startswith("INSERT INTO country ") for statement in sent)
    assert sent != []


def test_a_loading_is_no_collection_run_and_leaves_no_history_and_no_doubt(newest: Engine) -> None:
    by_hand(
        newest, ReferenceCountry("TR", "TUR", "Turkey"), ReferenceCountry("XK", "XKX", "Kosovo")
    )

    loaded(newest, *THREE)

    assert [rows_in(newest, table) for table in COUNT_OF] == [0, 0, 0]


# ------------------------------------------------------------- loaded again


@pytest.mark.usefixtures("clock")
def test_a_second_loading_adds_nothing_and_writes_nothing(newest: Engine) -> None:
    of_the_file = countries_of_the_project()
    loaded(newest, *of_the_file)
    before = (countries(newest), sources(newest), offers(newest))

    with written(newest) as sent:
        found = loaded(newest, *of_the_file)

    assert sent == []
    assert (countries(newest), sources(newest), offers(newest)) == before
    assert found == CountriesLoaded(
        added=(),
        as_they_were=tuple(one.alpha_2 for one in of_the_file),
        said_otherwise=(),
        not_in_the_file=(),
    )


def test_listening_for_what_is_written_hears_a_loading_that_writes(newest: Engine) -> None:
    # What the test above relies on: a loading that stores is heard.
    with written(newest) as sent:
        loaded(newest, NEW_ZEALAND)

    assert [statement.split()[2] for statement in sent] == ["source", "source_offer", "country"]


@pytest.mark.usefixtures("clock")
def test_a_later_loading_adds_only_what_the_store_does_not_have(newest: Engine) -> None:
    loaded(newest, NEW_ZEALAND, TURKIYE)
    before = countries(newest)

    with written(newest) as sent:
        found = loaded(newest, *THREE)

    assert found == CountriesLoaded(
        added=("SE",), as_they_were=("NZ", "TR"), said_otherwise=(), not_in_the_file=()
    )
    assert countries(newest)[:2] == before
    # The clock had been asked five times; the sixth is the moment of this
    # loading, and the seventh is when its one row was stored.
    assert countries(newest)[2] == (
        3,
        "SE",
        "SWE",
        "Sweden",
        1,
        RELEASE_ADDRESS,
        said(5),
        "2026-01-01",
        said(5),
        "public dataset",
        "high",
        "independent",
        said(6),
        said(6),
    )
    assert len(sent) == 1


def test_a_country_that_is_there_from_another_source_is_left_as_it_is(newest: Engine) -> None:
    federation = by_hand(newest, SWEDEN)
    before = countries(newest)

    found = loaded(newest, *THREE)

    assert found == CountriesLoaded(
        added=("NZ", "TR"), as_they_were=("SE",), said_otherwise=(), not_in_the_file=()
    )
    assert countries(newest)[:1] == before
    assert before[0][4:6] == (federation, BY_HAND_ADDRESS)
    assert known(newest) == [
        ("SE", "SWE", "Sweden"),
        ("NZ", "NZL", "New Zealand"),
        ("TR", "TUR", "T\u00fcrkiye"),
    ]


# ------------------------------------------- what the store says otherwise of

OTHERWISE = {
    "another name": ReferenceCountry("TR", "TUR", "Turkey"),
    "a name that differs by a capital": ReferenceCountry("TR", "TUR", "T\u00dcRKIYE"),
    "a name with its letter written as two": ReferenceCountry("TR", "TUR", "Tu\u0308rkiye"),
    "a name with a space after it": ReferenceCountry("TR", "TUR", "T\u00fcrkiye "),
    "another code of three": ReferenceCountry("TR", "TRK", "T\u00fcrkiye"),
    "another code of three and another name": ReferenceCountry("TR", "TRK", "Turkey"),
}


@pytest.mark.parametrize("stored", OTHERWISE.values(), ids=OTHERWISE.keys())
def test_a_country_the_store_says_otherwise_of_is_left_and_named(
    newest: Engine, stored: ReferenceCountry
) -> None:
    by_hand(newest, stored)
    before = countries(newest)

    found = loaded(newest, *THREE)

    assert found == CountriesLoaded(
        added=("NZ", "SE"), as_they_were=(), said_otherwise=("TR",), not_in_the_file=()
    )
    assert countries(newest)[:1] == before
    assert known(newest) == [
        (stored.alpha_2, stored.alpha_3, stored.name),
        ("NZ", "NZL", "New Zealand"),
        ("SE", "SWE", "Sweden"),
    ]


def test_a_code_of_three_the_store_has_under_another_code_of_two_is_left_and_named(
    newest: Engine,
) -> None:
    by_hand(newest, ReferenceCountry("TK", "TUR", "T\u00fcrkiye"))
    before = countries(newest)

    found = loaded(newest, *THREE)

    # The file says TUR is the code of TR. The store has it for TK, which
    # the file does not have.
    assert found == CountriesLoaded(
        added=("NZ", "SE"), as_they_were=(), said_otherwise=("TR",), not_in_the_file=("TK",)
    )
    assert countries(newest)[:1] == before
    assert [row[0] for row in known(newest)] == ["TK", "NZ", "SE"]


def test_a_country_the_file_does_not_have_is_left_and_named(newest: Engine) -> None:
    by_hand(newest, ReferenceCountry("XK", "XKX", "Kosovo"))
    before = countries(newest)

    found = loaded(newest, *countries_of_the_project())

    assert found.not_in_the_file == ("XK",)
    assert (len(found.added), found.as_they_were, found.said_otherwise) == (249, (), ())
    assert countries(newest)[:1] == before
    assert len(countries(newest)) == 250


def test_the_countries_the_file_does_not_have_are_named_in_the_order_of_their_codes(
    newest: Engine,
) -> None:
    by_hand(
        newest,
        ReferenceCountry("XK", "XKX", "Kosovo"),
        SWEDEN,
        ReferenceCountry("AN", "ANT", "Netherlands Antilles"),
        ReferenceCountry("SU", "SUN", "USSR"),
    )

    found = loaded(newest, *THREE)

    assert found.not_in_the_file == ("AN", "SU", "XK")
    assert found.as_they_were == ("SE",)
    assert len(countries(newest)) == 6


def test_what_was_found_is_named_in_the_order_of_the_file(newest: Engine) -> None:
    by_hand(
        newest,
        ReferenceCountry("AD", "AND", "Andorra"),
        ReferenceCountry("ZW", "ZWE", "Zimbabwe"),
        ReferenceCountry("BE", "BEL", "Belgium, Kingdom of"),
        ReferenceCountry("YE", "YEM", "Yemen Republic"),
    )
    the_file = (
        ReferenceCountry("ZW", "ZWE", "Zimbabwe"),
        TURKIYE,
        ReferenceCountry("YE", "YEM", "Yemen"),
        ReferenceCountry("AD", "AND", "Andorra"),
        NEW_ZEALAND,
        ReferenceCountry("BE", "BEL", "Belgium"),
    )

    found = loaded(newest, *the_file)

    assert found == CountriesLoaded(
        added=("TR", "NZ"),
        as_they_were=("ZW", "AD"),
        said_otherwise=("YE", "BE"),
        not_in_the_file=(),
    )
    assert [row[0] for row in known(newest)] == ["AD", "ZW", "BE", "YE", "TR", "NZ"]


def test_nothing_is_changed_and_nothing_deleted_whatever_is_found(newest: Engine) -> None:
    by_hand(
        newest,
        SWEDEN,
        ReferenceCountry("TR", "TUR", "Turkey"),
        ReferenceCountry("NC", "NZL", "New Zealand"),
        ReferenceCountry("XK", "XKX", "Kosovo"),
    )
    before = countries(newest)

    with written(newest) as sent:
        found = loaded(newest, *THREE)

    assert found == CountriesLoaded(
        added=(), as_they_were=("SE",), said_otherwise=("NZ", "TR"), not_in_the_file=("NC", "XK")
    )
    assert countries(newest) == before
    # Only the source of the countries and its offer were stored.
    assert [statement.split()[:3] for statement in sent] == [
        ["INSERT", "INTO", "source"],
        ["INSERT", "INTO", "source_offer"],
    ]


# ------------------------------------------------------- what is handed over


def test_a_list_that_is_given_one_country_at_a_time_is_taken(newest: Engine) -> None:
    with unit_of_work(newest) as work:
        found = load_countries(work, (country for country in THREE))

    assert found.added == ("NZ", "SE", "TR")
    assert len(countries(newest)) == 3


def test_no_countries_are_no_rows(newest: Engine) -> None:
    by_hand(newest, SWEDEN)

    found = loaded(newest)

    assert found == CountriesLoaded(
        added=(), as_they_were=(), said_otherwise=(), not_in_the_file=("SE",)
    )
    assert known(newest) == [("SE", "SWE", "Sweden")]


TWICE = {
    "a code of two letters": (NEW_ZEALAND, SWEDEN, ReferenceCountry("NZ", "NZX", "Aotearoa")),
    "a code of three letters": (NEW_ZEALAND, SWEDEN, ReferenceCountry("NX", "NZL", "Aotearoa")),
    "a whole country": (NEW_ZEALAND, SWEDEN, NEW_ZEALAND),
}


@pytest.mark.parametrize("those", TWICE.values(), ids=TWICE.keys())
def test_a_list_that_has_one_code_twice_is_refused_by_the_store(
    newest: Engine, those: tuple[ReferenceCountry, ...]
) -> None:
    with pytest.raises(IntegrityError, match=r"UNIQUE constraint failed: country\.alpha_"):
        loaded(newest, *those)

    assert countries(newest) == []
    assert sources(newest) == []


# ------------------------------------------------------- the unit of work


def test_a_source_that_is_described_otherwise_refuses_the_loading(newest: Engine) -> None:
    with unit_of_work(newest) as work:
        work.add(
            Source(
                name=NAME,
                website="https://iso-codes.example",
                category=SourceCategory.REFERENCE,
                collection_method=CollectionMethod.DATASET,
                licence=LICENCE,
                usage_restrictions=USAGE_RESTRICTIONS,
            )
        )
    before = sources(newest)

    with pytest.raises(CountriesSourceError, match="It differs in its website and offer of"):
        loaded(newest, *THREE)

    assert countries(newest) == []
    assert sources(newest) == before


def test_the_rows_are_written_when_the_function_returns(newest: Engine) -> None:
    with unit_of_work(newest) as work:
        load_countries(work, THREE)

        rows = work.connection().exec_driver_sql("SELECT alpha_2 FROM country ORDER BY id")
        assert [code for (code,) in rows] == ["NZ", "SE", "TR"]


def test_nothing_is_kept_when_the_unit_of_work_fails_afterwards(newest: Engine) -> None:
    def the_work() -> None:
        with unit_of_work(newest) as work:
            load_countries(work, THREE)
            raise RuntimeError("the job died")

    with pytest.raises(RuntimeError, match="the job died"):
        the_work()

    assert countries(newest) == []
    assert sources(newest) == []
    assert offers(newest) == []


def test_what_the_unit_of_work_did_before_goes_with_a_refused_loading(newest: Engine) -> None:
    def the_work() -> None:
        with unit_of_work(newest) as work:
            work.add(
                Source(
                    name="Example Federation",
                    website="https://federation.example",
                    category=SourceCategory.GOVERNING_BODY,
                    collection_method=CollectionMethod.SUBMITTED,
                )
            )
            load_countries(work, (NEW_ZEALAND, NEW_ZEALAND))

    with pytest.raises(IntegrityError):
        the_work()

    assert sources(newest) == []
    assert countries(newest) == []
