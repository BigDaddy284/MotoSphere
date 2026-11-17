# MotoSphere – Progress

Completed work, the current task, test reports and next steps. A report is
added here only after the planner's independent test run. Numbers and commit
references are copied from real output, never estimated.

## Current state

- **Phase:** 1 – Foundation
- **Current task:** FND-024 – Application icon in the Sky Classic style (`NOT STARTED`, the planner is writing its plan)
- **Tasks verified:** 20 of 218
- **Application state:** there is no server: the site will be static files on GitHub Pages. The data pipeline has a command line, `uv run python -m motosphere <command>`, with two commands so far: `version`, and `export --out <directory>`, which writes the published data manifest (`manifest.json`; it holds no record counts yet because nothing is published). The frontend starts with `npm run dev` and shows the application's layout (top bar with today's date, sections panel with the nine sections to choose from, globe area and details panel; the side panels can be closed to give the globe area the whole width; no globe or data yet), and has its own unit tests (`npm test`) and browser tests (`npm run e2e`). The page uses the owner's Graphite theme. The two are not connected yet; no globe and no data store.

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

### FND-009 – Frontend project skeleton (2026-11-17)

Implementation: Complete. Pull request #9, built in its own thread.

What was implemented: `frontend/` as a Vite + React + TypeScript project
(strict mode plus unchecked-index, implicit-override and exact-optional
checks), committed `package-lock.json`, an original favicon, an `App`
component rendering the application name and tagline, and an entry point that
fails with a clear message if the page has no root element. README "Running
the frontend", TESTING.md gates and CHANGELOG updated. Exactly the ten planned
files; no template demo content; no deviations.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9; installed vite 8.3.8, react 19.3.1,
typescript 7.0.2, @vitejs/plugin-react 6.3.0):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. Lock file references only
  the public npm registry.
- Frontend type check: passed. Frontend build: passed (`dist/index.html`,
  one script bundle, favicon).
- Browser check, headless Chromium, built page via `npm run preview`: title
  `MotoSphere`, `lang="en"`, one main landmark, heading and tagline visible,
  no console errors or warnings, no failed requests. Same result against
  `npm run dev`.
- Gate checks: 5 planted defects (wrong type, unused import, implicit any,
  unchecked index access, invalid Vite configuration) all reported; type
  check and build exit non-zero.
- Repository checks: 9/9 passed. Backend tests: 55/55 passed (unchanged).
- `git status` clean after the full run.

Unit, API and integration tests: 64/64 passed (backend 55, repository 9).
Type checking: passed (backend and frontend). Lint and format: passed (backend).
Build: passed (frontend).
Browser verification: passed.

Overall applicable tests: 64/64 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the page is unstyled until FND-013; no automated frontend
tests until FND-010 and no automated browser tests until FND-012 (the browser
check above was run by the planner with a script outside the repository).
Not run on Windows 11; first Windows run is FND-018.

