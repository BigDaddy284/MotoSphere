"""Tests of the check runner, `scripts/check.py` (tasks FND-017, FND-030 and FND-031).

Standard library only:

    python -m unittest discover -s tests/scripts -v

The stand-in gates are real commands run by the real Python, so these tests
exercise the runner as it is used, without running the project's slow gates.
"""

import configparser
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
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


def says(key: str, tool: str, *lines: str, exit_code: int = 0) -> check.Gate:
    """A test gate for the given tool that writes these lines, as that tool would."""
    code = f"import sys; sys.stderr.write({chr(10).join(lines) + chr(10)!r}); sys.exit({exit_code})"
    return check.Gate(key, f"Says {key}", ("python", "-c", code), tests=tool)


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

    def run_gate(self, gate: check.Gate) -> check.Result:
        self.echoed: list[bytes] = []
        return check.run_gate(gate, self.root, self.echoed.append)

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
                "tools-types",
                "tools-lint",
                "tools-format",
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

    def test_gates_that_run_tests_name_the_tool_that_counts_them(self) -> None:
        self.assertEqual(
            {gate.key: gate.tests for gate in check.GATES if gate.tests},
            {
                "repo": "unittest",
                "scripts": "unittest",
                "backend-tests": "pytest",
                "frontend-tests": "vitest",
                "browser-tests": "playwright",
            },
        )
        self.assertEqual(sorted(check.COUNTERS), ["playwright", "pytest", "unittest", "vitest"])

    def test_tooling_gates_use_the_tools_the_pipeline_has_locked(self) -> None:
        commands = {gate.key: gate.command for gate in check.GATES if gate.key.startswith("tools-")}

        self.assertEqual(sorted(commands), ["tools-format", "tools-lint", "tools-types"])
        for key, command in commands.items():
            with self.subTest(gate=key):
                self.assertEqual(command[:4], ("uv", "run", "--project", "backend"))
        self.assertEqual(commands["tools-types"][4:], ("mypy",))
        self.assertEqual(commands["tools-lint"][4:], ("ruff", "check", *check.TOOLING))
        self.assertEqual(
            commands["tools-format"][4:], ("ruff", "format", "--check", *check.TOOLING)
        )

    def test_every_python_file_outside_the_pipeline_is_under_the_tooling_gates(self) -> None:
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"],  # noqa: S607
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        outside = [
            path
            for path in listed.stdout.splitlines()
            if not path.startswith(("backend/", "frontend/"))
        ]

        self.assertIn("scripts/check.py", outside)
        self.assertIn("tests/repo/test_repo_hygiene.py", outside)
        for path in outside:
            with self.subTest(path=path):
                self.assertIn(path.split("/")[0], check.TOOLING)

    def test_tooling_follows_the_rules_of_the_pipeline(self) -> None:
        with (ROOT / "ruff.toml").open("rb") as file:
            rules = tomllib.load(file)
        types = configparser.ConfigParser()
        types.read(ROOT / "mypy.ini", encoding="utf-8")

        self.assertEqual(
            rules, {"extend": "backend/pyproject.toml", "lint": {"extend-ignore": ["PT"]}}
        )
        self.assertEqual(types["mypy"]["files"], ", ".join(check.TOOLING))
        self.assertEqual(types["mypy"]["strict"], "True")

    def test_testing_document_lists_every_gate_with_its_command(self) -> None:
        document = (ROOT / "TESTING.md").read_text(encoding="utf-8")
        for gate in check.GATES:
            with self.subTest(gate=gate.key):
                folder = "repository root" if gate.folder == "." else f"`{gate.folder}/`"
                row = f"| `{gate.key}` | {gate.name} | `{' '.join(gate.command)}` | {folder} |"
                self.assertTrue(row in document, f"TESTING.md has no row: {row}")
        rows = re.findall(r"^\| `[a-z-]+` \| ", document, flags=re.MULTILINE)
        self.assertEqual(len(rows), len(check.GATES))


