"""TRIAL ONLY (FND-057). What a data store of a test costs, by where its file is.

Usage (in backend/): uv run python ../trial/storebench.py <folder> [<folder> ...]
"""

import sqlite3
import sys
import time
from pathlib import Path

from motosphere.db.migrations import migrate
from motosphere.db.store import open_store


def commits(folder: Path, synchronous: str | None, count: int = 200) -> float:
    path = folder / f"commits-{synchronous}.sqlite3"
    connection = sqlite3.connect(path)
    if synchronous is not None:
        connection.execute(f"PRAGMA synchronous = {synchronous}")
    connection.execute("CREATE TABLE t (x)")
    connection.commit()
    start = time.perf_counter()
    for number in range(count):
        connection.execute("INSERT INTO t VALUES (?)", (number,))
        connection.commit()
    took = time.perf_counter() - start
    connection.close()
    return took / count * 1000


def stores(folder: Path, count: int = 20) -> float:
    start = time.perf_counter()
    for number in range(count):
        engine = open_store(folder / f"store-{number}.sqlite3")
        migrate(engine)
        engine.dispose()
    return (time.perf_counter() - start) / count * 1000


def files(folder: Path, count: int = 300) -> float:
    start = time.perf_counter()
    for number in range(count):
        path = folder / f"file-{number}.txt"
        path.write_bytes(b"x" * 4096)
        path.unlink()
    return (time.perf_counter() - start) / count * 1000


import tempfile

print(f"Python's own temporary folder: {tempfile.gettempdir()}")
for name in sys.argv[1:]:
    folder = Path(name)
    folder.mkdir(parents=True, exist_ok=True)
    print(f"{folder}:")
    print(f"  a file written and removed: {files(folder):.2f} ms")
    for synchronous in (None, "NORMAL", "OFF"):
        print(f"  one commit, synchronous {synchronous or 'as SQLite has it'}: {commits(folder, synchronous):.2f} ms")
    print(f"  a store opened and given every migration: {stores(folder):.1f} ms", flush=True)
