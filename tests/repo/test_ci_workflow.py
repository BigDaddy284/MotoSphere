"""Checks on the continuous integration workflows (tasks FND-018 and FND-032).

The workflows are read as text: the repository checks use the standard
library only, and it has no YAML reader. The files are kept plain enough for
that, and the checks are strict about their layout for the same reason.

Run from the repository root:

    python -m unittest discover -s tests/repo -v
"""

import json
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
CHECKS = WORKFLOWS / "checks.yml"

# The actions a workflow may use. Adding one is a decision about whose code
# runs with access to the repository, so it is made here and not in passing.
KNOWN_ACTIONS = (
    "actions/checkout",
    "actions/setup-node",
    "actions/setup-python",
    "astral-sh/setup-uv",
)

# The only expressions a workflow may contain. Text that comes from outside,
# such as the title of a pull request, must never reach a command.
KNOWN_EXPRESSIONS = (
    "github.event_name == 'pull_request'",
    "github.ref",
    "matrix.name",
    "matrix.os",
)

# The machines the gates run on, each a named image and not "the latest".
MACHINES = (
    ("Linux", "ubuntu-24.04"),
    ("Windows", "windows-2025"),
)

# An action pinned to a full commit, with the release it belongs to beside it.
PINNED = re.compile(r"^ +uses: ([\w.-]+/[\w.-]+)@[0-9a-f]{40} # v\d+\.\d+\.\d+$")


def workflows() -> dict[str, str]:
    """Return the text of every workflow, by file name."""
    files = sorted(WORKFLOWS.glob("*.y*ml")) if WORKFLOWS.is_dir() else []
    return {file.name: file.read_text(encoding="utf-8") for file in files}


def commands(text: str) -> list[str]:
    """Return every command the steps of a workflow run, in order."""
    found: list[str] = []
    lines = text.splitlines()
    for number, line in enumerate(lines):
        step = re.match(r"^( +)run: (.+)$", line)
        if step is None:
            continue
        if step.group(2) != "|":
            found.append(step.group(2))
            continue
        inside = step.group(1) + "  "
        for following in lines[number + 1 :]:
            if not following.startswith(inside):
                break
            found.append(following.strip())
    return found


class WorkflowSafetyTest(unittest.TestCase):
    """Rules that hold for every workflow in the repository."""

    def test_there_is_a_workflow_to_check(self) -> None:
        self.assertIn("checks.yml", workflows())

    def test_every_action_is_pinned_to_a_commit_with_its_release(self) -> None:
        for name, text in workflows().items():
            used = [line for line in text.splitlines() if re.search(r"\buses:", line)]
            self.assertTrue(used, f"{name} uses no action")
            for line in used:
                with self.subTest(workflow=name, line=line.strip()):
                    self.assertRegex(line, PINNED)

    def test_only_known_actions_are_used(self) -> None:
        for name, text in workflows().items():
            for action in re.findall(r"\buses: *([^@\s]+)", text):
                with self.subTest(workflow=name, action=action):
                    self.assertIn(action, KNOWN_ACTIONS)

    def test_no_workflow_runs_code_from_outside_with_the_rights_of_the_repository(self) -> None:
        for name, text in workflows().items():
            with self.subTest(workflow=name):
                self.assertNotIn("pull_request_target", text)
                self.assertNotIn("workflow_run", text)
                self.assertNotIn("secrets.", text)

    def test_every_workflow_limits_what_its_token_may_do(self) -> None:
        for name, text in workflows().items():
            with self.subTest(workflow=name):
                self.assertRegex(text, re.compile(r"^permissions:$", re.MULTILINE))
                self.assertNotIn("write-all", text)

    def test_no_text_from_outside_reaches_a_command(self) -> None:
        for name, text in workflows().items():
            for expression in re.findall(r"\$\{\{(.*?)\}\}", text):
                with self.subTest(workflow=name, expression=expression.strip()):
                    self.assertIn(expression.strip(), KNOWN_EXPRESSIONS)


class ChecksWorkflowTest(unittest.TestCase):
    """The workflow that runs every gate."""

    text: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CHECKS.read_text(encoding="utf-8")

    def test_runs_for_pull_requests_and_for_changes_to_main(self) -> None:
        self.assertIn("\non:\n  pull_request:\n  push:\n    branches: [main]\n\n", self.text)

    def test_its_token_can_only_read(self) -> None:
        self.assertEqual(self.text.count("permissions:"), 1)
        self.assertIn("\npermissions:\n  contents: read\n\n", self.text)

    def test_checkout_keeps_no_credentials(self) -> None:
        self.assertEqual(self.text.count("actions/checkout@"), 1)
        self.assertRegex(
            self.text,
            r"uses: actions/checkout@\S+ # \S+\n +with:\n +persist-credentials: false\n",
        )

    def test_runs_the_check_runner_and_nothing_in_its_place(self) -> None:
        self.assertEqual(
            commands(self.text),
            [
                "npm ci",
                "npx playwright install --with-deps chromium",
                "python scripts/check.py",
            ],
        )

    def test_nothing_lets_a_failing_step_pass(self) -> None:
        self.assertNotIn("continue-on-error", self.text)
        self.assertNotRegex(self.text, re.compile(r"^ +(- )?if:", re.MULTILINE))
        self.assertNotRegex(self.text, re.compile(r"^ +(- )?shell:", re.MULTILINE))

    def test_runs_on_linux_and_on_windows(self) -> None:
        machines = re.findall(r"^ +- name: (\w+)\n +os: (\S+)$", self.text, re.MULTILINE)

        self.assertEqual(machines, list(MACHINES))
        self.assertEqual(
            re.findall(r"^ +runs-on: (.+)$", self.text, re.MULTILINE), ["${{ matrix.os }}"]
        )
        self.assertIn("All gates (${{ matrix.name }})", self.text)

    def test_one_machine_failing_does_not_stop_the_other(self) -> None:
        self.assertEqual(re.findall(r"^ +fail-fast: (.+)$", self.text, re.MULTILINE), ["false"])

    def test_the_job_has_a_time_limit(self) -> None:
        self.assertRegex(self.text, re.compile(r"^ +timeout-minutes: \d+$", re.MULTILINE))

    def test_every_step_runs_one_command(self) -> None:
        # On Windows a step with several commands only fails on its last one.
        self.assertNotRegex(self.text, re.compile(r"^ +run: *[|>]", re.MULTILINE))

    def test_tools_are_the_versions_the_project_supports(self) -> None:
        with (ROOT / "backend" / "pyproject.toml").open("rb") as file:
            oldest_python = tomllib.load(file)["project"]["requires-python"]
        package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
        oldest_node = package["engines"]["node"]

        python = re.findall(r'^ +python-version: "(.+)"$', self.text, re.MULTILINE)
        node = re.findall(r'^ +node-version: "(.+)"$', self.text, re.MULTILINE)
        uv = re.findall(r'^ +version: "(.+)"$', self.text, re.MULTILINE)

        # The oldest Python the pipeline supports, so that nothing newer
        # slips into the code unnoticed.
        self.assertEqual([f">={version}" for version in python], [oldest_python])
        self.assertEqual(len(node), 1)
        self.assertTrue(oldest_node.startswith(f">={node[0]}."), (node, oldest_node))
        self.assertEqual(len(uv), 1)
        self.assertRegex(uv[0], r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