class CountTest(unittest.TestCase):
    """Reading test counts from the closing lines each tool really writes."""

    def test_unittest_all_passed(self) -> None:
        output = "test_a (test_s.S.test_a) ... ok\n\n-----\nRan 9 tests in 0.093s\n\nOK\n"

        self.assertEqual(check.count_unittest(output), check.Counts(9, 0, 0))

    def test_unittest_a_single_test(self) -> None:
        self.assertEqual(
            check.count_unittest("Ran 1 test in 0.001s\n\nOK\n"), check.Counts(1, 0, 0)
        )

    def test_unittest_every_kind_of_outcome(self) -> None:
        output = (
            "Ran 6 tests in 0.001s\n\n"
            "FAILED (failures=1, errors=1, skipped=1, expected failures=1, "
            "unexpected successes=1)\n"
        )

        self.assertEqual(check.count_unittest(output), check.Counts(1, 3, 2))

    def test_unittest_skipped_tests_do_not_stop_it_saying_ok(self) -> None:
        output = "Ran 3 tests in 0.001s\n\nOK (skipped=1, expected failures=1)\n"

        self.assertEqual(check.count_unittest(output), check.Counts(1, 0, 2))

    def test_unittest_no_tests(self) -> None:
        output = "Ran 0 tests in 0.000s\n\nNO TESTS RAN\n"

        self.assertEqual(check.count_unittest(output), check.Counts(0, 0, 0))

    def test_unittest_last_report_counts_when_the_output_quotes_another(self) -> None:
        # A failing test of the runner shows the output of the run it started.
        output = (
            "AssertionError: 1 != 0 : \n"
            "Ran 2 tests in 0.1s\n\nFAILED (failures=2)\n\n"
            "Ran 30 tests in 1.0s\n\nOK\n"
        )

        self.assertEqual(check.count_unittest(output), check.Counts(30, 0, 0))

    def test_unittest_without_closing_lines(self) -> None:
        self.assertIsNone(check.count_unittest("Traceback (most recent call last):\n"))
        self.assertIsNone(check.count_unittest("Ran 3 tests in 0.1s\n"))

    def test_pytest_all_passed(self) -> None:
        output = "=" * 29 + " 115 passed in 2.51s " + "=" * 30 + "\n"

        self.assertEqual(check.count_pytest(output), check.Counts(115, 0, 0))

    def test_pytest_every_kind_of_outcome(self) -> None:
        output = (
            "==== 1 failed, 1 passed, 1 skipped, 1 xfailed, 1 xpassed, 1 error in 0.42s =====\n"
        )

        self.assertEqual(check.count_pytest(output), check.Counts(1, 2, 3))

    def test_pytest_tests_left_out_count_as_skipped(self) -> None:
        output = (
            "================== 1 passed, 1 skipped, 4 deselected in 0.02s ==================\n"
        )

        self.assertEqual(check.count_pytest(output), check.Counts(1, 0, 5))

    def test_pytest_quiet_form_with_warnings(self) -> None:
        self.assertEqual(
            check.count_pytest("115 passed, 2 warnings in 2.51s\n"), check.Counts(115, 0, 0)
        )

    def test_pytest_without_counts(self) -> None:
        self.assertIsNone(check.count_pytest("===== no tests ran in 0.01s =====\n"))
        self.assertIsNone(check.count_pytest("ERROR: file or directory not found: tests\n"))

    def test_vitest_all_passed(self) -> None:
        output = (
            " Test Files  12 passed (12)\n      Tests  199 passed (199)\n   Start at  14:55:53\n"
        )

        self.assertEqual(check.count_vitest(output), check.Counts(199, 0, 0))

    def test_vitest_every_kind_of_outcome(self) -> None:
        output = "      Tests  1 failed | 200 passed | 1 skipped | 1 todo (203)\n"

        self.assertEqual(check.count_vitest(output), check.Counts(200, 1, 2))

    def test_vitest_counts_tests_and_not_test_files(self) -> None:
        self.assertIsNone(check.count_vitest(" Test Files  1 failed | 11 passed (12)\n"))

    def test_playwright_all_passed(self) -> None:
        output = (
            "  \u2713  80 [chromium] \u203a e2e/theme.spec.ts:69:3 (166ms)\n\n  80 passed (10.0s)\n"
        )

        self.assertEqual(check.count_playwright(output), check.Counts(80, 0, 0))

    def test_playwright_failed_and_skipped(self) -> None:
        output = (
            "  1 failed\n"
            "    [chromium] \u203a e2e/sample.spec.ts:6:1 \u203a fails \u2500\u2500\u2500\n"
            "  2 skipped\n"
            "  4 passed (3.6s)\n"
        )

        self.assertEqual(check.count_playwright(output), check.Counts(4, 1, 2))

    def test_playwright_other_outcomes_and_a_time_in_minutes(self) -> None:
        output = "  1 flaky\n  1 interrupted\n  2 did not run\n  3 passed (1.2m)\n"

        self.assertEqual(check.count_playwright(output), check.Counts(3, 2, 2))

    def test_playwright_without_closing_lines(self) -> None:
        output = (
            "  \u2713  79 [chromium] \u203a e2e/theme.spec.ts:52:3 (156ms)\nError: no tests found\n"
        )

        self.assertIsNone(check.count_playwright(output))


