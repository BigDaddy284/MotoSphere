"""Tests for the export step."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from motosphere.publish.export import export_published_data
from motosphere.publish.manifest import Manifest, build_manifest, manifest_to_json

NOW = datetime(2026, 11, 17, 2, 30, 0, tzinfo=UTC)


def _entries(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir())


def test_writes_the_manifest_and_returns_its_path(tmp_path: Path) -> None:
    manifest_path = export_published_data(tmp_path, NOW)

    assert manifest_path == tmp_path / "manifest.json"
    assert manifest_path.read_bytes() == manifest_to_json(build_manifest(NOW)).encode()
    assert _entries(tmp_path) == ["manifest.json"]


def test_written_manifest_is_valid(tmp_path: Path) -> None:
    manifest_path = export_published_data(tmp_path, NOW)

    assert Manifest.model_validate_json(manifest_path.read_bytes()) == build_manifest(NOW)


def test_creates_missing_directories(tmp_path: Path) -> None:
    directory = tmp_path / "site" / "data"

    manifest_path = export_published_data(directory, NOW)

    assert manifest_path == directory / "manifest.json"
    assert _entries(directory) == ["manifest.json"]


def test_same_time_gives_identical_bytes(tmp_path: Path) -> None:
    first = export_published_data(tmp_path / "first", NOW)
    second = export_published_data(tmp_path / "second", NOW)

    assert first.read_bytes() == second.read_bytes()


def test_exporting_again_replaces_the_manifest(tmp_path: Path) -> None:
    later = NOW + timedelta(hours=1)
    export_published_data(tmp_path, NOW)

    manifest_path = export_published_data(tmp_path, later)

    assert Manifest.model_validate_json(manifest_path.read_bytes()).generated_at == later
    assert manifest_path.read_bytes() == manifest_to_json(build_manifest(later)).encode()
    assert _entries(tmp_path) == ["manifest.json"]


def test_directory_that_is_a_file_is_an_error(tmp_path: Path) -> None:
    existing = tmp_path / "data"
    existing.write_bytes(b"not a directory\n")

    with pytest.raises((FileExistsError, NotADirectoryError)):
        export_published_data(existing, NOW)

    assert existing.read_bytes() == b"not a directory\n"
    assert _entries(tmp_path) == ["data"]
