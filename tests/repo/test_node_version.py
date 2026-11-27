"""Checks that the project asks for the Node.js its locked packages need (FND-046).

A package in the frontend's lock file may say which Node.js it runs on. The
project says the least Node.js it works with in one place, the `engines` of
`frontend/package.json`; the check of the tools a computer needs
(`scripts/tools.py`) reads it there, and the README repeats it for people.
These checks hold the lock file, that one place and the README together.

Standard library only, as all repository checks. Run from the repository
root:

    python -m unittest discover -s tests/repo -v
"""

import json
import re
import unittest
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "frontend" / "package.json"
LOCK = ROOT / "frontend" / "package-lock.json"
README = ROOT / "README.md"

Version = tuple[int, int, int]

# The one form in which the project names its least Node.js, which is the
# form the check of the tools reads: `>=22.22.2`.
LEAST = re.compile(r">=(\d+\.\d+(?:\.\d+)?)")
# A version as a package writes it: `22`, `22.13`, `22.13.0`, `v12.22.7`.
WRITTEN = re.compile(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?")
# Where the README tells a person which Node.js to have, and any place where
# it names Node.js with a number at all.
README_SAYS = re.compile(r"Node\.js(?:\]\([^)]*\))? (\d+(?:\.\d+)+) or newer")
README_NAMES_A_NUMBER = re.compile(r"Node\.js(?:\]\([^)]*\))?\s+v?\d")


class NotReadError(Exception):
    """A range is written in a form these checks do not read."""


class UnusableError(Exception):
    """A file of the project is not what these checks can go by."""


def parts(written: str) -> tuple[int, ...]:
    """The numbers of a version as they are written: `22.13` is (22, 13)."""
    found = WRITTEN.fullmatch(written)
    if found is None:
        raise NotReadError(written)
    return tuple(int(part) for part in found.groups() if part is not None)


def whole(numbers: tuple[int, ...]) -> Version:
    """A version with all three numbers: (22, 13) is (22, 13, 0)."""
    major, minor, patch = (*numbers, 0, 0)[:3]
    return (major, minor, patch)


def alternatives(written: str) -> list[tuple[Version, Version | None]]:
    """A range as its alternatives: where each begins and, if it ends, before which version.

    Read are the forms the lock file uses: `>=22.12.0`, `>= 12.0.0`, `^20.19.0`,
    `20`, and several of them with `||` between. Anything else is not guessed at.
    """
    read: list[tuple[Version, Version | None]] = []
    for alternative in written.split("||"):
        text = alternative.strip()
        if text.startswith(">="):
            read.append((whole(parts(text[2:].strip())), None))
        elif text.startswith("^"):
            numbers = parts(text[1:])
            if numbers[0] == 0:
                raise NotReadError(written)
            read.append((whole(numbers), (numbers[0] + 1, 0, 0)))
        else:
            numbers = parts(text)
            if len(numbers) == 3:
                raise NotReadError(written)
            ends = (numbers[0] + 1, 0, 0) if len(numbers) == 1 else (numbers[0], numbers[1] + 1, 0)
            read.append((whole(numbers), ends))
    return read


def allows(written: str, node: Version) -> bool:
    """Whether a range a package gives allows this Node.js."""
    return any(
        begins <= node and (ends is None or node < ends) for begins, ends in alternatives(written)
    )


def oldest_enough(ranges: Iterable[str]) -> Version | None:
    """The oldest Node.js that every one of the ranges allows; None when there is none.

    Only where one of the ranges begins can the answer change, so those are
    the versions that are tried.
    """
    every = list(ranges)
    begin = {begins for written in every for begins, _ in alternatives(written)}
    enough = [node for node in begin if all(allows(written, node) for written in every)]
    return min(enough) if enough else None


def node_of(package: object) -> object:
    """What a package, or the project, says of Node.js under `engines`; None when nothing."""
    engines = package.get("engines") if isinstance(package, dict) else None
    return engines.get("node") if isinstance(engines, dict) else None


def packages_of(lock: dict[str, object]) -> dict[str, object]:
    """Every entry of a lock file; the one with no name is the project itself."""
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        raise UnusableError("the lock file has no packages")
    return packages


def ranges_of(lock: dict[str, object]) -> dict[str, str]:
    """Every package of a lock file that says which Node.js it runs on, with its range.

    The project's own entry is left out: it is what is being checked.
    """
    ranges: dict[str, str] = {}
    for name, package in packages_of(lock).items():
        said = node_of(package)
        if name == "" or said is None:
            continue
        if not isinstance(said, str):
            raise UnusableError(f"the lock file: {name} names its Node.js as {said!r}")
        ranges[name] = said
    return ranges


def least_of(package: dict[str, object]) -> str:
    """The least Node.js a package file asks for, as it is written: `22.22.2`."""
    said = node_of(package)
    found = LEAST.fullmatch(said) if isinstance(said, str) else None
    if found is None:
        raise UnusableError(f"the package file names no least Node.js in the form >=1.2: {said!r}")
    return found[1]


def asked_for_in(text: str) -> list[str]:
    """Every Node.js a text tells a person to have, as written: `22.22.2`.

    A text that names Node.js with a number in other words than "or newer"
    is not gone by: a number these checks did not read would not be held.
    """
    said = README_SAYS.findall(text)
    if len(said) != len(README_NAMES_A_NUMBER.findall(text)):
        raise UnusableError("the text names Node.js with a number in words that are not read")
    return said


def names_in(package: dict[str, object], group: str) -> list[str]:
    """The packages the project names in one group of its package file."""
    named = package.get(group)
    return list(named) if isinstance(named, dict) else []


def load(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise UnusableError(f"{path.name} is not a list of names and values")
    return loaded


class ReadingARangeTest(unittest.TestCase):
    def test_a_range_allows_what_it_says(self) -> None:
        cases = (
            (">=22.12.0", (22, 12, 0), True),
            (">=22.12.0", (22, 11, 9), False),
            (">=22.12.0", (30, 0, 0), True),
            (">=22.12", (22, 12, 0), True),
            (">=22.12", (22, 11, 0), False),
            (">=22", (22, 0, 0), True),
            (">=22", (21, 99, 99), False),
            (">= 12.0.0", (12, 0, 0), True),
            (">= 12.0.0", (11, 9, 0), False),
            (">=v12.22.7", (12, 22, 7), True),
            (">=v12.22.7", (12, 22, 6), False),
            ("^22.13.0", (22, 13, 0), True),
            ("^22.13.0", (22, 12, 9), False),
            ("^22.13.0", (22, 99, 0), True),
            ("^22.13.0", (23, 0, 0), False),
            ("^13.7", (13, 7, 0), True),
            ("^13.7", (13, 6, 9), False),
            ("^13.7", (14, 0, 0), False),
            ("^10", (10, 0, 0), True),
            ("^10", (11, 0, 0), False),
            ("20", (20, 0, 0), True),
            ("20", (20, 99, 9), True),
            ("20", (19, 9, 9), False),
            ("20", (21, 0, 0), False),
            ("20.19", (20, 19, 0), True),
            ("20.19", (20, 19, 5), True),
            ("20.19", (20, 20, 0), False),
            ("20.19", (20, 18, 9), False),
            ("20 || >=22", (20, 5, 0), True),
            ("20 || >=22", (21, 5, 0), False),
            ("20 || >=22", (22, 0, 0), True),
            ("^20.19.0 || ^22.13.0 || >=23.5.0", (22, 12, 0), False),
            ("^20.19.0 || ^22.13.0 || >=23.5.0", (22, 13, 0), True),
            ("^20.19.0 || ^22.13.0 || >=23.5.0", (23, 4, 9), False),
            ("^20.19.0 || ^22.13.0 || >=23.5.0", (23, 5, 0), True),
            ("^20.19.0||>=22.12.0", (21, 0, 0), False),
            ("^20.19.0||>=22.12.0", (22, 12, 0), True),
        )
        for written, node, allowed in cases:
            with self.subTest(range=written, node=node):
                self.assertIs(allows(written, node), allowed)

    def test_a_range_in_another_form_is_not_guessed_at(self) -> None:
        for written in (
            "",
            "*",
            "x",
            "22.x",
            ">22",
            "<23",
            "<=22.12.0",
            ">=22 <23",
            "~22.12.0",
            "22.12.0",
            "=22.12.0",
            "^0.4.0",
            "20 - 22",
            ">=22.12.0.1",
            ">=twenty",
            ">=22.12.0 ||",
            "|| >=22",
            ">=22 | >=24",
            "^",
            ">=",
            ">=-1",
        ):
            with self.subTest(range=written), self.assertRaises(NotReadError):
                allows(written, (22, 22, 2))

    def test_the_oldest_node_that_every_range_allows(self) -> None:
        cases: tuple[tuple[tuple[str, ...], Version | None], ...] = (
            ((">=18",), (18, 0, 0)),
            ((">=18", ">=22.12"), (22, 12, 0)),
            ((">=22.12", ">=18"), (22, 12, 0)),
            ((">=18", "^20.19.0 || >=22.12.0"), (20, 19, 0)),
            (("^20.19.0 || >=22.12.0", "^22.13.0 || >=24.0.0"), (22, 13, 0)),
            (("^20.19.0 || >=22.12.0", "^22.13.0 || >=24.0.0", ">=22.17.0"), (22, 17, 0)),
            (("^22.22.2 || ^24.15.0 || >=26.0.0", ">=22.19.0", ">=22.17.0"), (22, 22, 2)),
            (("^20.19.0 || ^22.13.0 || >=23.5.0", "^22.14.0 || >=24.0.0"), (22, 14, 0)),
            (("20 || >=22", "^20.19.0"), (20, 19, 0)),
            # Where the two meet only later: the first ends before the second begins.
            (("^20.19.0 || >=24.0.0", "^22.13.0 || >=26.0.0"), (26, 0, 0)),
            (("^20.19.0", "^22.13.0"), None),
            (("20", ">=22"), None),
            ((), None),
        )
        for ranges, oldest in cases:
            with self.subTest(ranges=ranges):
                self.assertEqual(oldest_enough(ranges), oldest)


class GoingByTheFilesTest(unittest.TestCase):
    def test_the_ranges_of_a_lock_file_are_those_of_its_packages_and_not_the_projects_own(
        self,
    ) -> None:
        lock: dict[str, object] = {
            "packages": {
                "": {"name": "the project", "engines": {"node": ">=30"}},
                "node_modules/one": {"engines": {"node": ">=18"}},
                "node_modules/two": {"engines": {"node": "^20.19.0 || >=22.12.0", "npm": ">=6"}},
                "node_modules/three": {"engines": {"npm": ">=6"}},
                "node_modules/four": {"version": "1.0.0"},
                "node_modules/five": {"engines": ["node >=4"]},
            }
        }

        self.assertEqual(
            ranges_of(lock),
            {"node_modules/one": ">=18", "node_modules/two": "^20.19.0 || >=22.12.0"},
        )

    def test_a_lock_file_these_checks_cannot_go_by_is_said_to_be_one(self) -> None:
        unusable: tuple[dict[str, object], ...] = (
            {},
            {"packages": []},
            {"packages": {"node_modules/one": {"engines": {"node": 22}}}},
        )
        for lock in unusable:
            with self.subTest(lock=lock), self.assertRaises(UnusableError):
                ranges_of(lock)

    def test_the_least_node_of_a_package_file_is_read_in_one_form_only(self) -> None:
        self.assertEqual(least_of({"engines": {"node": ">=22.22.2"}}), "22.22.2")
        self.assertEqual(least_of({"engines": {"node": ">=22.12"}}), "22.12")
        for said in ("^22.22.2", ">= 22.22.2", "22.22.2", ">=22", ">=22.22.2 ", "", None, 22):
            with self.subTest(said=said), self.assertRaises(UnusableError):
                least_of({"engines": {"node": said}})
        without: tuple[dict[str, object], ...] = ({}, {"engines": {}}, {"engines": ">=22.22.2"})
        for package in without:
            with self.subTest(package=package), self.assertRaises(UnusableError):
                least_of(package)

    def test_the_node_a_text_asks_for_is_read_wherever_it_names_one(self) -> None:
        self.assertEqual(asked_for_in("Node.js is needed, and npm with it."), [])
        self.assertEqual(asked_for_in("You need Node.js 22.22.2 or newer."), ["22.22.2"])
        self.assertEqual(
            asked_for_in(
                "[Node.js](https://nodejs.org/) 22.22.2 or newer, which includes npm.\n"
                "The checks also need Node.js 22.12 or newer."
            ),
            ["22.22.2", "22.12"],
        )
        for text in (
            "You need Node.js 22.12 at least.",
            "You need Node.js v22.12.",
            "You need [Node.js](https://nodejs.org/) 22.",
            "Node.js 22.22.2 or newer here, and Node.js 22 there.",
            "Node.js\n22.12 or later",
        ):
            with self.subTest(text=text), self.assertRaises(UnusableError):
                asked_for_in(text)


class LeastNodeTest(unittest.TestCase):
    def test_the_lock_file_says_the_same_of_the_project(self) -> None:
        self.assertIsNotNone(node_of(load(PACKAGE)))
        self.assertEqual(node_of(packages_of(load(LOCK))[""]), node_of(load(PACKAGE)))

    def test_the_lock_file_holds_the_packages_the_project_names(self) -> None:
        # A lock file that held nothing would have nothing to disagree with.
        package = load(PACKAGE)
        named = [*names_in(package, "dependencies"), *names_in(package, "devDependencies")]
        packages = packages_of(load(LOCK))

        self.assertGreater(len(named), 0)
        for name in named:
            with self.subTest(package=name):
                self.assertIn(f"node_modules/{name}", packages)
        self.assertGreater(len(ranges_of(load(LOCK))), len(named))

    def test_every_locked_package_runs_on_the_least_node(self) -> None:
        least = whole(parts(least_of(load(PACKAGE))))

        for name, written in ranges_of(load(LOCK)).items():
            with self.subTest(package=name, range=written):
                self.assertTrue(allows(written, least))

    def test_the_least_node_is_the_oldest_that_every_locked_package_runs_on(self) -> None:
        # A least Node.js above it would turn people away for nothing.
        least = whole(parts(least_of(load(PACKAGE))))

        self.assertEqual(least, oldest_enough(ranges_of(load(LOCK)).values()))

    def test_the_readme_names_the_least_node_wherever_it_names_one(self) -> None:
        said = asked_for_in(README.read_text(encoding="utf-8"))

        # Written as the check of the tools prints it, number for number. A
        # README that named none would not be equal either.
        self.assertEqual(set(said), {least_of(load(PACKAGE))})


if __name__ == "__main__":
    unittest.main()
