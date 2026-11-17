"""Tests of the check runner, `scripts/check.py` (task FND-017).

Standard library only:

    python -m unittest discover -s tests/scripts -v

The stand-in gates are real commands run by the real Python, so these tests
exercise the runner as it is used, without running the project's slow gates.
"""

import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# The runner is a script, not an installed package, so its folder is added to
# the places Python imports from.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check.py"

PASSES = check.Gate("passes", "Passes", ("python", "-c", "pass"))
FAILS = check.Gate("fails", "Fails", ("python", "-c", "raise SystemExit(3)"))
MISSING = check.Gate("missing", "Missing", ("no-such-program-for-motosphere", "--version"))


def notes(key: str, folder: str = ".") -> check.Gate:
    """A gate that adds its key to `log.txt` in the folder it runs in."""
    code = f"open('log.txt', 'a', encoding='utf-8').write('{key}\\n')"
    return check.Gate(key, f"Notes {key}", ("python", "-c", code), folder)


class TemporaryRootTest(unittest.TestCase):
    """Gives each test an empty folder to use as the repository."""

    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def log(self, folder: str = ".") -> list[str]:
        path = self.root / folder / "log.txt"
        return path.read_text(encoding="utf-8").split() if path.exists() else []

    def run_main(self, arguments: list[str], gates: list[check.Gate]) -> tuple[int, str]:
        out = io.StringIO()
        code = check.main(arguments, gates, self.root, out)
        return code, out.getvalue()


class GateTableTest(unittest.TestCase):
    def test_gates_run_in_this_order(self) -> None:
        self.assertEqual(
            [gate.key for gate in check.GATES],
            [
                "repo",
                "scripts",
                "backend-lock",
                "backend-install",
                "backend-types",
                "backend-lint",
                "backend-format",
                "backend-tests",
                "frontend-install",
                "frontend-lint",
                "frontend-format",
                "frontend-types",
                "frontend-tests",
                "frontend-build",
                "browser-tests",
                "frontend-audit",
            ],
        )

    def test_keys_are_plain_words_joined_by_hyphens(self) -> None:
        for gate in check.GATES:
            with self.subTest(gate=gate.key):
                self.assertRegex(gate.key, r"^[a-z]+(-[a-z]+)*$")

    def test_names_are_all_different(self) -> None:
        names = [gate.name for gate in check.GATES]
        self.assertEqual(len(names), len(set(names)))

    def test_every_gate_runs_in_a_folder_that_exists(self) -> None:
        for gate in check.GATES:
            with self.subTest(gate=gate.key):
                self.assertTrue((ROOT / gate.folder).is_dir())

    def test_every_npm_script_a_gate_runs_exists(self) -> None:
        package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
        wanted = []
        for gate in check.GATES:
            if gate.command[:2] == ("npm", "run"):
                wanted.append(gate.command[2])
            elif gate.command == ("npm", "test"):
                wanted.append("test")
        self.assertEqual(len(wanted), 6)
        for script in wanted:
            with self.subTest(script=script):
                self.assertIn(script, package["scripts"])

    def test_gates_that_start_python_tests_point_at_folders_with_tests(self) -> None:
        folders = [gate.command[-2] for gate in check.GATES if gate.command[0] == "python"]
        self.assertEqual(folders, ["tests/repo", "tests/scripts"])
        for folder in folders:
            with self.subTest(folder=folder):
                self.assertTrue(list((ROOT / folder).glob("test_*.py")))

    def test_testing_document_lists_every_gate_with_its_command(self) -> None:
        document = (ROOT / "TESTING.md").read_text(encoding="utf-8")
        for gate in check.GATES:
            with self.subTest(gate=gate.key):
                folder = "repository root" if gate.folder == "." else f"`{gate.folder}/`"
                row = f"| `{gate.key}` | {gate.name} | `{' '.join(gate.command)}` | {folder} |"
                self.assertTrue(row in document, f"TESTING.md has no row: {row}")
        rows = re.findall(r"^\| `[a-z-]+` \| ", document, flags=re.MULTILINE)
        self.assertEqual(len(rows), len(check.GATES))


