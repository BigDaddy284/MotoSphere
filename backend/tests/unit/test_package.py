"""Smoke tests for the motosphere package."""

import re
import tomllib
from pathlib import Path

import motosphere

BACKEND_DIR = Path(__file__).resolve().parents[2]
PYPROJECT = BACKEND_DIR / "pyproject.toml"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def _pyproject_version() -> str:
    with PYPROJECT.open("rb") as handle:
        data = tomllib.load(handle)
    version = data["project"]["version"]
    assert isinstance(version, str)
    return version


def test_package_imports() -> None:
    assert motosphere.__name__ == "motosphere"
    assert motosphere.__doc__ is not None
    assert motosphere.__doc__.strip() != ""


def test_version_matches_pyproject() -> None:
    assert motosphere.__version__ == _pyproject_version()


def test_version_is_well_formed() -> None:
    assert isinstance(motosphere.__version__, str)
    assert VERSION_PATTERN.fullmatch(motosphere.__version__) is not None


def test_package_is_loaded_from_src() -> None:
    assert motosphere.__file__ is not None
    package_dir = Path(motosphere.__file__).resolve().parent
    assert package_dir == BACKEND_DIR / "src" / "motosphere"
