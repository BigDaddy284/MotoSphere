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

For the gates that run tests, the number of tests passed, failed and skipped
is read from the tool's own closing lines. Such a gate also fails when a test
was skipped, when no test ran, or when the numbers cannot be found: a test
that did not run has proved nothing.
"""

import argparse
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
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
    # For a gate that runs tests: the tool whose closing lines hold the counts.
    tests: str = ""


@dataclass(frozen=True)
class Counts:
    """How many tests a gate ran, by outcome.

    "Failed" includes errors. "Skipped" is every test that neither passed nor
    failed: skipped, expected to fail, still to do, left out or not run.
    """

    passed: int
    failed: int
    skipped: int


@dataclass(frozen=True)
class Result:
    """What happened when a gate ran."""

    gate: Gate
    passed: bool
    seconds: float
    note: str = ""
    counts: Counts | None = None


# The folders that hold Python files outside the pipeline.
TOOLING = ("scripts", "tests")

# In the order they run. The two install gates come before the gates that need
# what they install, so the runner works from a clean checkout.
GATES: tuple[Gate, ...] = (
    Gate(
        "repo",
        "Repository checks",
        ("python", "-m", "unittest", "discover", "-s", "tests/repo", "-v"),
        tests="unittest",
    ),
    Gate(
        "scripts",
        "Script tests",
        ("python", "-m", "unittest", "discover", "-s", "tests/scripts", "-v"),
        tests="unittest",
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
    Gate("backend-tests", "Backend tests", ("uv", "run", "pytest"), "backend", "pytest"),
    # The Python files outside the pipeline are checked with the pipeline's
    # locked tools, from the repository root (`ruff.toml`, `mypy.ini`).
    Gate("tools-types", "Tooling type check", ("uv", "run", "--project", "backend", "mypy")),
    Gate(
        "tools-lint",
        "Tooling lint",
        ("uv", "run", "--project", "backend", "ruff", "check", *TOOLING),
    ),
    Gate(
        "tools-format",
        "Tooling format",
        ("uv", "run", "--project", "backend", "ruff", "format", "--check", *TOOLING),
    ),
    Gate("frontend-install", "Frontend install", ("npm", "ci"), "frontend"),
    Gate("frontend-lint", "Frontend lint", ("npm", "run", "lint"), "frontend"),
    Gate("frontend-format", "Frontend format", ("npm", "run", "format:check"), "frontend"),
    Gate("frontend-types", "Frontend type check", ("npm", "run", "typecheck"), "frontend"),
    Gate("frontend-tests", "Frontend unit tests", ("npm", "test"), "frontend", "vitest"),
    Gate("frontend-build", "Frontend build", ("npm", "run", "build"), "frontend"),
    Gate("browser-tests", "Browser tests", ("npm", "run", "e2e"), "frontend", "playwright"),
    # `npm audit`, with the exceptions recorded in `frontend/audit-exceptions.json`.
    Gate("frontend-audit", "Frontend dependency audit", ("python", "scripts/audit.py")),
)


def find_program(name: str) -> str | None:
    """The full path of a program, or None when it is not installed.

    "python" is the Python that runs this script. Everything else is looked
    up on the PATH, which on Windows also finds `npm.cmd` for "npm".
    """
    if name == "python":
        return sys.executable
    return shutil.which(name)


def numbers(text: str, pattern: str) -> dict[str, int]:
    """Every "<number> <word>" pair in the text, as word to number."""
    return {word: int(number) for number, word in re.findall(pattern, text)}


def count_unittest(output: str) -> Counts | None:
    """Read `Ran 9 tests in 0.1s` and `OK (skipped=1)` or `FAILED (failures=1)`."""
    ran = list(re.finditer(r"^Ran (\d+) tests? in ", output, flags=re.MULTILINE))
    if not ran:
        return None
    verdict = re.search(
        r"^(?:OK|FAILED|NO TESTS RAN)(?: \((.*)\))?\s*$",
        output[ran[-1].end() :],
        flags=re.MULTILINE,
    )
    if verdict is None:
        return None
    detail = {
        words: int(number)
        for words, number in re.findall(r"([a-z]+(?: [a-z]+)*)=(\d+)", verdict[1] or "")
    }
    failed = sum(detail.get(word, 0) for word in ("failures", "errors", "unexpected successes"))
    skipped = sum(detail.get(word, 0) for word in ("skipped", "expected failures"))
    return Counts(int(ran[-1][1]) - failed - skipped, failed, skipped)


def count_pytest(output: str) -> Counts | None:
    """Read `==== 1 failed, 114 passed, 2 skipped in 2.51s ====`."""
    closing = re.findall(
        r"^=* ?(\d+ [a-z]+(?:, \d+ [a-z]+)*) in [\d.]+s", output, flags=re.MULTILINE
    )
    if not closing:
        return None
    found = numbers(closing[-1], r"(\d+) ([a-z]+)")
    failed = sum(found.get(word, 0) for word in ("failed", "error", "errors"))
    skipped = sum(found.get(word, 0) for word in ("skipped", "xfailed", "xpassed", "deselected"))
    return Counts(found.get("passed", 0), failed, skipped)


def count_vitest(output: str) -> Counts | None:
    """Read `Tests  1 failed | 198 passed | 1 skipped (200)`."""
    closing = re.findall(
        r"^\s*Tests\s+(\d+ [a-z]+(?: \| \d+ [a-z]+)*) \(\d+\)\s*$", output, flags=re.MULTILINE
    )
    if not closing:
        return None
    found = numbers(closing[-1], r"(\d+) ([a-z]+)")
    skipped = found.get("skipped", 0) + found.get("todo", 0)
    return Counts(found.get("passed", 0), found.get("failed", 0), skipped)


def count_playwright(output: str) -> Counts | None:
    """Read the closing lines `1 failed`, `2 skipped` and `80 passed (10.0s)`."""
    outcomes = "passed|failed|flaky|interrupted|skipped|did not run"
    found = numbers(output, rf"(?m)^\s+(\d+) ({outcomes})(?: \([\d.]+(?:ms|s|m|h)\))?\s*$")
    if not found:
        return None
    failed = sum(found.get(word, 0) for word in ("failed", "flaky", "interrupted"))
    skipped = found.get("skipped", 0) + found.get("did not run", 0)
    return Counts(found.get("passed", 0), failed, skipped)


COUNTERS: dict[str, Callable[[str], Counts | None]] = {
    "unittest": count_unittest,
    "pytest": count_pytest,
    "vitest": count_vitest,
    "playwright": count_playwright,
}


def without_colours(text: str) -> str:
    """The text without the escape codes that terminals read as colours."""
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def judge(gate: Gate, exit_code: int, output: str) -> tuple[str, Counts | None]:
    """Why the gate failed ("" when it passed), and its test counts if it has any."""
    counts = COUNTERS[gate.tests](without_colours(output)) if gate.tests else None
    if exit_code != 0:
        return f"exit code {exit_code}", counts
    if not gate.tests:
        return "", None
    if counts is None:
        return "the test counts could not be read", None
    if counts.skipped:
        return "tests were skipped", counts
    if counts.passed == 0:
        return "no test ran", counts
    return "", counts


def run_gate(gate: Gate, root: Path, echo: Callable[[bytes], None]) -> Result:
    """Run one gate and wait for it. Its output is passed on line by line, and kept."""
    program = find_program(gate.command[0])
    if program is None:
        return Result(gate, False, 0.0, f"{gate.command[0]} is not installed")
    started = time.monotonic()
    kept: list[bytes] = []
    try:
        # The commands are the fixed ones listed above, never outside input.
        with (
            subprocess.Popen(  # noqa: S603
                [program, *gate.command[1:]],
                cwd=root / gate.folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ) as process
        ):
            if process.stdout is not None:
                for line in process.stdout:
                    echo(line)
                    kept.append(line)
        exit_code = process.returncode
    except OSError as error:
        return Result(gate, False, time.monotonic() - started, f"could not start: {error}")
    seconds = time.monotonic() - started
    note, counts = judge(gate, exit_code, b"".join(kept).decode("utf-8", errors="replace"))
    return Result(gate, note == "", seconds, note, counts)


def echo_to(out: TextIO) -> Callable[[bytes], None]:
    """A function that passes a gate's output on to where the runner writes.

    A real terminal or pipe gets the bytes exactly as the gate wrote them, so
    nothing depends on the terminal's character set. Anything else, such as
    the text buffer a test hands in, gets them as text.
    """
    binary = getattr(out, "buffer", None)

    def echo(data: bytes) -> None:
        if binary is None:
            out.write(data.decode("utf-8", errors="replace"))
        else:
            binary.write(data)
            binary.flush()

    return echo


def tally(counts: Counts) -> str:
    """Counts as a person reads them: `198 passed, 1 failed`."""
    parts = [f"{counts.passed} passed"]
    if counts.failed:
        parts.append(f"{counts.failed} failed")
    if counts.skipped:
        parts.append(f"{counts.skipped} skipped")
    return ", ".join(parts)


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
        if result.counts is not None:
            line += f"  {tally(result.counts)}"
        lines.append(f"{line}  {result.note}" if result.note else line)
    failed = [result.gate.name for result in results if not result.passed]
    verdict = f"{len(results) - len(failed)} of {len(results)} gates passed."
    if failed:
        verdict += f" FAILED: {', '.join(failed)}."
    lines += ["", verdict]
    counted = [result.counts for result in results if result.counts is not None]
    if counted:
        lines.append(
            f"Tests: {sum(counts.passed for counts in counted)} passed, "
            f"{sum(counts.failed for counts in counted)} failed, "
            f"{sum(counts.skipped for counts in counted)} skipped."
        )
    return "\n".join([*lines, ""])


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
    echo = echo_to(out)
    for number, gate in enumerate(chosen, start=1):
        out.write(f"\n=== [{number}/{len(chosen)}] {gate.name}: {describe(gate)}\n")
        out.flush()
        results.append(run_gate(gate, root, echo))
    out.write(summary(results))
    out.flush()
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
