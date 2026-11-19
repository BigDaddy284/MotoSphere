"""Tests of what the ``schema`` command says, and of its place in the command line."""

import pytest

from motosphere.cli import main
from motosphere.cli.schema import report

STORE = "/data/store.sqlite3"


@pytest.mark.parametrize(
    ("version", "lacking", "sentence"),
    [
        (None, 0, f"There is no data store: {STORE} does not exist."),
        (0, 0, f"The data store is up to date: {STORE} is at schema version 0."),
        (5, 0, f"The data store is up to date: {STORE} is at schema version 5."),
        (
            0,
            1,
            f"The data store lacks 1 migration: {STORE} is at schema version 0, "
            "and the newest is version 1.",
        ),
        (
            1,
            2,
            f"The data store lacks 2 migrations: {STORE} is at schema version 1, "
            "and the newest is version 3.",
        ),
        (
            2,
            3,
            f"The data store lacks 3 migrations: {STORE} is at schema version 2, "
            "and the newest is version 5.",
        ),
    ],
    ids=[
        "no file",
        "up to date, no migration yet",
        "up to date",
        "lacks one",
        "lacks two",
        "lacks three",
    ],
)
def test_the_report_says_which_schema_the_store_has(
    version: int | None, lacking: int, sentence: str
) -> None:
    assert report(STORE, version, lacking) == sentence


def test_schema_is_in_the_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])

    assert exit_info.value.code == 0
    assert "schema    say which schema the data store has" in capsys.readouterr().out


def test_schema_has_its_own_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["schema", "--help"])

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("usage: python -m motosphere schema")
    assert "Say which schema the data store has" in captured.out
    assert "MOTOSPHERE_STORE_PATH" in captured.out
    assert captured.err == ""


def test_schema_takes_no_argument(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["schema", "now"])

    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("usage: python -m motosphere ")
    assert "now" in captured.err
