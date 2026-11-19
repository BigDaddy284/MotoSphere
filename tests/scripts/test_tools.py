"""Tests for the check of the tools, `scripts/tools.py` (task FND-019).

Run from the repository root:

    python -m unittest discover -s tests/scripts -v

The lines the tools print were copied from real runs: Git, uv, Node.js, npm
and Python on Linux, and Git on Windows from a log of GitHub's Windows
machine. Where a test needs a tool that is missing, too old or broken, a
stand-in answers for it, and the stand-in programs are run by the real Python.
"""

import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# The script is not an installed package, so its folder is added to the places
# Python imports from.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tools

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "tools.py"

# What each tool printed, in a real run, when asked for its version.
PRINTED = {
    "python": "Python 3.13.18\n",
    "git": "git version 2.43.0\n",
    "uv": "uv 0.11.32 (x86_64-unknown-linux-gnu)\n",
    "node": "v22.23.4\n",
    "npm": "10.9.9\n",
}
GIT_ON_WINDOWS = "git version 2.56.0.windows.4\n"

EVERYTHING_FOUND = (
    "The tools MotoSphere needs on this computer:\n"
    "\n"
    "  FOUND    Python 3.13.18 (3.12 or newer is needed)\n"
    "  FOUND    Git 2.43.0\n"
    "  FOUND    uv 0.11.32\n"
    "  FOUND    Node.js 22.23.4 (22.12 or newer is needed)\n"
    "  FOUND    npm 10.9.9\n"
    "\n"
    "5 of 5 tools are ready.\n"
)


def find(name: str) -> str | None:
    """A computer that has every tool: each program is found under its name."""
    return name


def ask(program: str) -> str:
    """A computer whose tools print what the real ones printed."""
    return PRINTED[program]


class ProjectTest(unittest.TestCase):
    """A stand-in for the project: a folder with the two files that name versions."""

    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.write(tools.PYTHON_FILE, '[project]\nname = "x"\nrequires-python = ">=3.12"\n')
        self.write(tools.NODE_FILE, '{"engines": {"node": ">=22.12"}}\n')

    def write(self, name: str, text: str) -> None:
        path = self.folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class ReadVersionTest(unittest.TestCase):
    def test_reads_what_each_tool_really_prints(self) -> None:
        self.assertEqual(tools.read_version(PRINTED["python"]), (3, 13, 18))
        self.assertEqual(tools.read_version(PRINTED["git"]), (2, 43, 0))
        self.assertEqual(tools.read_version(PRINTED["uv"]), (0, 11, 32))
        self.assertEqual(tools.read_version(PRINTED["node"]), (22, 23, 4))
        self.assertEqual(tools.read_version(PRINTED["npm"]), (10, 9, 9))

    def test_reads_git_on_windows_without_what_follows_the_version(self) -> None:
        self.assertEqual(tools.read_version(GIT_ON_WINDOWS), (2, 56, 0))

    def test_finds_no_version_where_none_is_printed(self) -> None:
        self.assertIsNone(tools.read_version(""))
        self.assertIsNone(tools.read_version("this program cannot be run\n"))

    def test_a_lone_number_is_not_a_version(self) -> None:
        self.assertIsNone(tools.read_version("stopped with error 127\n"))


class NewEnoughTest(unittest.TestCase):
    def test_the_least_version_itself_is_new_enough(self) -> None:
        self.assertTrue(tools.new_enough((22, 12), (22, 12)))
        self.assertTrue(tools.new_enough((22, 12, 0), (22, 12)))
        self.assertTrue(tools.new_enough((22, 12), (22, 12, 0)))

    def test_a_newer_version_is_new_enough(self) -> None:
        self.assertTrue(tools.new_enough((22, 23, 4), (22, 12)))
        self.assertTrue(tools.new_enough((24, 0, 1), (22, 12)))
        self.assertTrue(tools.new_enough((23,), (22, 12)))

    def test_an_older_version_is_not(self) -> None:
        self.assertFalse(tools.new_enough((22, 11, 9), (22, 12)))
        self.assertFalse(tools.new_enough((20, 19, 0), (22, 12)))
        self.assertFalse(tools.new_enough((22,), (22, 12)))

    def test_the_parts_are_compared_as_numbers_not_as_text(self) -> None:
        self.assertFalse(tools.new_enough((3, 9, 18), (3, 12)))
        self.assertTrue(tools.new_enough((3, 100), (3, 12)))


