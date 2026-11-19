"""Shared pytest fixtures for the backend tests."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, event
from sqlalchemy.pool import PoolProxiedConnection

from motosphere.core.settings import ENV_PREFIX, get_settings
from motosphere.db.store import open_store

# The tests of the `store` fixture run pytest itself (test_store_fixture.py).
pytest_plugins = ["pytester"]


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


@pytest.fixture
def store(tmp_path: Path) -> Iterator[Engine]:
    """A real data store of the test's own: an SQLite file in the test's temporary folder.

    It is opened the way the pipeline opens its store, and it is empty. A
    connection the test leaves open is closed for it when the test ends, so
    that the file can be removed, and the test is reported as an error.
    """
    engine = open_store(tmp_path / "store.sqlite3")
    taken: list[PoolProxiedConnection] = []

    def remember(_connection: object, _entry: object, proxy: PoolProxiedConnection) -> None:
        taken.append(proxy)

    event.listen(engine, "checkout", remember)
    yield engine
    left_open = [proxy for proxy in taken if proxy.is_valid]
    for proxy in left_open:
        proxy.close()
    if left_open:
        pytest.fail(
            f"Connections to its store that the test left open: {len(left_open)}. "
            "They were closed for it."
        )
