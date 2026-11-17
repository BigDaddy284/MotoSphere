"""Tests for the dependency audit, `scripts/audit.py` (task FND-033).

Run from the repository root:

    python -m unittest discover -s tests/scripts -v

No test here asks the npm registry anything. The report the tests read was
copied from a real `npm audit --json` run on 2026-11-17, cut down to four of
its six packages, and the stand-in audit commands are run by the real Python.
"""

import datetime as dt
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# The script is not an installed package, so its folder is added to the places
# Python imports from.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import audit
import check

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit.py"

PICOMATCH = "GHSA-fc5q-39xc-vjpf"
URL = f"https://github.com/advisories/{PICOMATCH}"
TITLE = "picomatch vulnerable to ReDoS through single-branch repeated extglobs"
REASON = "It only reads patterns written in this repository, never anything from outside."
TODAY = dt.date(2026, 11, 20)

# From a real run: one advisory, about picomatch, and three of the packages
# that are affected because they use it.
REPORT = {
    "auditReportVersion": 2,
    "vulnerabilities": {
        "fdir": {
            "name": "fdir",
            "severity": "high",
            "isDirect": False,
            "via": ["picomatch"],
            "effects": ["tinyglobby"],
            "range": ">=5.2.1",
            "nodes": ["node_modules/fdir"],
            "fixAvailable": True,
        },
        "picomatch": {
            "name": "picomatch",
            "severity": "high",
            "isDirect": False,
            "via": [
                {
                    "source": 1247710,
                    "name": "picomatch",
                    "dependency": "picomatch",
                    "title": TITLE,
                    "url": URL,
                    "severity": "high",
                    "cwe": ["CWE-1333"],
                    "cvss": {
                        "score": 7.5,
                        "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
                    },
                    "range": "<=4.0.7",
                }
            ],
            "effects": ["fdir", "tinyglobby", "vite", "vitest"],
            "range": "*",
            "nodes": ["node_modules/picomatch"],
            "fixAvailable": {"name": "vitest", "version": "3.1.4", "isSemVerMajor": True},
        },
        "tinyglobby": {
            "name": "tinyglobby",
            "severity": "high",
            "isDirect": False,
            "via": ["fdir", "picomatch"],
            "effects": ["vite", "vitest"],
            "range": "*",
            "nodes": ["node_modules/tinyglobby"],
            "fixAvailable": {"name": "vitest", "version": "3.1.4", "isSemVerMajor": True},
        },
        "vite": {
            "name": "vite",
            "severity": "high",
            "isDirect": True,
            "via": ["picomatch", "tinyglobby"],
            "effects": ["@vitejs/plugin-react", "vitest"],
            "range": ">=6.3.0-beta.0",
            "nodes": ["node_modules/vite"],
            "fixAvailable": {"name": "vite", "version": "6.2.7", "isSemVerMajor": True},
        },
    },
    "metadata": {
        "vulnerabilities": {"info": 0, "low": 0, "moderate": 0, "high": 4, "critical": 0},
    },
}
CLEAN = {"auditReportVersion": 2, "vulnerabilities": {}, "metadata": {}}

ADVISORY = audit.Advisory(PICOMATCH, "picomatch", "high", TITLE, URL)


def entry(**changes: object) -> dict[str, object]:
    """One exception as the file holds it, with the given fields changed."""
    return {
        "advisory": PICOMATCH,
        "package": "picomatch",
        "reason": REASON,
        "accepted": "2026-11-17",
        "review_by": "2026-12-17",
        **changes,
    }


def file_with(*entries: object) -> str:
    return json.dumps({"exceptions": list(entries)})


def accepted(**changes: object) -> audit.Accepted:
    (exception,) = audit.read_exceptions(file_with(entry(**changes)))
    return exception


