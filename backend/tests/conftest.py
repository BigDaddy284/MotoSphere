"""Shared pytest fixtures for the backend tests."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from motosphere.core.settings import ENV_PREFIX, get_settings


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Keep every test independent of the machine's environment and any real .env file."""
    for name in list(os.environ):
        if name.upper().startswith(ENV_PREFIX):
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
