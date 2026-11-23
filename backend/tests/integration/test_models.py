"""Tests that the whole schema is whole: no model anywhere in the code is missing from it.

Each question is asked of a new Python, which has loaded nothing but what
it is told to: in the Python that runs the tests, other tests have loaded
models already.
"""

import subprocess
import sys

TIMEOUT_SECONDS = 60

# Load every module MotoSphere has, and say which tables the models then say.
EVERY_MODULE = """
import importlib
import pkgutil

import motosphere
from motosphere.db.base import Base

for module in pkgutil.walk_packages(motosphere.__path__, "motosphere."):
    if module.name != "motosphere.__main__":
        importlib.import_module(module.name)
print(*sorted(Base.metadata.tables))
"""
# Take the whole schema from where it is to be taken, and say its tables.
THE_SCHEMA = """
from motosphere.db.models import SCHEMA

print(*sorted(SCHEMA.tables))
"""
# Load one model by its own module, and say the tables.
ONE_MODULE = """
from motosphere.db.base import Base
from motosphere.db.models.source import Source

print(*sorted(Base.metadata.tables))
"""


def tables_said_after(statements: str) -> list[str]:
    """The tables the models say in a new Python that has run ``statements``."""
    # The command is fixed (this Python running the text above) and no shell is used.
    ran = subprocess.run(  # noqa: S603
        [sys.executable, "-c", statements],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert ran.returncode == 0, ran.stderr
    return ran.stdout.split()


def test_the_schema_has_every_table_a_model_anywhere_in_the_code_says() -> None:
    everywhere = tables_said_after(EVERY_MODULE)

    assert "source" in everywhere
    assert tables_said_after(THE_SCHEMA) == everywhere


def test_loading_one_model_loads_them_all() -> None:
    assert tables_said_after(ONE_MODULE) == tables_said_after(EVERY_MODULE)