class JudgeTest(unittest.TestCase):
    PLAIN = check.Gate("plain", "Plain", ("x",))
    TESTS = check.Gate("tests", "Tests", ("x",), tests="pytest")

    def test_gate_without_tests_passes_on_exit_code_zero_whatever_it_wrote(self) -> None:
        self.assertEqual(check.judge(self.PLAIN, 0, "3 failed, 1 skipped in 0.1s\n"), ("", None))

    def test_gate_without_tests_fails_on_another_exit_code(self) -> None:
        self.assertEqual(check.judge(self.PLAIN, 2, ""), ("exit code 2", None))

    def test_test_gate_passes_when_every_test_passed(self) -> None:
        self.assertEqual(
            check.judge(self.TESTS, 0, "5 passed in 0.1s\n"), ("", check.Counts(5, 0, 0))
        )

    def test_test_gate_that_failed_keeps_its_counts(self) -> None:
        self.assertEqual(
            check.judge(self.TESTS, 1, "1 failed, 4 passed in 0.1s\n"),
            ("exit code 1", check.Counts(4, 1, 0)),
        )

    def test_test_gate_fails_when_a_test_was_skipped(self) -> None:
        self.assertEqual(
            check.judge(self.TESTS, 0, "4 passed, 2 skipped in 0.1s\n"),
            ("tests were skipped", check.Counts(4, 0, 2)),
        )

    def test_test_gate_fails_when_no_test_ran(self) -> None:
        self.assertEqual(
            check.judge(self.TESTS, 0, "3 warnings in 0.1s\n"),
            ("no test ran", check.Counts(0, 0, 0)),
        )

    def test_test_gate_fails_when_its_counts_cannot_be_read(self) -> None:
        self.assertEqual(
            check.judge(self.TESTS, 0, "all good\n"), ("the test counts could not be read", None)
        )

    def test_counts_are_read_from_coloured_output(self) -> None:
        # As pytest, Vitest and Playwright write them when colours are forced on.
        pytest_line = (
            "\x1b[32m============================= \x1b[32m\x1b[1m115 passed\x1b[0m\x1b[32m"
            " in 2.40s\x1b[0m\x1b[32m ==============================\x1b[0m\n"
        )
        vitest_line = (
            "\x1b[2m      Tests \x1b[22m \x1b[1m\x1b[32m199 passed\x1b[39m\x1b[22m"
            "\x1b[90m (199)\x1b[39m\n"
        )
        playwright_line = "\n\x1b[32m  3 passed\x1b[39m\x1b[2m (2.9s)\x1b[22m\n"

        for tool, line, passed in (
            ("pytest", pytest_line, 115),
            ("vitest", vitest_line, 199),
            ("playwright", playwright_line, 3),
        ):
            with self.subTest(tool=tool):
                gate = check.Gate("coloured", "Coloured", ("x",), tests=tool)
                self.assertEqual(check.judge(gate, 0, line), ("", check.Counts(passed, 0, 0)))


