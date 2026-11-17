# MotoSphere – Progress

Completed work, the current task, test reports and next steps. A report is
added here only after the planner's independent test run. Numbers and commit
references are copied from real output, never estimated.

## Current state

- **Phase:** 1 – Foundation
- **Current task:** FND-009 – Frontend project skeleton (`IN PROGRESS`, with a builder)
- **Tasks verified:** 8 of 211
- **Application state:** the backend API starts with `uv run python -m motosphere` and answers `GET /api/health`. No user interface and no database yet.

## Reports

### PLAN-000 – Project planning baseline (2026-11-16)

Not a development task: no application code and therefore no tests.

Done:

- Read DESIGN.md and CLAUDE.md in full and added both to the repository.
- Inspected the repository (empty, no commits) and the build environment
  (Python 3.13, uv, Node 22, npm, PostgreSQL 16 present; PostGIS 3.4
  installable from the system package archive; Chromium and Playwright
  present).
- Evaluated the proposed stack and recorded decisions in ARCHITECTURE.md,
  including a preliminary evaluation of Scrapling.
- Broke the build into 13 phases and 211 named tasks in TASKS.md, with
  Phase 1 specified in full (19 tasks).
- Described the plan → build → independent test → merge loop in
  docs/WORKFLOW.md.
- Wrote the implementation plan for the first task, docs/plans/FND-001.md.

Open items carried forward:

- Imagery and terrain providers are undecided until their licence terms are
  verified (tasks GLB-012 and GLB-016).
- No software licence has been chosen for the repository.

Next task: FND-001 – Repository hygiene baseline.

### FND-001 – Repository hygiene baseline (2026-11-16)

Implementation: Complete. Pull request #1, built in its own thread.

What was implemented: `.gitignore`, `.gitattributes`, `.editorconfig`,
`README.md`, document stubs `DATA_SOURCES.md`, `DATABASE.md`, `TESTING.md`,
`CHANGELOG.md`, and the repository check suite
`tests/repo/test_repo_hygiene.py`. Exactly the nine planned files; no existing
file modified.

Independent test run (planner, clean checkout of the pull request, Linux,
Git 2.43.0):

- Repository checks, Python 3.13.18: 9/9 passed.
- Repository checks, Python 3.12.3: 9/9 passed.
- Mutation checks: 10 deliberate defects introduced one at a time (ignore rule
  removed, environment file tracked, lock files ignored, wrong `.ps1` line
  ending, required document deleted, broken README link, CRLF content in the
  index, changelog heading removed, wrong `.editorconfig` line ending, binary
  marker removed). The suite failed on all 10 and returned to 9/9 after each
  was reverted.
- Behaviour check with real files: a `.ps1` file checks out with CRLF and a
  `.py` file committed with CRLF is stored and checked out with LF.

Unit tests: 9/9 passed.
Integration tests: not applicable.
Build: not applicable (no application code).
Type checking: not applicable.
Browser verification: not applicable.

Overall applicable tests: 9/9 passed (100%).

Status: PASSED – VERIFIED.

Known limitations: not run on Windows 11. The suite uses only the Python
standard library and Git with argument lists, and its first Windows run is the
CI task FND-018.

