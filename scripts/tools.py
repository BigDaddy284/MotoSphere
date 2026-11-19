"""Says whether this computer has the tools MotoSphere needs.

    python scripts/tools.py

MotoSphere needs Python, Git, uv, Node.js and npm (README.md). For each of
them the script says which version it found and, where the project asks for
a least version, which one. A tool that is missing, too old or broken is
named with the place to get it. The script installs nothing and changes
nothing.

The least versions are read from the project's own files, where the tools
themselves read them: Python's from `backend/pyproject.toml` and Node.js's
from `frontend/package.json`.

The script uses the Python standard library only. Its exit code is 0 when
every tool is ready and 1 when one is not, or when the check could not be
carried out.
"""

import sys

# The least Python this script itself runs on: the one the project asks for
# (a test compares the two). An older Python cannot run the lines below, so
# it is told here, in plain words, before it reaches them.
LEAST_PYTHON = (3, 12)
if sys.version_info < LEAST_PYTHON:
    sys.exit(
        "MotoSphere needs Python {}.{} or newer, and this is Python {}.{}. "
        "Get a newer one from https://www.python.org/downloads/".format(
            *LEAST_PYTHON, *sys.version_info[:2]
        )
    )

import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tomllib  # noqa: E402
from collections.abc import Callable, Sequence  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import TextIO  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Where each least version is written.
PYTHON_FILE = "backend/pyproject.toml"
NODE_FILE = "frontend/package.json"

# How long a tool may take to say its version.
TIMEOUT_SECONDS = 30

Version = tuple[int, ...]


class UnusableError(Exception):
    """The check could not be carried out. The message says why, in plain words."""


class BrokenError(Exception):
    """A tool is there but does not work. The message says why, in plain words."""


@dataclass(frozen=True)
class Tool:
    """One tool: its name, the program that starts it and where to get it."""

    name: str
    program: str
    source: str
    # The key of this tool's least version in `least_versions`, if it has one.
    least: str = ""


# In the order a new computer needs them.
TOOLS: tuple[Tool, ...] = (
    Tool("Python", "python", "https://www.python.org/downloads/", "python"),
    Tool("Git", "git", "https://git-scm.com/downloads"),
    Tool("uv", "uv", "https://docs.astral.sh/uv/getting-started/installation/"),
    Tool("Node.js", "node", "https://nodejs.org/en/download", "node"),
    Tool("npm", "npm", "https://nodejs.org/en/download (it comes with Node.js)"),
)


@dataclass(frozen=True)
class Finding:
    """What the check found out about one tool."""

    tool: Tool
    # FOUND, TOO OLD, MISSING or BROKEN.
    state: str
    version: Version | None = None
    least: Version | None = None
    # For a broken tool: what went wrong.
    reason: str = ""

    @property
    def ready(self) -> bool:
        return self.state == "FOUND"


Find = Callable[[str], str | None]
Ask = Callable[[str], str]


def text_of(version: Version) -> str:
    """A version the way people write it: 22.12."""
    return ".".join(str(part) for part in version)


def read_version(text: str) -> Version | None:
    """The first version number in what a tool printed, or None without one.

    `git version 2.56.0.windows.4` is 2.56.0, `v22.23.4` is 22.23.4 and
    `uv 0.11.32 (x86_64-unknown-linux-gnu)` is 0.11.32.
    """
    found = re.search(r"\d+(?:\.\d+)+", text)
    if found is None:
        return None
    return tuple(int(part) for part in found[0].split("."))


def new_enough(version: Version, least: Version) -> bool:
    """Whether a version is the least version or a newer one. 22.12 is 22.12.0."""
    width = max(len(version), len(least))
    padded = version + (0,) * (width - len(version))
    return padded >= least + (0,) * (width - len(least))


def read_least(text: object, where: str) -> Version:
    """A least version written as `>=3.12`, the only form this check reads."""
    found = re.fullmatch(r"\s*>=\s*(\d+(?:\.\d+)*)\s*", text) if isinstance(text, str) else None
    if found is None:
        raise UnusableError(f"{where} does not name a least version in the form >=1.2")
    return tuple(int(part) for part in found[1].split("."))


