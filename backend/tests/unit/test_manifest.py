"""Tests for the manifest model and its JSON form."""

import json
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

import motosphere
from motosphere.publish.manifest import (
    FORMAT_VERSION,
    MANIFEST_FILE_NAME,
    Manifest,
    build_manifest,
    manifest_to_json,
)

NOW = datetime(2026, 11, 17, 2, 30, 0, tzinfo=UTC)
FIELDS = ("format_version", "generated_at", "application_version", "counts")


def _valid_data(**changes: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "format_version": 1,
        "generated_at": NOW,
        "application_version": "0.1.0",
        "counts": {},
    }
    data.update(changes)
    return data


def _manifest(**changes: Any) -> Manifest:
    return Manifest.model_validate(_valid_data(**changes))


def _assert_rejected(data: dict[str, Any], field: str) -> None:
    with pytest.raises(ValidationError) as error_info:
        Manifest.model_validate(data)
    assert field in str(error_info.value)


def test_constants() -> None:
    assert FORMAT_VERSION == 1
    assert MANIFEST_FILE_NAME == "manifest.json"


def test_build_manifest_describes_the_current_data() -> None:
    manifest = build_manifest(NOW)

    assert manifest.format_version == 1
    assert manifest.generated_at == NOW
    assert manifest.application_version == motosphere.__version__
    assert manifest.counts == {}


def test_generation_time_is_stored_in_utc() -> None:
    local = datetime(2026, 11, 17, 4, 30, 0, tzinfo=timezone(timedelta(hours=2)))

    manifest = _manifest(generated_at=local)

    assert manifest.generated_at == NOW
    assert manifest.generated_at.hour == 2
    assert manifest.generated_at.utcoffset() == timedelta(0)


def test_generation_time_is_stored_to_the_second() -> None:
    manifest = _manifest(generated_at=NOW.replace(microsecond=123456))

    assert manifest.generated_at == NOW
    assert manifest.generated_at.microsecond == 0


def test_generation_time_must_carry_a_time_zone() -> None:
    _assert_rejected(_valid_data(generated_at=NOW.replace(tzinfo=None)), "generated_at")


def test_json_has_a_fixed_layout() -> None:
    manifest = _manifest(counts={"tracks": 3, "events": 12})

    assert manifest_to_json(manifest) == (
        "{\n"
        '  "application_version": "0.1.0",\n'
        '  "counts": {\n'
        '    "events": 12,\n'
        '    "tracks": 3\n'
        "  },\n"
        '  "format_version": 1,\n'
        '  "generated_at": "2026-11-17T02:30:00Z"\n'
        "}\n"
    )


def test_json_of_the_built_manifest() -> None:
    text = manifest_to_json(build_manifest(NOW))

    assert json.loads(text) == {
        "format_version": 1,
        "generated_at": "2026-11-17T02:30:00Z",
        "application_version": motosphere.__version__,
        "counts": {},
    }


def test_json_does_not_depend_on_the_order_of_the_counts() -> None:
    first = _manifest(counts={"tracks": 3, "events": 12})
    second = _manifest(counts={"events": 12, "tracks": 3})

    assert manifest_to_json(first) == manifest_to_json(second)


def test_json_reads_back_to_the_same_manifest() -> None:
    manifest = _manifest(counts={"tracks": 3, "events": 12})

    assert Manifest.model_validate_json(manifest_to_json(manifest)) == manifest


def test_manifest_is_immutable() -> None:
    manifest = build_manifest(NOW)
    # Assigned through setattr, because the type checker already refuses a direct assignment.
    field = "format_version"

    with pytest.raises(ValidationError) as error_info:
        setattr(manifest, field, 2)
    assert "frozen" in str(error_info.value)
    assert manifest.format_version == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("format_version", 0, id="format-version-zero"),
        pytest.param("format_version", "one", id="format-version-text"),
        pytest.param("application_version", "", id="application-version-empty"),
        pytest.param("generated_at", "yesterday", id="generated-at-text"),
        pytest.param("counts", {"tracks": -1}, id="count-negative"),
        pytest.param("counts", {"tracks": 1.5}, id="count-fraction"),
        pytest.param("counts", {"Tracks": 1}, id="kind-capitalised"),
        pytest.param("counts", {"": 1}, id="kind-empty"),
        pytest.param("counts", {"tracks per country": 1}, id="kind-with-spaces"),
    ],
)
def test_invalid_values_are_rejected(field: str, value: object) -> None:
    _assert_rejected(_valid_data(**{field: value}), field)


def test_unknown_fields_are_rejected() -> None:
    _assert_rejected(_valid_data(internal_note="checked by hand"), "internal_note")


@pytest.mark.parametrize("field", FIELDS)
def test_every_field_is_required(field: str) -> None:
    data = _valid_data()
    del data[field]

    _assert_rejected(data, field)


def test_schema_names_every_field_and_allows_no_others() -> None:
    schema = Manifest.model_json_schema()

    assert sorted(schema["required"]) == sorted(FIELDS)
    assert sorted(schema["properties"]) == sorted(FIELDS)
    assert schema["additionalProperties"] is False


def test_json_keeps_text_outside_ascii_as_it_is() -> None:
    text = manifest_to_json(_manifest(application_version="0.1.0+ernée"))

    assert '"application_version": "0.1.0+ernée"' in text
    assert "\\u" not in text