class RunGateTest(TemporaryRootTest):
    def test_gate_passes_when_its_command_exits_with_zero(self) -> None:
        result = self.run_gate(PASSES)

        self.assertIs(result.passed, True)
        self.assertEqual(result.note, "")
        self.assertIs(result.gate, PASSES)

    def test_gate_fails_when_its_command_exits_with_anything_else(self) -> None:
        result = self.run_gate(FAILS)

        self.assertIs(result.passed, False)
        self.assertEqual(result.note, "exit code 3")

    def test_gate_fails_without_an_error_when_its_program_is_not_installed(self) -> None:
        result = self.run_gate(MISSING)

        self.assertIs(result.passed, False)
        self.assertEqual(result.note, "no-such-program-for-motosphere is not installed")

    def test_gate_fails_without_an_error_when_its_folder_is_missing(self) -> None:
        result = self.run_gate(notes("lost", "no-such-folder"))

        self.assertIs(result.passed, False)
        self.assertRegex(result.note, r"^could not start: ")

    def test_gate_runs_in_its_folder_under_the_root(self) -> None:
        (self.root / "inner").mkdir()

        result = self.run_gate(notes("here", "inner"))

        self.assertIs(result.passed, True)
        self.assertEqual(self.log("inner"), ["here"])
        self.assertEqual(self.log(), [])

    def test_python_means_the_python_that_runs_the_runner(self) -> None:
        code = "import sys; open('python.txt', 'w', encoding='utf-8').write(sys.executable)"

        self.run_gate(check.Gate("which", "Which", ("python", "-c", code)))

        self.assertEqual((self.root / "python.txt").read_text(encoding="utf-8"), sys.executable)

    def test_other_programs_are_found_on_the_path(self) -> None:
        self.assertEqual(check.find_program("git"), shutil.which("git"))
        self.assertIsNotNone(check.find_program("git"))

    def test_time_a_gate_took_is_measured(self) -> None:
        slow = check.Gate("slow", "Slow", ("python", "-c", "import time; time.sleep(0.3)"))

        result = self.run_gate(slow)

        self.assertGreaterEqual(result.seconds, 0.3)
        self.assertLess(result.seconds, 30)

    def test_output_of_a_gate_is_passed_on_as_it_was_written(self) -> None:
        code = (
            "import sys; sys.stdout.buffer.write(b'one\\n'); sys.stdout.flush(); "
            "sys.stderr.buffer.write(b'two \\xff\\xfe\\n'); sys.stderr.flush(); "
            "sys.stdout.buffer.write('\u2713 three\\n'.encode('utf-8'))"
        )

        result = self.run_gate(check.Gate("loud", "Loud", ("python", "-c", code)))

        self.assertIs(result.passed, True)
        self.assertEqual(b"".join(self.echoed), b"one\ntwo \xff\xfe\n" + "\u2713 three\n".encode())

    def test_gate_without_tests_has_no_counts(self) -> None:
        self.assertIsNone(self.run_gate(PASSES).counts)

    def test_test_gate_reports_its_counts(self) -> None:
        result = self.run_gate(says("ok", "unittest", "Ran 3 tests in 0.1s", "", "OK"))

        self.assertIs(result.passed, True)
        self.assertEqual(result.counts, check.Counts(3, 0, 0))
        self.assertEqual(result.note, "")

    def test_test_gate_fails_when_a_test_was_skipped(self) -> None:
        result = self.run_gate(
            says("skip", "unittest", "Ran 3 tests in 0.1s", "", "OK (skipped=1)")
        )

        self.assertIs(result.passed, False)
        self.assertEqual(result.note, "tests were skipped")
        self.assertEqual(result.counts, check.Counts(2, 0, 1))

    def test_test_gate_fails_when_it_writes_no_counts(self) -> None:
        result = self.run_gate(says("mute", "vitest", "nothing to see"))

        self.assertIs(result.passed, False)
        self.assertEqual(result.note, "the test counts could not be read")


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

    def test_output_of_each_gate_appears_under_its_announcement(self) -> None:
        loud = check.Gate("loud", "Loud", ("python", "-c", "print('hello from the gate')"))

        _, text = self.run_main([], [loud, PASSES])

        self.assertLess(text.index("=== [1/2] Loud"), text.index("hello from the gate"))
        self.assertLess(text.index("hello from the gate"), text.index("=== [2/2] Passes"))

    def test_summary_shows_the_counts_of_each_test_gate_and_their_total(self) -> None:
        gates = [
            says("a", "unittest", "Ran 3 tests in 0.1s", "", "OK"),
            PASSES,
            says("b", "pytest", "==== 2 passed in 0.1s ===="),
        ]

        code, text = self.run_main([], gates)

        self.assertEqual(code, 0)
        self.assertRegex(text, r"(?m)^  PASSED  Says a +\d+\.\d s  3 passed$")
        self.assertRegex(text, r"(?m)^  PASSED  Passes +\d+\.\d s$")
        self.assertRegex(text, r"(?m)^  PASSED  Says b +\d+\.\d s  2 passed$")
        self.assertTrue(
            text.endswith("\n3 of 3 gates passed.\nTests: 5 passed, 0 failed, 0 skipped.\n")
        )

    def test_summary_has_no_line_about_tests_when_no_gate_counts_any(self) -> None:
        _, text = self.run_main([], [PASSES, FAILS])

        self.assertNotIn("Tests:", text)
        self.assertTrue(text.endswith("\n1 of 2 gates passed. FAILED: Fails.\n"))

    def test_skipped_test_fails_the_run(self) -> None:
        gates = [
            says("a", "playwright", "  1 skipped", "  4 passed (3.0s)"),
            says("b", "vitest", "      Tests  6 passed (6)"),
        ]

        code, text = self.run_main([], gates)

        self.assertEqual(code, 1)
        self.assertRegex(
            text,
            r"(?m)^  FAILED  Says a +\d+\.\d s  4 passed, 1 skipped  tests were skipped$",
        )
        self.assertIn("1 of 2 gates passed. FAILED: Says a.\n", text)
        self.assertIn("Tests: 10 passed, 0 failed, 1 skipped.\n", text)

    def test_failed_tests_are_counted_in_the_summary(self) -> None:
        failing = says(
            "a", "unittest", "Ran 5 tests in 0.1s", "", "FAILED (failures=1, errors=1)", exit_code=1
        )

        code, text = self.run_main([], [failing])

        self.assertEqual(code, 1)
        self.assertRegex(
            text, r"(?m)^  FAILED  Says a +\d+\.\d s  3 passed, 2 failed  exit code 1$"
        )
        self.assertIn("Tests: 3 passed, 2 failed, 0 skipped.\n", text)


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

    def run_script(
        self, *arguments: str, console: str = "utf-8"
    ) -> subprocess.CompletedProcess[str]:
        # Started from another folder, to show that the script finds its repository itself.
        # `console` is the character set the runner believes its terminal has.
        return subprocess.run(  # noqa: S603
            [sys.executable, str(self.script), *arguments],
            cwd=self.elsewhere,
            env={**os.environ, "PYTHONIOENCODING": console},
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
        self.assertIn(
            "1 of 1 gates passed.\nTests: 1 passed, 0 failed, 0 skipped.\n", finished.stdout
        )
        self.assertRegex(finished.stdout, r"(?m)^  PASSED  Repository checks +\d+\.\d s  1 passed$")
        # The gate's own output is shown, under its announcement.
        self.assertLess(finished.stdout.index("=== [1/1]"), finished.stdout.index("Ran 1 test in"))
        self.assertLess(finished.stdout.index("Ran 1 test in"), finished.stdout.index("Summary"))
        # The gate ran in the repository the script is in, not where it was started.
        self.assertTrue((self.root / "ran.txt").exists())
        self.assertFalse((self.elsewhere / "ran.txt").exists())

    def test_exit_code_of_the_script_is_one_when_the_gate_fails(self) -> None:
        self.add_repository_checks("self.fail('planted')")

        finished = self.run_script("--only", "repo")

        self.assertEqual(finished.returncode, 1, finished.stdout + finished.stderr)
        self.assertIn("0 of 1 gates passed. FAILED: Repository checks.\n", finished.stdout)
        self.assertRegex(
            finished.stdout,
            r"(?m)^  FAILED  Repository checks +\d+\.\d s  0 passed, 1 failed  exit code 1$",
        )
        self.assertIn("Tests: 0 passed, 1 failed, 0 skipped.\n", finished.stdout)

    def test_exit_code_of_the_script_is_one_when_a_test_is_skipped(self) -> None:
        self.add_repository_checks("self.skipTest('planted')")

        finished = self.run_script("--only", "repo")

        self.assertEqual(finished.returncode, 1, finished.stdout + finished.stderr)
        line = r"  FAILED  Repository checks +\d+\.\d s  0 passed, 1 skipped  tests were skipped"
        self.assertRegex(finished.stdout, rf"(?m)^{line}$")
        self.assertIn("Tests: 0 passed, 0 failed, 1 skipped.\n", finished.stdout)

    def test_output_outside_ascii_passes_through_unchanged(self) -> None:
        # Written as bytes, the way the Node.js tools write their check marks.
        self.add_repository_checks(
            "import sys; sys.stderr.flush(); "
            "sys.stderr.buffer.write('\\u2713 na\\u00efve\\n'.encode('utf-8')); sys.stderr.flush()"
        )

        # A terminal that can only show ASCII, like an old Windows console,
        # must not make the runner stumble over what a gate writes.
        finished = self.run_script("--only", "repo", console="ascii")

        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        self.assertIn("\u2713 na\u00efve\n", finished.stdout)
        self.assertIn("1 of 1 gates passed.\n", finished.stdout)

    def test_help_explains_the_options(self) -> None:
        finished = self.run_script("--help")

        self.assertEqual(finished.returncode, 0)
        self.assertIn("--list", finished.stdout)
        self.assertIn("--only", finished.stdout)


if __name__ == "__main__":
    unittest.main()
