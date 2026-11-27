"""Tests of what the ``countries`` command says, and of its place in the command line."""

import pytest

from motosphere.cli import countries, main
from motosphere.cli.countries import EXIT_NOT_LOADED, report
from motosphere.reference.countries_load import CountriesLoaded

STORE = "/data/store.sqlite3"
IN_THE_QUEUE = "and what the release says waits in the review queue."


def found(
    added: tuple[str, ...] = (),
    as_they_were: tuple[str, ...] = (),
    said_otherwise: tuple[str, ...] = (),
    not_in_the_file: tuple[str, ...] = (),
) -> CountriesLoaded:
    return CountriesLoaded(
        added=added,
        as_they_were=as_they_were,
        said_otherwise=said_otherwise,
        not_in_the_file=not_in_the_file,
    )


def first(countries_of_the_release: str, added: str, there: str) -> str:
    return (
        f"Of the {countries_of_the_release} of release 4.20.1 of iso-codes, {added} added to "
        f"the data store {STORE} and {there} there already."
    )


@pytest.mark.parametrize(
    ("loaded", "sentence"),
    [
        (found(added=("AD", "AE", "AF")), first("3 countries", "3 were", "none was")),
        (found(as_they_were=("AD", "AE", "AF")), first("3 countries", "none was", "3 were")),
        (found(added=("AD",), as_they_were=("AE",)), first("2 countries", "1 was", "1 was")),
        (
            found(added=("AD", "AE"), as_they_were=("AF", "AG", "AI")),
            first("5 countries", "2 were", "3 were"),
        ),
        (found(added=("AD",)), first("1 country", "1 was", "none was")),
        (found(as_they_were=("AD",)), first("1 country", "none was", "1 was")),
        (found(), first("0 countries", "none was", "none was")),
    ],
    ids=[
        "all added",
        "all there already",
        "one and one",
        "two and three",
        "one country, added",
        "one country, there already",
        "no country at all",
    ],
)
def test_the_first_line_counts_what_was_added_and_what_was_there(
    loaded: CountriesLoaded, sentence: str
) -> None:
    assert report(STORE, loaded) == sentence


@pytest.mark.parametrize(
    ("loaded", "lines"),
    [
        (
            found(as_they_were=("AD",), said_otherwise=("TR",)),
            [
                first("2 countries", "none was", "1 was"),
                "The data store says something else of 1 of them than the release does: TR. "
                f"It was left as it is, {IN_THE_QUEUE}",
            ],
        ),
        (
            found(added=("AD",), said_otherwise=("FR", "NZ", "TR")),
            [
                first("4 countries", "1 was", "none was"),
                "The data store says something else of 3 of them than the release does: "
                f"FR, NZ, TR. They were left as they are, {IN_THE_QUEUE}",
            ],
        ),
        (
            found(as_they_were=("AD", "AE"), not_in_the_file=("XK",)),
            [
                first("2 countries", "none was", "2 were"),
                "The data store has 1 country that the release does not have: XK. "
                "It was left as it is.",
            ],
        ),
        (
            found(as_they_were=("AD", "AE"), not_in_the_file=("XA", "XK")),
            [
                first("2 countries", "none was", "2 were"),
                "The data store has 2 countries that the release does not have: XA, XK. "
                "They were left as they are.",
            ],
        ),
        (
            found(
                added=("AD",),
                as_they_were=("AE",),
                said_otherwise=("TR", "FR"),
                not_in_the_file=("XK",),
            ),
            [
                first("4 countries", "1 was", "1 was"),
                "The data store says something else of 2 of them than the release does: "
                f"TR, FR. They were left as they are, {IN_THE_QUEUE}",
                "The data store has 1 country that the release does not have: XK. "
                "It was left as it is.",
            ],
        ),
    ],
    ids=[
        "one the store says otherwise of",
        "three the store says otherwise of",
        "one the release does not have",
        "two the release does not have",
        "all three lines, the codes in the order they were given",
    ],
)
def test_a_line_follows_for_what_the_store_says_otherwise_of_and_for_what_the_release_lacks(
    loaded: CountriesLoaded, lines: list[str]
) -> None:
    assert report(STORE, loaded).split("\n") == lines


def test_the_report_names_the_release_the_loading_has(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(countries, "RELEASE", "5.0")

    assert report(STORE, found(added=("AD", "AE"))) == (
        f"Of the 2 countries of release 5.0 of iso-codes, 2 were added to the data store {STORE} "
        "and none was there already."
    )


def test_what_is_not_loaded_ends_with_the_exit_code_1() -> None:
    assert EXIT_NOT_LOADED == 1


def test_countries_is_in_the_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])

    assert exit_info.value.code == 0
    listed = capsys.readouterr().out.splitlines()
    assert [line.split(maxsplit=1) for line in listed if line.startswith("    countries ")] == [
        ["countries", "load the countries into the data store"]
    ]


def test_countries_has_its_own_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["countries", "--help"])

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("usage: python -m motosphere countries")
    said = " ".join(captured.out.split())
    assert "Load the countries of the reference file that comes with the pipeline" in said
    assert "No country is changed and none is taken out" in said
    assert "Nothing is fetched." in said
    assert "MOTOSPHERE_STORE_PATH" in said
    assert captured.err == ""


def test_countries_takes_no_argument(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["countries", "again"])

    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unrecognized arguments: again" in captured.err
