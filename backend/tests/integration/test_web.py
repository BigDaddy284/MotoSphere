"""Tests of a web address, with a table made in a real SQLite file.

The model here is made for the tests. It is a subclass of the real
``Base``, so it proves what a model gets when it says that a column is a
web address, but it is kept in a schema of its own (``Proof.metadata``),
so the real schema never sees it.
"""

import re

import pytest
from sqlalchemy import Engine, MetaData, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base, broken_rules
from motosphere.db.texts import WHITE_SPACE
from motosphere.db.web import WebAddress, WebAddressText
from motosphere.db.work import unit_of_work

A_TIME = "2026-11-19T08:00:00.000000+00:00"
AN_ADDRESS = "https://example.org/"
REFUSED = "CHECK constraint failed: ck_proof_source_{}_web_address"
THE_CHECK = (
    "CONSTRAINT ck_proof_source_{0}_web_address CHECK ((({0} GLOB "
    "'[Hh][Tt][Tt][Pp][Ss]://[^/?#]*') OR ({0} GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*')) AND NOT ({0} "
    "GLOB '*[' || char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, "
    "8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288) || ']*') AND "
    "instr({0}, char(0)) = 0)"
)

# Each text that is not a web address, with what it is.
NOT_ONE = {
    "no characters": "",
    "a space": " ",
    "the name of a site alone": "example.org",
    "a name and a path": "www.example.org/tracks",
    "two slashes and no scheme": "//example.org",
    "the scheme for files": "ftp://example.org/",
    "the scheme for a script": "javascript:alert(1)",
    "the scheme for mail": "mailto:someone@example.org",
    "a file on this computer": "file:///C:/tracks.html",
    "another scheme with an address in it": "data:text/html,https://example.org",
    "https and nothing after it": "https://",
    "http and nothing after it": "http://",
    "a third slash where the name must begin": "https:///tracks",
    "a question where the name must begin": "https://?country=NL",
    "a place on the page where the name must begin": "https://#list",
    "a third slash where the name must begin, after http": "http:///tracks",
    "a question where the name must begin, after http": "http://?country=NL",
    "a place on the page where the name must begin, after http": "http://#list",
    "one slash": "https:/example.org",
    "no slash": "https:example.org",
    "a letter too many in the scheme": "httpss://example.org",
    "words before the scheme": "see https://example.org",
    "a letter before the scheme": "xhttp://example.org",
    "a space before it": " https://example.org",
    "a space after it": "https://example.org ",
    "a line end after it": "https://example.org\n",
    "the line end of Windows after it": "https://example.org\r\n",
    "a space in it": "https://example.org/the tracks",
    "a tab in it": "https://example.org/the\ttracks",
    "the space that cannot be broken in it": "https://example.org/the" + chr(160) + "tracks",
    "the wide space in it": "https://example.org/" + chr(12288),
    "only a space after the scheme": "https:// ",
    "two addresses": "https://example.org https://example.com",
    "a character with the number 0": "https://example.org/" + chr(0),
    "a space behind a character with the number 0": "https://example.org/" + chr(0) + " b",
}