class ReadLeastTest(unittest.TestCase):
    def test_reads_a_least_version(self) -> None:
        self.assertEqual(tools.read_least(">=3.12", "the file"), (3, 12))
        self.assertEqual(tools.read_least(" >= 22.12.1 ", "the file"), (22, 12, 1))
        self.assertEqual(tools.read_least(">=22", "the file"), (22,))

    def test_refuses_any_other_form_and_says_where_it_is_written(self) -> None:
        for written in ("^22.12", ">=3.12,<4", "3.12", ">3.12", "", ">=", None, 3.12):
            with self.subTest(written=written), self.assertRaises(tools.UnusableError) as raised:
                tools.read_least(written, "the file (the key)")
            self.assertEqual(
                str(raised.exception),
                "the file (the key) does not name a least version in the form >=1.2",
            )


class LeastVersionsTest(ProjectTest):
    def test_reads_both_least_versions_from_the_projects_files(self) -> None:
        self.write(tools.PYTHON_FILE, '[project]\nrequires-python = ">=3.14"\n')
        self.write(tools.NODE_FILE, '{"engines": {"node": ">=24.1.2"}}\n')

        self.assertEqual(tools.least_versions(self.folder), {"python": (3, 14), "node": (24, 1, 2)})

    def test_the_real_project_names_both_in_a_form_the_check_reads(self) -> None:
        self.assertEqual(sorted(tools.least_versions(ROOT)), ["node", "python"])

    def test_the_script_itself_asks_for_the_python_the_project_asks_for(self) -> None:
        self.assertEqual(tools.LEAST_PYTHON, tools.least_versions(ROOT)["python"])

    def test_every_tool_with_a_least_version_has_one_in_the_project(self) -> None:
        named = {tool.least for tool in tools.TOOLS if tool.least}

        self.assertEqual(named, set(tools.least_versions(ROOT)))

    def test_refuses_a_missing_or_unreadable_file(self) -> None:
        for name, text in (
            (tools.PYTHON_FILE, None),
            (tools.PYTHON_FILE, "[project\n"),
            (tools.NODE_FILE, None),
            (tools.NODE_FILE, "{"),
        ):
            with self.subTest(name=name, text=text):
                self.setUp()
                if text is None:
                    (self.folder / name).unlink()
                else:
                    self.write(name, text)
                with self.assertRaises(tools.UnusableError) as raised:
                    tools.least_versions(self.folder)
                self.assertEqual(str(raised.exception), f"{name} is missing or cannot be read")

    def test_refuses_a_file_that_names_no_least_version(self) -> None:
        for name, text, where in (
            (tools.PYTHON_FILE, '[project]\nname = "x"\n', "requires-python"),
            (tools.PYTHON_FILE, 'project = "x"\n', "requires-python"),
            (tools.NODE_FILE, "{}", "engines, node"),
            (tools.NODE_FILE, '{"engines": []}', "engines, node"),
            (tools.NODE_FILE, "[]", "engines, node"),
        ):
            with self.subTest(name=name, text=text):
                self.setUp()
                self.write(name, text)
                with self.assertRaises(tools.UnusableError) as raised:
                    tools.least_versions(self.folder)
                self.assertEqual(
                    str(raised.exception),
                    f"{name} ({where}) does not name a least version in the form >=1.2",
                )


class FindProgramTest(unittest.TestCase):
    def test_python_is_the_python_that_runs_the_script(self) -> None:
        self.assertEqual(tools.find_program("python"), sys.executable)

    def test_finds_a_program_that_is_installed(self) -> None:
        found = tools.find_program("git")

        self.assertIsNotNone(found)
        self.assertEqual(found, shutil.which("git"))

    def test_finds_nothing_for_a_program_that_is_not_installed(self) -> None:
        self.assertIsNone(tools.find_program("motosphere-no-such-tool"))


class AskVersionTest(unittest.TestCase):
    """Real programs: the real Python, asked for its version or told what to do."""

    def test_returns_what_the_program_prints(self) -> None:
        printed = tools.ask_version(sys.executable)

        self.assertEqual(tools.read_version(printed), sys.version_info[:3])

    def test_returns_what_is_printed_as_an_error_too(self) -> None:
        printed = tools.ask_version(
            sys.executable, ("-c", "import sys; sys.stderr.write('tool 1.2.3')")
        )

        self.assertEqual(printed, "tool 1.2.3")

    def test_a_program_that_fails_is_broken(self) -> None:
        with self.assertRaises(tools.BrokenError) as raised:
            tools.ask_version(sys.executable, ("-c", "import sys; sys.exit(3)"))

        self.assertEqual(str(raised.exception), "it stopped with exit code 3")

    def test_a_program_that_gives_no_answer_is_broken(self) -> None:
        with self.assertRaises(tools.BrokenError) as raised:
            tools.ask_version(sys.executable, ("-c", "import time; time.sleep(60)"), 0.5)

        self.assertEqual(str(raised.exception), "it gave no answer within 0.5 seconds")

    def test_a_program_that_cannot_be_started_is_broken(self) -> None:
        with (
            tempfile.TemporaryDirectory() as folder,
            self.assertRaises(tools.BrokenError) as raised,
        ):
            tools.ask_version(str(Path(folder) / "no-such-program"))

        self.assertEqual(str(raised.exception), "it could not be started")

    def test_waits_thirty_seconds_unless_told_otherwise(self) -> None:
        self.assertEqual(tools.TIMEOUT_SECONDS, 30)


