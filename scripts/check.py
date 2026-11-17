"""Run every check of the project, in order, and say which passed.

Standard library only, so it runs with a plain Python 3.12+ on Windows 11 and
Linux, from any folder:

    python scripts/check.py                     every gate
    python scripts/check.py --list              the gates, without running them
    python scripts/check.py --only repo         one gate
    python scripts/check.py --only frontend-lint frontend-tests

Every gate runs even when an earlier one failed, so one run shows everything
that is wrong. The exit code is 0 when every gate that ran passed, and 1
otherwise.
"""

import argparse
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Gate:
    """One check: a command, and the folder under the repository it runs in."""

    key: str
    name: str
    command: tuple[str, ...]
    folder: str = "."


@dataclass(frozen=True)
class Result:
    """What happened when a gate ran."""

    gate: Gate
    passed: bool
    seconds: float
    note: str = ""


# In the order they run. The two install gates come before the gates that need
# what they install, so the runner works from a clean checkout.
GATES: tuple[Gate, ...] = (
    Gate(
        "repo",
        "Repository checks",
        ("python", "-m", "unittest", "discover", "-s", "tests/repo", "-v"),
    ),
    Gate(
        "scripts",
        "Script tests",
        ("python", "-m", "unittest", "discover", "-s", "tests/scripts", "-v"),
    ),
    Gate("backend-lock", "Backend lock file", ("uv", "lock", "--check"), "backend"),
    Gate("backend-install", "Backend install", ("uv", "sync", "--locked"), "backend"),
    Gate("backend-types", "Backend type check", ("uv", "run", "mypy"), "backend"),
    Gate("backend-lint", "Backend lint", ("uv", "run", "ruff", "check", "."), "backend"),
    Gate(
        "backend-format",
        "Backend format",
        ("uv", "run", "ruff", "format", "--check", "."),
        "backend",
    ),
    Gate("backend-tests", "Backend tests", ("uv", "run", "pytest"), "backend"),
    Gate("frontend-install", "Frontend install", ("npm", "ci"), "frontend"),
    Gate("frontend-lint", "Frontend lint", ("npm", "run", "lint"), "frontend"),
    Gate("frontend-format", "Frontend format", ("npm", "run", "format:check"), "frontend"),
    Gate("frontend-types", "Frontend type check", ("npm", "run", "typecheck"), "frontend"),
    Gate("frontend-tests", "Frontend unit tests", ("npm", "test"), "frontend"),
    Gate("frontend-build", "Frontend build", ("npm", "run", "build"), "frontend"),
    Gate("browser-tests", "Browser tests", ("npm", "run", "e2e"), "frontend"),
    Gate("frontend-audit", "Frontend dependency audit", ("npm", "audit"), "frontend"),
)


def find_program(name: str) -> str | None:
    """The full path of a program, or None when it is not installed.

    "python" is the Python that runs this script. Everything else is looked
    up on the PATH, which on Windows also finds `npm.cmd` for "npm".
    """
    if name == "python":
        return sys.executable
    return shutil.which(name)


def run_gate(gate: Gate, root: Path) -> Result:
    """Run one gate and wait for it. Its output goes straight to the terminal."""
    program = find_program(gate.command[0])
    if program is None:
        return Result(gate, False, 0.0, f"{gate.command[0]} is not installed")
    started = time.monotonic()
    try:
        # The commands are the fixed ones listed above, never outside input.
        finished = subprocess.run(  # noqa: S603
            [program, *gate.command[1:]], cwd=root / gate.folder, check=False
        )
    except OSError as error:
        return Result(gate, False, time.monotonic() - started, f"could not start: {error}")
    seconds = time.monotonic() - started
    if finished.returncode != 0:
        return Result(gate, False, seconds, f"exit code {finished.returncode}")
    return Result(gate, True, seconds)


def describe(gate: Gate) -> str:
    """The command of a gate as a person would type it."""
    command = " ".join(gate.command)
    return command if gate.folder == "." else f"{command}  (in {gate.folder}/)"


def summary(results: Sequence[Result]) -> str:
    """The closing report: one line for each gate, then the verdict."""
    width = max(len(result.gate.name) for result in results)
    lines = ["", "Summary", ""]
    for result in results:
        line = (
            f"  {'PASSED' if result.passed else 'FAILED'}  "
            f"{result.gate.name:<{width}}  {result.seconds:7.1f} s"
        )
        lines.append(f"{line}  {result.note}" if result.note else line)
    failed = [result.gate.name for result in results if not result.passed]
    verdict = f"{len(results) - len(failed)} of {len(results)} gates passed."
    if failed:
        verdict += f" FAILED: {', '.join(failed)}."
    return "\n".join([*lines, "", verdict, ""])


def main(
    arguments: Sequence[str] | None = None,
    gates: Sequence[Gate] = GATES,
    root: Path = ROOT,
    out: TextIO = sys.stdout,
) -> int:
    parser = argparse.ArgumentParser(
        prog="check.py", description="Run the project's checks and say which passed."
    )
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument(
        "--list", action="store_true", help="show the gates and their commands, and run nothing"
    )
    choice.add_argument(
        "--only",
        nargs="+",
        choices=[gate.key for gate in gates],
        metavar="GATE",
        help="run only these gates (see --list for their names)",
    )
    options = parser.parse_args(arguments)

    if options.list:
        width = max(len(gate.key) for gate in gates)
        for gate in gates:
            out.write(f"{gate.key:<{width}}  {describe(gate)}\n")
        return 0

    chosen = [gate for gate in gates if options.only is None or gate.key in options.only]
    results: list[Result] = []
    for number, gate in enumerate(chosen, start=1):
        out.write(f"\n=== [{number}/{len(chosen)}] {gate.name}: {describe(gate)}\n")
        out.flush()
        results.append(run_gate(gate, root))
    out.write(summary(results))
    out.flush()
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
