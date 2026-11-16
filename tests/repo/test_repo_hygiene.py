"""Repository hygiene checks for MotoSphere (task FND-001).

Standard library only, so the suite runs with a plain Python 3.12+ and Git on
Windows 11 and Linux with nothing installed:

    python -m unittest discover -s tests/repo -v

Tests that inspect tracked files read the Git index, so stage changes first.
"""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DOCUMENTS = (
    "README.md",
    "CLAUDE.md",
    "DESIGN.md",
    "TASKS.md",
    "PROGRESS.md",
    "ARCHITECTURE.md",
    "DATA_SOURCES.md",
    "DATABASE.md",
    "TESTING.md",
    "CHANGELOG.md",
)

README_LINKED_DOCUMENTS = (
    "DESIGN.md",
    "CLAUDE.md",
    "TASKS.md",
    "PROGRESS.md",
    "ARCHITECTURE.md",
    "DATA_SOURCES.md",
    "DATABASE.md",
    "TESTING.md",
    "CHANGELOG.md",
    "docs/WORKFLOW.md",
)

IGNORED_SAMPLE_PATHS = (
    ".env",
    ".env.local",
    "backend/.env",
    "backend/.venv/pyvenv.cfg",
    "backend/src/motosphere/__pycache__/x.pyc",
    "backend/.pytest_cache/README.md",
    "backend/.mypy_cache/x.json",
    "backend/.ruff_cache/x",
    "backend/motosphere.egg-info/PKG-INFO",
    "frontend/node_modules/react/index.js",
    "frontend/dist/index.html",
    "frontend/playwright-report/index.html",
    "frontend/test-results/x.txt",
    "frontend/tsconfig.tsbuildinfo",
    "logs/app.log",
    "server.pem",
    "Thumbs.db",
    ".DS_Store",
    ".idea/workspace.xml",
)

NOT_IGNORED_SAMPLE_PATHS = (
    ".env.example",
    "backend/.env.example",
    "backend/pyproject.toml",
    "backend/uv.lock",
    "backend/src/motosphere/__init__.py",
    "backend/tests/test_smoke.py",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/src/main.tsx",
    "frontend/e2e/smoke.spec.ts",
    "scripts/start.ps1",
    "docs/plans/FND-001.md",
    "tests/repo/test_repo_hygiene.py",
)

SECRET_FILE_NAMES = ("id_rsa", "id_ed25519")
SECRET_SUFFIXES = (".pem", ".key")

MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
CODE_FENCE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)


def git(*args: str) -> subprocess.CompletedProcess:
    """Run Git in the repository root with an argument list (never a shell)."""
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def check_ignore(path: str) -> int:
    """Return the exit code of `git check-ignore -q` for a sample path."""
    return git("check-ignore", "-q", "--", path).returncode


def check_attr(path: str) -> dict:
    """Return the `text` and `eol` attributes Git resolves for a path."""
    result = git("check-attr", "text", "eol", "--", path)
    if result.returncode != 0:
        raise RuntimeError(f"git check-attr failed for {path}: {result.stderr.strip()}")
    attributes = {}
    for line in result.stdout.splitlines():
        # Format: "<path>: <attribute>: <value>"
        _, name, value = line.rsplit(": ", 2)
        attributes[name] = value
    return attributes


def tracked_files() -> list:
    result = git("ls-files")
    if result.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line]


class RepositoryHygieneTest(unittest.TestCase):
    def test_required_documents_exist(self):
        for name in REQUIRED_DOCUMENTS:
            with self.subTest(document=name):
                path = ROOT / name
                self.assertTrue(path.exists(), f"{name} is missing")
                self.assertTrue(path.is_file(), f"{name} is not a file")
                content = path.read_text(encoding="utf-8")
                self.assertTrue(content.strip(), f"{name} is empty")

    def test_generated_and_secret_paths_are_ignored(self):
        for path in IGNORED_SAMPLE_PATHS:
            with self.subTest(path=path):
                code = check_ignore(path)
                self.assertEqual(code, 0, f"{path} is not ignored (git check-ignore exit {code})")

    def test_source_paths_are_not_ignored(self):
        for path in NOT_IGNORED_SAMPLE_PATHS:
            with self.subTest(path=path):
                code = check_ignore(path)
                if code not in (0, 1):
                    raise RuntimeError(f"git check-ignore failed for {path} with exit code {code}")
                self.assertEqual(code, 1, f"{path} is ignored but must be tracked")

    def test_no_secret_or_environment_files_tracked(self):
        offending = []
        for path in tracked_files():
            name = path.rsplit("/", 1)[-1]
            is_env_file = (name == ".env" or name.startswith(".env.")) and name != ".env.example"
            is_secret = name.endswith(SECRET_SUFFIXES) or name in SECRET_FILE_NAMES
            if is_env_file or is_secret:
                offending.append(path)
        self.assertEqual(offending, [], f"Secret or environment files are tracked: {offending}")

    def test_line_ending_attributes(self):
        expectations = (
            ("backend/src/app.py", "eol", "lf"),
            ("frontend/src/main.tsx", "eol", "lf"),
            ("README.md", "eol", "lf"),
            ("scripts/start.ps1", "eol", "crlf"),
            ("scripts/run.bat", "eol", "crlf"),
            ("scripts/run.cmd", "eol", "crlf"),
            ("frontend/public/logo.png", "text", "unset"),
            ("frontend/public/font.woff2", "text", "unset"),
        )
        for path, attribute, expected in expectations:
            with self.subTest(path=path, attribute=attribute):
                self.assertEqual(check_attr(path).get(attribute), expected)

    def test_tracked_text_files_are_lf_in_repository(self):
        result = git("ls-files", "--eol")
        self.assertEqual(result.returncode, 0, result.stderr)
        offending = []
        for line in result.stdout.splitlines():
            if not line:
                continue
            info, _, path = line.partition("\t")
            index_eol = info.split()[0]
            if index_eol in ("i/crlf", "i/mixed"):
                offending.append(f"{path} ({index_eol})")
        self.assertEqual(offending, [], f"Tracked files without LF line endings in the index: {offending}")

    def test_editorconfig_baseline(self):
        content = (ROOT / ".editorconfig").read_text(encoding="utf-8")
        for key, value in (
            ("root", "true"),
            ("charset", "utf-8"),
            ("end_of_line", "lf"),
            ("insert_final_newline", "true"),
        ):
            with self.subTest(setting=key):
                pattern = rf"^\s*{re.escape(key)}\s*=\s*{re.escape(value)}\s*$"
                self.assertRegex(content, re.compile(pattern, re.MULTILINE))

    def test_readme_links_resolve(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        text = CODE_FENCE.sub("", text)
        linked = set()
        for target in MARKDOWN_LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            linked.add(target)
            with self.subTest(link=target):
                self.assertTrue((ROOT / target).exists(), f"README link target does not exist: {target}")
        for document in README_LINKED_DOCUMENTS:
            with self.subTest(required_link=document):
                self.assertIn(document, linked, f"README does not link to {document}")

    def test_changelog_has_unreleased_section(self):
        content = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertRegex(content, re.compile(r"^## \[Unreleased\]\s*$", re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