Commit: `76b694e` (squash merge of pull request #9).

Next task: FND-010 – Frontend unit testing.

### FND-010 – Frontend unit testing (2026-11-17)

TASK: FND-010 – Frontend unit testing

Implementation: Complete (builder thread, pull request #10). Vitest with
jsdom and Testing Library; `npm test` runs the suite once and exits. Five
tests: three for `App` (heading with the application name, tagline, exactly
one main landmark) and two for the entry point (renders `App` into the root
element; fails with a clear message when the root element is missing). Test
files are type-checked with the rest of the frontend. README, TESTING.md and
CHANGELOG updated. Exactly the ten planned files; no application code
changed; no deviations.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9; installed vitest 5.1.0, jsdom 31.0.1,
@testing-library/react 16.3.3, @testing-library/jest-dom 7.0.1):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. Lock file references only
  the public npm registry.
- Frontend unit tests: 5/5 passed (2 files), exit code 0, no warnings.
- Frontend type check: passed. Frontend build: passed; bundle unchanged at
  219.76 kB and no test code in `dist/`.
- No `any`, `@ts-ignore`, skipped or focused tests.
- Gate checks: 6 planted defects all detected (heading level changed, error
  message changed, type error inside a test file, tagline removed, second
  main landmark added, entry point no longer rendering `App`); the test run
  or the type check exits non-zero each time.
- Repository checks: 9/9 passed.
- Backend (not touched by this pull request), re-run on `main` after the
  merge: lock check, mypy, ruff lint and format passed; 55/55 tests passed.
- `git status` clean after the full run.

Unit, API and integration tests: 69/69 passed (frontend 5, backend 55,
repository 9).
Type checking: passed (backend and frontend). Lint and format: passed (backend).
Build: passed (frontend).
Browser verification: not applicable to this task (no visible change; the
page was verified in FND-009).

Overall applicable tests: 69/69 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: no frontend lint or format gate until FND-011; no
automated browser tests until FND-012. Not run on Windows 11; first Windows
run is FND-018.

Planning note for FND-011: the linter will be oxlint, not the ESLint named in
the original plan, because the project uses the native TypeScript 7 compiler.
The reason is recorded in `ARCHITECTURE.md` §3. The planner trial-ran the
configuration on the merged frontend before writing the plan.

Commit: `0914ec5` (squash merge of pull request #10).

Next task: FND-011 – Frontend linting and formatting.

### FND-011 – Frontend linting and formatting (2026-11-17)

TASK: FND-011 – Frontend linting and formatting

Implementation: Complete (builder thread, pull request #11). oxlint with the
React, TypeScript, import, accessibility, Vitest and promise rule sets
(`npm run lint`, warnings fail the gate) and Prettier (`npm run format:check`,
`npm run format`). Raw HTML rendering, `eval`, `any`, non-null assertions and
console output are banned. README, TESTING.md and CHANGELOG updated. Exactly
the nine planned files; the configuration is identical to the plan; the only
existing file reformatted is `tsconfig.json`; no source file changed; no
deviations.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9; installed oxlint 1.94.0, prettier 3.10.1):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. Lock file references only
  the public npm registry.
- Frontend lint: passed, covering exactly the 7 project files. Frontend
  format check: passed.
- Frontend unit tests: 5/5 passed. Type check: passed. Build: passed, bundle
  unchanged at 219.76 kB.
- No suppression comments anywhere in `frontend/`.
- Gate checks: 8 planted defects all reported with a non-zero exit code:
  the plan's probe file (17 findings, including unused variable, `any`,
  hook called conditionally, missing effect dependency, non-null assertion,
  `@ts-ignore`, loose equality, `eval`, `debugger`, missing image text,
  click handler without keyboard support and raw HTML); raw HTML in `App`;
  `console.log` in the entry point; an import used only for its side effect;
  a focused unit test (`it.only`); a skipped unit test (`it.skip`); a badly
  formatted new file; double quotes in `App`. Control: a style sheet import
  is allowed, as planned.
- Repository checks: 9/9 passed.
- Backend: not touched and not re-run; no backend file has changed since its
  55/55 run on commit `0914ec5`.
- `git status` clean after the full run.

Unit tests: 14/14 passed (frontend 5, repository 9).
Type checking: passed (frontend). Lint and format: passed (frontend).
Build: passed (frontend).
Browser verification: not applicable to this task (no visible change).

Overall applicable tests: 14/14 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the linter does not use type information; type errors are
caught by the type-check gate. Not run on Windows 11; first Windows run is
FND-018.

Planning note for FND-012: in the planner's trial, the linter reported a
skipped Vitest test but not a skipped Playwright test. Skipped browser tests
are therefore checked by the planner in review, and the check runner
(FND-017) is now required to fail when any test is reported as skipped.

Commit: `4aa7988` (squash merge of pull request #11).

Next task: FND-012 – Browser test infrastructure.

### FND-012 – Browser test infrastructure (2026-11-17)

TASK: FND-012 – Browser test infrastructure

Implementation: Complete (builder thread, pull request #12). Playwright
(pinned to 1.63.0, Chromium only): `npm run e2e` builds the frontend, serves
the build on the loopback address and opens it headlessly. Four browser
tests: title and language, visible name and tagline, one main landmark, and
the page icon is really served. A shared fixture fails any browser test in
which the page logs an error or warning, throws, has a failed request or
receives an HTTP error status. Browser tests have their own strict type-check
project. README, TESTING.md and CHANGELOG updated. Exactly the twelve planned
files, identical to the planner's trial; nothing under `frontend/src/`
changed; no deviations.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9; Playwright 1.63.0 with its matching headless
Chromium):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. Lock file references only
  the public npm registry.
- Frontend lint: passed (10 files). Format check: passed.
- Frontend unit tests: 5/5 passed (the unit run does not pick up the browser
  tests). Type check: passed. Build: passed, bundle unchanged at 219.76 kB.
- Browser tests: 4/4 passed in about 3 seconds.
- No skipped or focused tests and no suppressions.
- Gate checks: 11 planted defects all detected with a non-zero exit code:
  console error, console warning, uncaught error and failed network request
  (each fails all 4 tests through the shared fixture); wrong page title;
  heading demoted; icon file missing; type error in a browser test (type
  check); focused test (`test.only`); port 4173 already in use (clear
  message, nothing tested by accident); application that does not build.
- Repository checks: 9/9 passed.
- Backend: not touched and not re-run; no backend file has changed since its
  55/55 run on commit `0914ec5`.
- `git status` clean after the full run (results folder is ignored).

Browser tests: 4/4 passed. Unit tests: 14/14 passed (frontend 5,
repository 9).
Type checking: passed (frontend). Lint and format: passed (frontend).
Build: passed (frontend).
Browser verification: passed (automated, headless Chromium, production build).

Overall applicable tests: 18/18 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: Chromium only. A skipped Playwright test is not caught by
the linter (the check runner in FND-017 must fail on skipped tests; until
then the planner checks in review). The README instruction for installing
Chromium on a new machine (`npx playwright install chromium`) has not been
run by us, because the build environment has Chromium pre-installed; its
first real run is CI in FND-018. Not run on Windows 11; first Windows run is
FND-018.

Commit: `e806b63` (squash merge of pull request #12).

Next task: FND-013 – Dark theme design tokens.

### PLAN-001 – Re-plan for GitHub Pages hosting and the owner's visual identity (2026-11-17)

Not a build task: a planning change made by the planner after two decisions
by the owner on 2026-11-17.

1. **Hosting: GitHub Pages only, with no server.** The owner chose this on a
   decision card over "Pages preview now, full hosting later" and "keep it
   local". Consequences, recorded in `ARCHITECTURE.md`:
   - The backend becomes a command-line data pipeline (collect, validate,
     store, export) run by a scheduled GitHub Actions job or on the owner's
     PC. There is no API server.
   - The data store is SQLite instead of PostgreSQL with PostGIS.
   - The frontend reads versioned, published data files (manifest, map
     tiles, lists, details, search index) instead of calling an API.
   - Administration works through reports and version-controlled decision
     files instead of a logged-in admin interface.
   - The FastAPI application, health endpoint and server start command
     verified in FND-007 and FND-008 are removed by the new task FND-020.
     Settings and logging (FND-005, FND-006) stay.
   - New foundation tasks: FND-020 (pipeline command line replaces the API
     server), FND-021 (data manifest export), FND-022 (GitHub Pages
     deployment). FND-016 and FND-019 were rewritten. Phase 2 is now "Data
     store and published data" (DAT, PUB); later phases keep their task
     counts with server items reworded as published-data items.
   - GitHub limits checked against GitHub's documentation on 2026-11-17: a
     published site may be at most 1 GB, traffic has a soft limit of 100 GB
     a month, a deployment times out after 10 minutes, Pages on GitHub Free
     needs a public repository, and scheduled workflows in a public
     repository are disabled after 60 days without repository activity.
2. **Visual identity.** The owner supplied the Graphite theme and the Sky
   Classic icon style. The reference files are in `docs/design/`. New tasks:
   FND-023 (apply the Graphite theme) and FND-024 (application icon), both
   before the layout task FND-014. FND-013 is still merged as planned,
   because it delivers the token and contrast-test machinery; its
   provisional colours are replaced by FND-023.
3. **Name.** The owner confirmed the product is called MotoSphere only; the
   earlier working title was removed from all documents.

Task totals: Phase 1 now has 24 tasks; the project has 216 named tasks.

Tests: repository checks 9/9 passed after the document changes. No code
changed.

Open points for the owner: GitHub Pages must be switched on for the
repository before FND-022 can be verified (a public repository, or a paid
plan for a private one).

### FND-013 – Dark theme design tokens (2026-11-17)

TASK: FND-013 – Dark theme design tokens

Implementation: Complete (builder thread, pull request #13). Design tokens
as CSS custom properties (13 colours, system fonts and type scale, spacing,
radii, motion) in one file, and base styles that apply them: dark colour
scheme, typography, keyboard focus ring and reduced motion. A WCAG contrast
helper for tests. Token tests: exact token set, no duplicates, hex colours,
25 contrast cases, no raw colours outside the token file, no unknown token
names in any style sheet. Five browser tests of the applied theme.
TESTING.md and CHANGELOG updated. Exactly the ten planned files; the two
style sheets are identical to the plan. Deviations, both accepted: sorted
copies (`toSorted`) instead of in-place sorting, and the contrast helper
written without a non-null assertion.

Independent test run (planner, the pull request merged with `main` in a
clean checkout, Linux, Node 22.23.4, npm 10.9.9):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. No dependency changed.
- Frontend lint: passed. Format check: passed.
- Frontend unit tests: 46/46 passed (4 files). Type check: passed.
- Build: passed; script bundle unchanged at 219.76 kB plus one 2.00 kB style
  sheet.
- Browser tests: 9/9 passed.
- No skipped or focused tests and no suppressions.
- Gate checks: 11 planted defects all detected: low-contrast colour (exactly
  the 3 affected cases fail); misspelt token (unit and browser); raw hex
  colour; raw `rgb()` colour; duplicate token; styles not imported (4 browser
  tests fail); focus ring rule removed; reduced-motion rule removed; style
  sheet processing switched off in the unit runner; an extra token outside
  the agreed set; and a wrong coefficient in the contrast maths (caught by
  the helper's own tests).
- Repository checks: 9/9 passed.
- Backend: not touched and not re-run; no backend file has changed since its
  55/55 run on commit `0914ec5`.
- `git status` clean after the full run.

Unit tests: 55/55 passed (frontend 46, repository 9). Browser tests: 9/9
passed.
Type checking: passed (frontend). Lint and format: passed (frontend).
Build: passed (frontend).
Browser verification: passed (automated, headless Chromium, production build).

Overall applicable tests: 64/64 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the colours are provisional. While this task was being
built the owner supplied the Graphite theme; FND-023 replaces the colour
values and font stack. The page content sits in the top-left corner until
the layout task FND-014. Not run on Windows 11; first Windows run is FND-018.

Commit: `7e04f76` (squash merge of pull request #13).

Next task: FND-023 – Apply the owner's Graphite theme.

### FND-023 – Apply the owner's Graphite theme (2026-11-17)

TASK: FND-023 – Apply the owner's Graphite theme

Implementation: Complete (builder thread, pull request #14). The provisional
colours are replaced by the owner's Graphite theme under Graphite's own role
names: six surfaces (bar, canvas, panel, window, control, pressed), two line
colours, text, secondary and disabled text, the accent blue with its sky and
light variants, the selection colour and an accent gradient. The font stack
starts with Segoe UI Variable Text and Segoe UI. Status colours are
unchanged. Base styles use the canvas as page background, the sky blue for
links and the focus ring, and the selection colour for selected text. Exactly
the six planned files; `tokens.css`, `base.css` and the browser tests are
identical to the planner's trial; no deviations.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. No dependency changed.
- Frontend lint: passed. Format check: passed.
- Frontend unit tests: 69/69 passed (4 files), including 47 contrast cases
  and a check of the 16 Graphite tokens against the owner's values.
- Independent comparison by the planner of `tokens.css` with the owner's
  files in `docs/design/graphite-theme/`: 15 colours in the CSS reference and
  the on-accent colour in the JSON reference all match exactly.
- Type check: passed. Build: passed (script bundle 219.76 kB, style sheet
  2.37 kB).
- Browser tests: 9/9 passed. Screenshot of the built page checked by the
  planner.
- No old token name remains in `frontend/`; no skipped or focused tests and
  no suppressions.
- Gate checks: 8 planted defects all detected: one owner colour changed by
  one digit; secondary text too dark; an old token name (unit and browser);
  wrong focus ring colour (browser); font stack reordered (browser); page
  background on the wrong surface (browser); a status colour too dark; the
  on-accent colour darkened.
- Repository checks: 9/9 passed.
- Backend: not touched and not re-run; no backend file has changed since its
  55/55 run on commit `0914ec5`.
- `git status` clean after the full run.

Unit tests: 78/78 passed (frontend 69, repository 9). Browser tests: 9/9
passed.
Type checking: passed (frontend). Lint and format: passed (frontend).
Build: passed (frontend).
Browser verification: passed (automated, headless Chromium, production build).

Overall applicable tests: 87/87 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: white on the owner's accent blue measures 3.89:1, below
the 4.5:1 guideline for small text. The colours are used as supplied; the
pair is limited to bold button labels, the test records the 3:1 level, and
the owner has been told. The owner's control border colour is below 3:1
against the surfaces, which is not tested. Segoe UI is only present on
Windows; other systems fall back to their system font. Not run on Windows
11; first Windows run is FND-018.

Planning notes: the layout task was split into regions (FND-014), section
navigation (FND-025) and the current date (FND-026). The application icon
(FND-024) waits for the owner to choose a symbol from the published
mock-ups, so FND-014 goes first.

Commit: `15a9f59` (squash merge of pull request #14).

Next task: FND-014 – Application shell layout.

### FND-014 – Application shell layout (2026-11-17)

TASK: FND-014 – Application shell layout

Implementation: Complete (builder thread, pull request #15). The page now has
its final regions as named landmarks: a top bar with the name and tagline,
the sections panel on the left, the globe stage in the centre and the
details panel on the right, in the Graphite bar, panel and canvas colours.
Three layout size tokens were added. The shell is exactly one screen high,
so the page never scrolls; the panels scroll inside themselves. The sections
panel and the stage are empty until their own tasks. Exactly the ten planned
files; the component, its style sheet, `App.tsx`, the tokens and the token
test are identical to the planner's trial; no deviations.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. No dependency changed.
- Frontend lint: passed. Format check: passed.
- Frontend unit tests: 75/75 passed (5 files), 6 of them new component
  tests. Type check: passed.
- Build: passed (script bundle 220.44 kB, style sheet 3.62 kB).
- Browser tests: 16/16 passed, 7 of them new: at 1366×768 and at 1920×1080
  the regions fill the screen without overlapping, the stage is the largest
  region and the page does not scroll; and the regions use the Graphite
  surfaces.
- Existing tests unchanged apart from the one planned theme assertion; no
  skipped or focused tests and no suppressions.
- Gate checks: 9 planted defects all detected: page taller than the screen;
  details panel too wide for the stage to be the largest; missing landmark
  name; regions out of reading order; a raw colour on the stage; an unknown
  layout token; a fixed stage width; the details panel on the wrong surface;
  the tagline removed.
- Repository checks: 9/9 passed.
- Backend: not touched and not re-run; no backend file has changed since its
  55/55 run on commit `0914ec5`.
- `git status` clean after the full run.

Unit tests: 84/84 passed (frontend 75, repository 9). Browser tests: 16/16
passed.
Type checking: passed (frontend). Lint and format: passed (frontend).
Build: passed (frontend).
Browser verification: passed (automated, headless Chromium, production build).

Overall applicable tests: 100/100 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: desktop sizes only, from 1366×768; there is no
small-screen layout yet. The sections panel and the stage are empty until
FND-025 and Phase 3. An unknown layout token is caught by the unit test but
not by the browser tests, which still pass because the grid falls back to
automatic sizing. Not run on Windows 11; first Windows run is FND-018.

Planning notes: the owner rejected the first icon mock-ups and has chosen a
globe outline with MOTO along the top of the rim and SPHERE along the
bottom; the lettering font is still to be chosen, so FND-024 stays behind
the layout tasks. While trial-running FND-025 the planner found that a
browser test which presses a key straight after loading the page can lose
the key; the plan makes such tests wait for the page to be drawn first.

Commit: `0bfd7e1` (squash merge of pull request #15).

Next task: FND-025 – Section navigation.

### FND-025 – Section navigation (2026-11-17)

TASK: FND-025 – Section navigation

Implementation: Complete (builder thread, pull request #16). The sections
panel lists Explore, Events, Tracks, Championships, Riders, Teams, Results,
News and Statistics as buttons. One is current (Explore at start) and is
marked with `aria-current="page"` and the Graphite selection style; another
can be chosen by click, or with Tab and Enter or Space. The choice is state
in `App`. One development dependency was added,
`@testing-library/user-event` 14.6.12 (MIT), so that unit tests press keys
the way a user does. Exactly the planned files; the component, its style
sheet, the section list, `App.tsx`, `AppShell.tsx`, `package.json` and the
lock file are identical to the planner's trial; the tests differ from the
trial only in wording. No deviations.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. The lock file changed by
  the one package only.
- Frontend lint: passed. Format check: passed.
- Frontend unit tests: 86/86 passed (6 files), 11 of them new. Type check:
  passed.
- Build: passed (script bundle 221.14 kB, style sheet 4.33 kB).
- Browser tests: 21/21 passed, three runs in a row; 5 of them new (list and
  start state, click and selection style, keyboard and focus ring, hover,
  fit at 1366×768).
- No skipped or focused tests, no suppressions and no fixed sleeps.
- Gate checks: 12 planted defects all detected: two sections marked current;
  the choice ignored; two sections swapped; buttons taken out of the
  keyboard order; selection style removed (browser only); focus ring removed
  (browser only); list too tall for the panel (browser only); a raw colour
  (unit only); hover style removed (browser only); the list not rendered by
  the shell; every click reporting the first section; one section dropped.
- Repository checks: 9/9 passed.
- Backend: not touched and not re-run; no backend file has changed since its
  55/55 run on commit `0914ec5`.
- `git status` clean after the full run.

Unit tests: 95/95 passed (frontend 86, repository 9). Browser tests: 21/21
passed.
Type checking: passed (frontend). Lint and format: passed (frontend).
Build: passed (frontend).
Browser verification: passed (automated, headless Chromium, production build).

Overall applicable tests: 116/116 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: choosing a section changes only which item is marked
current; the panels and the globe do not react yet, and the choice is not
kept in the address bar, so a reload returns to Explore. The sections have
no icons (the icon style rules come with FND-024). Not run on Windows 11;
first Windows run is FND-018.

Commit: `385d15e` (squash merge of pull request #16).

Next task: FND-015 – Collapsible side panels.

### FND-015 – Collapsible side panels (2026-11-17)

TASK: FND-015 – Collapsible side panels

Implementation: Complete (builder thread, pull request #17). A Sections
button and a Details button in the top bar close and open the two side
panels. `aria-expanded` gives the state and `aria-controls` names the panel.
A closed panel stays in the page, hidden, and the globe stage takes its
room: the grid's side columns are now automatic and the panels carry their
own width. The choice is kept in session storage, so it survives a reload
and ends with the tab; unknown stored values and unusable storage both mean
open. A shared browser test helper, `tabTo`, reaches an element with the Tab
key. Exactly the planned files; the hook, the shell, its style sheet, the
test setup and the helper are identical to the planner's trial. One
deviation, accepted: the test for unusable storage also checks that storage
was tried.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. No dependency changed.
- Frontend lint: passed. Format check: passed.
- Frontend unit tests: 96/96 passed (6 files), 10 of them new. Type check:
  passed.
- Build: passed (script bundle 221.87 kB, style sheet 5.05 kB).
- Browser tests: 30/30 passed, three runs in a row; 9 of them new (start
  state, stage edges with each panel and both closed, keyboard, keyboard
  order, reload, new tab, button style). The FND-014 layout tests pass
  unmodified. Two existing keyboard tests were changed as planned, because
  the top bar buttons now come first in the Tab order.
- No skipped or focused tests, no suppressions and no fixed sleeps.
- Gate checks: 14 planted defects all detected: panel never hidden; state
  not announced; choice not stored; unguarded storage read; unguarded
  storage write; local storage instead of session storage (caught by the
  new-tab browser test); stage not growing (browser only); button naming
  the wrong panel; no style for the open state (browser only); both buttons
  driving one panel; one storage key for both panels; button out of the
  keyboard order; unknown stored value treated as closed; closed panel only
  made invisible instead of hidden.
- Repository checks: 9/9 passed.
- Backend: not touched and not re-run; no backend file has changed since its
  55/55 run on commit `0914ec5`.
- `git status` clean after the full run.

Unit tests: 105/105 passed (frontend 96, repository 9). Browser tests: 30/30
passed.
Type checking: passed (frontend). Lint and format: passed (frontend).
Build: passed (frontend).
Browser verification: passed (automated, headless Chromium, production
build), plus screenshots checked by the planner during the trial.

Overall applicable tests: 135/135 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the buttons are text only until the icon task; panels
open and close at once, without animation; the choice is per browser tab and
is not kept after the tab is closed. Not run on Windows 11; first Windows
run is FND-018.

Commit: `98bf3c3` (squash merge of pull request #17).

Next task: FND-026 – Current date in the top bar.

### FND-026 – Current date in the top bar (2026-11-17)

TASK: FND-026 – Current date in the top bar

Implementation: Complete (builder thread, pull request #18, two commits).
The top bar shows today's date, written out in the language of the user's
browser, for the day where the user is, in a `time` element whose `datetime`
attribute holds the day as `YYYY-MM-DD`. A hook sets one timer for the next
local midnight, worked out from the calendar, and also checks the day
whenever the page comes back into view, because a timer does not run while a
device sleeps. Only `Date` and `Intl.DateTimeFormat` are used. The shell has
a new `info` slot at the right-hand end of the top bar. Exactly the planned
files; the day functions, the hook, the component, the shell changes and the
browser tests are identical to the planner's trial.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. No dependency changed.
- Frontend lint: passed. Format check: passed.
- Frontend unit tests: 115/115 passed (8 files), 19 of them new; also
  115/115 with the machine's time zone set to America/Los_Angeles,
  Pacific/Kiritimati, Asia/Kolkata, Australia/Lord_Howe and Pacific/Apia.
  Type check: passed.
- Build: passed (script bundle 222.72 kB, style sheet 5.10 kB).
- Browser tests: 35/35 passed, three runs in a row; 5 of them new, with an
  emulated language, time zone and clock: British English in London,
  American English in Los Angeles (previous day), German in Tokyo (next
  day), the change at midnight without a reload, and the position and
  colour of the date.
- No skipped or focused tests, no suppressions and no fixed sleeps.
- Gate checks, first run: 14 of 15 planted defects detected. Not detected:
  removing a different function from the one that was added as the
  page-visibility listener, which leaves the real listener attached. The
  test only counted calls. The task was sent back; the builder changed that
  one test to compare the functions (second commit, no other change).
- Second run on the fixed pull request: lint, format check, unit tests
  (115/115, also in Los Angeles time), type check, build, browser tests
  (35/35), audit and repository checks all passed again, and the remaining
  defect is now detected. All 15: day taken from UTC; no timer; timer set
  once only; no check on coming back into view; timer not cleared; day
  formatted in the device's time zone; fixed language; date not rendered by
  the shell; date not pushed to the right-hand end (browser only); fixed
  24-hour timer; listener not removed; no `datetime` attribute; month off by
  one; wrong listener removed; short weekday name.
- Repository checks: 9/9 passed.
- Backend: not touched and not re-run; no backend file has changed since its
  55/55 run on commit `0914ec5`.
- `git status` clean after the full run.

Unit tests: 124/124 passed (frontend 115, repository 9). Browser tests: 35/35
passed.
Type checking: passed (frontend). Lint and format: passed (frontend).
Build: passed (frontend).
Browser verification: passed (automated, headless Chromium, production
build), plus a screenshot checked by the planner during the trial.

Overall applicable tests: 159/159 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the wording comes from the browser's own language data,
so punctuation can differ slightly between browsers (Chromium writes
"Tuesday, 17 November 2026" for British English). Two defects (day taken
from UTC, day formatted in the device's time zone) are caught by the browser
tests on any machine, but by the unit tests only on a machine that is not on
UTC. Not run on Windows 11; first Windows run is FND-018.

Planning note: the application icon (FND-024) is still waiting for the
owner's final choice of lettering, so the pipeline command line (FND-020)
goes next.

Commit: `5e782de` (squash merge of pull request #18).

Next task: FND-020 – Replace the API server with the pipeline command line.

### FND-020 – Replace the API server with the pipeline command line (2026-11-17)

TASK: FND-020 – Replace the API server with the pipeline command line

Implementation: Complete (builder thread, pull request #19). The FastAPI
application, the health endpoint, the server start-up, the `api_host` and
`api_port` settings, their tests and the `fastapi`, `uvicorn` and `httpx2`
dependencies are gone. `python -m motosphere` is now the data pipeline's
command line, in a new `motosphere.cli` package built on the standard
library's `argparse`, with one command, `version`. Arguments are parsed
before the settings are loaded, so `--help` works with broken settings;
results go to standard output and logs and errors to standard error. README,
TESTING.md, `.env.example` and the changelog follow. Exactly the planned
files; all source files, `pyproject.toml` and `uv.lock` are identical to the
planner's trial. One correction to the plan: regenerating the lock removed
13 packages, not 12 (the planner's count missed `annotated-doc`); 20 remain,
as expected.

Independent test run (planner, clean checkout of the pull request, Linux,
uv 0.11.32):

- `uv lock --check`: passed. `uv sync --locked`: passed.
- mypy: passed (14 source files). ruff check: passed. ruff format check:
  passed.
- Backend tests: 61/61 passed on Python 3.13.18 and 61/61 on Python 3.12.3,
  no warnings: 13 unit tests for the command line, 7 integration tests that
  run the real command as a separate process, 18 for the settings, 9 for the
  package (including that the server packages are not installed), 14 for
  logging.
- Real commands: `version` prints `motosphere 0.1.0` (exit 0); no command
  and an unknown command print the usage (exit 2); `--help` lists the
  command (exit 0); two invalid settings give one line starting
  `Configuration error:` (exit 2).
- The lock file holds 20 packages and none of fastapi, uvicorn, starlette,
  httpx or anyio. A search of `backend/`, README and TESTING.md for the old
  names finds only the tests that check they are gone.
- One suppression, as planned (`noqa: S603` on the fixed child-process
  call); no skipped tests.
- Gate checks: 13 of 14 planted defects detected: version on the wrong
  stream; wrong exit code for a configuration error; command made optional;
  settings loaded before the arguments; logging not set up; a server
  setting left behind; default program name; configuration error over
  several lines; version without the name; arguments ignored; a server
  dependency left behind; configuration error on standard output; the `api`
  package left behind. Not detected: the command line ignoring a command's
  exit code. That is a gap in the plan, not in the builder's work: the only
  command always returns 0, so no test could see it. The code is correct;
  the test is added by FND-021, whose command can fail.
- Repository checks: 9/9 passed.
- Frontend: not touched and not re-run; no frontend file has changed since
  its run on pull request #18 (115 unit, 35 browser).
- `git status` clean after the full run.

Unit and integration tests: 70/70 passed (backend 61, repository 9).
Type checking: passed (backend). Lint and format: passed (backend).
Build: not applicable (no frontend change).
Browser or integration verification: passed (the real command run as a
process by 7 tests and by hand).

Overall applicable tests: 70/70 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the exit-code gap described above, closed by FND-021. The
command line has only the `version` command. Exit code 2 is used both for
wrong arguments and for invalid settings. Not run on Windows 11; first
Windows run is FND-018.

Commit: `f80fe8d` (squash merge of pull request #19).

Next task: FND-021 – Data manifest export command.

### FND-021 – Data manifest export command (2026-11-17)

TASK: FND-021 – Data manifest export command

Implementation: Complete (builder thread, pull request #20, two commits).
`python -m motosphere export --out <directory>` writes `manifest.json`: the
data format version, the generation time in UTC to the second, the
application version and the number of published records of each kind, which
is an empty object because nothing is published yet. A new
`motosphere.publish` package holds the manifest model (immutable, no unknown
fields), a writer that puts a file in place in one step and leaves nothing
behind when it fails, and the export step. The JSON is deterministic: sorted
keys, a fixed layout, `\n` line breaks on every system and text outside
ASCII kept as it is. Exactly the planned files; the six source files are
identical to the planner's trial, and `pyproject.toml` and `uv.lock` are
unchanged. The builder wrote the tests from the plan's named list.

Independent test run (planner, clean checkout of the pull request, Linux,
uv 0.11.32):

- `uv lock --check`: passed (20 packages). `uv sync --locked`: passed.
- mypy: passed (23 source files). ruff check: passed. ruff format check:
  passed (23 files).
- Backend tests, first run: 114/114 passed on Python 3.13.18 and 114/114 on
  Python 3.12.3, no warnings.
- Real commands: export into a new directory two levels deep (exit 0; the
  directory holds only `manifest.json`, which ends with `}` and one `\n` and
  has no carriage return; the path is printed on standard output and one log
  line goes to standard error); export again a second later (the file is
  replaced and only `generated_at` differs); export into a path that is a
  file (`Export failed: cannot write to …: File exists`, exit 1, the file
  untouched); no `--out` and an empty `--out` (usage, exit 2); an invalid
  setting (one line starting `Configuration error:`, exit 2).
- One suppression, the existing one (`noqa: S603` on the fixed child-process
  call); no skipped tests.
- Gate checks, first run: 32 of 34 planted defects detected. Not detected:
  (a) writing the JSON with ASCII escapes instead of the text itself, and
  (b) letting the writer overwrite an existing temporary file. (a) was a gap
  in the plan, not in the builder's work: the plan asked for no such test.
  The task was sent back for one test, which the builder added as a second
  commit with no other change. (b) cannot be observed in practice, because
  the temporary file's name carries 64 random bits; no test was asked for.
- Second run on the fixed pull request: lock check, sync, mypy, ruff check,
  ruff format check, backend tests (115/115 on Python 3.13.18 and 115/115 on
  3.12.3, no warnings), repository checks and the real command all passed
  again; 33 of 34 planted defects detected, (a) now among them. The 33: not
  atomic (two ways); temporary file not removed; keys not sorted; local time
  instead of UTC; microseconds kept; unknown fields allowed; negative counts
  allowed; any record kind name allowed; model not immutable; format version
  zero allowed; empty application version allowed; directory not created;
  parent directories not created; export failure exits 0; error not caught;
  reason over several lines; path not printed; empty directory accepted;
  exit code ignored; no final line break; platform line endings; wrong
  application version; command not registered; no log line; ASCII escapes;
  wrong file name; invented counts; wrong format version; `--out` optional;
  generation time not the current time; error on standard output; file not
  flushed to disk.
- Tests per file: integration 10, command line 15, export command 9, export
  step 6, logging 14, manifest 26, package 9, writer 8, settings 18.
- Repository checks: 9/9 passed.
- Frontend: not touched and not re-run; no frontend file has changed since
  its run on pull request #18 (115 unit, 35 browser).
- `git status` clean after the full run.

Unit and integration tests: 124/124 passed (backend 115, repository 9).
Type checking: passed (backend). Lint and format: passed (backend).
Build: not applicable (no frontend change).
Browser or integration verification: passed (the real command run as a
process by 10 tests and by hand).

Overall applicable tests: 124/124 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the manifest has no file list or content hashes yet
(PUB-001) and there is no JSON Schema file (PUB-002). The frontend does not
read the manifest yet (FND-016). If the 64-bit random name of a temporary
file ever matched an existing file, the export would fail and remove that
file; this is not expected to happen. Not run on Windows 11; first Windows
run is FND-018.

Owner's note: the owner reported on 2026-11-17 that GitHub Pages is switched
on with GitHub Actions as its source, so the deployment task (FND-022) is no
longer waiting for the owner. Its first workflow run will confirm the
setting.

Commit: `b234233` (squash merge of pull request #20).

Next task: FND-024 – Application icon in the Sky Classic style.
