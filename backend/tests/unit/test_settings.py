"""Tests for the backend settings module."""

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from motosphere.core.settings import ENV_PREFIX, Environment, LogLevel, Settings, get_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = BACKEND_DIR / ".env.example"
README = BACKEND_DIR.parent / "README.md"


def _write_dotenv(directory: Path, content: str) -> None:
    (directory / ".env").write_text(content, encoding="utf-8")


def _active_env_example_names() -> set[str]:
    names: set[str] = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, separator, _ = stripped.partition("=")
        assert separator == "=", f"Not a NAME=value line: {line!r}"
        names.add(name.strip())
    return names


def test_settings_are_exactly_the_documented_ones() -> None:
    assert set(Settings.model_fields) == {"environment", "log_level", "store_path"}


def test_defaults_without_environment() -> None:
    settings = Settings()

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.log_level is LogLevel.INFO


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOTOSPHERE_ENVIRONMENT", "production")
    monkeypatch.setenv("MOTOSPHERE_LOG_LEVEL", "WARNING")

    settings = Settings()

    assert settings.environment is Environment.PRODUCTION
    assert settings.log_level is LogLevel.WARNING


def test_dotenv_file_overrides_defaults(tmp_path: Path) -> None:
    _write_dotenv(
        tmp_path,
        "MOTOSPHERE_ENVIRONMENT=test\nMOTOSPHERE_LOG_LEVEL=ERROR\n",
    )

    settings = Settings()

    assert settings.environment is Environment.TEST
    assert settings.log_level is LogLevel.ERROR


def test_environment_variable_beats_dotenv_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_dotenv(tmp_path, "MOTOSPHERE_LOG_LEVEL=ERROR\n")
    monkeypatch.setenv("MOTOSPHERE_LOG_LEVEL", "DEBUG")

    assert Settings().log_level is LogLevel.DEBUG


def test_values_are_normalised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOTOSPHERE_LOG_LEVEL", "debug")
    monkeypatch.setenv("MOTOSPHERE_ENVIRONMENT", " Production ")

    settings = Settings()

    assert settings.log_level is LogLevel.DEBUG
    assert settings.environment is Environment.PRODUCTION


@pytest.mark.parametrize("value", ["LOUD", "", "10"])
def test_invalid_log_level_is_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("MOTOSPHERE_LOG_LEVEL", value)

    with pytest.raises(ValidationError, match="log_level"):
        Settings()


@pytest.mark.parametrize("value", ["staging", ""])
def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("MOTOSPHERE_ENVIRONMENT", value)

    with pytest.raises(ValidationError, match="environment"):
        Settings()


def test_unknown_key_in_dotenv_file_is_rejected(tmp_path: Path) -> None:
    _write_dotenv(tmp_path, "MOTOSPHERE_LOG_LEVLE=INFO\n")

    with pytest.raises(ValidationError, match="log_levle"):
        Settings()


@pytest.mark.parametrize(
    ("line", "name"),
    [
        ("MOTOSPHERE_API_HOST=127.0.0.1", "api_host"),
        ("MOTOSPHERE_API_PORT=8000", "api_port"),
    ],
)
def test_removed_server_settings_are_rejected(tmp_path: Path, line: str, name: str) -> None:
    _write_dotenv(tmp_path, line + "\n")

    with pytest.raises(ValidationError, match=name):
        Settings()


def test_settings_are_immutable() -> None:
    settings = Settings()
    field_name = "log_level"

    with pytest.raises(ValidationError) as error:
        setattr(settings, field_name, LogLevel.ERROR)

    assert field_name in str(error.value)
    assert "frozen" in str(error.value)

    assert settings.log_level is LogLevel.INFO


def test_get_settings_is_cached_and_clearable(monkeypatch: pytest.MonkeyPatch) -> None:
    first = get_settings()
    assert get_settings() is first
    assert first.log_level is LogLevel.INFO

    monkeypatch.setenv("MOTOSPHERE_LOG_LEVEL", "ERROR")
    assert get_settings() is first
    assert get_settings().log_level is LogLevel.INFO

    get_settings.cache_clear()
    reloaded = get_settings()
    assert reloaded is not first
    assert reloaded.log_level is LogLevel.ERROR


def test_env_example_lists_every_setting() -> None:
    expected = {ENV_PREFIX + name.upper() for name in Settings.model_fields}

    assert _active_env_example_names() == expected


def test_env_example_values_equal_defaults(tmp_path: Path) -> None:
    defaults = Settings().model_dump()

    shutil.copyfile(ENV_EXAMPLE, tmp_path / ".env")

    assert Settings().model_dump() == defaults


def test_the_store_is_kept_in_the_store_folder_by_default() -> None:
    assert Settings().store_path == Path("store/motosphere.sqlite3")


def test_the_store_path_comes_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    elsewhere = tmp_path / "elsewhere" / "data.sqlite3"
    monkeypatch.setenv("MOTOSPHERE_STORE_PATH", str(elsewhere))

    assert Settings().store_path == elsewhere


def test_the_store_path_comes_from_the_dotenv_file(tmp_path: Path) -> None:
    _write_dotenv(tmp_path, "MOTOSPHERE_STORE_PATH=other/place.sqlite3\n")

    assert Settings().store_path == Path("other/place.sqlite3")


def test_spaces_around_the_store_path_are_dropped_and_spaces_inside_it_stay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOTOSPHERE_STORE_PATH", "  my store/data.sqlite3  ")

    assert Settings().store_path == Path("my store/data.sqlite3")


@pytest.mark.parametrize("value", ["", "   ", "\t"])
def test_an_empty_store_path_is_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("MOTOSPHERE_STORE_PATH", value)

    with pytest.raises(ValidationError, match="store_path") as error:
        Settings()

    assert "the path of the data store must not be empty" in str(error.value)


@pytest.mark.parametrize("value", [None, "elsewhere/data.sqlite3"], ids=["default", "set"])
def test_reading_the_settings_creates_no_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is not None:
        monkeypatch.setenv("MOTOSPHERE_STORE_PATH", value)

    settings = Settings()

    assert not settings.store_path.exists()
    assert list(tmp_path.iterdir()) == []


def _as_written(value: object) -> str:
    return value.as_posix() if isinstance(value, Path) else str(value)


def test_readme_lists_every_setting_with_its_default() -> None:
    readme = README.read_text(encoding="utf-8")

    for name, value in Settings().model_dump().items():
        row = f"| `{ENV_PREFIX}{name.upper()}` | `{_as_written(value)}` |"
        assert readme.count(row) == 1, row
