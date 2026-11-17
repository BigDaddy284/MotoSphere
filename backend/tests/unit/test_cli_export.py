"""Tests for the ``export`` command, calling :func:`motosphere.cli.main` directly."""

import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import motosphere
from motosphere.cli import main
from motosphere.core.logging_config import HANDLER_NAME
from motosphere.publish import export as export_step
from motosphere.publish.manifest import Manifest

EXPORT_USAGE_PREFIX = "usage: python -m motosphere export "
LOG_LINE_PART = " INFO [motosphere.cli.export] Exported the published data to "


def _entries(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir())


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:
    """Undo every change main() makes to the root logger."""
    root = logging.getLogger()
    original_level = root.level
    yield
    for handler in [handler for handler in root.handlers if handler.name == HANDLER_NAME]:
        root.removeHandler(handler)
    root.setLevel(original_level)


def test_export_writes_the_manifest_and_prints_its_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = tmp_path / "site" / "data"
    before = datetime.now(UTC).replace(microsecond=0)

    assert main(["export", "--out", str(directory)]) == 0

    after = datetime.now(UTC)
    manifest_path = directory / "manifest.json"
    assert capsys.readouterr().out == f"{manifest_path}\n"
    manifest = Manifest.model_validate_json(manifest_path.read_bytes())
    assert manifest.format_version == 1
    assert manifest.application_version == motosphere.__version__
    assert manifest.counts == {}
    assert before <= manifest.generated_at <= after
    assert manifest.generated_at.utcoffset() == timedelta(0)


def test_export_logs_what_it_did_on_standard_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = tmp_path / "site" / "data"

    assert main(["export", "--out", str(directory)]) == 0

    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 1
    assert LOG_LINE_PART in lines[0]
    assert str(directory) in lines[0]


def test_relative_directory_is_taken_from_the_working_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The shared fixture has made tmp_path the working directory.
    assert main(["export", "--out", "data"]) == 0

    assert (tmp_path / "data" / "manifest.json").is_file()
    assert capsys.readouterr().out == f"{Path('data') / 'manifest.json'}\n"


def test_directory_that_is_a_file_is_reported_on_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    existing = tmp_path / "data"
    existing.write_bytes(b"not a directory\n")

    assert main(["export", "--out", str(existing)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith(f"Export failed: cannot write to {existing}: ")
    assert existing.read_bytes() == b"not a directory\n"


def test_write_failure_is_reported_on_one_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def refuse(_path: Path, _text: str) -> None:
        raise PermissionError(13, "Permission\ndenied")

    monkeypatch.setattr(export_step, "write_text_atomically", refuse)
    directory = tmp_path / "data"

    assert main(["export", "--out", str(directory)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"Export failed: cannot write to {directory}: Permission denied\n"
    assert _entries(directory) == []


def test_out_is_required(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["export"])

    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(EXPORT_USAGE_PREFIX)
    assert "--out" in captured.err


@pytest.mark.parametrize("value", ["", "   "], ids=["empty", "spaces"])
def test_empty_directory_is_a_usage_error(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["export", "--out", value])

    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "the directory must not be empty" in captured.err
    # The shared fixture has made tmp_path the working directory.
    assert _entries(tmp_path) == []


def test_export_has_its_own_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["export", "--help"])

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith(EXPORT_USAGE_PREFIX)
    assert "Write the published data files into a directory." in captured.out
    assert "--out <directory>" in captured.out
    assert captured.err == ""
