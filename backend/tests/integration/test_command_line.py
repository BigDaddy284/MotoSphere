"""Integration tests that run the real ``python -m motosphere`` command as a separate process.

Each test runs the command in an empty working directory, so no real ``.env``
file is read, and with every ``MOTOSPHERE_`` variable removed from the
environment except the ones the test sets itself.
"""

import os
import subprocess
import sys
from pathlib import Path

import motosphere
from motosphere.core.settings import ENV_PREFIX

TIMEOUT_SECONDS = 60
USAGE_PREFIX = "usage: python -m motosphere "


def _run(
    cwd: Path, *arguments: str, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = {
        name: value for name, value in os.environ.items() if not name.upper().startswith(ENV_PREFIX)
    }
    if extra_env is not None:
        env.update(extra_env)
    # The command is fixed (this Python running the motosphere module) and no shell is used.
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "motosphere", *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def _assert_one_configuration_error(result: subprocess.CompletedProcess[str], name: str) -> None:
    assert result.returncode == 2
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert len(lines) == 1, result.stderr
    assert lines[0].startswith("Configuration error: ")
    assert name in lines[0]


def test_version_command(tmp_path: Path) -> None:
    result = _run(tmp_path, "version")

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"motosphere {motosphere.__version__}\n"
    assert result.stderr == ""


def test_no_command_prints_usage_and_fails(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith(USAGE_PREFIX)


def test_unknown_command_prints_usage_and_fails(tmp_path: Path) -> None:
    result = _run(tmp_path, "serve")

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith(USAGE_PREFIX)
    assert "'serve'" in result.stderr


def test_help_succeeds(tmp_path: Path) -> None:
    result = _run(tmp_path, "--help")

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(USAGE_PREFIX)
    assert result.stderr == ""


def test_invalid_environment_variable_exits_with_code_2(tmp_path: Path) -> None:
    result = _run(tmp_path, "version", extra_env={"MOTOSPHERE_LOG_LEVEL": "LOUD"})

    _assert_one_configuration_error(result, "log_level")


def test_dotenv_file_in_the_working_directory_is_read(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("MOTOSPHERE_ENVIRONMENT=staging\n", encoding="utf-8")

    result = _run(tmp_path, "version")

    _assert_one_configuration_error(result, "environment")


def test_removed_server_setting_is_rejected(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("MOTOSPHERE_API_PORT=8000\n", encoding="utf-8")

    result = _run(tmp_path, "version")

    _assert_one_configuration_error(result, "api_port")
