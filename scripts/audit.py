"""Checks the frontend's dependencies against published security advisories.

    python scripts/audit.py

It runs `npm audit` in `frontend/` and fails on every advisory it reports,
with one way out: an exception recorded in `frontend/audit-exceptions.json`.
An exception is a decision somebody made and wrote down, with the reason and
a date by which it must be looked at again. The check also fails when an
exception is past that date and when it is no longer needed, so the list can
neither be forgotten nor grow stale.

The script uses the Python standard library only. Its exit code is 0 when the
check passed and 1 when it did not, or when it could not be carried out.
"""

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parent.parent

# Where the exceptions are recorded, from the repository root.
EXCEPTIONS = "frontend/audit-exceptions.json"

# The command that reports the advisories, run in `frontend/`.
AUDIT = ("npm", "audit", "--json")

# The longest an exception may stand before somebody looks at it again.
LONGEST_DAYS = 31

# An exception must say why, in a sentence, not in a word.
SHORTEST_REASON = 40

# How GitHub names an advisory, for example GHSA-fc5q-39xc-vjpf.
ADVISORY_ID = re.compile(r"^GHSA(-[23456789cfghjmpqrvwx]{4}){3}$")

FIELDS = ("advisory", "package", "reason", "accepted", "review_by")


class UnusableError(Exception):
    """The audit could not be judged. The message says why, in plain words."""


@dataclass(frozen=True)
class Advisory:
    """One advisory that `npm audit` reports for an installed package."""

    identity: str
    package: str
    severity: str
    title: str
    url: str


@dataclass(frozen=True)
class Accepted:
    """One recorded exception: an advisory accepted for now, and why."""

    advisory: str
    package: str
    reason: str
    accepted: dt.date
    review_by: dt.date


