"""Tests of the machine's own SQLite: the one inside the Python that runs them.

These are the tests that prove, on every machine the gates run on, that the
data store can rely on what `motosphere.db.sqlite` names. Nothing is stood
in for here.
"""

import sqlite3
from pathlib import Path

from motosphere.db.sqlite import LEAST_VERSION, missing, text_of, version_of


def test_this_machines_sqlite_is_new_enough() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        found = version_of(connection)
    finally:
        connection.close()

    assert found >= LEAST_VERSION, f"SQLite {text_of(found)} on this machine"


def test_this_machines_sqlite_has_everything_the_store_relies_on() -> None:
    assert missing() == []


def test_the_check_leaves_no_file_behind(tmp_path: Path) -> None:
    # The tests run with the temporary folder as the working directory.
    missing()

    assert list(tmp_path.iterdir()) == []
    assert Path.cwd() == tmp_path