def least_versions(root: Path) -> dict[str, Version]:
    """The least versions the project asks for, read from the project's own files."""
    try:
        project = tomllib.loads((root / PYTHON_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        raise UnusableError(f"{PYTHON_FILE} is missing or cannot be read") from None
    try:
        package = json.loads((root / NODE_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise UnusableError(f"{NODE_FILE} is missing or cannot be read") from None

    requires = project.get("project", {})
    engines = package.get("engines", {}) if isinstance(package, dict) else {}
    return {
        "python": read_least(
            requires.get("requires-python") if isinstance(requires, dict) else None,
            f"{PYTHON_FILE} (requires-python)",
        ),
        "node": read_least(
            engines.get("node") if isinstance(engines, dict) else None,
            f"{NODE_FILE} (engines, node)",
        ),
    }


def find_program(name: str) -> str | None:
    """The full path of a program, or None when it is not installed.

    "python" is the Python that runs this script. Everything else is looked
    up on the PATH, which on Windows also finds `npm.cmd` for "npm".
    """
    if name == "python":
        return sys.executable
    return shutil.which(name)


def ask_version(
    program: str,
    arguments: Sequence[str] = ("--version",),
    timeout: float = TIMEOUT_SECONDS,
) -> str:
    """What a program prints when asked for its version."""
    try:
        # The program is one of the five named in TOOLS, by its full path.
        finished = subprocess.run(  # noqa: S603
            [program, *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise BrokenError(f"it gave no answer within {timeout:g} seconds") from None
    except OSError:
        raise BrokenError("it could not be started") from None
    if finished.returncode != 0:
        raise BrokenError(f"it stopped with exit code {finished.returncode}")
    return finished.stdout + finished.stderr


def look_at(tool: Tool, least: Version | None, find: Find, ask: Ask) -> Finding:
    """Find one tool, ask its version and compare it with the least version."""
    program = find(tool.program)
    if program is None:
        return Finding(tool, "MISSING", least=least)
    try:
        answer = ask(program)
    except BrokenError as error:
        return Finding(tool, "BROKEN", least=least, reason=str(error))
    version = read_version(answer)
    if version is None:
        return Finding(tool, "BROKEN", least=least, reason="it did not say its version")
    if least is not None and not new_enough(version, least):
        return Finding(tool, "TOO OLD", version, least)
    return Finding(tool, "FOUND", version, least)


def line_for(finding: Finding) -> str:
    """One line of the report about one tool."""
    tool = finding.tool
    needed = "" if finding.least is None else f" ({text_of(finding.least)} or newer is needed)"
    if finding.state == "MISSING":
        return f"  MISSING  {tool.name}{needed}. Get it from {tool.source}"
    if finding.state == "BROKEN":
        return f"  BROKEN   {tool.name}: {finding.reason}. Get it again from {tool.source}"
    found = "" if finding.version is None else f" {text_of(finding.version)}"
    if finding.state == "TOO OLD":
        return f"  TOO OLD  {tool.name}{found}{needed}. Get a newer one from {tool.source}"
    return f"  FOUND    {tool.name}{found}{needed}"


def main(
    arguments: Sequence[str] | None = None,
    root: Path = ROOT,
    out: TextIO = sys.stdout,
    find: Find = find_program,
    ask: Ask = ask_version,
) -> int:
    """Look at every tool and write what was found. Returns the exit code."""
    parser = argparse.ArgumentParser(
        description="Say whether this computer has the tools MotoSphere needs."
    )
    parser.parse_args(arguments)

    try:
        least = least_versions(root)
    except UnusableError as error:
        out.write(f"The tools could not be checked: {error}\n")
        return 1

    findings = [look_at(tool, least.get(tool.least), find, ask) for tool in TOOLS]
    out.write("The tools MotoSphere needs on this computer:\n\n")
    for finding in findings:
        out.write(line_for(finding) + "\n")
    ready = sum(finding.ready for finding in findings)
    out.write(f"\n{ready} of {len(findings)} tools are ready.\n")
    return 0 if ready == len(findings) else 1


if __name__ == "__main__":
    sys.exit(main())
