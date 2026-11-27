"""Checks on which packages the frontend installs (GLB-001).

What the site ships to a visitor's browser is named under `dependencies`
in `frontend/package.json`; what only builds and tests it is named under
`devDependencies`. A package under `dependencies` is code of someone else
that every visitor runs, so adding one is a decision, and it is made here
and not in passing. The engine of the globe is the Cesium engine by
itself, `@cesium/engine`: not the full `cesium` package with its ready-made
viewer, and no wrapper around it (ARCHITECTURE.md, section 3). The engine
keeps its arithmetic in a package of its own, `@cesium/core`, and asks
that it be taken from there; so the project names that package too, and
there must be one copy of it for the engine and the application alike.

Standard library only, as all repository checks. Run from the repository
root:

    python -m unittest discover -s tests/repo -v
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "frontend" / "package.json"
LOCK = ROOT / "frontend" / "package-lock.json"

ENGINE = "@cesium/engine"
# The packages the site ships. Adding one is a decision about whose code
# every visitor runs.
SHIPPED = ("@cesium/core", "@cesium/engine", "react", "react-dom")
# Decided against: the full package and the ready-made viewer, whose
# controls MotoSphere does not use, and wrappers that must follow every
# release of the engine.
NOT_INSTALLED = ("cesium", "@cesium/widgets", "resium")


class UnusableError(Exception):
    """A file of the project is not what these checks can go by."""


def group(document: dict[str, object], name: str) -> dict[str, object]:
    """One group of a package file or a lock file, such as `dependencies`."""
    found = document.get(name)
    if not isinstance(found, dict):
        raise UnusableError(f"there is no {name}")
    return found


def load(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise UnusableError(f"{path.name} is not a list of names and values")
    return loaded


def places(lock: dict[str, object]) -> dict[str, list[str]]:
    """Where a lock file installs each package, by the package's name.

    `node_modules/a/node_modules/@b/c` is a place of the package `@b/c`. A
    package with two places is installed twice, as two copies of its code.
    """
    found: dict[str, list[str]] = {}
    for where in group(lock, "packages"):
        if where != "":
            found.setdefault(where.rpartition("node_modules/")[2], []).append(where)
    return found


def only_for_the_work(package: object) -> bool:
    """Whether a lock file marks a package as one the site does not ship."""
    return isinstance(package, dict) and package.get("dev") is True


class ReadingALockFileTest(unittest.TestCase):
    def test_a_package_is_known_by_its_name_wherever_it_is_put(self) -> None:
        lock: dict[str, object] = {
            "packages": {
                "": {"name": "the project"},
                "node_modules/one": {"version": "1.0.0"},
                "node_modules/@two/three": {"version": "2.0.0"},
                "node_modules/one/node_modules/four": {"version": "4.0.0"},
                "node_modules/one/node_modules/@two/three": {"version": "2.1.0"},
            }
        }

        self.assertEqual(
            places(lock),
            {
                "one": ["node_modules/one"],
                "@two/three": [
                    "node_modules/@two/three",
                    "node_modules/one/node_modules/@two/three",
                ],
                "four": ["node_modules/one/node_modules/four"],
            },
        )

    def test_a_package_is_only_for_the_work_when_the_lock_file_says_so(self) -> None:
        self.assertTrue(only_for_the_work({"version": "1.0.0", "dev": True}))
        for package in ({"version": "1.0.0"}, {"dev": False}, {"dev": "true"}, None):
            with self.subTest(package=package):
                self.assertFalse(only_for_the_work(package))

    def test_a_file_without_the_group_asked_for_is_not_gone_by(self) -> None:
        unusable: tuple[dict[str, object], ...] = ({}, {"packages": []}, {"packages": "none"})
        for lock in unusable:
            with self.subTest(lock=lock), self.assertRaises(UnusableError):
                places(lock)


class ShippedPackagesTest(unittest.TestCase):
    def test_the_site_ships_these_packages_and_no_other(self) -> None:
        self.assertEqual(sorted(group(load(PACKAGE), "dependencies")), sorted(SHIPPED))

    def test_no_package_is_named_both_as_shipped_and_as_only_for_the_work(self) -> None:
        package = load(PACKAGE)
        both = set(group(package, "dependencies")) & set(group(package, "devDependencies"))

        self.assertEqual(both, set())

    def test_the_lock_file_names_the_same_packages_for_the_project(self) -> None:
        package = load(PACKAGE)
        project = group(group(load(LOCK), "packages"), "")

        for name in ("dependencies", "devDependencies"):
            with self.subTest(group=name):
                self.assertEqual(group(project, name), group(package, name))

    def test_the_lock_file_installs_one_copy_of_each_package_the_site_ships(self) -> None:
        # Two copies of the engine's arithmetic would be two kinds of every
        # position: one made by the application is then not one the engine
        # knows as its own.
        found = places(load(LOCK))

        for name in SHIPPED:
            with self.subTest(package=name):
                self.assertEqual(found.get(name), [f"node_modules/{name}"])

    def test_the_lock_file_installs_what_the_site_ships_as_shipped(self) -> None:
        packages = group(load(LOCK), "packages")

        for name in SHIPPED:
            with self.subTest(package=name):
                self.assertFalse(only_for_the_work(packages.get(f"node_modules/{name}")))

    def test_the_engine_of_the_globe_is_the_engine_by_itself(self) -> None:
        self.assertIn(ENGINE, SHIPPED)
        found = places(load(LOCK))
        package = load(PACKAGE)
        named = {*group(package, "dependencies"), *group(package, "devDependencies")}

        for name in NOT_INSTALLED:
            with self.subTest(package=name):
                self.assertNotIn(name, found)
                self.assertNotIn(name, named)


if __name__ == "__main__":
    unittest.main()