class LookAtTest(unittest.TestCase):
    NODE = tools.Tool("Node.js", "node", "https://nodejs.org/en/download", "node")

    def test_a_tool_that_is_new_enough_is_found(self) -> None:
        finding = tools.look_at(self.NODE, (22, 12), find, ask)

        self.assertEqual(finding, tools.Finding(self.NODE, "FOUND", (22, 23, 4), (22, 12)))
        self.assertTrue(finding.ready)

    def test_a_tool_without_a_least_version_is_found_at_any_version(self) -> None:
        finding = tools.look_at(self.NODE, None, find, lambda _: "v0.1.0")

        self.assertEqual(finding, tools.Finding(self.NODE, "FOUND", (0, 1, 0), None))
        self.assertTrue(finding.ready)

    def test_a_tool_older_than_the_least_version_is_too_old(self) -> None:
        finding = tools.look_at(self.NODE, (22, 12), find, lambda _: "v20.19.5")

        self.assertEqual(finding, tools.Finding(self.NODE, "TOO OLD", (20, 19, 5), (22, 12)))
        self.assertFalse(finding.ready)

    def test_a_tool_that_is_not_installed_is_missing_and_is_not_asked(self) -> None:
        asked: list[str] = []

        def record(program: str) -> str:
            asked.append(program)
            return "v22.23.4"

        finding = tools.look_at(self.NODE, (22, 12), lambda _: None, record)

        self.assertEqual(finding, tools.Finding(self.NODE, "MISSING", None, (22, 12)))
        self.assertFalse(finding.ready)
        self.assertEqual(asked, [])

    def test_the_tool_is_asked_by_the_path_it_was_found_at(self) -> None:
        asked: list[str] = []

        def record(program: str) -> str:
            asked.append(program)
            return "v22.23.4"

        tools.look_at(self.NODE, (22, 12), lambda name: f"/found/{name}", record)

        self.assertEqual(asked, ["/found/node"])

    def test_a_tool_that_does_not_work_is_broken(self) -> None:
        def fail(_: str) -> str:
            raise tools.BrokenError("it stopped with exit code 1")

        finding = tools.look_at(self.NODE, (22, 12), find, fail)

        self.assertEqual(
            finding,
            tools.Finding(
                self.NODE, "BROKEN", None, (22, 12), reason="it stopped with exit code 1"
            ),
        )
        self.assertFalse(finding.ready)

    def test_a_tool_that_does_not_say_its_version_is_broken(self) -> None:
        finding = tools.look_at(self.NODE, (22, 12), find, lambda _: "Usage: node [options]")

        self.assertEqual(
            finding,
            tools.Finding(self.NODE, "BROKEN", None, (22, 12), reason="it did not say its version"),
        )


