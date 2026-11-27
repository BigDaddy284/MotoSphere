"""Tests for the MotoSphere command line, calling :func:`motosphere.cli.main` directly."""

import argparse
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

import motosphere
from motosphere.cli import main, version
from motosphere.cli.app import build_parser
from motosphere.core.logging_config import HANDLER_NAME
from motosphere.core.settings import Settings

USAGE_PREFIX = "usage: python -m motosphere "


def _named_handlers() -> list[logging.Handler]:
    return [handler for handler in logging.getLogger().handlers if handler.name == HANDLER_NAME]


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:
    """Undo every change main() makes to the root logger."""
    root = logging.getLogger()
    original_level = root.level
    yield
    for handler in _named_handlers():
        root.removeHandler(handler)
    root.setLevel(original_level)


def test_version_prints_the_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"motosphere {motosphere.__version__}\n"
    assert captured.err == ""


def test_arguments_default_to_those_of_the_process(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["motosphere", "version"])

    assert main() == 0

    assert capsys.readouterr().out == f"motosphere {motosphere.__version__}\n"


def test_no_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([])

    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(USAGE_PREFIX)
    assert "<command>" in captured.err


def test_unknown_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["serve"])

    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(USAGE_PREFIX)
    assert "'serve'" in captured.err


def test_unexpected_argument_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["version", "--port", "8000"])

    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(USAGE_PREFIX)
    assert "--port" in captured.err


def test_help_lists_the_commands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith(USAGE_PREFIX)
    assert "version" in captured.out
    assert "print the MotoSphere version" in captured.out
    assert captured.err == ""


def test_help_lists_every_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    # Each command has a line of its own: its name, and what it does.
    listed = dict(
        line.split(maxsplit=1) for line in captured.out.splitlines() if line.startswith("    ")
    )
    assert listed["export"] == "write the published data files"
    assert listed["version"] == "print the MotoSphere version"


def test_exit_code_of_the_command_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    def finish_with_seven(_arguments: argparse.Namespace, _settings: Settings) -> int:
        return 7

    monkeypatch.setattr(version, "run", finish_with_seven)

    assert main(["version"]) == 7


def test_every_command_has_its_own_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["version", "--help"])

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("usage: python -m motosphere version")
    assert "Print the installed MotoSphere version." in captured.out
    assert captured.err == ""


def test_parser_can_be_built_more_than_once() -> None:
    first = build_parser().parse_args(["version"])
    second = build_parser().parse_args(["version"])

    assert first.command == "version"
    assert second.command == "version"
    assert first.handler is second.handler


def test_logging_is_configured_from_the_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOTOSPHERE_LOG_LEVEL", "WARNING")

    assert main(["version"]) == 0

    assert logging.getLogger().level == logging.WARNING
    assert len(_named_handlers()) == 1


def test_invalid_setting_is_reported_on_one_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MOTOSPHERE_LOG_LEVEL", "LOUD")

    assert main(["version"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("Configuration error: ")
    assert "log_level" in lines[0]
    assert _named_handlers() == []


def test_several_invalid_settings_are_reported_on_one_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MOTOSPHERE_LOG_LEVEL", "LOUD")
    monkeypatch.setenv("MOTOSPHERE_ENVIRONMENT", "staging")

    assert main(["version"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("Configuration error: ")
    assert "log_level" in lines[0]
    assert "environment" in lines[0]


def test_unknown_dotenv_key_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # The shared fixture has made tmp_path the working directory.
    (tmp_path / ".env").write_text("MOTOSPHERE_LOG_LEVLE=INFO\n", encoding="utf-8")

    assert main(["version"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("Configuration error: ")
    assert "log_levle" in captured.err


def test_help_works_with_invalid_settings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MOTOSPHERE_LOG_LEVEL", "LOUD")

    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith(USAGE_PREFIX)
    assert "Configuration error" not in captured.out
    assert "Configuration error" not in captured.err