def prints(report: object, exit_code: int = 0) -> tuple[str, ...]:
    """A stand-in audit command: the real Python, printing this report."""
    program = f"import sys; sys.stdout.write({json.dumps(report)!r}); sys.exit({exit_code})"
    return (sys.executable, "-c", program)


class ReadExceptionsTest(unittest.TestCase):
    def refused(self, text: str, why: str) -> None:
        with self.assertRaises(audit.UnusableError) as caught:
            audit.read_exceptions(text)
        self.assertIn(why, str(caught.exception))
        self.assertIn("frontend/audit-exceptions.json", str(caught.exception))

    def test_reads_an_exception_with_its_reason_and_dates(self) -> None:
        self.assertEqual(
            audit.read_exceptions(file_with(entry())),
            (
                audit.Accepted(
                    PICOMATCH, "picomatch", REASON, dt.date(2026, 11, 17), dt.date(2026, 12, 17)
                ),
            ),
        )

    def test_an_empty_list_is_no_exception(self) -> None:
        self.assertEqual(audit.read_exceptions(file_with()), ())

    def test_refuses_what_is_not_json(self) -> None:
        self.refused("{", "is not valid JSON")

    def test_refuses_anything_but_one_list_named_exceptions(self) -> None:
        for text in ("[]", "{}", '{"exceptions": {}}', '{"exceptions": [], "ignore": ["all"]}'):
            with self.subTest(text=text):
                self.refused(text, 'must hold one list, named "exceptions"')

    def test_refuses_a_missing_or_an_unknown_field(self) -> None:
        without_reason = entry()
        del without_reason["reason"]
        for wrong in (without_reason, entry(severity="low"), "GHSA-fc5q-39xc-vjpf"):
            with self.subTest(entry=wrong):
                self.refused(file_with(wrong), "exception 1: must have exactly the fields")

    def test_refuses_a_field_that_is_not_text(self) -> None:
        self.refused(file_with(entry(reason=None)), "every field must be text")

    def test_refuses_an_advisory_that_is_not_an_id(self) -> None:
        for wrong in ("", "*", "picomatch", "CVE-2026-1234", f"{PICOMATCH} "):
            with self.subTest(advisory=wrong):
                self.refused(file_with(entry(advisory=wrong)), '"advisory" must be an id')

    def test_refuses_an_exception_without_a_package(self) -> None:
        self.refused(file_with(entry(package=" ")), '"package" is empty')

    def test_refuses_a_reason_too_short_to_be_one(self) -> None:
        self.refused(file_with(entry(reason="dev only")), '"reason" must say why')
        self.refused(file_with(entry(reason="x" + " " * 60)), '"reason" must say why')

    def test_refuses_a_date_that_is_not_one(self) -> None:
        self.refused(file_with(entry(accepted="17/11/2026")), '"accepted" must be a date')
        self.refused(file_with(entry(review_by="2026-11-31")), '"review_by" is not a real date')

    def test_refuses_a_review_date_that_is_not_after_the_start(self) -> None:
        self.refused(file_with(entry(review_by="2026-11-17")), '"review_by" must be after')

    def test_an_exception_may_stand_31_days_and_no_longer(self) -> None:
        audit.read_exceptions(file_with(entry(review_by="2026-12-18")))
        self.refused(file_with(entry(review_by="2026-12-19")), "at most 31 days")

    def test_refuses_the_same_advisory_twice(self) -> None:
        self.refused(file_with(entry(), entry()), f"exception 2: {PICOMATCH} is listed twice")