class MainTest(ProjectTest):
    def run_main(self, find: tools.Find = find, ask: tools.Ask = ask) -> tuple[int, str]:
        out = io.StringIO()
        code = tools.main([], self.folder, out, find, ask)
        return code, out.getvalue()

    def test_passes_and_lists_every_tool_when_all_are_ready(self) -> None:
        code, written = self.run_main()

        self.assertEqual(code, 0)
        self.assertEqual(written, EVERYTHING_FOUND)

    def test_looks_at_the_five_tools_in_order(self) -> None:
        looked: list[str] = []

        def record(name: str) -> str | None:
            looked.append(name)
            return name

        self.run_main(find=record)

        self.assertEqual(looked, ["python", "git", "uv", "node", "npm"])

    def test_fails_and_says_where_to_get_what_is_not_ready(self) -> None:
        def some(name: str) -> str | None:
            return None if name in ("uv", "npm") else name

        def old(program: str) -> str:
            if program == "git":
                raise tools.BrokenError("it stopped with exit code 1")
            return "v20.19.5\n" if program == "node" else PRINTED[program]

        code, written = self.run_main(some, old)

        self.assertEqual(code, 1)
        self.assertEqual(
            written,
            "The tools MotoSphere needs on this computer:\n"
            "\n"
            "  FOUND    Python 3.13.18 (3.12 or newer is needed)\n"
            "  BROKEN   Git: it stopped with exit code 1. "
            "Get it again from https://git-scm.com/downloads\n"
            "  MISSING  uv. "
            "Get it from https://docs.astral.sh/uv/getting-started/installation/\n"
            "  TOO OLD  Node.js 20.19.5 (22.12 or newer is needed). "
            "Get a newer one from https://nodejs.org/en/download\n"
            "  MISSING  npm. "
            "Get it from https://nodejs.org/en/download (it comes with Node.js)\n"
            "\n"
            "1 of 5 tools are ready.\n",
        )

    def test_a_missing_tool_is_told_its_least_version(self) -> None:
        _, written = self.run_main(find=lambda name: None if name == "node" else name)

        self.assertIn(
            "  MISSING  Node.js (22.12 or newer is needed). "
            "Get it from https://nodejs.org/en/download\n",
            written,
        )

    def test_compares_with_the_least_versions_the_project_names(self) -> None:
        self.write(tools.NODE_FILE, '{"engines": {"node": ">=24.1"}}\n')

        code, written = self.run_main()

        self.assertEqual(code, 1)
        self.assertIn("  TOO OLD  Node.js 22.23.4 (24.1 or newer is needed). ", written)
        self.assertTrue(written.endswith("\n4 of 5 tools are ready.\n"))

    def test_fails_in_plain_words_when_a_least_version_cannot_be_read(self) -> None:
        (self.folder / tools.NODE_FILE).unlink()
        looked: list[str] = []

        def record(name: str) -> str | None:
            looked.append(name)
            return name

        code, written = self.run_main(find=record)

        self.assertEqual(code, 1)
        self.assertEqual(
            written,
            "The tools could not be checked: frontend/package.json is missing or cannot be read\n",
        )
        self.assertEqual(looked, [])

    def test_every_tool_names_a_place_on_an_encrypted_connection(self) -> None:
        for tool in tools.TOOLS:
            with self.subTest(tool=tool.name):
                self.assertTrue(tool.source.startswith("https://"), tool.source)


class ProgramTest(unittest.TestCase):
    """The script as a separate process, the way a person starts it."""

    def setUp(self) -> None:
        # Another folder than the repository: the script finds the project by
        # its own place, not by where it is started.
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)

    def run_python(
        self, *arguments: str, path: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        environment = None if path is None else {**os.environ, "PATH": path}
        # The arguments are the real Python, this repository's script and
        # values the test wrote.
        return subprocess.run(  # noqa: S603
            [sys.executable, *arguments],
            cwd=self.folder,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    @staticmethod
    def states(lines: list[str]) -> list[str]:
        """The five lines about the tools, cut down to the state and the name."""
        return [" ".join(line.split()[:2]).rstrip(".") for line in lines[2:7]]

    def test_passes_on_this_computer_which_has_every_tool(self) -> None:
        finished = self.run_python(str(SCRIPT))

        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        lines = finished.stdout.splitlines()
        self.assertEqual(lines[0], "The tools MotoSphere needs on this computer:")
        self.assertEqual(
            self.states(lines),
            ["FOUND Python", "FOUND Git", "FOUND uv", "FOUND Node.js", "FOUND npm"],
        )
        python = ".".join(str(part) for part in sys.version_info[:3])
        self.assertIn(f"  FOUND    Python {python} (", lines[2])
        self.assertEqual(lines[-1], "5 of 5 tools are ready.")
        self.assertEqual(finished.stderr, "")

    def test_fails_where_only_python_can_be_found(self) -> None:
        # A PATH that holds one empty folder: no tool is found on it.
        finished = self.run_python(str(SCRIPT), path=str(self.folder))

        self.assertEqual(finished.returncode, 1, finished.stdout + finished.stderr)
        lines = finished.stdout.splitlines()
        self.assertEqual(
            self.states(lines),
            ["FOUND Python", "MISSING Git", "MISSING uv", "MISSING Node.js", "MISSING npm"],
        )
        self.assertEqual(lines[-1], "1 of 5 tools are ready.")
        self.assertEqual(finished.stderr, "")

    def test_tells_an_older_python_in_plain_words_that_it_is_too_old(self) -> None:
        # The real Python, told that it is Python 3.11 before it reads the script.
        pretend = (
            "import runpy, sys; "
            "sys.version_info = (3, 11, 9, 'final', 0); "
            "runpy.run_path(sys.argv[1], run_name='__main__')"
        )
        finished = self.run_python("-c", pretend, str(SCRIPT))

        self.assertEqual(finished.returncode, 1)
        self.assertEqual(finished.stdout, "")
        self.assertEqual(
            finished.stderr,
            "MotoSphere needs Python 3.12 or newer, and this is Python 3.11. "
            "Get a newer one from https://www.python.org/downloads/\n",
        )


if __name__ == "__main__":
    unittest.main()
