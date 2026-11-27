"""Checks on the workflows: the gates and the deployment (FND-018, FND-032, FND-034, FND-037).

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
    "actions/deploy-pages",
    "actions/download-artifact",
    "actions/setup-node",
    "actions/setup-python",
    "actions/upload-pages-artifact",
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

# The jobs of the checks workflow, in order: the gates, the two jobs that
# publish the site, and the job that checks what was published.
JOBS = ("gates", "site", "deploy", "live")

# The one condition a job may have: it runs for a change to `main` only. The
# workflow starts for nothing but pull requests and changes to `main`.
ONLY_FOR_MAIN = "    if: github.event_name == 'push'\n"

# The name GitHub's own actions give the built site when one job hands it to
# another, and the file inside it.
SITE_ARTIFACT = "github-pages"
SITE_TAR = "artifact.tar"

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


def jobs(text: str) -> dict[str, str]:
    """Return the text of every job of a workflow, by its key, in order."""
    found: dict[str, str] = {}
    key = ""
    for line in text.split("\njobs:\n", 1)[1].splitlines(keepends=True):
        start = re.match(r"^  (\w+):$", line.rstrip("\n"))
        if start is not None:
            key = start.group(1)
            found[key] = ""
        elif key:
            found[key] += line
    return found


def actions(text: str) -> list[str]:
    """Return the actions a piece of a workflow uses, in order."""
    return re.findall(r"\buses: *([^@\s]+)", text)


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
            for action in actions(text):
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
    """The workflow that runs every gate, and the job that does it."""

    text: str
    jobs: dict[str, str]
    gates: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CHECKS.read_text(encoding="utf-8")
        cls.jobs = jobs(cls.text)
        cls.gates = cls.jobs["gates"]

    def test_runs_for_pull_requests_and_for_changes_to_main(self) -> None:
        self.assertIn("\non:\n  pull_request:\n  push:\n    branches: [main]\n\n", self.text)

    def test_its_jobs_are_the_gates_the_two_that_publish_and_the_check(self) -> None:
        self.assertEqual(tuple(self.jobs), JOBS)

    def test_its_token_can_only_read(self) -> None:
        self.assertIn("\npermissions:\n  contents: read\n\n", self.text)
        for name in ("gates", "site", "live"):
            with self.subTest(job=name):
                self.assertNotIn("permissions", self.jobs[name])

    def test_checkout_keeps_no_credentials(self) -> None:
        kept_out = re.findall(
            r"uses: actions/checkout@\S+ # \S+\n +with:\n +persist-credentials: false\n",
            self.text,
        )
        self.assertEqual(self.text.count("actions/checkout@"), 3)
        self.assertEqual(len(kept_out), 3)

    def test_runs_the_check_runner_and_nothing_in_its_place(self) -> None:
        self.assertEqual(
            commands(self.gates),
            [
                "npm ci",
                "npx playwright install --with-deps chromium",
                "python scripts/check.py",
            ],
        )

    def test_nothing_lets_a_failing_step_pass(self) -> None:
        self.assertNotIn("continue-on-error", self.text)
        self.assertNotRegex(self.text, re.compile(r"^ +(- )?shell:", re.MULTILINE))
        # No step has a condition, and the gates always run.
        self.assertNotRegex(self.text, re.compile(r"^ {5,}(- )?if:", re.MULTILINE))
        self.assertNotRegex(self.gates, re.compile(r"^ +(- )?if:", re.MULTILINE))
        self.assertNotIn("needs:", self.gates)

    def test_runs_on_linux_and_on_windows(self) -> None:
        machines = re.findall(r"^ +- name: (\w+)\n +os: (\S+)$", self.text, re.MULTILINE)

        self.assertEqual(machines, list(MACHINES))
        self.assertEqual(
            re.findall(r"^ +runs-on: (.+)$", self.gates, re.MULTILINE), ["${{ matrix.os }}"]
        )
        self.assertIn("All gates (${{ matrix.name }})", self.gates)

    def test_one_machine_failing_does_not_stop_the_other(self) -> None:
        self.assertEqual(re.findall(r"^ +fail-fast: (.+)$", self.text, re.MULTILINE), ["false"])

    def test_every_job_has_a_time_limit(self) -> None:
        for name, job in self.jobs.items():
            with self.subTest(job=name):
                self.assertRegex(job, re.compile(r"^    timeout-minutes: \d+$", re.MULTILINE))

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

        # The gates and the site are prepared alike: two jobs, one version of
        # each tool. Python is the oldest the pipeline supports, so that
        # nothing newer slips into the code unnoticed. The check of the
        # published site needs Python only.
        self.assertEqual([f">={version}" for version in python], [oldest_python] * 3)
        self.assertEqual(len(node), 2)
        self.assertEqual(len(set(node)), 1)
        self.assertTrue(oldest_node.startswith(f">={node[0]}."), (node, oldest_node))
        self.assertEqual(len(uv), 2)
        self.assertEqual(len(set(uv)), 1)
        self.assertRegex(uv[0], r"^\d+\.\d+\.\d+$")


class DeploymentTest(unittest.TestCase):
    """The two jobs that publish the site on GitHub Pages."""

    text: str
    site: str
    deploy: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CHECKS.read_text(encoding="utf-8")
        cls.site = jobs(cls.text)["site"]
        cls.deploy = jobs(cls.text)["deploy"]

    def test_the_site_is_built_only_after_every_gate_passed(self) -> None:
        self.assertIn("    needs: gates\n", self.site)
        self.assertIn("    needs: site\n", self.deploy)
        self.assertEqual(self.text.count("needs:"), 3)

    def test_a_pull_request_never_publishes(self) -> None:
        conditions = re.findall(r"^ +(?:- )?if:.*\n", self.text, re.MULTILINE)

        self.assertIn(ONLY_FOR_MAIN, self.site)
        self.assertIn(ONLY_FOR_MAIN, self.deploy)
        self.assertEqual(conditions, [ONLY_FOR_MAIN] * 3)

    def test_only_the_deployment_may_publish(self) -> None:
        rights = [line for line in self.text.splitlines() if re.search(r":\s*write\b", line)]

        self.assertEqual(rights, ["      pages: write", "      id-token: write"])
        self.assertIn(
            "    permissions:\n      pages: write\n      id-token: write\n    environment:",
            self.deploy,
        )
        self.assertEqual(self.text.count("permissions:"), 2)

    def test_the_job_that_publishes_runs_nothing_of_its_own(self) -> None:
        self.assertEqual(commands(self.deploy), [])
        self.assertEqual(actions(self.deploy), ["actions/deploy-pages"])

    def test_the_deployment_goes_through_the_pages_environment(self) -> None:
        self.assertIn("    environment: github-pages\n", self.deploy)
        self.assertEqual(self.text.count("environment:"), 1)

    def test_the_site_is_the_exported_data_and_the_built_application(self) -> None:
        self.assertEqual(commands(self.site), ["npm ci", "npm run data", "npm run build"])
        self.assertEqual(self.site.count("        working-directory: frontend\n"), 3)
        self.assertEqual(actions(self.site)[-1], "actions/upload-pages-artifact")
        self.assertRegex(
            self.site,
            r"uses: actions/upload-pages-artifact@\S+ # \S+\n +with:\n +path: frontend/dist\n\n",
        )

    def test_the_site_is_built_where_it_is_picked_up(self) -> None:
        # Vite writes the build to `dist` unless it is told otherwise.
        config = (ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
        self.assertNotIn("outDir", config)

    def test_both_jobs_run_on_a_named_linux_image(self) -> None:
        for job in (self.site, self.deploy):
            self.assertEqual(re.findall(r"^ +runs-on: (.+)$", job, re.MULTILINE), [MACHINES[0][1]])


class PublishedSiteTest(unittest.TestCase):
    """The job that checks the published site after each deployment."""

    text: str
    live: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CHECKS.read_text(encoding="utf-8")
        cls.live = jobs(cls.text)["live"]

    def address(self) -> str:
        """The address the job checks: the last word of its one command."""
        (command,) = commands(self.live)
        return command.split()[-1]

    def test_the_site_is_checked_only_after_it_was_published(self) -> None:
        self.assertIn("    needs: deploy\n", self.live)
        self.assertIn(ONLY_FOR_MAIN, self.live)

    def test_the_check_has_no_right_but_to_read(self) -> None:
        self.assertNotIn("permissions", self.live)
        self.assertNotIn("environment", self.live)
        self.assertNotIn("token", self.live)

    def test_it_takes_the_site_this_run_built(self) -> None:
        self.assertEqual(
            actions(self.live),
            ["actions/checkout", "actions/setup-python", "actions/download-artifact"],
        )
        self.assertRegex(
            self.live,
            r"uses: actions/download-artifact@\S+ # \S+\n"
            rf" +with:\n +name: {SITE_ARTIFACT}\n +path: built\n\n",
        )
        # It is this run's site: the step names no other run to take one from.
        self.assertNotIn("run-id", self.text)
        self.assertNotIn("repository:", self.text)

    def test_it_runs_the_check_of_the_published_site_and_nothing_else(self) -> None:
        (command,) = commands(self.live)

        self.assertEqual(command, f"python scripts/live.py built/{SITE_TAR} {self.address()}")
        self.assertTrue((ROOT / "scripts" / "live.py").is_file())

    def test_the_address_is_where_the_site_is_published(self) -> None:
        site = (ROOT / "frontend" / "site.ts").read_text(encoding="utf-8")
        (path,) = re.findall(r"^export const SITE_PATH = '(.+)'$", site, re.MULTILINE)

        self.assertRegex(self.address(), rf"^https://[a-z0-9-]+\.github\.io{re.escape(path)}$")
        # The address people are given is the address that is checked.
        for document in ("README.md", "TESTING.md"):
            with self.subTest(document=document):
                text = (ROOT / document).read_text(encoding="utf-8")
                self.assertIn(f"<{self.address()}>", text)

    def test_it_runs_on_a_named_linux_image(self) -> None:
        self.assertEqual(
            re.findall(r"^ +runs-on: (.+)$", self.live, re.MULTILINE), [MACHINES[0][1]]
        )


if __name__ == "__main__":
    unittest.main()