class AdvisoriesTest(unittest.TestCase):
    def test_reads_the_advisory_from_a_real_report_once(self) -> None:
        self.assertEqual(audit.advisories(REPORT), (ADVISORY,))

    def test_a_report_without_affected_packages_has_no_advisory(self) -> None:
        self.assertEqual(audit.advisories(CLEAN), ())

    def test_an_advisory_listed_under_two_packages_comes_back_once(self) -> None:
        report = json.loads(json.dumps(REPORT))
        cause = report["vulnerabilities"]["picomatch"]["via"][0]
        report["vulnerabilities"]["fdir"]["via"].append(dict(cause))

        self.assertEqual(audit.advisories(report), (ADVISORY,))

    def test_two_advisories_come_back_in_a_fixed_order(self) -> None:
        other = {
            "name": "vite",
            "title": "Something else",
            "url": "https://github.com/advisories/GHSA-2222-3333-4444",
            "severity": "low",
        }
        report = json.loads(json.dumps(REPORT))
        report["vulnerabilities"]["vite"]["via"].append(other)

        self.assertEqual(
            [(found.identity, found.package) for found in audit.advisories(report)],
            [("GHSA-2222-3333-4444", "vite"), (PICOMATCH, "picomatch")],
        )

    def test_an_advisory_from_elsewhere_keeps_its_address_as_its_name(self) -> None:
        report = json.loads(json.dumps(REPORT))
        report["vulnerabilities"]["picomatch"]["via"][0]["url"] = "https://example.org/a/1"

        self.assertEqual(
            [found.identity for found in audit.advisories(report)], ["https://example.org/a/1"]
        )

    def test_an_answer_that_is_not_a_report_is_refused(self) -> None:
        answers: tuple[object, ...] = ({"message": "no"}, [], "found 0 vulnerabilities", None)
        for answer in answers:
            with self.subTest(answer=answer):
                with self.assertRaises(audit.UnusableError) as caught:
                    audit.advisories(answer)
                self.assertEqual(str(caught.exception), "npm audit gave no report")

    def test_an_error_from_npm_is_passed_on_in_its_own_words(self) -> None:
        error = {"error": {"code": "ENOLOCK", "summary": "This command requires a lockfile."}}

        with self.assertRaises(audit.UnusableError) as caught:
            audit.advisories(error)
        self.assertEqual(
            str(caught.exception), "npm audit gave no report: This command requires a lockfile."
        )

    def test_affected_packages_without_a_readable_advisory_are_refused(self) -> None:
        report = json.loads(json.dumps(REPORT))
        report["vulnerabilities"]["picomatch"]["via"] = ["fdir"]

        with self.assertRaises(audit.UnusableError) as caught:
            audit.advisories(report)
        self.assertIn("names no advisory", str(caught.exception))


class JudgeTest(unittest.TestCase):
    def test_nothing_reported_and_nothing_accepted_passes(self) -> None:
        self.assertEqual(audit.judge((), (), TODAY), [])

    def test_an_advisory_without_an_exception_is_a_problem(self) -> None:
        self.assertEqual(audit.judge((ADVISORY,), (), TODAY), [f"picomatch: {TITLE} (high) {URL}"])

    def test_an_advisory_with_an_exception_passes(self) -> None:
        self.assertEqual(audit.judge((ADVISORY,), (accepted(),), TODAY), [])

    def test_an_exception_holds_up_to_and_on_its_review_date(self) -> None:
        self.assertEqual(audit.judge((ADVISORY,), (accepted(),), dt.date(2026, 11, 17)), [])
        self.assertEqual(audit.judge((ADVISORY,), (accepted(),), dt.date(2026, 12, 17)), [])

    def test_an_exception_past_its_review_date_is_a_problem(self) -> None:
        (problem,) = audit.judge((ADVISORY,), (accepted(),), dt.date(2026, 12, 18))

        self.assertIn(f"the exception for {PICOMATCH} (picomatch) was due for review", problem)
        self.assertIn("2026-12-17", problem)

    def test_an_exception_nothing_needs_any_more_is_a_problem(self) -> None:
        self.assertEqual(
            audit.judge((), (accepted(),), TODAY),
            [f"the exception for {PICOMATCH} (picomatch) is no longer needed: remove it"],
        )

    def test_an_exception_covers_only_its_own_advisory(self) -> None:
        other = audit.Advisory("GHSA-2222-3333-4444", "vite", "low", "Something else", "u")

        self.assertEqual(
            audit.judge((ADVISORY, other), (accepted(),), TODAY), ["vite: Something else (low) u"]
        )

    def test_an_exception_for_another_package_is_a_problem(self) -> None:
        (problem,) = audit.judge((ADVISORY,), (accepted(package="vite"),), TODAY)

        self.assertIn("names the package vite, but the advisory is about picomatch", problem)

    def test_an_exception_dated_in_the_future_is_a_problem(self) -> None:
        (problem,) = audit.judge((ADVISORY,), (accepted(),), dt.date(2026, 11, 16))

        self.assertIn("is dated in the future (2026-11-17)", problem)