def read_date(entry: dict[str, str], field: str, where: str) -> dt.date:
    """A date written as 2026-11-17."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry[field]):
        raise UnusableError(f'{where}: "{field}" must be a date written like 2026-11-17')
    try:
        return dt.date.fromisoformat(entry[field])
    except ValueError:
        raise UnusableError(f'{where}: "{field}" is not a real date') from None


def read_exceptions(text: str) -> tuple[Accepted, ...]:
    """Read and check the exceptions file. Every fault is named in plain words."""
    try:
        document = json.loads(text)
    except ValueError as error:
        raise UnusableError(f"{EXCEPTIONS} is not valid JSON: {error}") from None
    if (
        not isinstance(document, dict)
        or list(document) != ["exceptions"]
        or not isinstance(document["exceptions"], list)
    ):
        raise UnusableError(f'{EXCEPTIONS} must hold one list, named "exceptions"')

    accepted: list[Accepted] = []
    for number, entry in enumerate(document["exceptions"], start=1):
        where = f"{EXCEPTIONS}, exception {number}"
        if not isinstance(entry, dict) or sorted(entry) != sorted(FIELDS):
            raise UnusableError(f"{where}: must have exactly the fields {', '.join(FIELDS)}")
        if not all(isinstance(value, str) for value in entry.values()):
            raise UnusableError(f"{where}: every field must be text")
        if not ADVISORY_ID.fullmatch(entry["advisory"]):
            raise UnusableError(f'{where}: "advisory" must be an id like GHSA-fc5q-39xc-vjpf')
        if not entry["package"].strip():
            raise UnusableError(f'{where}: "package" is empty')
        if len(entry["reason"].strip()) < SHORTEST_REASON:
            raise UnusableError(
                f'{where}: "reason" must say why in at least {SHORTEST_REASON} characters'
            )
        since = read_date(entry, "accepted", where)
        until = read_date(entry, "review_by", where)
        if until <= since:
            raise UnusableError(f'{where}: "review_by" must be after "accepted"')
        if (until - since).days > LONGEST_DAYS:
            raise UnusableError(
                f'{where}: "review_by" may be at most {LONGEST_DAYS} days after "accepted"'
            )
        if any(earlier.advisory == entry["advisory"] for earlier in accepted):
            raise UnusableError(f"{where}: {entry['advisory']} is listed twice")
        accepted.append(
            Accepted(entry["advisory"], entry["package"], entry["reason"].strip(), since, until)
        )
    return tuple(accepted)


def advisories(report: object) -> tuple[Advisory, ...]:
    """The advisories in a report from `npm audit --json`, each one once."""
    packages = report.get("vulnerabilities") if isinstance(report, dict) else None
    if not isinstance(packages, dict):
        detail = ""
        if isinstance(report, dict) and isinstance(report.get("error"), dict):
            detail = f": {report['error'].get('summary') or report['error'].get('code')}"
        raise UnusableError(f"npm audit gave no report{detail}")

    found: dict[tuple[str, str], Advisory] = {}
    for package in packages.values():
        for cause in package.get("via", []) if isinstance(package, dict) else []:
            # A cause that is only a name points at another package in the
            # report; the advisory itself is listed under that package.
            if not isinstance(cause, dict):
                continue
            url = str(cause.get("url", ""))
            last = url.rsplit("/", 1)[-1]
            advisory = Advisory(
                identity=last if ADVISORY_ID.fullmatch(last) else url,
                package=str(cause.get("name", "")),
                severity=str(cause.get("severity", "")),
                title=str(cause.get("title", "")),
                url=url,
            )
            found[(advisory.identity, advisory.package)] = advisory
    if packages and not found:
        # The report lists affected packages but no advisory this script can
        # read. Passing here would switch the check off without a word.
        raise UnusableError("npm audit lists affected packages but names no advisory")
    return tuple(found[key] for key in sorted(found))


def judge(found: Sequence[Advisory], accepted: Sequence[Accepted], today: dt.date) -> list[str]:
    """Everything that is wrong, in plain words. An empty list means the check passed."""
    exceptions = {exception.advisory: exception for exception in accepted}
    problems: list[str] = []
    for advisory in found:
        exception = exceptions.get(advisory.identity)
        if exception is None:
            problems.append(
                f"{advisory.package}: {advisory.title} ({advisory.severity}) {advisory.url}"
            )
        elif exception.package != advisory.package:
            problems.append(
                f"the exception for {advisory.identity} names the package "
                f"{exception.package}, but the advisory is about {advisory.package}"
            )
    reported = {advisory.identity for advisory in found}
    for exception in accepted:
        name = f"the exception for {exception.advisory} ({exception.package})"
        if exception.advisory not in reported:
            problems.append(f"{name} is no longer needed: remove it")
        elif exception.accepted > today:
            problems.append(f"{name} is dated in the future ({exception.accepted})")
        elif today > exception.review_by:
            problems.append(
                f"{name} was due for review on {exception.review_by}: "
                "look at the advisory again, then renew the exception or remove it"
            )
    return problems


def run_audit(root: Path, command: Sequence[str] = AUDIT) -> object:
    """Run the audit command in `frontend/` and return its report."""
    program = shutil.which(command[0])
    if program is None:
        raise UnusableError(f"{command[0]} is not installed")
    try:
        # The command is the fixed one above, never outside input. npm ends
        # with exit code 1 when it reports advisories, so the exit code says
        # nothing here: the report does.
        completed = subprocess.run(  # noqa: S603
            [program, *command[1:]],
            cwd=root / "frontend",
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise UnusableError(f"{command[0]} could not be started: {error}") from None
    try:
        return json.loads(completed.stdout.decode("utf-8", errors="replace"))
    except ValueError:
        raise UnusableError(
            f"{command[0]} gave no report (exit code {completed.returncode})"
        ) from None


def main(
    arguments: Sequence[str] | None = None,
    root: Path = ROOT,
    today: dt.date | None = None,
    out: TextIO = sys.stdout,
    command: Sequence[str] = AUDIT,
) -> int:
    """Run the check and write what it found. Returns the exit code."""
    parser = argparse.ArgumentParser(
        description="Check the frontend's dependencies against published security advisories."
    )
    parser.parse_args(arguments)
    day = today or dt.datetime.now(dt.UTC).date()

    try:
        try:
            text = (root / EXCEPTIONS).read_text(encoding="utf-8")
        except OSError:
            raise UnusableError(f"{EXCEPTIONS} is missing or cannot be read") from None
        accepted = read_exceptions(text)
        found = advisories(run_audit(root, command))
    except UnusableError as error:
        out.write(f"The dependency audit could not be judged: {error}\n")
        return 1

    problems = judge(found, accepted, day)
    out.write(
        f"npm audit reports {len(found)} {'advisory' if len(found) == 1 else 'advisories'}.\n"
    )
    reported = {advisory.identity for advisory in found}
    for exception in accepted:
        if exception.advisory in reported:
            out.write(
                f"  recorded exception: {exception.advisory} ({exception.package}), "
                f"review by {exception.review_by}. {exception.reason}\n"
            )
    if problems:
        out.write("FAILED:\n")
        for problem in problems:
            out.write(f"  - {problem}\n")
        return 1
    out.write("Dependency audit passed.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