class Proof(Base):
    """A model of the tests' own: what ``Base`` gives a web address, in a schema of its own."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofSource(Proof):
    __tablename__ = "proof_source"

    website: Mapped[WebAddress]
    # No value, or a web address.
    feed: Mapped[WebAddress | None]
    # A model that says more of the column.
    link: Mapped[WebAddress | None] = mapped_column(unique=True)
    # Text of any kind, as before.
    note: Mapped[str]


@pytest.fixture
def made(store: Engine) -> Engine:
    """The store, with the table of the tests made in it."""
    with store.begin() as connection:
        Proof.metadata.create_all(connection)
    return store


def source(**said: str | None) -> ProofSource:
    """A source every column of which is as it must be, unless ``said`` otherwise."""
    as_it_must_be = {"website": AN_ADDRESS, "feed": None, "link": None, "note": ""}
    return ProofSource(**(as_it_must_be | said))


def written(made: Engine) -> str:
    """How the file itself says the table is made."""
    with made.connect() as connection:
        text = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE name = 'proof_source'"
        ).scalar_one()
    return str(text)


def websites(made: Engine) -> list[str]:
    """The websites of the sources the file holds, read without the model."""
    with made.connect() as connection:
        return list(
            connection.exec_driver_sql("SELECT website FROM proof_source ORDER BY id").scalars()
        )


def test_a_web_address_is_text_in_a_strict_table(made: Engine) -> None:
    columns = ProofSource.__table__.c

    assert [column.name for column in columns if isinstance(column.type, WebAddressText)] == [
        "website",
        "feed",
        "link",
    ]
    assert broken_rules(Proof.metadata) == []

    with made.connect() as connection:
        in_the_file = {
            name: (declared, bool(required))
            for _, name, declared, required, _, _ in connection.exec_driver_sql(
                "PRAGMA table_info(proof_source)"
            )
        }

    assert in_the_file == {
        "id": ("INTEGER", True),
        "website": ("TEXT", True),
        "feed": ("TEXT", False),
        "link": ("TEXT", False),
        "note": ("TEXT", True),
        "created_at": ("TEXT", True),
        "updated_at": ("TEXT", True),
    }


def test_the_file_has_a_check_named_by_the_rule_for_each_such_column_and_for_no_other(
    made: Engine,
) -> None:
    sources = written(made)

    assert sorted(re.findall(r"CONSTRAINT (\w+) CHECK", sources)) == [
        "ck_proof_source_feed_web_address",
        "ck_proof_source_link_web_address",
        "ck_proof_source_website_web_address",
    ]
    for column in ("website", "feed", "link"):
        assert THE_CHECK.format(column) in sources
    assert "CONSTRAINT uq_proof_source_link UNIQUE (link)" in sources


@pytest.mark.parametrize(
    "address",
    [
        "https://example.org",
        "http://example.org/",
        "HTTPS://Example.ORG/Tracks",
        "HTTP://EXAMPLE.ORG/",
        "hTtP://example.org",
        "https://example.org:8443/tracks/index.html?country=NL&page=2#list",
        "https://example.org/the%20tracks",
        "https://example.org/caf" + chr(233),
        "http://192.0.2.1/",
        "https://[2001:db8::1]/",
        "http://x",
        "https://example.org/*?[a-z]^",
        "https://example.org/o'brien",
    ],
    ids=[
        "https",
        "http",
        "large letters",
        "large letters only",
        "small and large letters in the scheme",
        "a port, a path, a question and a place on the page",
        "a space written as its number",
        "a letter beyond ASCII",
        "a number for a site",
        "a number of the newer kind for a site",
        "one character after the scheme",
        "the characters GLOB has a use for",
        "a quote",
    ],
)
def test_a_web_address_is_stored_as_it_was_given(made: Engine, address: str) -> None:
    with unit_of_work(made) as work:
        work.add(source(website=address))

    assert websites(made) == [address]
    with unit_of_work(made) as work:
        assert work.scalars(select(ProofSource.website)).one() == address


@pytest.mark.parametrize("text", list(NOT_ONE.values()), ids=list(NOT_ONE))
def test_text_that_is_not_a_web_address_is_refused_and_the_refusal_names_the_check(
    made: Engine, text: str
) -> None:
    refusal = REFUSED.format("website")

    with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
        work.add_all([source(), source(website=text)])

    assert websites(made) == []


def test_every_white_space_character_is_refused_wherever_it_is(made: Engine) -> None:
    stored = []
    for number in WHITE_SPACE:
        for address in (
            "https://" + chr(number) + "example.org",
            "https://example.org/the" + chr(number) + "tracks",
            "https://example.org/" + chr(number),
        ):
            try:
                with unit_of_work(made) as work:
                    work.add(source(website=address))
            except IntegrityError:
                continue
            stored.append(address)

    assert stored == []
    assert websites(made) == []


@pytest.mark.parametrize(
    "address",
    [
        "https://no-such-site.invalid/",
        "https://.",
        "https://example.org/" + chr(8203),
        "https://example.org/" + chr(1),
    ],
    ids=[
        "a site there is not",
        "a full stop for a name",
        "a space without width, which Python does not call white space",
        "a control character that is not white space",
    ],
)
def test_the_check_does_not_know_whether_an_address_leads_anywhere(
    made: Engine, address: str
) -> None:
    with unit_of_work(made) as work:
        work.add(source(website=address))

    assert websites(made) == [address]


def test_text_that_is_not_a_web_address_written_past_the_model_is_refused(made: Engine) -> None:
    statement = (
        "INSERT INTO proof_source (website, note, created_at, updated_at) VALUES (?, '', ?, ?)"
    )
    refusal = REFUSED.format("website")

    with made.begin() as connection:
        connection.exec_driver_sql(statement, (AN_ADDRESS, A_TIME, A_TIME))
    # The number is stored as the text '1' by the strict table, and that is no address.
    for not_one in ("example.org", "https://example.org/the tracks", "", 1):
        with pytest.raises(IntegrityError, match=refusal), made.begin() as connection:
            connection.exec_driver_sql(statement, (not_one, A_TIME, A_TIME))

    assert websites(made) == [AN_ADDRESS]


def test_a_change_to_text_that_is_not_a_web_address_is_refused_and_the_row_stays_as_it_was(
    made: Engine,
) -> None:
    refusal = REFUSED.format("website")
    with unit_of_work(made) as work:
        work.add(source())

    with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
        work.scalars(select(ProofSource)).one().website = "example.org"
    with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
        work.execute(update(ProofSource).values(website=""))
    with pytest.raises(IntegrityError, match=refusal), made.begin() as connection:
        connection.exec_driver_sql("UPDATE proof_source SET website = 'https://example.org '")

    assert websites(made) == [AN_ADDRESS]


def test_a_change_to_another_web_address_is_stored(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(source())
    with unit_of_work(made) as work:
        work.scalars(select(ProofSource)).one().website = "http://example.com/tracks"

    assert websites(made) == ["http://example.com/tracks"]


def test_a_column_that_may_be_without_a_value_holds_none_or_a_web_address(made: Engine) -> None:
    refusal = REFUSED.format("feed")

    with unit_of_work(made) as work:
        work.add_all([source(), source(feed="https://example.org/feed.xml")])
    for not_one in ("", " ", "example.org/feed.xml"):
        with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
            work.add(source(feed=not_one))

    with made.connect() as connection:
        feeds = connection.exec_driver_sql("SELECT feed FROM proof_source ORDER BY id").scalars()
        assert list(feeds) == [None, "https://example.org/feed.xml"]


def test_a_column_of_which_the_model_says_more_has_its_check_too(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(source(link="https://example.org/a"))
    with (
        pytest.raises(IntegrityError, match=REFUSED.format("link")),
        unit_of_work(made) as work,
    ):
        work.add(source(link="example.org/b"))
    with (
        pytest.raises(
            IntegrityError, match=re.escape("UNIQUE constraint failed: proof_source.link")
        ),
        unit_of_work(made) as work,
    ):
        work.add(source(link="https://example.org/a"))

    with made.connect() as connection:
        links = connection.exec_driver_sql("SELECT link FROM proof_source ORDER BY id").scalars()
        assert list(links) == ["https://example.org/a"]


def test_two_spellings_of_one_address_are_two_addresses_to_the_store(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all(
            [
                source(link="https://example.org/a"),
                source(link="HTTPS://EXAMPLE.ORG/a"),
                source(link="https://example.org/a/"),
            ]
        )

    with unit_of_work(made) as work:
        found = work.scalars(
            select(ProofSource.id).where(ProofSource.link == "https://example.org/a")
        ).all()

    assert found == [1]


def test_text_of_any_kind_is_stored_in_another_column_as_before(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all([source(note=""), source(note="example.org"), source(note=" ")])

    with made.connect() as connection:
        notes = connection.exec_driver_sql("SELECT note FROM proof_source ORDER BY id").scalars()
        assert list(notes) == ["", "example.org", " "]