Commit: `9acea2a` (squash merge of pull request #1).

Next task: FND-002 – Backend project skeleton.

### FND-002 – Backend project skeleton (2026-11-16)

Implementation: Complete. Pull request #2, built in its own thread.

What was implemented: `backend/` as a uv project (`pyproject.toml`, committed
`uv.lock`, Python >= 3.12), the `motosphere` package whose `__version__` comes
from the project metadata, a `py.typed` marker, and four pytest smoke tests.
README, TESTING.md and CHANGELOG.md updated. Exactly the planned files.

Independent test run (planner, clean checkout of the pull request, Linux,
uv 0.11.32, pytest 9.2.0):

- `uv lock --check`: passed.
- `uv sync --locked`: passed; installs `motosphere==0.1.0` from the checkout.
- Backend unit tests, Python 3.13.18: 4/4 passed, no warnings.
- Backend unit tests, Python 3.12.3: 4/4 passed, no warnings.
- Repository checks: 9/9 passed.
- Mutation checks: 5 deliberate defects introduced one at a time (version
  literal in code, warning raised in a test, unknown pytest marker, malformed
  version, dependency added without re-locking). All 5 detected.
- `git status` clean after the full run (environment and caches are ignored).
- The lock file references only the public Python package index.

Unit tests: 13/13 passed (backend 4, repository 9).
Integration tests: not applicable.
Build: locked install passed.
Type checking: not applicable yet (FND-004).
Browser verification: not applicable.

Overall applicable tests: 13/13 passed (100%).

Status: PASSED – VERIFIED.

Known limitations: not run on Windows 11; first Windows run is FND-018.

Commit: `6daf3ea` (squash merge of pull request #2).

Next task: FND-003 – Backend linting and formatting.

### FND-003 – Backend linting and formatting (2026-11-16)

Implementation: Complete. Pull request #3, built in its own thread.

What was implemented: ruff added to the backend `dev` group and locked at
0.17.5; `[tool.ruff]` configuration with style, bug, pytest and security
(bandit) rule sets; README, TESTING.md and CHANGELOG.md updated. No source
file needed changing. No `# noqa`, no global ignores.

Independent test run (planner, clean checkout of the pull request, Linux,
uv 0.11.32):

- `uv lock --check`: passed. `uv sync --locked`: passed.
- Backend lint (`ruff check .`): passed.
- Backend format (`ruff format --check .`): passed, 2 files already formatted.
- Backend unit tests, Python 3.13.18: 4/4 passed. Python 3.12.3: 4/4 passed.
- Repository checks: 9/9 passed.
- Gate checks: the plan's probe file was reported with I001, F401, S602 and
  S607 and by the format check (both exit non-zero). Two further probes were
  reported with T201 and DTZ005 (print, naive datetime) and S307 (`eval` in a
  test file, confirming security rules still apply to tests). Gates returned
  to passing after each probe was removed.
- The lock file includes the Windows build of ruff.
- `git status` clean after the full run.

Unit tests: 13/13 passed (backend 4, repository 9).
Lint: passed. Format: passed.
Build: locked install passed.
Type checking: not applicable yet (FND-004).
Browser verification: not applicable.

Overall applicable tests: 13/13 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: root-level Python (`tests/repo`) is not linted until the
check runner in FND-017. Not run on Windows 11; first Windows run is FND-018.

Commit: `2e3edaf` (squash merge of pull request #3).

Next task: FND-004 – Backend type checking.

### FND-004 – Backend type checking (2026-11-16)

Implementation: Complete. Pull request #4, built in its own thread.

What was implemented: mypy added to the backend `dev` group and locked at
2.4.1; `[tool.mypy]` strict configuration over `src` and `tests`; README,
TESTING.md and CHANGELOG.md updated. No source file needed changing. No
`# type: ignore`, no overrides.

Independent test run (planner, clean checkout of the pull request, Linux,
uv 0.11.32):

- `uv lock --check`: passed. `uv sync --locked`: passed.
- Backend type check (`mypy`), Python 3.13.18: passed, 2 source files.
  Python 3.12.3: passed, 2 source files.
- Backend lint: passed. Backend format: passed.
- Backend unit tests, Python 3.13.18: 4/4 passed. Python 3.12.3: 4/4 passed.
- Repository checks: 9/9 passed.
- Gate checks: the plan's probe file was reported with an incompatible
  argument type and a missing annotation (exit non-zero). Further probes were
  reported for an unannotated test function, unreachable code and a
  `type: ignore` without an error code. The gate returned to passing after
  each probe was removed.
- `git status` clean after the full run.

Unit tests: 13/13 passed (backend 4, repository 9).
Type checking: passed. Lint: passed. Format: passed.
Build: locked install passed.
Browser verification: not applicable.

Overall applicable tests: 13/13 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Review note: the pull request left one README sentence about `ruff format`
below the new mypy block. The planner moved it back under the ruff commands in
the follow-up documentation commit; repository checks re-run at 9/9.

Known limitations: not run on Windows 11; first Windows run is FND-018.

Commit: `ebd84ce` (squash merge of pull request #4).

Next task: FND-005 – Backend settings module.

### FND-005 – Backend settings module (2026-11-16)

Implementation: Complete. Pull request #5, built in its own thread.

What was implemented: `motosphere.core.settings` (`Environment`, `LogLevel`,
immutable `Settings` with environment, API host, API port and log level, and a
cached `get_settings()`); `backend/.env.example`; an autouse test fixture that
isolates tests from the machine's environment and any real `.env`; 14 test
functions (18 cases); a "Configuration" section in README; CHANGELOG entry.
Runtime dependencies pydantic 2.14.3 and pydantic-settings 2.16.3 (locked).
No suppressions.

Independent test run (planner, clean checkout of the pull request, Linux,
uv 0.11.32):

- `uv lock --check`: passed. `uv sync --locked`: passed.
- Backend unit tests, Python 3.13.18: 22/22 passed, no warnings.
  Python 3.12.3: 22/22 passed.
- Backend type check, both Pythons: passed, 6 source files.
- Backend lint: passed. Backend format: passed.
- Repository checks: 9/9 passed. Only `backend/.env.example` is tracked.
- Isolation: with a real `backend/.env` (port 9999) and invalid `MOTOSPHERE_`
  variables in the shell, the suite still passed 22/22.
- Real behaviour from the command line: a value in `backend/.env` is read;
  an environment variable beats the file; a misspelt key in the file stops
  loading with an error naming it; an out-of-range port is rejected with an
  error naming `api_port`.
- Mutation checks: 11 planted defects (changed default, unknown keys allowed,
  not frozen, no normalisation, port bound removed, example missing a
  setting, example with a non-default value, cache removed, empty host
  allowed, `.env` not read, isolation fixture disabled) all detected.

Unit tests: 31/31 passed (backend 22, repository 9).
Type checking: passed. Lint: passed. Format: passed.
Build: locked install passed.
Browser verification: not applicable.

Overall applicable tests: 31/31 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Testing note: when a source file is changed and restored within the same
second, Python can reuse stale bytecode and report results for the earlier
version. Mutation checks are therefore run with bytecode caching disabled
(`PYTHONDONTWRITEBYTECODE=1`, `__pycache__` removed between runs).

Known limitations: not run on Windows 11; first Windows run is FND-018.

Commit: `dfe2687` (squash merge of pull request #5).

Next task: FND-006 – Backend logging configuration.

### FND-006 – Backend logging configuration (2026-11-16)

Implementation: Complete. Pull request #6, built in its own thread.

What was implemented: `motosphere.core.logging_config` with
`configure_logging(settings)`: root level from settings, one handler named
`motosphere` on standard error, line format
`<UTC timestamp> <LEVEL> [<logger>] <message>`, carriage returns and line
feeds in messages escaped, tracebacks kept intact. 10 test functions
(14 cases). CHANGELOG entry. No new dependencies, no suppressions.

Deviations from the plan, both accepted (behaviour unchanged):
`converter = staticmethod(time.gmtime)` because a plain assignment fails
strict type checking, and `@typing.override` on `formatMessage` so the
standard-library method name passes the naming rule without a suppression.

Independent test run (planner, clean checkout of the pull request, Linux,
uv 0.11.32):

- `uv lock --check`: passed. `uv sync --locked`: passed.
- Backend unit tests, Python 3.13.18: 36/36 passed, no warnings.
  Python 3.12.3: 36/36 passed.
- Backend type check, both Pythons: passed, 8 source files.
- Backend lint: passed. Backend format: passed.
- Repository checks: 9/9 passed.
- Real behaviour from the command line: configuring twice then logging a
  message containing a line break writes exactly one line to standard error
  with the break shown as `\n`, and nothing to standard output; the debug
  message appears only with `MOTOSPHERE_LOG_LEVEL=debug`; with the machine
  time zone set to Tokyo the timestamp is still UTC.
- Mutation checks: 7 planted defects (escaping removed, old handler not
  removed, local time instead of UTC, level not applied, foreign handlers
  removed, wrong line format, handler not named) all detected.

Unit tests: 45/45 passed (backend 36, repository 9).
Type checking: passed. Lint: passed. Format: passed.
Build: locked install passed.
Browser verification: not applicable.

Overall applicable tests: 45/45 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: nothing calls `configure_logging` yet; the API entry point
does so in FND-008. Not run on Windows 11; first Windows run is FND-018.

Commit: `de01322` (squash merge of pull request #6).

Next task: FND-007 – API application factory and health endpoint.

### FND-007 – API application factory and health endpoint (2026-11-16)

Implementation: Complete. Pull request #7, built in its own thread.

What was implemented: `motosphere.api` with `create_app(settings)` (a new
independent FastAPI application per call, settings stored on the application)
and `GET /api/health` returning status, name and version with
`Cache-Control: no-store`. Documentation at `/api/docs`, schema at
`/api/openapi.json`, default documentation paths not served. 10 API tests.
Dependencies locked: fastapi 0.163.1 (with starlette 1.10.0) and, for the test
client, httpx2 2.16.2. No suppressions, no deviations.

Independent test run (planner, clean checkout of the pull request, Linux,
uv 0.11.32):

- `uv lock --check`: passed. `uv sync --locked`: passed.
- Backend tests, Python 3.13.18: 46/46 passed, no warnings.
  Python 3.12.3: 46/46 passed.
- Backend type check, both Pythons: passed, 12 source files.
- Backend lint: passed. Backend format: passed.
- Repository checks: 9/9 passed.
- Mutation checks: 7 planted defects (wrong application name, cache header
  removed, documentation at the default path, given settings ignored,
  hard-coded version, health accepting POST, schema at the default path) all
  detected.

Unit and API tests: 55/55 passed (backend 46, repository 9).
Type checking: passed. Lint: passed. Format: passed.
Build: locked install passed.
Browser verification: not applicable.

Overall applicable tests: 55/55 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: exercised through the in-process test client only; no
server process exists until FND-008, which adds real HTTP verification.
Not run on Windows 11; first Windows run is FND-018.

Commit: `70a32c3` (squash merge of pull request #7).

Next task: FND-008 – Backend run command.

### FND-008 – Backend run command (2026-11-17)

Implementation: Complete. Pull request #8, built in its own thread.

What was implemented: `python -m motosphere` (`motosphere.__main__.main`):
loads settings, configures logging, serves the application with uvicorn
0.54.0 (locked) on the configured host and port with uvicorn's own log
configuration disabled so every line uses the MotoSphere format. Invalid
configuration prints one `Configuration error:` line naming each setting and
exits with code 2. Four unit tests and five integration tests that start the
real server as a child process and call it over HTTP. README "Running the
API", TESTING.md and CHANGELOG updated. No suppressions.

Deviations from the plan, accepted (behaviour unchanged): one `Popen` call
with per-platform `creationflags`; the port-in-use test holds the blocking
socket from the moment the port is chosen.

Independent test run (planner, clean checkout of the pull request, Linux,
uv 0.11.32):

- `uv lock --check`: passed. `uv sync --locked`: passed.
- Backend tests, Python 3.13.18: 55/55 passed, three runs in a row, no
  warnings. Python 3.12.3: 55/55 passed. No server process left running.
- Backend type check, both Pythons: passed, 15 source files.
- Backend lint: passed. Backend format: passed.
- Repository checks: 9/9 passed.
- Real server, by hand with curl: `GET /api/health` returned 200,
  `cache-control: no-store` and
  `{"status":"ok","name":"MotoSphere","version":"0.1.0"}`; `/api/docs` 200;
  unknown path 404; every log line in the MotoSphere format on standard error
  and nothing on standard output; interrupt shut the server down cleanly with
  exit code 0; a `backend/.env` changed the port and silenced INFO lines at
  WARNING level; port `0` and a non-numeric port with an invalid log level
  each produced one `Configuration error:` line and exit code 2.
- Mutation checks: 7 planted defects (uvicorn log configuration left on,
  wrong exit code, logging not configured, configured port ignored,
  configured host ignored, traceback instead of message, entry point guard
  removed) all detected, with no process left behind after failures.

Unit, API and integration tests: 64/64 passed (backend 55, repository 9).
Type checking: passed. Lint: passed. Format: passed.
Build: locked install passed.
Integration verification: passed (real process, real HTTP).
Browser verification: not applicable.

Overall applicable tests: 64/64 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: verified on Linux only. The Windows-only branches of the
integration test helper (new process group, Ctrl+Break) have not been
executed; their first run is the Windows CI job in FND-018, and start/stop on
a real Windows 11 machine is FND-019.

Commit: `219166f` (squash merge of pull request #8).

Next task: FND-009 – Frontend project skeleton.
