"""Tests for the ``python -m motosphere`` entry point, with the server call replaced."""

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from fastapi import FastAPI

from motosphere.__main__ import main
from motosphere.core.logging_config import HANDLER_NAME


class _RunRecorder:
    """Stands in for ``uvicorn.run`` and records every call instead of starting a server."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append((args, kwargs))


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


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _RunRecorder:
    run_recorder = _RunRecorder()
    monkeypatch.setattr(uvicorn, "run", run_recorder)
    return run_recorder


def test_main_runs_server_with_settings(
    monkeypatch: pytest.MonkeyPatch, recorder: _RunRecorder
) -> None:
    monkeypatch.setenv("MOTOSPHERE_API_HOST", "localhost")
    monkeypatch.setenv("MOTOSPHERE_API_PORT", "9321")

    assert main() == 0

    assert len(recorder.calls) == 1
    args, kwargs = recorder.calls[0]
    assert len(args) == 1
    app = args[0]
    assert isinstance(app, FastAPI)
    assert app.state.settings.api_port == 9321
    assert kwargs == {"host": "localhost", "port": 9321, "log_config": None}


def test_main_configures_logging(monkeypatch: pytest.MonkeyPatch, recorder: _RunRecorder) -> None:
    monkeypatch.setenv("MOTOSPHERE_LOG_LEVEL", "WARNING")

    assert main() == 0

    assert logging.getLogger().level == logging.WARNING
    assert len(_named_handlers()) == 1
    assert len(recorder.calls) == 1


def test_main_reports_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
    recorder: _RunRecorder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MOTOSPHERE_API_PORT", "0")

    assert main() == 2

    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("Configuration error: ")
    assert "api_port" in lines[0]
    assert recorder.calls == []


def test_main_reports_unknown_dotenv_key(
    tmp_path: Path,
    recorder: _RunRecorder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The shared fixture has made tmp_path the working directory.
    (tmp_path / ".env").write_text("MOTOSPHERE_API_PROT=9000\n", encoding="utf-8")

    assert main() == 2

    message = capsys.readouterr().err
    assert message.startswith("Configuration error: ")
    assert "api_prot" in message
    assert recorder.calls == []
