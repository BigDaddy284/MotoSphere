"""Checks on the licences of the packages the site is built with (FND-050).

The lock file of the frontend names the licence of every package. What the
site passes on to every visitor is code of the packages the lock file does
not mark as only for the work, and passing code on is what a licence puts
conditions on. So the licence of each of those packages must be one the
project has accepted: one a person has read, with what it asks and how the
project meets that written down here. A package under any other licence,
or with none named, fails these checks until a person has read the licence
and put it on the list, in the same pull request, where a reviewer sees it.

A licence is taken as the lock file writes it. `(MIT AND Zlib)` is one
entry of the list, not two: what a combination asks is for a person to
read, not for a check to work out.

Standard library only, as all repository checks. Run from the repository
root:

    python -m unittest discover -s tests/repo -v
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "frontend" / "package-lock.json"

# The licences the project has accepted for code the site passes on, each
# as the lock file writes it, with what it asks and how the project meets
# it. The site's file of licences is `licences.txt`, which the build writes
# (FND-047). The seven here were read by the planner of the project in the
# texts the packages bring (PLAN-038). The list is the project's own record
# of what it relies on, not a lawyer's opinion.
ACCEPTED = {
    "MIT": (
        "Asks that its copyright notice and its text go with every copy: "
        "both are in the site's file of licences."
    ),
    "ISC": (
        "Asks what MIT asks, in fewer words: its notice and its text are in "
        "the site's file of licences."
    ),
    "0BSD": "Asks nothing of whoever passes the code on.",
    "BSD-3-Clause": (
        "Asks that its notice and its text go with every copy, and that the "
        "names of its authors are not used to promote what is built with it: "
        "both are in the site's file of licences, and the site promotes "
        "itself with nobody's name."
    ),
    "Apache-2.0": (
        "Asks that its text and what a NOTICE file of the package says go "
        "with every copy, and that a changed file says it was changed: the "
        "site's file of licences holds both, and the project changes no "
        "file of a package. The build packs the code, which the licence "
        "calls its object form and does not count as a change."
    ),
    "(MPL-2.0 OR Apache-2.0)": (
        "A choice of two licences: the project takes Apache-2.0, which is on this list."
    ),
    "(MIT AND Zlib)": (
        "Both hold. MIT is on this list. Zlib asks that nobody says they "
        "wrote the code who did not, that a changed source is marked as "
        "changed, and that its notice stays in a source that is passed on: "
        "the site's file of licences names the package as its authors', the "
        "project changes no file of a package, and it passes on the code as "
        "the build packs it, not its source."
    ),
}
# What the lock file says of the four packages the project itself names as
# shipped. If the reading below ever found nothing, the checks of the real
# lock file would pass without having looked.
NAMED_BY_THE_PROJECT = {
    "node_modules/@cesium/core": "Apache-2.0",
    "node_modules/@cesium/engine": "Apache-2.0",
    "node_modules/react": "MIT",
    "node_modules/react-dom": "MIT",
}


class UnusableError(Exception):
    """A lock file is not what these checks can go by."""


def shipped(lock: object) -> dict[str, object]:
    """What a lock file says is the licence of each package the site may ship.

    By the place the package is put (`node_modules/react`), so a package
    that is put in two places is held twice. The value is what the lock
    file gives, whatever it is; `None` when it gives nothing.
    """
    packages = lock.get("packages") if isinstance(lock, dict) else None
    if not isinstance(packages, dict):
        raise UnusableError("the lock file has no list of packages")
    found: dict[str, object] = {}
    for where, said in packages.items():
        if where == "":
            continue
        if not isinstance(said, dict):
            raise UnusableError(f"{where} is not a list of names and values")
        if said.get("dev") is not True:
            found[where] = said.get("license")
    return found


def not_accepted(found: dict[str, object], accepted: dict[str, str]) -> list[str]:
    """One sentence for every package whose licence is not on the list."""
    problems = []
    for where in sorted(found):
        licence = found[where]
        if not isinstance(licence, str) or licence.strip() == "":
            problems.append(f"{where} names no licence.")
        elif licence not in accepted:
            problems.append(f"{where} is under {licence}, which is not on the list.")
    return problems


def not_used(found: dict[str, object], accepted: dict[str, str]) -> list[str]:
    """The licences on the list that no package is under."""
    return sorted(
        set(accepted) - {licence for licence in found.values() if isinstance(licence, str)}
    )


# A list made up for the tests of how packages are held to a list.
A_LIST = {"MIT": "Read.", "(MIT AND Zlib)": "Read."}


class ReadingTheLicencesTest(unittest.TestCase):
    def test_the_licences_are_those_of_the_packages_not_only_for_the_work(self) -> None:
        lock = {
            "packages": {
                "": {"name": "the project", "license": "UNLICENSED"},
                "node_modules/shipped": {"version": "1.0.0", "license": "MIT"},
                "node_modules/@scope/shipped": {"version": "2.0.0", "license": "ISC"},
                "node_modules/tool": {"version": "3.0.0", "license": "GPL-3.0", "dev": True},
                "node_modules/left-out-or-not": {
                    "version": "4.0.0",
                    "license": "Apache-2.0",
                    "optional": True,
                },
                "node_modules/asked-for-by-another": {
                    "version": "5.0.0",
                    "license": "0BSD",
                    "peer": True,
                },
            }
        }

        self.assertEqual(
            shipped(lock),
            {
                "node_modules/shipped": "MIT",
                "node_modules/@scope/shipped": "ISC",
                "node_modules/left-out-or-not": "Apache-2.0",
                "node_modules/asked-for-by-another": "0BSD",
            },
        )

    def test_a_package_is_only_for_the_work_when_the_lock_file_says_exactly_that(self) -> None:
        for dev in (False, "true", 1, None):
            with self.subTest(dev=dev):
                lock = {"packages": {"node_modules/one": {"license": "MIT", "dev": dev}}}

                self.assertEqual(shipped(lock), {"node_modules/one": "MIT"})

    def test_a_package_put_in_two_places_is_read_in_each(self) -> None:
        lock = {
            "packages": {
                "node_modules/one": {"version": "1.0.0", "license": "MIT"},
                "node_modules/two/node_modules/one": {"version": "0.9.0", "license": "GPL-2.0"},
            }
        }

        self.assertEqual(
            shipped(lock),
            {"node_modules/one": "MIT", "node_modules/two/node_modules/one": "GPL-2.0"},
        )

    def test_what_the_lock_file_gives_is_kept_as_it_is(self) -> None:
        for licence in (None, "", "  ", 5, ["MIT"], {"type": "MIT"}, "mit"):
            with self.subTest(licence=licence):
                lock = {"packages": {"node_modules/one": {"license": licence}}}

                self.assertEqual(shipped(lock), {"node_modules/one": licence})

    def test_a_package_that_names_no_licence_has_none(self) -> None:
        self.assertEqual(
            shipped({"packages": {"node_modules/one": {"version": "1.0.0"}}}),
            {"node_modules/one": None},
        )

    def test_a_lock_file_without_packages_is_not_gone_by(self) -> None:
        unusable: tuple[object, ...] = ({}, {"packages": []}, {"packages": "none"}, [], None, "x")
        for lock in unusable:
            with self.subTest(lock=lock), self.assertRaises(UnusableError):
                shipped(lock)

    def test_a_package_that_is_no_list_of_names_and_values_is_not_gone_by(self) -> None:
        for said in (None, "MIT", ["MIT"], 1):
            with self.subTest(said=said), self.assertRaises(UnusableError):
                shipped({"packages": {"node_modules/one": said}})


class HoldingToTheListTest(unittest.TestCase):
    def test_a_package_under_a_licence_on_the_list_is_passed(self) -> None:
        found: dict[str, object] = {"node_modules/one": "MIT", "node_modules/two": "(MIT AND Zlib)"}

        self.assertEqual(not_accepted(found, A_LIST), [])

    def test_a_package_under_another_licence_is_named_with_it(self) -> None:
        found: dict[str, object] = {
            "node_modules/two": "GPL-3.0",
            "node_modules/one": "MIT",
            "node_modules/@scope/three": "Elastic-2.0",
        }

        self.assertEqual(
            not_accepted(found, A_LIST),
            [
                "node_modules/@scope/three is under Elastic-2.0, which is not on the list.",
                "node_modules/two is under GPL-3.0, which is not on the list.",
            ],
        )

    def test_a_package_that_names_no_licence_is_reported(self) -> None:
        for licence in (None, "", "  ", 5, ["MIT"], {"type": "MIT"}):
            with self.subTest(licence=licence):
                self.assertEqual(
                    not_accepted({"node_modules/one": licence}, A_LIST),
                    ["node_modules/one names no licence."],
                )

    def test_a_licence_is_taken_as_it_is_written(self) -> None:
        written = (
            "mit",
            "MIT ",
            " MIT",
            "MIT OR GPL-3.0",
            "(MIT OR Zlib)",
            "(Zlib AND MIT)",
            "MIT AND Zlib",
            "Zlib",
            "MIT-0",
            "SEE LICENSE IN LICENSE.md",
        )
        for licence in written:
            with self.subTest(licence=licence):
                self.assertEqual(
                    not_accepted({"node_modules/one": licence}, A_LIST),
                    [f"node_modules/one is under {licence}, which is not on the list."],
                )

    def test_two_licences_on_the_list_do_not_make_their_combination_one(self) -> None:
        each = {"MIT": "Read.", "ISC": "Read."}
        for licence in ("(MIT AND ISC)", "(MIT OR ISC)", "MIT AND ISC", "MIT OR ISC", "MIT, ISC"):
            with self.subTest(licence=licence):
                self.assertEqual(
                    not_accepted({"node_modules/one": licence}, each),
                    [f"node_modules/one is under {licence}, which is not on the list."],
                )

    def test_a_licence_on_the_list_that_no_package_is_under_is_reported(self) -> None:
        self.assertEqual(not_used({"node_modules/one": "MIT"}, A_LIST), ["(MIT AND Zlib)"])
        self.assertEqual(not_used({}, A_LIST), ["(MIT AND Zlib)", "MIT"])
        self.assertEqual(
            not_used({"node_modules/one": "MIT", "node_modules/two": "(MIT AND Zlib)"}, A_LIST),
            [],
        )

    def test_a_package_without_a_licence_uses_none_of_the_list(self) -> None:
        found: dict[str, object] = {"node_modules/one": None, "node_modules/two": ["MIT"]}

        self.assertEqual(not_used(found, {"MIT": "Read."}), ["MIT"])


class AcceptedLicencesTest(unittest.TestCase):
    def found(self) -> dict[str, object]:
        return shipped(json.loads(LOCK.read_text(encoding="utf-8")))

    def test_every_package_the_site_may_ship_is_under_an_accepted_licence(self) -> None:
        self.assertEqual(not_accepted(self.found(), ACCEPTED), [])

    def test_every_accepted_licence_is_one_a_package_is_under(self) -> None:
        # A licence nobody ships under any more is taken off the list: the
        # list says what the site passes on today.
        self.assertEqual(not_used(self.found(), ACCEPTED), [])

    def test_the_list_says_of_every_licence_why_it_is_accepted(self) -> None:
        for licence, why in ACCEPTED.items():
            with self.subTest(licence=licence):
                self.assertEqual(licence, licence.strip())
                self.assertGreaterEqual(len(why.split()), 5)
                self.assertTrue(why.endswith("."))

    def test_the_reading_finds_the_packages_the_project_names(self) -> None:
        found = self.found()

        self.assertEqual(
            {where: found.get(where) for where in NAMED_BY_THE_PROJECT}, NAMED_BY_THE_PROJECT
        )


if __name__ == "__main__":
    unittest.main()