class TemporaryRootTest(unittest.TestCase):
    """A stand-in repository with a `frontend/` folder, removed after each test."""

    def setUp(self) -> None:
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        self.root = Path(folder).resolve()
        (self.root / "frontend").mkdir()

    def record(self, *entries: object) -> None:
        (self.root / audit.EXCEPTIONS).write_text(file_with(*entries), encoding="utf-8")

    def run_main(
        self, report: object, exit_code: int = 0, today: dt.date = TODAY
    ) -> tuple[int, str]:
        out = io.StringIO()
        code = audit.main([], self.root, today, out, prints(report, exit_code))
        return code, out.getvalue()


class RunAuditTest(TemporaryRootTest):
    def test_returns_the_report_the_command_prints(self) -> None:
        self.assertEqual(audit.run_audit(self.root, prints(CLEAN)), CLEAN)

    def test_reads_the_report_whatever_the_exit_code(self) -> None:
        # npm ends with exit code 1 whenever it reports an advisory.
        self.assertEqual(audit.run_audit(self.root, prints(REPORT, exit_code=1)), REPORT)

    def test_runs_in_the_frontend_folder(self) -> None:
        program = "import json, os; print(json.dumps(os.path.basename(os.getcwd())))"

        self.assertEqual(audit.run_audit(self.root, (sys.executable, "-c", program)), "frontend")

    def test_a_command_that_prints_no_report_is_refused(self) -> None:
        with self.assertRaises(audit.UnusableError) as caught:
            audit.run_audit(self.root, (sys.executable, "-c", "import sys; sys.exit(7)"))
        self.assertIn("gave no report (exit code 7)", str(caught.exception))

    def test_a_program_that_is_not_installed_is_refused(self) -> None:
        with self.assertRaises(audit.UnusableError) as caught:
            audit.run_audit(self.root, ("motosphere-no-such-program", "audit"))
        self.assertEqual(str(caught.exception), "motosphere-no-such-program is not installed")

    def test_the_real_command_is_npm_audit_as_json(self) -> None:
        self.assertEqual(audit.AUDIT, ("npm", "audit", "--json"))