class RunGateTest(TemporaryRootTest):
    def test_gate_passes_when_its_command_exits_with_zero(self) -> None:
        result = check.run_gate(PASSES, self.root)

        self.assertIs(result.passed, True)
        self.assertEqual(result.note, "")
        self.assertIs(result.gate, PASSES)

    def test_gate_fails_when_its_command_exits_with_anything_else(self) -> None:
        result = check.run_gate(FAILS, self.root)

        self.assertIs(result.passed, False)
        self.assertEqual(result.note, "exit code 3")

    def test_gate_fails_without_an_error_when_its_program_is_not_installed(self) -> None:
        result = check.run_gate(MISSING, self.root)

        self.assertIs(result.passed, False)
        self.assertEqual(result.note, "no-such-program-for-motosphere is not installed")

    def test_gate_fails_without_an_error_when_its_folder_is_missing(self) -> None:
        result = check.run_gate(notes("lost", "no-such-folder"), self.root)

        self.assertIs(result.passed, False)
        self.assertRegex(result.note, r"^could not start: ")

    def test_gate_runs_in_its_folder_under_the_root(self) -> None:
        (self.root / "inner").mkdir()

        result = check.run_gate(notes("here", "inner"), self.root)

        self.assertIs(result.passed, True)
        self.assertEqual(self.log("inner"), ["here"])
        self.assertEqual(self.log(), [])

    def test_python_means_the_python_that_runs_the_runner(self) -> None:
        code = "import sys; open('python.txt', 'w', encoding='utf-8').write(sys.executable)"

        check.run_gate(check.Gate("which", "Which", ("python", "-c", code)), self.root)

        self.assertEqual((self.root / "python.txt").read_text(encoding="utf-8"), sys.executable)

    def test_other_programs_are_found_on_the_path(self) -> None:
        self.assertEqual(check.find_program("git"), shutil.which("git"))
        self.assertIsNotNone(check.find_program("git"))

    def test_time_a_gate_took_is_measured(self) -> None:
        slow = check.Gate("slow", "Slow", ("python", "-c", "import time; time.sleep(0.3)"))

        result = check.run_gate(slow, self.root)

        self.assertGreaterEqual(result.seconds, 0.3)
        self.assertLess(result.seconds, 30)


class MainTest(TemporaryRootTest):
    def test_exit_code_is_zero_when_every_gate_passes(self) -> None:
        code, text = self.run_main([], [PASSES, notes("a")])

        self.assertEqual(code, 0)
        self.assertIn("2 of 2 gates passed.\n", text)
        self.assertNotIn("FAILED", text)
        self.assertEqual(len(re.findall(r"^  PASSED  ", text, flags=re.MULTILINE)), 2)

    def test_exit_code_is_one_when_a_gate_fails_and_the_summary_names_it(self) -> None:
        code, text = self.run_main([], [PASSES, FAILS, notes("a")])

        self.assertEqual(code, 1)
        self.assertIn("2 of 3 gates passed. FAILED: Fails.\n", text)
        self.assertRegex(text, r"(?m)^  FAILED  Fails +\d+\.\d s  exit code 3$")
        self.assertRegex(text, r"(?m)^  PASSED  Passes +\d+\.\d s$")

    def test_gates_after_a_failed_one_still_run(self) -> None:
        self.run_main([], [FAILS, notes("a"), MISSING, notes("b")])

        self.assertEqual(self.log(), ["a", "b"])

    def test_summary_names_every_failed_gate(self) -> None:
        code, text = self.run_main([], [FAILS, PASSES, MISSING])

        self.assertEqual(code, 1)
        self.assertIn("1 of 3 gates passed. FAILED: Fails, Missing.\n", text)
        self.assertIn("no-such-program-for-motosphere is not installed\n", text)

    def test_gates_run_in_the_order_of_the_table(self) -> None:
        self.run_main([], [notes("a"), notes("b"), notes("c")])

        self.assertEqual(self.log(), ["a", "b", "c"])

    def test_each_gate_is_announced_with_its_place_and_command(self) -> None:
        (self.root / "inner").mkdir()

        _, text = self.run_main([], [PASSES, notes("a", "inner")])

        self.assertIn("\n=== [1/2] Passes: python -c pass\n", text)
        self.assertRegex(text, r"\n=== \[2/2\] Notes a: python -c .*  \(in inner/\)\n")
        self.assertLess(text.index("=== [2/2]"), text.index("Summary"))

    def test_only_runs_the_named_gates_in_the_order_of_the_table(self) -> None:
        gates = [notes("a"), notes("b"), notes("c")]

        code, text = self.run_main(["--only", "c", "a"], gates)

        self.assertEqual(code, 0)
        self.assertEqual(self.log(), ["a", "c"])
        self.assertIn("=== [1/2] Notes a:", text)
        self.assertIn("=== [2/2] Notes c:", text)
        self.assertIn("2 of 2 gates passed.\n", text)

    def test_only_reports_the_failure_of_a_named_gate(self) -> None:
        code, text = self.run_main(["--only", "fails"], [PASSES, FAILS])

        self.assertEqual(code, 1)
        self.assertIn("0 of 1 gates passed. FAILED: Fails.\n", text)

    def test_only_refuses_a_name_that_is_not_a_gate(self) -> None:
        errors = io.StringIO()

        with contextlib.redirect_stderr(errors), self.assertRaises(SystemExit) as stopped:
            self.run_main(["--only", "nonsense"], [notes("a")])

        self.assertEqual(stopped.exception.code, 2)
        self.assertIn("nonsense", errors.getvalue())
        self.assertEqual(self.log(), [])

    def test_list_shows_every_gate_and_runs_nothing(self) -> None:
        (self.root / "inner").mkdir()

        code, text = self.run_main(["--list"], [PASSES, notes("a", "inner")])

        self.assertEqual(code, 0)
        lines = text.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "passes  python -c pass")
        self.assertRegex(lines[1], r"^a       python -c .*  \(in inner/\)$")
        self.assertEqual(self.log("inner"), [])

    def test_list_and_only_cannot_be_combined(self) -> None:
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as stopped,
        ):
            self.run_main(["--list", "--only", "a"], [notes("a")])

        self.assertEqual(stopped.exception.code, 2)
        self.assertEqual(self.log(), [])


