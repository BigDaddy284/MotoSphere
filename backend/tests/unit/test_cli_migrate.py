"""Tests of what the ``migrate`` command says, and of its place in the command line."""

import pytest

from motosphere.cli import main
from motosphere.cli.migrate import report

STORE = "/data/store.sqlite3"


@pytest.mark.parametrize(
    ("made", "applied", "version", "sentence"),
    [
        (True, [], 0, f"A new data store was made: {STORE} is at schema version 0."),
        (True, [1, 2, 3], 3, f"A new data store was made: {STORE} is at schema version 3."),
        (
            False,
            [1],
            1,
            f"The data store was brought up to date: {STORE} went from schema version 0 to 1.",
        ),
        (
            False,
            [3, 4, 5],
            5,
            f"The data store was brought up to date: {STORE} went from schema version 2 to 5.",
        ),
        (False, [], 5, f"The data store is up to date: {STORE} is at schema version 5."),
    ],
    ids=[
        "a new store, nothing to apply",
        "a new store",
        "one migration",
        "three migrations",
        "up to date",
    ],
)
def test_the_report_says_what_was_done(
    made: bool, applied: list[int], version: int, sentence: str
) -> None:
    assert report(STORE, made, applied, version) == sentence


def test_migrate_is_in_the_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])

    assert exit_info.value.code == 0
    assert "migrate   bring the data store to the newest schema" in capsys.readouterr().out


def test_migrate_has_its_own_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["migrate", "--help"])

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("usage: python -m motosphere migrate")
    assert "Bring the data store to the newest schema." in captured.out
    assert "MOTOSPHERE_STORE_PATH" in captured.out
    assert captured.err == ""


def test_migrate_takes_no_argument(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["migrate", "now"])

    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("usage: python -m motosphere ")
    assert "now" in captured.err