class MainTest(TemporaryRootTest):
    def test_passes_when_nothing_is_reported(self) -> None:
        self.record()

        code, output = self.run_main(CLEAN)

        self.assertEqual(code, 0)
        self.assertEqual(output, "npm audit reports 0 advisories.\nDependency audit passed.\n")

    def test_fails_on_an_advisory_and_names_it(self) -> None:
        self.record()

        code, output = self.run_main(REPORT, exit_code=1)

        self.assertEqual(code, 1)
        self.assertEqual(
            output,
            f"npm audit reports 1 advisory.\nFAILED:\n  - picomatch: {TITLE} (high) {URL}\n",
        )

    def test_passes_on_an_advisory_with_an_exception_and_says_so(self) -> None:
        self.record(entry())

        code, output = self.run_main(REPORT, exit_code=1)

        self.assertEqual(code, 0)
        self.assertEqual(
            output,
            "npm audit reports 1 advisory.\n"
            f"  recorded exception: {PICOMATCH} (picomatch), review by 2026-12-17. {REASON}\n"
            "Dependency audit passed.\n",
        )

    def test_fails_when_an_exception_is_past_its_review_date(self) -> None:
        self.record(entry())

        code, output = self.run_main(REPORT, exit_code=1, today=dt.date(2026, 12, 18))

        self.assertEqual(code, 1)
        self.assertIn("recorded exception", output)
        self.assertIn("FAILED:\n  - the exception for", output)
        self.assertNotIn("passed", output)

    def test_fails_when_an_exception_is_no_longer_needed(self) -> None:
        self.record(entry())

        code, output = self.run_main(CLEAN)

        self.assertEqual(code, 1)
        self.assertIn("is no longer needed: remove it", output)
        self.assertNotIn("recorded exception:", output)

    def test_fails_in_plain_words_when_the_exceptions_cannot_be_read(self) -> None:
        code, output = self.run_main(CLEAN)

        self.assertEqual(code, 1)
        self.assertEqual(
            output,
            "The dependency audit could not be judged: "
            "frontend/audit-exceptions.json is missing or cannot be read\n",
        )

    def test_fails_in_plain_words_when_the_exceptions_are_faulty(self) -> None:
        self.record(entry(reason="because"))

        code, output = self.run_main(REPORT, exit_code=1)

        self.assertEqual(code, 1)
        self.assertIn("could not be judged: frontend/audit-exceptions.json, exception 1", output)

    def test_fails_in_plain_words_when_the_audit_gives_no_report(self) -> None:
        self.record()

        code, output = self.run_main({"error": {"code": "ENOLOCK", "summary": "No lockfile."}}, 1)

        self.assertEqual(code, 1)
        self.assertEqual(
            output,
            "The dependency audit could not be judged: npm audit gave no report: No lockfile.\n",
        )

    def test_uses_today_when_no_day_is_given(self) -> None:
        today = dt.datetime.now(dt.UTC).date()

        def code_for(accepted_days_ago: int, review_in_days: int) -> tuple[int, str]:
            self.record(
                entry(
                    accepted=str(today - dt.timedelta(days=accepted_days_ago)),
                    review_by=str(today + dt.timedelta(days=review_in_days)),
                )
            )
            out = io.StringIO()
            return audit.main([], self.root, None, out, prints(REPORT, 1)), out.getvalue()

        # Accepted yesterday and due tomorrow holds; due yesterday does not.
        self.assertEqual(code_for(1, 1)[0], 0)
        code, output = code_for(20, -1)
        self.assertEqual(code, 1)
        self.assertIn("was due for review", output)


class RepositoryTest(unittest.TestCase):
    """The files of the real repository."""

    def test_the_recorded_exceptions_can_be_read(self) -> None:
        text = (ROOT / audit.EXCEPTIONS).read_text(encoding="utf-8")

        for exception in audit.read_exceptions(text):
            with self.subTest(advisory=exception.advisory):
                self.assertLessEqual((exception.review_by - exception.accepted).days, 31)

    def test_the_check_runner_runs_this_script_for_the_audit_gate(self) -> None:
        (gate,) = [gate for gate in check.GATES if gate.key == "frontend-audit"]

        self.assertEqual(gate.command, ("python", "scripts/audit.py"))
        self.assertEqual(gate.folder, ".")
        self.assertTrue(SCRIPT.is_file())

    def test_the_script_runs_as_a_program_and_fails_without_a_traceback(self) -> None:
        # A copy in a stand-in repository with no exceptions file: the script
        # must say so and end with exit code 1, before npm is ever asked.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / "scripts").mkdir()
            (root / "frontend").mkdir()
            shutil.copy(SCRIPT, root / "scripts" / "audit.py")

            # The arguments are the real Python and a file this test wrote.
            completed = subprocess.run(  # noqa: S603
                [sys.executable, str(root / "scripts" / "audit.py")],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 1)
        self.assertIn(
            "could not be judged: frontend/audit-exceptions.json is missing", completed.stdout
        )
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