class CommandLineTest(TemporaryRootTest):
    """The script itself, run as a separate process the way a person runs it.

    Every test here runs a copy of the script inside a small stand-in
    repository, never the script in the real one. One of the real gates runs
    these tests, so a defect in the runner could otherwise make it start
    itself again and again without end. In the stand-in repository the worst
    a defect can do is run gates that fail at once.
    """

    def setUp(self) -> None:
        super().setUp()
        (self.root / "scripts").mkdir()
        self.script = self.root / "scripts" / "check.py"
        shutil.copyfile(SCRIPT, self.script)
        elsewhere = tempfile.TemporaryDirectory()
        self.addCleanup(elsewhere.cleanup)
        self.elsewhere = Path(elsewhere.name)

    def add_repository_checks(self, body: str) -> None:
        folder = self.root / "tests" / "repo"
        folder.mkdir(parents=True)
        lines = [
            "import unittest",
            "",
            "",
            "class SampleTest(unittest.TestCase):",
            "    def test_sample(self):",
            f"        {body}",
            "",
        ]
        (folder / "test_sample.py").write_text("\n".join(lines), encoding="utf-8")

    def run_script(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        # Started from another folder, to show that the script finds its repository itself.
        return subprocess.run(  # noqa: S603
            [sys.executable, str(self.script), *arguments],
            cwd=self.elsewhere,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_list_names_every_gate_and_runs_nothing(self) -> None:
        self.add_repository_checks("open('ran.txt', 'w').close()")

        finished = self.run_script("--list")

        self.assertEqual(finished.returncode, 0, finished.stderr)
        lines = finished.stdout.splitlines()
        self.assertEqual([line.split()[0] for line in lines], [gate.key for gate in check.GATES])
        self.assertEqual(lines[0], "repo              python -m unittest discover -s tests/repo -v")
        self.assertFalse((self.root / "ran.txt").exists())

    def test_exit_code_of_the_script_is_zero_when_the_gate_passes(self) -> None:
        self.add_repository_checks("open('ran.txt', 'w').close()")

        finished = self.run_script("--only", "repo")

        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        self.assertIn("=== [1/1] Repository checks: python -m unittest", finished.stdout)
        self.assertIn("1 of 1 gates passed.\n", finished.stdout)
        # The gate ran in the repository the script is in, not where it was started.
        self.assertTrue((self.root / "ran.txt").exists())
        self.assertFalse((self.elsewhere / "ran.txt").exists())

    def test_exit_code_of_the_script_is_one_when_the_gate_fails(self) -> None:
        self.add_repository_checks("self.fail('planted')")

        finished = self.run_script("--only", "repo")

        self.assertEqual(finished.returncode, 1, finished.stdout + finished.stderr)
        self.assertIn("0 of 1 gates passed. FAILED: Repository checks.\n", finished.stdout)
        self.assertRegex(
            finished.stdout, r"(?m)^  FAILED  Repository checks +\d+\.\d s  exit code 1$"
        )

    def test_help_explains_the_options(self) -> None:
        finished = self.run_script("--help")

        self.assertEqual(finished.returncode, 0)
        self.assertIn("--list", finished.stdout)
        self.assertIn("--only", finished.stdout)


if __name__ == "__main__":
    unittest.main()
