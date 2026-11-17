"""Tests for writing published files atomically."""

from pathlib import Path

import pytest

from motosphere.publish.files import write_text_atomically


def _entries(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir())


def _failing(*_arguments: object, **_keywords: object) -> None:
    raise OSError("simulated failure")


def test_writes_the_text_as_utf8(tmp_path: Path) -> None:
    target = tmp_path / "manifest.json"

    write_text_atomically(target, '{"name": "Ernée"}\n')

    assert target.read_bytes() == b'{"name": "Ern\xc3\xa9e"}\n'


def test_line_breaks_are_written_as_given(tmp_path: Path) -> None:
    target = tmp_path / "lines.txt"

    write_text_atomically(target, "one\ntwo\n")

    assert target.read_bytes() == b"one\ntwo\n"


def test_replaces_an_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "manifest.json"
    target.write_bytes(b"an earlier and much longer content\n")

    write_text_atomically(target, "new\n")

    assert target.read_bytes() == b"new\n"


def test_leaves_only_the_target_behind(tmp_path: Path) -> None:
    write_text_atomically(tmp_path / "manifest.json", "{}\n")

    assert _entries(tmp_path) == ["manifest.json"]


def test_failed_replace_leaves_nothing_behind(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(Path, "replace", _failing)

    with pytest.raises(OSError, match="simulated failure"):
        write_text_atomically(tmp_path / "manifest.json", "{}\n")

    assert _entries(tmp_path) == []


def test_failed_replace_keeps_the_earlier_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "manifest.json"
    target.write_bytes(b"earlier\n")
    monkeypatch.setattr(Path, "replace", _failing)

    with pytest.raises(OSError, match="simulated failure"):
        write_text_atomically(target, "new\n")

    assert _entries(tmp_path) == ["manifest.json"]
    assert target.read_bytes() == b"earlier\n"


def test_failed_write_leaves_nothing_behind(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("motosphere.publish.files.os.fsync", _failing)

    with pytest.raises(OSError, match="simulated failure"):
        write_text_atomically(tmp_path / "manifest.json", "{}\n")

    assert _entries(tmp_path) == []


def test_missing_directory_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        write_text_atomically(tmp_path / "missing" / "manifest.json", "{}\n")

    assert _entries(tmp_path) == []
