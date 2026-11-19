# MotoSphere – Progress

Completed work, the current task, test reports and next steps. A report is
added here only after the planner's independent test run. Numbers and commit
references are copied from real output, never estimated.

## Current state

- **Phase:** 2 – Data store and published data (Phase 1 – Foundation is complete)
- **Current task:** DAT-033 – A column without its check for empty text is named (`IN PROGRESS`, with a builder)
- **Tasks verified:** 59 of 248
- **Application state:** there is no server: the site is static files on GitHub Pages, at <https://bigdaddy284.github.io/MotoSphere/>. The data pipeline has a command line, `uv run python -m motosphere <command>`, with four commands so far: `version`; `export --out <directory>`, which writes the published data manifest (`manifest.json`; it holds no record counts yet because nothing is published); `migrate`, which brings the data store the settings name to the newest schema, makes it if it is not there, and says in one sentence what it did; and `schema`, which says in one sentence which schema that store has, whether it lacks migrations or that there is none, and changes nothing. The frontend starts with `npm run dev` and shows the application's layout (top bar with the data status and today's date, sections panel with the nine sections to choose from, globe area and details panel; the side panels can be closed to give the globe area the whole width, and on a screen under 900 pixels wide an open panel lies over the globe area instead of beside it, the top bar takes the lines it needs, and the page opens with both panels closed; on a touch screen the buttons and the sections are tall enough for a finger, and on a phone the layout is as tall as the part of the screen the browser really shows; no globe or data yet), and has its own unit tests (`npm test`) and browser tests (`npm run e2e`). The page uses the owner's Graphite theme and carries the MotoSphere icon. `npm run data` exports the published data into the frontend for local use, and the browser tests run against freshly exported data, read by the frontend's own manifest reader. The top bar shows when the published data was updated, or that it is unavailable: the first thing from the pipeline that reaches the user's screen. One command, `python scripts/check.py`, runs every check of the project, counts the tests (1064 today) and fails if any test was skipped. Its last gate checks the frontend's dependencies against published security advisories; an advisory can be accepted for at most 31 days in `frontend/audit-exceptions.json`, and none is today. GitHub runs the same command on Linux and on Windows for every pull request and every change to `main`, and publishes the site for every change to `main` that passes every gate (first published on 2026-11-17). One more command, `python scripts/live.py <site.tar> <address>`, says whether an address serves exactly the site that was built, and after every deployment a job runs it against the published site, so a broken or stale site turns the run red. `python scripts/tools.py` says whether a computer has the tools the project needs. There is no offline version (the owner's decision, 2026-11-19): MotoSphere is the published site. The data store is decided but not built: the pipeline names what it needs from SQLite (version 3.45.0 or newer and six features) and its tests check that on every machine; the pipeline knows where the store's file is from the setting `MOTOSPHERE_STORE_PATH`, and Git ignores that file; one function, `open_store`, opens it through SQLAlchemy with foreign keys enforced on every connection and failed work taken back as a whole, and one function, `unit_of_work`, gives a session whose work is kept as a whole or not at all; every backend test that needs a store gets a real one of its own from the fixture `store`; the store's schema changes only by numbered migrations, which `migrate` applies, each kept as a whole with the store's new version or not at all (the list is still empty); only a store of MotoSphere's is migrated: the first migration marks the file, and a file that has anything in it and not that mark is refused and left as it is; one function, `pending`, says which migrations a store lacks without writing anything, and refuses the same stores in the same words; `migrate` and `schema` are the only commands that use the store, and only `migrate` writes to it; there is a base for all models, which makes every table strict and names its constraints and indexes by one rule, and a test that holds every table to that; a time is stored as text in one form, in UTC with its offset written out, a time without an offset is refused, and a model's `datetime` column gets that type from the base; every model gets its key from the base, a whole number `id` that SQLite never gives twice, and the two times `created_at` and `updated_at`, which the store's code sets from the store's one clock; the test that holds every table to the rules names a table without that key or without those two times; a model can say of a column that its text must not be empty, and SQLite itself then refuses empty text in it, also text of nothing but white space; there is no model and no table yet (`DATABASE.md`). No globe yet.

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

### FND-024 – Application icon in the Sky Classic style (2026-11-17)

TASK: FND-024 – Application icon in the Sky Classic style

Implementation: Complete (builder thread, pull request #21). The owner's
approved icon and a small design for sizes under 64 pixels were added by the
planner beforehand (`docs/design/icon/`, with the rules for both). The
builder added the script `npm run icons`, which generates the served files
from the two designs with the browser the browser tests already use, and
committed its output: `favicon.svg` (the small design, byte for byte),
`favicon.ico` (16, 32 and 48 pixel images) and `apple-touch-icon.png`
(180 pixels, the full design on a `#1e1f22` background). The page links all
three. No new dependency. Exactly the planned files; the script, the
browser tests, the page, and all three generated files are identical, byte
for byte, to the planner's trial.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. `package-lock.json`
  unchanged.
- Frontend lint: passed. Format check: passed.
- Frontend unit tests: 115/115 passed (8 files; none new, none changed).
  Type check: passed.
- Build: passed; the built site holds the three icon files.
- Browser tests: 47/47 passed, three runs in a row; 13 of them new and one
  earlier icon test replaced. They check, against the production build: the
  page's three links; the content type of each file; that the served SVG is
  the small design; that neither design holds a script, an event handler, a
  link, an embedded image or an outside address; the colours of both
  designs; the directory and the images of the ICO file; the colours of
  chosen pixels of the 16, 32 and 48 pixel images and of the touch icon, as
  the browser decodes them.
- `npm run icons` run again: no file changed. SHA-256 of the generated
  files: `favicon.svg` `b9512f45…094be8` (718 bytes), `favicon.ico`
  `d641973b…fe0a48c` (6415 bytes), `apple-touch-icon.png`
  `967e6141…308a062d` (29806 bytes).
- No skipped or focused tests and no suppressions.
- Gate checks: 23 of 23 planted defects detected: no link to the fallback
  icon; no link to the touch icon; vector link to a missing file; fallback
  link without its size; served vector icon different from the design; the
  old placeholder left in place; a size missing from the ICO file; sizes in
  the wrong order; ICO images drawn from the full design; drawn at the wrong
  size; drawn on a solid background; touch icon drawn from the small design;
  with see-through corners; at the wrong size; on a black background; wrong
  bit depth in the ICO directory; wrong image offsets; and, in the designs, a
  script element, an event handler, an embedded outside image, an outside
  address in a paint, and colours off the palette (two ways).
- Visual check by the planner: the committed files at 16, 32, 48 and 180
  pixels, true size and enlarged, on dark and light backgrounds. The globe
  reads clearly at 32 and 48 pixels; at 16 pixels it is a sky-blue ring with
  a hint of the grid on the dark tile; at 180 pixels the lettering is
  readable.
- Repository checks: 9/9 passed.
- Backend: not touched and not re-run; no backend file has changed since its
  115/115 run on pull request #20.
- `git status` clean after the full run.

Unit tests: 124/124 passed (frontend 115, repository 9). Browser tests: 47/47
passed.
Type checking: passed (frontend). Lint and format: passed (frontend).
Build: passed (frontend).
Browser verification: passed (automated, headless Chromium, production
build), plus the planner's visual check.

Overall applicable tests: 171/171 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the owner approved the full design; the small design is
the planner's reduction of it, shown to the owner on the same day, and may
still change if the owner asks. The PNG and ICO images were drawn by
Chromium on Linux, and another system may draw slightly different bytes, so
the tests check sizes and pixels, not hashes. Which of the linked icons a
browser picks for its tab is the browser's choice and is not tested. There
is no web app manifest and no icon inside the page yet. Not run on
Windows 11; first Windows run is FND-018.

Commit: `a8cf14d` (squash merge of pull request #21).

Next task: FND-016 – Frontend data client and data status.

### PLAN-002 – The data client task split into three (2026-11-17)

"Frontend data client and data status" was too large to test thoroughly as
one task: it held a reader for untrusted data, the wiring that puts really
exported data in front of the development server and the browser tests, and
a new part of the page. It is now three tasks, in this order:

- FND-016 – Manifest reader in the frontend (fetch and check the manifest;
  unit tests only).
- FND-027 – Real published data in local development and browser tests.
- FND-028 – Data status in the top bar.

Phase 1 has 28 tasks and the project 220. No requirement was dropped.

Next task: FND-016 – Manifest reader in the frontend.

### FND-016 – Manifest reader in the frontend (2026-11-17)

TASK: FND-016 – Manifest reader in the frontend

Implementation: Complete (builder thread, pull request #22). One module,
`frontend/src/data/manifest.ts`, with no dependency and no React.
`parseManifest` checks a parsed JSON value field by field and returns the
manifest or the reason there is none; the format version is checked first
and unknown extra fields are ignored. `loadManifest` fetches
`data/manifest.json` under the application's base path with
`cache: 'no-cache'` and never throws: its result is the manifest,
`unavailable`, `malformed` or `unsupported`. Exactly the planned files; the
module and its tests are identical to the planner's trial. Nothing on the
page changed, and the built script bundle has the same size as before.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. No dependency changed.
- Frontend lint: passed. Format check: passed.
- Frontend unit tests: 177/177 passed (9 files), 62 of them new; also
  177/177 with the machine on Los Angeles time. Type check: passed.
- The 62 new tests: 48 for checking a manifest (among them the exact text
  the real export command wrote during the verification of FND-021, 13
  generation times and 12 kinds of counts that must be rejected), 3 for the
  manifest's address and 11 for fetching it with a stand-in fetch function.
- Build: passed (script bundle 222.72 kB, unchanged).
- Browser tests: 47/47 passed (none new).
- No skipped or focused tests and no suppressions.
- Gate checks: 33 of 33 planted defects detected: any format version
  accepted; format version checked last; zero allowed; a fraction allowed; a
  newer format reported as malformed; length of the generation time not
  checked; dates that do not exist allowed; unreadable generation time not
  caught; generation time of any type; empty application version;
  application version of any type; negative, fractional and inexact counts;
  record kind names not checked; counts not checked; lists accepted as
  objects; null accepted as an object; counts returned empty; fields mixed
  up; server errors not checked; server error reported as malformed; failed
  request not caught; unreadable answer reported as unavailable; unreadable
  answer not caught; answer not checked; no request for the current copy;
  signal not passed on; wrong address; base path without a final slash;
  base path ignored; given fetch function ignored; wrong supported version.
- Repository checks: 9/9 passed.
- Backend: not touched and not re-run; no backend file has changed since its
  115/115 run on pull request #20.
- `git status` clean after the full run.

Unit tests: 186/186 passed (frontend 177, repository 9). Browser tests: 47/47
passed.
Type checking: passed (frontend). Lint and format: passed (frontend).
Build: passed (frontend).
Browser or integration verification: not applicable yet; the module is not
used by the page. Its first run against a really served manifest is FND-027.

Overall applicable tests: 233/233 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the reader is written by hand to match the pipeline's
manifest model; the types generated from a JSON Schema (PUB-002) will
replace the hand-written checks or be tested against them. The one sample
of real output in the tests was copied from a real run and would not notice
a later change in the pipeline; FND-027 closes that by reading a freshly
exported manifest in the browser tests. A missing file on a server that
answers every address with the application's page is reported as
`malformed`, not `unavailable`. Not run on Windows 11; first Windows run is
FND-018.

Commit: `d42bfe4` (squash merge of pull request #22).

Next task: FND-027 – Real published data in local development and browser tests.

### FND-027 – Real published data in local development and browser tests (2026-11-17)

TASK: FND-027 – Real published data in local development and browser tests

Implementation: Complete (builder thread, pull request #23). `npm run data`
in `frontend/` runs the pipeline's export through uv, from the `backend/`
folder, and writes into `frontend/public/data/`, which Git and Prettier
ignore. The browser tests' web server runs it before the build, so the built
site under test carries data exported for that run; when the export fails,
the server does not start and no test runs. The Playwright configuration
records when the run started. Six new browser tests use the frontend's own
manifest reader against the served site. This is the first time the pipeline
and the frontend meet. Exactly the planned files; the tests, the
configuration and the ignore rules are identical to the planner's trial.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9, uv 0.11.32):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. No dependency changed;
  `package-lock.json` and `uv.lock` are untouched.
- Frontend lint: passed. Format check: passed, also with exported data in
  place.
- Frontend unit tests: 177/177 passed (9 files; none new). Type check:
  passed. Build: passed.
- Browser tests: 53/53 passed, three runs in a row; 6 of them new: the built
  site serves the manifest as JSON; the frontend's reader accepts it; it was
  generated no earlier than the start of the run; its application version is
  the one in `backend/pyproject.toml`; a page can fetch and read it; the data
  folder holds nothing but the manifest.
- Backend: lock check, sync, mypy (23 source files), ruff check and ruff
  format check passed; 115/115 tests passed.
- Development server, by hand: after `npm run data`, `npm run dev` served
  `/data/manifest.json` with status 200 as `application/json`.
- No skipped or focused tests and no suppressions. The exported data is not
  tracked and does not show in `git status`.
- Gate checks: 7 of 7 planted defects detected: no export before the build
  with old data left behind (only the freshness test fails, as intended); no
  export and no data; export into the wrong folder; a failing export (the
  server does not start and the run exits with an error); a failing export
  that is ignored; the start of the run not recorded; the exported data not
  ignored by Git (repository checks).
- Repository checks: 9/9 passed, with two sample paths added.
- `git status` clean after the full run.

Unit and integration tests: 301/301 passed (frontend 177, backend 115,
repository 9). Browser tests: 53/53 passed.
Type checking: passed (frontend and backend). Lint and format: passed
(frontend and backend).
Build: passed (frontend).
Browser or integration verification: passed (automated, headless Chromium,
production build with really exported data), plus the development server
checked by hand.

Overall applicable tests: 354/354 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the browser tests now need uv as well as Node.js, and the
continuous integration task (FND-018) must install both. `npm run dev` does
not export by itself; `npm run data` is run by hand. The Prettier ignore
entry for the data folder is a guard that no test exercises: today's
manifest happens to be formatted the way Prettier wants. The page does not
show the data yet (FND-028). Not run on Windows 11; first Windows run is
FND-018.

Commit: `f117964` (squash merge of pull request #23).

Next task: FND-028 – Data status in the top bar.

### PLAN-003 – A task added for expected page problems (2026-11-17)

While trial-running FND-028 the planner found one case that the browser
tests cannot cover yet. Every browser test fails when the page reports an
HTTP error or a failed request, by design. A manifest the server does not
have is answered with HTTP 404 on GitHub Pages, so a browser test of that
case would always fail, whatever the page showed. The local preview server
does not help: it answers a missing file with the page itself and status
200, which FND-028 does test.

Weakening the rule for every test would hide real faults, so one small task
was added after FND-028:

- FND-029 – Browser tests can expect a page problem (a single test names
  the problems it expects; then the data status is tested in the browser
  with HTTP 404 and with a failed request).

In FND-028 those two cases are covered by unit tests (the reader's own
tests from FND-016 and the component's). Phase 1 has 29 tasks and the
project 221. No requirement was dropped.

Next task: FND-028 – Data status in the top bar.

### FND-028 – Data status in the top bar (2026-11-17)

TASK: FND-028 – Data status in the top bar

Implementation: Complete (builder thread, pull request #24). A hook,
`useManifest`, loads the published manifest once when the application
starts; it stops the request when its component goes away and ignores a late
answer. A component, `DataStatus`, shows one line in the top bar before the
date: "Loading data…", then "Data updated" with the day the data was
generated (in the language of the browser, for the day where the user is, in
a `time` element that carries the exact moment), or "Data unavailable", or
"Reload the page to see the data" when the data is in a newer format than
the application reads. The line is an `output` element, so changes are
announced to assistive technology. Exactly the planned files; all twelve
code and test files are identical to the planner's trial.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9, uv 0.11.32):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. No dependency changed.
- Frontend lint: passed. Format check: passed.
- Frontend unit tests: 199/199 passed (12 files); 22 new: the hook 10, the
  date 5, the component 6, the application 1. Passed again, 199/199, with
  the time zone set to Asia/Tokyo.
- Type check: passed. Build: passed (script bundle 224.92 kB, style sheet
  5.15 kB).
- Browser tests: 62/62 passed, three runs in a row; 9 of them new: the real
  exported manifest for a British user in London; position between the
  tagline and the date, colour and size at 1366 pixels; the American way for
  the day in Los Angeles; the German way for the day in Tokyo; loading until
  the answer arrives; a web page as the answer; a damaged manifest; a newer
  format; the rest of the page still working when the data is unavailable.
- Looked at in a browser (production build with really exported data, 1366
  and 1100 pixels wide): "Data updated 17 November 2026" then "Tuesday, 17
  November 2026" on one line, in the quiet colour, before the Details
  button.
- No skipped or focused tests and no suppressions.
- Gate checks: 22 of 22 planted defects detected: the status never leaving
  loading; the reason for a failure lost; a loader that throws; the request
  not stopped; a late answer used; loading on every draw; a new loader
  ignored; the base path ignored; the signal not passed on; a newer format
  reported as unavailable; every failure asking for a reload; no `time`
  element; a wrong machine-readable moment; a fixed language; not announced;
  no space after "Data updated"; the day taken in UTC; a short month name;
  the status missing from the page; the date before the status; no room
  between the two; the information laid out as boxes that the top bar cuts
  off. Three of these are detected only by the browser tests (the two layout
  defects always; the UTC day on a machine whose own time zone is UTC).
- Repository checks: 9/9 passed.
- `git status` clean after the full run.
- Backend gates: not run again. No backend file changed since they passed
  for FND-027 (115/115), and the browser tests run the real export command.

Unit and integration tests: 208/208 passed (frontend 199, repository 9).
Browser tests: 62/62 passed.
Type checking: passed. Lint and format: passed.
Build: passed.
Browser or integration verification: passed (automated, headless Chromium,
production build with really exported data), plus the top bar looked at by
the planner.

Overall applicable tests: 270/270 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the status is loaded once per page load, with no retry
and no refresh while the page stays open. A manifest answered with HTTP 404
and a failed request are covered by unit tests only, because every browser
test fails on those by design; their browser tests come with FND-029. Not
run on Windows 11; first Windows run is FND-018.

Commit: `d45e008` (squash merge of pull request #24).

Next task: FND-029 – Browser tests can expect a page problem.

### FND-029 – Browser tests can expect a page problem (2026-11-17)

TASK: FND-029 – Browser tests can expect a page problem

Implementation: Complete (builder thread, pull request #25). Every browser
test still fails when the page logs an error or a warning, throws an
uncaught error, has a failed request or receives an HTTP error. A test about
a failure now names what it expects with `expectProblem(/pattern/)`; it
fails if an expected problem does not happen and still fails on any problem
it did not name. The judgement is one function with no browser in it,
`unexplained`. The rule has tests of its own for the first time, and the
data status is now tested in the browser with a manifest answered with HTTP
404 and with a failed request. The application itself did not change.
Exactly the planned files; the three test and fixture files are identical to
the planner's trial.

Independent test run (planner, clean checkout of the pull request, Linux,
Node 22.23.4, npm 10.9.9, uv 0.11.32):

- `npm ci`: passed. `npm audit`: 0 vulnerabilities. No dependency changed.
- Frontend lint: passed. Format check: passed. No lint suppression, and no
  skipped or focused test.
- Frontend unit tests: 199/199 passed (12 files; none new). Type check:
  passed. Build: passed.
- Browser tests: 80/80 passed, three runs in a row, none skipped; 18 new: 7
  of the judgement (nothing wrong, unexpected problems named, an expected
  problem accepted once or several times, a missing one named, another
  problem beside the expected one, every expected problem wanted); 9 of the
  rule in a real page (a healthy page, information in the console, a test
  that must fail on an unexpected problem, on a missing expected one and on
  a second problem, console errors and warnings counted, two expected
  problems); 2 of the data status ("Data unavailable" with HTTP 404 and with
  a failed request, the rest of the page still working).
- The three tests that must fail under the rule are marked `test.fail()`;
  Playwright reports them as passed, and as failed if the rule ever stops
  working (shown by the first planted defect).
- Gate checks: 14 of 14 planted defects detected: the rule switched off;
  only missing problems reported; only unexpected problems reported; a
  problem having to match every pattern; a pattern having to match every
  problem; anything allowed once something is expected; expectations not
  remembered; console warnings, console errors, uncaught errors, failed
  requests, HTTP 404 and all HTTP errors not recorded; console information
  recorded as a problem.
- Repository checks: 9/9 passed.
- `git status` clean after the full run.
- Backend gates: not run again. No backend file changed since they passed
  for FND-027 (115/115), and the browser tests run the real export command.

Unit and integration tests: 208/208 passed (frontend 199, repository 9).
Browser tests: 80/80 passed.
Type checking: passed. Lint and format: passed.
Build: passed.
Browser or integration verification: passed (automated, headless Chromium,
production build with really exported data).

Overall applicable tests: 288/288 passed (100%), all gates passed.

Status: PASSED – VERIFIED.

Known limitations: the two new data status tests name the manifest's
address at the root of the site; the GitHub Pages task (FND-022) serves the
site from a sub-path and must keep them passing there. A `test.fail()` test
passes on any failure of its body, not only on the rule's; the bodies are
kept to one or two harmless steps for that reason. Not run on Windows 11;
first Windows run is FND-018.

Commit: `5f4fde1` (squash merge of pull request #25).

Next task: FND-017 – Unified check runner.

### PLAN-004 – The check runner task split into three (2026-11-17)

"Unified check runner" held three things that can each be tested on their
own: a runner that executes the gates and reports pass or fail; reading test
counts out of five different tools and failing on skipped tests; and
bringing the Python files outside the pipeline under lint, format and type
checks, which needs its own configuration. It is now three tasks, in this
order:

- FND-017 – Unified check runner (run every gate, summary, exit code,
  `--list`, `--only`).
- FND-030 – Test counts and skipped tests in the check runner. Earlier
  reports say the check runner "must fail on skipped tests"; that
  requirement now belongs to this task.
- FND-031 – Lint and format checks for Python outside the pipeline. The
  ruff task (FND-003) says root-level Python joins the gate with the check
  runner; that now belongs to this task.

Continuous integration (FND-018) comes after all three, as before. Phase 1
has 31 tasks and the project 223. No requirement was dropped.

A lesson from the trial run, written into the FND-017 plan: one of the real
gates runs the runner's own tests, so those tests must never run the real
script in the real repository. The planner's first trial did, and a planted
defect made the runner start itself without end until it was stopped by
hand. The tests now run a copy of the script in a stand-in repository, where
the worst a defect can do is run gates that fail at once.

Next task: FND-017 – Unified check runner.

### FND-017 – Unified check runner (2026-11-17)

TASK: FND-017 – Unified check runner

Implementation: Complete (builder thread, pull request #26).
`python scripts/check.py` (standard library only, started from any folder)
runs the project's 16 gates in order from a clean checkout: repository
checks, the runner's own tests, the pipeline's lock check, install, type
check, lint, format check and tests, and the frontend's install, lint,
format check, type check, unit tests, build, browser tests and dependency
audit. Every gate runs even when an earlier one failed; a summary names each
gate as passed or failed with the time it took; the exit code is 0 only when
every gate passed. `--list` shows the gates and `--only` runs the named
ones. `TESTING.md` lists the gates and a test keeps the list and the script
the same. Exactly the planned files; all six are identical to the planner's
trial.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The runner's tests: 30/30 passed, and 30/30 again on Python 3.12: the gate
  table 7, running one gate 8, the whole run with stand-in gates 11, the
  script as a separate process 4.
- Repository checks: 9/9 passed, with two sample paths added.
- `python scripts/check.py --list`: 16 gates, nothing run.
- The full run, started from another folder: 16 of 16 gates passed, exit
  code 0. Inside it: repository checks 9/9, script tests 30/30, lock file up
  to date, mypy on 23 source files, ruff check and format check, backend
  tests 115/115, `npm ci`, frontend lint, format check and type check,
  frontend unit tests 199/199, build, browser tests 80/80 with none
  skipped, `npm audit` with 0 vulnerabilities.
- Real failures, by hand: one frontend test broken on purpose gave exit code
  1 with "1 of 2 gates passed. FAILED: Frontend unit tests." while the lint
  gate named with it still passed and ran first, in the order of the table;
  with no uv on the PATH the gate failed with "uv is not installed" and no
  Python error; an unknown gate name was refused with exit code 2.
- Gate checks: 30 of 30 planted defects detected, among them: an exit code
  that is always 0; a failing command counted as passed; stopping after the
  first failure; `--only` ignored or run in the order given; `--list`
  running the gates; a missing program or a command that cannot start not
  handled; the gate's folder or the given root ignored; the wrong Python;
  wrong counts, names, notes and marks in the summary; no announcement; the
  time not measured; the script's exit code not passed on; a gate renamed,
  removed, out of order, pointing at a script or folder that does not exist;
  and the document and the script drifting apart in either direction.
- `git status` clean after the full run.

Unit and integration tests: 353/353 passed (script tests 30, repository 9,
backend 115, frontend 199). Browser tests: 80/80 passed.
Type checking: passed (frontend and backend). Lint and format: passed
(frontend and backend).
Build: passed (frontend).
Browser or integration verification: passed (the full run executes the real
gates, browser tests included).

Overall applicable tests: 433/433 passed (100%), all 16 gates passed.

Status: PASSED – VERIFIED.

Known limitations: the runner reports pass or fail for each gate, not test
counts, and does not yet fail on skipped tests (FND-030). The Python files
outside the pipeline are not yet under lint, format or type gates (FND-031);
the new files were written to pass the pipeline's rules. The frontend
dependency audit needs the network. The runner's tests must never run the
real script in the real repository (see PLAN-004). Not run on Windows 11;
first Windows run is FND-018.

Commit: `0620e94` (squash merge of pull request #26).

Next task: FND-030 – Test counts and skipped tests in the check runner.

### FND-030 – Test counts and skipped tests in the check runner (2026-11-17)

TASK: FND-030 – Test counts and skipped tests in the check runner

Implementation: Complete (builder thread, pull request #27). The runner now
reads every gate's output while passing it on to the terminal unchanged. For
the five gates that run tests it reads the number of tests passed, failed
and skipped from the tool's own closing lines (`unittest`, pytest, Vitest,
Playwright), with colour codes removed, shows them on the gate's line and
adds a total for the run. A test gate fails when its command fails, when a
test was skipped, when no test ran or when the counts cannot be found. Every
test that neither passed nor failed counts as skipped. Exactly the planned
files; all four are identical to the planner's trial.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The runner's tests: 70/70 passed, and 70/70 again on Python 3.12: the gate
  table 8, reading counts 19, judging a gate 8, running one gate 13, the
  whole run 16, the script as a separate process 6.
- Repository checks: 9/9 passed.
- The full run, started from another folder: 16 of 16 gates passed, exit
  code 0, with the line "Tests: 473 passed, 0 failed, 0 skipped."
  (repository checks 9, script tests 70, backend tests 115, frontend unit
  tests 199, browser tests 80). The eleven other gates passed as before:
  lock file, both installs, both type checks, both lints, both format
  checks, the build and the dependency audit (0 vulnerabilities).
- Real skipped tests, by hand: one skipped test planted in each of the five
  tools made all five gates fail with "tests were skipped", each line still
  showing its real count and "1 skipped"; the total read "473 passed, 0
  failed, 5 skipped" and the exit code was 1.
- A real failing test, by hand: one frontend test broken on purpose gave
  "198 passed, 1 failed  exit code 1" and exit code 1.
- A console limited to ASCII did not disturb a real run of the frontend
  unit tests.
- Gate checks: 51 of 51 planted defects detected: the three new rules
  switched off one by one; a failing exit code forgiven; colours not
  removed; each tool's reader miscounting one kind of outcome (errors,
  unexpected successes, expected failures, tests left out, tests still to
  do, flaky, interrupted and not-run tests); the wrong report or the wrong
  line read; output not passed on, not kept, error output lost, output that
  is not UTF-8, output forced through the console's character set; counts or
  totals missing or wrong in the summary; a gate reading the wrong tool or
  none; and the defects kept from FND-017.
- A defect found by the tests during the planner's trial, before the plan
  was written: `unittest` outcomes of two words after a comma ("errors",
  "expected failures") were first read with a leading space and so not
  counted. The fix and its tests are part of the plan.
- `git status` clean after the full run.

Unit and integration tests: 393/393 passed (repository 9, script tests 70,
backend 115, frontend 199). Browser tests: 80/80 passed.
Type checking: passed (frontend and backend). Lint and format: passed
(frontend and backend).
Build: passed (frontend).
Browser or integration verification: passed (the full run executes the real
gates, browser tests included).

Overall applicable tests: 473/473 passed (100%), all 16 gates passed.

Status: PASSED – VERIFIED.

Known limitations: the readers depend on the closing lines of the four
tools; if a tool changes its wording, the gate fails with "the test counts
could not be read" rather than passing. The lines for flaky, interrupted and
not-run browser tests follow Playwright's wording and were not produced by a
real run. With output read through a pipe, the tools no longer colour their
output or draw progress bars. The Python files outside the pipeline are not
yet under lint, format or type gates (FND-031). Not run on Windows 11; first
Windows run is FND-018.

Commit: `94f0862` (squash merge of pull request #27).

Next task: FND-031 – Lint and format checks for Python outside the pipeline.

### FND-031 – Lint and format checks for Python outside the pipeline (2026-11-17)

TASK: FND-031 – Lint and format checks for Python outside the pipeline

Implementation: Complete (builder thread, pull request #28). Three new gates
in the check runner (`tools-types`, `tools-lint`, `tools-format`) hold the
Python files outside the pipeline, in `scripts/` and `tests/`, to the
pipeline's rules. They run from the repository root with the ruff and mypy
the pipeline has locked, so there is no new dependency. `ruff.toml` extends
the pipeline's rules with only the pytest-style rules off; `mypy.ini` is as
strict as the pipeline's configuration. The repository checks were brought
into line (return types, full generic types, two marked and explained
exemptions for the Git call, two lines rewrapped). Exactly the planned
files; all eight are identical to the planner's trial.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The runner's tests: 73/73 passed, and 73/73 again on Python 3.12 (the
  gate table 11, of which 3 new; the rest as before).
- Repository checks: 9/9 passed.
- `--list`: 19 gates, the three new ones after "Backend tests" and before
  "Frontend install".
- The full run, started from another folder: 19 of 19 gates passed, exit
  code 0, with the line "Tests: 476 passed, 0 failed, 0 skipped."
  (repository checks 9, script tests 73, backend tests 115, frontend unit
  tests 199, browser tests 80). The pipeline's type check still covered 23
  source files; the new one covered 3.
- Real planted defects through the real gates: 20 of 20 failed the matching
  gate with exit code 1. In `scripts/`: a print call, an undefined name, an
  unsorted import, a function without types, a wrong type, an ignore
  without a code, bad formatting, and a new file with an unused import. In
  `tests/repo/`: an unused variable, a bare assert, `eval`, a test without a
  return type, a bare generic type, bad formatting. In `tests/scripts/`: a
  Git call without its marked exemption, an exemption that is not needed, a
  wrong type, a call the runner does not have, bad formatting. And a new
  folder under `tests/` with an untyped function.
- Gate checks through the runner's tests: 18 of 18 planted defects detected:
  each new gate removed; the format gate rewriting instead of checking; a
  gate leaving the tests out; a gate using a tool from the PATH instead of
  the locked one; the type gate run in the pipeline's folder; the tests
  folder not covered; the gates moved before the pipeline's install; rules
  that are not the pipeline's; security rules switched off; a type check
  that is not strict or leaves the tests out; a gate missing from, or
  different in, `TESTING.md`; and a Python file in a folder no gate covers.
- Without uv on the PATH the three gates failed with "uv is not installed",
  exit code 1, and no Python error.
- `git status` clean after the full run.

Unit and integration tests: 396/396 passed (repository 9, script tests 73,
backend 115, frontend 199). Browser tests: 80/80 passed.
Type checking: passed (frontend, backend and the Python files outside the
pipeline). Lint and format: passed (the same three).
Build: passed (frontend).
Browser or integration verification: passed (the full run executes the real
gates, browser tests included).

Overall applicable tests: 476/476 passed (100%), all 19 gates passed.

Status: PASSED – VERIFIED.

Known limitations: the three gates use the pipeline's environment, so they
need uv, like the pipeline's own gates. The cover is by folder (`scripts/`
and `tests/`); a test fails if a Python file appears outside the pipeline
anywhere else. Not run on Windows 11; first Windows run is FND-018.

Commit: `df929bf` (squash merge of pull request #28).

Next task: FND-018 – Continuous integration.

### PLAN-005 – Continuous integration split into Linux and Windows (2026-11-17)

"Continuous integration" asked for a workflow that passes on Linux and on
Windows. The project has never run on Windows, so that run is expected to
find things to fix, and those fixes can be tested on their own. Setting the
workflow up is a different job. It is now two tasks, in this order:

- FND-018 – Continuous integration (the workflow, on Linux, with the rules
  that keep it safe).
- FND-032 – Continuous integration on Windows (a second job, and whatever
  the first Windows run exposes).

Earlier reports and task entries say "first Windows run is FND-018". That
run is now FND-032. Phase 1 has 32 tasks and the project 224. No requirement
was dropped.

Found while trying the task out, and made part of FND-018: the repository
check "source paths are not ignored" (FND-001) asked Git whether sample
paths are ignored, but Git never reports a file it already tracks as
ignored. For every sample file that exists, the check could not fail. One
option (`--no-index`) corrects it; with it, an ignore rule that hides a
tracked source folder fails the check.

What the planner could not try: the workflow itself, which only runs on
GitHub. Its first real run is on the builder's pull request. The planner
ran every gate locally with the variables GitHub sets and with Python 3.12
(19 of 19 gates, 489 tests), and read the actions' pinned commits and
inputs from their own repositories.

Next task: FND-018 – Continuous integration.

### FND-018 – Continuous integration (2026-11-17)

TASK: FND-018 – Continuous integration

Implementation: Complete (builder thread, pull request #29). A GitHub
Actions workflow, `.github/workflows/checks.yml`, runs for every pull
request and every change to `main`. Its one job, on a Linux machine,
installs Python 3.12, uv 0.11.32, Node.js 22 and the browser for the browser
tests, then runs `python scripts/check.py`. Thirteen new repository checks
hold every workflow to its rules: a token that can only read, no secret, no
credentials left by the checkout, every action pinned to a full commit with
its release beside it, only four known actions, no text from outside in a
command, and no step that can be skipped or allowed to fail. The existing
check that source paths are not ignored now also sees files Git already
tracks. Exactly the planned files; all six are identical to the planner's
trial, and the workflow went green on its first real run.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- Repository checks: 22/22 passed, and 22/22 again on Python 3.12 (9 as
  before, 6 that hold for every workflow, 7 on the checks workflow).
- The runner's tests: 73/73 passed.
- The full run, started from another folder: 19 of 19 gates passed, exit
  code 0, with the line "Tests: 489 passed, 0 failed, 0 skipped."
  (repository checks 22, script tests 73, backend tests 115, frontend unit
  tests 199, browser tests 80).
- Gate checks: 32 of 32 planted defects in the workflow detected: an action
  named by a tag, pinned without its release, pinned to a shortened commit,
  not on the list, or taken from a container image; `pull_request_target`;
  a secret handed to the job; no limit on the token, a token that may
  write, `write-all`, a job giving itself more rights; the title of a pull
  request in a command; a trigger missing or for the wrong branch; checkout
  credentials kept; only some gates run, a failing run forgiven, the runner
  not started; `continue-on-error`, a condition that skips the step, a
  shell that carries on after a failure; the browser installed without the
  locked version; an unnamed machine image; no time limit; a newer Python,
  another Node.js line, an unpinned uv; the workflow removed; a second
  workflow that breaks the rules; and the workflows folder ignored by Git.
- `git status` clean after the full run.

On GitHub (Ubuntu 24.04, Python 3.12.16), read by the planner from the
job logs, not taken from the builder's report:

- Run 44125941639, final commit of the pull request (`9a94766`): green.
  The log ends with "19 of 19 gates passed." and "Tests: 489 passed, 0
  failed, 0 skipped.", with the same counts per gate as the local run.
- Run 44125492578, a commit with a failing test planted on purpose
  (`afd07e3`): red. "FAILED  Frontend unit tests  198 passed, 1 failed  exit
  code 1", "18 of 19 gates passed. FAILED: Frontend unit tests." and "Tests:
  488 passed, 1 failed, 0 skipped." The commit was reverted before the
  merge, and neither commit is on `main`.
- Run 44124894488, the first commit (`b2a0dc9`): green.
- Run 44126685964, for `main` after the merge (`a743a64`): green, with the
  same closing lines.

Unit and integration tests: 409/409 passed (repository 22, script tests 73,
backend 115, frontend 199). Browser tests: 80/80 passed.
Type checking: passed (frontend, backend and the Python files outside the
pipeline). Lint and format: passed (the same three).
Build: passed (frontend).
Browser or integration verification: passed, locally and on GitHub's
machine (the full run executes the real gates, browser tests included).

Overall applicable tests: 489/489 passed (100%), all 19 gates passed.

Status: PASSED – VERIFIED.

Known limitations: Linux only; the first Windows run is FND-032. A red run
is shown on the pull request but does not block a merge: that is a
repository setting (a required check), which only the owner can switch on.
The repository checks read the workflow as text, so its layout has to stay
plain. Every change to `main` now starts a run, the planner's own record
commits included.

Commit: `a743a64` (squash merge of pull request #29).

Next task: FND-032 – Continuous integration on Windows.

### FND-032 – Continuous integration on Windows (2026-11-17)

TASK: FND-032 – Continuous integration on Windows

Implementation: Complete (builder thread, pull request #31). The checks
workflow now runs its one set of steps on two machines, Linux
(`ubuntu-24.04`) and Windows (`windows-2025`). Each gives its own result,
"All gates (Linux)" and "All gates (Windows)", and one failing does not
stop the other. The browser install is two steps of one command each,
because on Windows a step with several commands only fails on its last one;
a repository check forbids such steps. Exactly the planned files; all four
are identical to the planner's trial.

This is the first time the project ran on Windows. It passed every gate
without any change to the application, the tests or the check runner.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- Repository checks: 25/25 passed, and 25/25 again on Python 3.12 (16 on
  the workflows, 13 before).
- The full run, started from another folder: 19 of 19 gates passed, exit
  code 0, with the line "Tests: 492 passed, 0 failed, 0 skipped."
  (repository checks 25, script tests 73, backend tests 115, frontend unit
  tests 199, browser tests 80).
- Gate checks: 41 of 41 planted defects in the workflow detected: the 30
  kept from FND-018, and no Windows machine, no Linux machine, either
  image left as "latest", every job run on Linux whatever its name says,
  one machine failing stopping the other (set or left to the default), job
  names that cannot be told apart, a step with two commands, a third
  machine nobody decided on, and the frontend's dependencies not installed
  before the browser.
- `git status` clean after the full run.

On GitHub, read by the planner from the runs and job logs:

- Run 44132384609, final commit of the pull request (`e7307d9`): both jobs
  green. The Windows log (windows-2025, Python 3.12.10) ends with "19 of 19
  gates passed." and "Tests: 492 passed, 0 failed, 0 skipped." The Windows
  job takes about five minutes, most of it installing the browser; the
  Linux job about two.
- Run 44131523747, a commit with a test that fails on Windows only
  (`d704714`): the Windows job red, stopped by exit code 1 at the step that
  runs the gates; the Linux job green; both ran to the end. The commit was
  reverted before the merge, and neither commit is on `main`.
- Run 44133777708, for `main` after the merge (`9e0c57a`): both jobs green.
- The planner's own trial before the hand-over (pull request #30, closed
  without merging, runs 44127512048 and 44128755891) gave the same results:
  Windows passed at the first attempt, and with the planted test the
  Windows log read "18 of 19 gates passed. FAILED: Repository checks." and
  "Tests: 492 passed, 1 failed, 0 skipped."

Unit and integration tests: 412/412 passed (repository 25, script tests 73,
backend 115, frontend 199). Browser tests: 80/80 passed.
Type checking: passed (frontend, backend and the Python files outside the
pipeline). Lint and format: passed (the same three).
Build: passed (frontend).
Browser or integration verification: passed on Linux and on Windows (the
full run executes the real gates, browser tests included, on both).

Overall applicable tests: 492/492 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the Windows machine is GitHub's Windows Server 2025, not
the owner's Windows 11 PC; scripts for local use and a run on that PC are
FND-019. A red run is shown on the pull request but does not block a merge
(a repository setting). A correction to the plan: prove-it step 7 was said
to fail 2 tests; as worded it fails 1 ("every step runs one command"), and
the planner confirmed that. The defect is detected either way.

Commit: `9e0c57a` (squash merge of pull request #31).

Next task: FND-022 – GitHub Pages deployment.

### PLAN-006 – A security advisory, and the GitHub Pages task split in two (2026-11-17)

Not a development task: no application code changed.

**The advisory.** While trying out the GitHub Pages task, the planner's full
run failed in the last gate, the dependency audit, and nowhere else (18 of
19 gates). The cause is not in the repository: on the afternoon of
2026-11-17, after the last green run on `main` (`03c52e5`), an advisory was
published for `picomatch` (GHSA-fc5q-39xc-vjpf, high: a pattern that is slow
to match, "ReDoS"). A clean checkout of `main` fails the same way.

- Where it reaches the project: only through the build and test tools. vite
  8.3.8 and vitest 5.1.0 use tinyglobby 0.2.17, which uses fdir 6.5.0, which
  uses picomatch 4.0.7. `npm audit --omit=dev` reports 0 vulnerabilities, so
  nothing that is published to users is affected.
- What can be done about it today: nothing by updating. Every version is
  affected, including the newest (4.0.7). npm's only offer is to go back
  two major versions of vite and vitest.
- What it means for this project: the weakness is a slow match for certain
  patterns. The patterns these tools read are the ones written in this
  repository's own configuration, never anything from outside.

So the gate has been failing on `main` and on every pull request since that
afternoon, and would go on failing until a fix is published. Three ways
out were considered. Leaving build tools out of the audit, or only failing
above some severity, would switch the check off for everything else as
well, and a compromised build tool can change what is published. Going back
two major versions swaps a small known risk for old tools. The third is the
new task:

- **FND-033 – Dependency audit with recorded exceptions.** The audit still
  fails on every advisory, except one that is recorded in the repository
  with a reason and a review day at most 31 days away, and it fails again
  by itself when that day has passed or the exception is no longer needed.
  One exception is recorded, for this advisory, **to be reviewed by
  2026-12-17**. The decision to accept it for a month is the planner's,
  made for the owner and reported to the owner.

Until FND-033 is merged, the run for `main` is red in that one gate on both
machines, including the run for this commit. Nothing is merged on a red
run: FND-033's own pull request is the first place the gate is green again.

**The split.** "GitHub Pages deployment" held two jobs that can be tested
apart: making the application work from the path it will have on GitHub
Pages (`/MotoSphere/`), which is tested locally in the browser, and the
deployment workflow, which can only be tested on GitHub. It is now two
tasks, in this order:

- FND-022 – The application served from the site's path. The planner's
  trial is done: 87 browser tests (7 new), all gates but the audit passing.
- FND-034 – GitHub Pages deployment (the workflow and the live address).

Phase 1 has 34 tasks and the project 226. No requirement was dropped.
Earlier reports that name "FND-022 – GitHub Pages deployment" as the next
task mean these two.

What the planner tried for FND-033 (Linux, Python 3.13.18 and 3.12.3, Node
22.23.4, npm 10.9.9, uv 0.11.32), with exactly the files in the plan:

- Script tests: 122 of 122 passed, on both Pythons.
- Full run: 19 of 19 gates, 541 tests passed, 0 failed, 0 skipped.
- The real audit without the exception, with an expired one, with one for
  another advisory and without a lock file: failed each time, with the
  reason in plain words.
- 53 of 53 planted defects detected.
- Not tried: Windows. The builder's pull request runs there.

Next task: FND-033 – Dependency audit with recorded exceptions.

### FND-033 – Dependency audit with recorded exceptions (2026-11-17)

TASK: FND-033 – Dependency audit with recorded exceptions

Implementation: Complete (builder thread, pull request #32). A new script,
`python scripts/audit.py` (standard library only), runs `npm audit --json`
in `frontend/` and fails on every advisory it reports, unless an exception
is recorded in `frontend/audit-exceptions.json` with the advisory's id, its
package, a reason of at least 40 characters, the day it was accepted and a
review day at most 31 days later. It also fails on an exception that is
past its review day, no longer needed, about another package or dated in
the future, on a faulty exceptions file, and on an answer from npm that is
not a report. Every exception in use is printed on every run. The gate
`frontend-audit` runs the script; it keeps its key, name and place. One
exception is recorded: GHSA-fc5q-39xc-vjpf (picomatch, a build and test
tool, no fixed version published), accepted on 2026-11-17, review by
2026-12-17. Exactly the nine planned files; all are identical to the
planner's trial except one line of `ARCHITECTURE.md` that the plan commit
itself had changed.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  541 passed, 0 failed, 0 skipped." (repository checks 25, script tests
  122, backend tests 115, frontend unit tests 199, browser tests 80). The
  audit gate printed "npm audit reports 1 advisory.", the recorded
  exception with its reason and "review by 2026-12-17", and "Dependency
  audit passed."
- Script tests again on Python 3.12: 122/122 passed.
- The real audit with the exception taken out: the gate failed and named
  "picomatch: picomatch vulnerable to ReDoS through single-branch repeated
  extglobs (high)" with the advisory's address. With the dates moved back
  to October: it failed with "was due for review on 2026-10-31".
- Gate checks: 53 of 53 planted defects detected by the script tests,
  among them: an advisory without an exception passing, only high
  advisories counting, an exception that never runs out or runs out a day
  early or late, one that nothing needs being kept, one for another
  package or dated in the future, 32 days or for ever, a one-word reason,
  any text as an advisory id, unknown or missing fields, a broken or
  missing exceptions file counted as no exceptions, an answer that is not
  a report counted as clean, the build tools left out of the audit, exit
  code 0 with problems found or when the check could not be carried out,
  exceptions or their reasons not shown, the day fixed instead of today,
  the gate still running npm directly or missing, and the recorded
  exception without a reason, for a year or for everything.
- `git status` clean after the full run.

On GitHub, read by the planner from the runs and job logs:

- Run 44138689020, the pull request's commit (`81c47c2`): both jobs green.
  The Linux log (ubuntu-24.04) and the Windows log (windows-2025) each end
  with "19 of 19 gates passed." and "Tests: 541 passed, 0 failed, 0
  skipped." The audit gate took 0.7 s on Linux and 1.0 s on Windows.
- Run 44138077506, for `main` before the merge (`f543974`, the plan
  commit): both jobs red, "18 of 19 gates passed. FAILED: Frontend
  dependency audit." and "Tests: 492 passed, 0 failed, 0 skipped." That is
  the failure this task answers; nothing else failed.
- Run 44140586126, for `main` after the merge (`4962ae1`): green.

Unit and integration tests: 461/461 passed (repository 25, script tests
122, backend 115, frontend 199). Browser tests: 80/80 passed.
Type checking: passed (frontend, backend and the Python files outside the
pipeline). Lint and format: passed (the same three).
Build: passed (frontend).
Browser or integration verification: passed on Linux and on Windows (the
full run executes the real gates, the real audit included, on both).

Overall applicable tests: 541/541 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the exception for GHSA-fc5q-39xc-vjpf is a decision
with a date. From 2026-12-18 the audit gate fails until somebody has
looked again: a fixed picomatch installed and the exception removed, or
the exception renewed with its reason. The gate needs the npm registry: with
no network it fails ("could not be judged") and never passes unseen. The
pipeline's Python dependencies are not audited yet (PRF-005). The builder
reported no deviation.

Commit: `4962ae1` (squash merge of pull request #32).

Next task: FND-022 – The application served from the site's path.

### FND-022 – The application served from the site's path (2026-11-17)

TASK: FND-022 – The application served from the site's path

Implementation: Complete (builder thread, pull request #33). The
application is built, developed and tested under `/MotoSphere/`, the path
it will have on GitHub Pages. The path is written once, in
`frontend/site.ts`, and read by the build (`vite.config.ts`) and by the
browser tests (`playwright.config.ts`). The browser tests reach the site
through a base address that ends with the path and write every address
relative to it; no address that starts at the root of the server is left
in them. Seven new browser tests check the path's name, that the
application is served there, that everything the page loads comes from
under it, and that the icon files and the data manifest are not at the
root. The application code did not change. The unit test for the
manifest's address now gives the build another path. Exactly the 18
planned files; all are identical to the planner's trial.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  548 passed, 0 failed, 0 skipped." (repository checks 25, script tests
  122, backend tests 115, frontend unit tests 199, browser tests 87).
- The development server, by hand: `/MotoSphere/` answers 200, `/`
  redirects (302), `/favicon.svg` is not there (404), and
  `/MotoSphere/favicon.svg` and `/MotoSphere/data/manifest.json` answer
  200.
- Gate checks: 10 of 10 planted defects detected in the pull request, each
  run through the type check, the unit tests and the browser tests: the
  build without the site path (30 browser tests failed), the path as the
  root (7), in small letters (3), without its closing slash (20), the
  application asking the root for its data (1 unit test, 49 browser
  tests), the data's address written out as `/MotoSphere/` (2 unit tests,
  and no browser test, which is why the unit test uses another path), an
  icon link that skips the path (1), the page asking the root for a file
  (59), the browser tests looking at the root (20), and a path that is not
  text (type check). The planner's trial had detected an eleventh, the
  build using relative addresses (72 browser tests failed).
- `git status` clean after the full run.

On GitHub, read by the planner from the runs and job logs:

- Run 44143905377, the pull request's commit (`f8e2044`): both jobs green.
  The Linux log and the Windows log each end with "19 of 19 gates passed."
  and "Tests: 548 passed, 0 failed, 0 skipped.", with 87 browser tests on
  each.
- Run 44158699104, for `main` after the merge (`f1b9897`): green.

Unit and integration tests: 461/461 passed (repository 25, script tests
122, backend 115, frontend 199). Browser tests: 87/87 passed.
Type checking: passed (frontend, backend and the Python files outside the
pipeline). Lint and format: passed (the same three).
Build: passed (frontend).
Browser or integration verification: passed on Linux and on Windows (the
production build served under `/MotoSphere/`), and the development server
by hand on Linux.

Overall applicable tests: 548/548 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the site is not published yet (FND-034). The path is
the repository's name; if the site moves to a domain of its own,
`frontend/site.ts` is the one place to change. The builder reported no
deviation in the files; the hand-over message did not reach the planner,
who found the pull request on GitHub.

Commit: `f1b9897` (squash merge of pull request #33).

Next task: FND-034 – GitHub Pages deployment.

### PLAN-007 – Checking the published site becomes its own task (2026-11-17)

Not a development task: no application code changed.

"GitHub Pages deployment" asked for two things: that the deployment
succeeds, and that the live address shows the application and the data.
The first is a workflow and its safety rules. The second is a check that
has to run somewhere that can reach the live address, with tests of its
own. They are now two tasks, in this order:

- FND-034 – GitHub Pages deployment (two jobs after the gates: build the
  site, publish the site).
- FND-035 – Check the published site after each deployment (a job that
  looks at the live address and fails the run when the site is broken or
  stale).

Why the second cannot simply be the planner looking: the planner's
environment may not reach `bigdaddy284.github.io` (its network policy
refuses the address), so the planner cannot open the published site. A
check that runs on GitHub after every deployment is the stronger answer in
any case. Until FND-035 is verified, "published" means that GitHub accepted
the deployment, and the owner can open the address to see it.

Phase 1 has 35 tasks and the project 227. No requirement was dropped.

What the planner tried for FND-034:

- Locally (Linux, Python 3.13.18 and 3.12.3, Node 22.23.4, npm 10.9.9, uv
  0.11.32): repository checks 34 of 34 on both Pythons; the full run 19 of
  19 gates, 557 tests passed, 0 failed, 0 skipped; 82 of 82 planted defects
  in the workflow detected.
- On GitHub, in a trial pull request (#34, closed without merging): run
  44158864492 with exactly the planned files, the gates green on Linux and
  on Windows with 557 tests each and both publishing jobs skipped; run
  44159606743 with a temporary variant that builds the site on a pull
  request, "Build the site" green, handing over `index.html`, the three
  icon files, `data/manifest.json` and the script and style sheet (110 kB),
  and "Publish the site" still skipped.
- Not tried, because GitHub only lets `main` publish: the publishing
  itself. Its first real run is the run for `main` after FND-034 is merged.

A correction found on the way, made part of FND-034: a comment in the
workflow said every commit on `main` gets its result. Runs for `main` go
one at a time, and a run that is still waiting gives way to a newer one, so
a commit in the middle of a quick series may get none. That order is what
keeps an older commit from replacing a newer one on the site.

Next task: FND-034 – GitHub Pages deployment.

### FND-034 – GitHub Pages deployment (2026-11-17)

TASK: FND-034 – GitHub Pages deployment

Implementation: Complete (builder thread, pull request #35). The checks
workflow has two more jobs after the gates. "Build the site" waits for the
gates on both machines, exports the published data, builds the application
and hands `frontend/dist` to the next job; it can only read the repository.
"Publish the site" is the only job with the right to publish (`pages:
write`, `id-token: write`); it checks out nothing and runs no command of
its own, and goes through the `github-pages` environment. Both run for a
change to `main` only, never for a pull request. Two actions of GitHub's
own were added, each pinned to a commit. The repository checks hold the
workflow to all of this (34 tests, 25 before). Exactly the 6 planned
files; all are identical to the planner's trial.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  557 passed, 0 failed, 0 skipped." (repository checks 34, script tests
  122, backend tests 115, frontend unit tests 199, browser tests 87).
- The 34 repository checks again on Python 3.12.3: OK.
- Gate checks: 82 of 82 planted defects in the workflow detected by the
  repository checks, among them a pull request that publishes, a site
  built without waiting for the gates or when a gate failed, a build job
  that may publish, a publishing job that may change the repository, runs
  a command or skips the Pages environment, a site without its data, the
  whole repository published, an action named by a tag, a start by hand,
  and a fourth job.

On GitHub, read by the planner from the runs and job logs:

- Run 44160652237, the pull request's commit (`6563e24`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 557 passed, 0 failed, 0 skipped."; "Build the
  site" and "Publish the site" skipped, as they must be on a pull request.
- Run 44162680770, for `main` after the merge (`fbfe689`): all four jobs green.
  The gates on both machines end with the same two lines. "Build the
  site" took 17 seconds and handed over `index.html`, `favicon.ico`,
  `favicon.svg`, `apple-touch-icon.png`, `data/manifest.json` and one
  script and one style sheet under `assets/` (110550 bytes). "Publish the
  site" ran with a token that could read the run's metadata and write to
  Pages and nothing else; its log says "Created deployment for
  fbfe689f075f1f162783e4b26b39f6ec473bd72a" and "Reported success!". This
  was the first deployment, and it confirms that GitHub Pages is switched
  on for the repository with GitHub Actions as its source.

Unit and integration tests: 470/470 passed (repository 34, script tests
122, backend 115, frontend 199). Browser tests: 87/87 passed.
Type checking: passed (frontend, backend and the Python files outside the
pipeline). Lint and format: passed (the same three).
Build: passed (frontend, in the gates and again in "Build the site").
Browser or integration verification: the browser tests passed on Linux and
on Windows against the production build served under `/MotoSphere/`; the
deployment itself succeeded on GitHub.

Overall applicable tests: 557/557 passed (100%), all 19 gates passed, on
both machines; the deployment succeeded.

Status: PASSED – VERIFIED.

Known limitations: "published" means that GitHub Pages accepted the
deployment and reported success. Nobody has yet looked at
<https://bigdaddy284.github.io/MotoSphere/> on the project's behalf: the
planner's environment may not reach the address (tried again after the
deployment, refused by its network policy), and the deployment's log does
not print the address. The owner can open it; the automatic check of what
a visitor gets, after every deployment, is the next task. From now on
every change to `main` that passes every gate republishes the site, the
planner's bookkeeping commits included. The builder reported no deviation.

Commit: `fbfe689` (squash merge of pull request #35).

Next task: FND-035 – Check the published site after each deployment.

### PLAN-008 – The audit exception has to go; the site check in two tasks; phone screens (2026-11-18)

Not a development task: no application code changed.

Three changes to the task list.

1. A new task, first in line: FND-036 – Remove the audit exception that is
   no longer needed. On 2026-11-18 `npm audit` reports 0 advisories for the
   same lock file: the picomatch advisory (GHSA-fc5q-39xc-vjpf), accepted a
   day earlier with a review date of 2026-12-17, is no longer reported, and
   the npm registry's list of advisories for picomatch (4.0.7, still the
   latest version) no longer holds it. The planner could not read why (the
   advisory's page cannot be reached from the planning environment). The
   audit fails on an exception nothing reports any more, as it was built
   to, so the last gate now fails on `main` and on every pull request:
   "the exception for GHSA-fc5q-39xc-vjpf (picomatch) is no longer needed:
   remove it". Nothing in the repository changed; the last run for `main`
   (44164180581, at `c04a5db`, 2026-11-17) was green. The run for this
   planning commit is expected to be red in that one gate, and the site is
   not republished until FND-036 is merged.
2. Checking the published site is two tasks: FND-035 is the check itself,
   a script with its own tests against a stand-in server, and FND-037 is
   the job that runs it after each deployment. The first can be tested
   completely before it is merged; the second can only show itself on
   `main`.
3. Three tasks for phone screens, FND-038 to FND-040: the globe keeps the
   screen (side panels start closed and lie over the globe), the top bar
   fits, and full height with controls a finger can hit. The owner opened
   the published site on a phone on 2026-11-17: it loads, and it is not
   usable there. DESIGN.md asks for a responsive interface, and no task
   covered it. They come before the globe (Phase 3), so that the globe is
   built into a layout that already works on a phone.

What the planner tried for FND-036 (Linux, Python 3.13.18, Node 22.23.4,
npm 10.9.9, uv 0.11.32), with the list of exceptions empty and the
changelog changed:

- `python scripts/audit.py`: "npm audit reports 0 advisories." and
  "Dependency audit passed."
- The full run: 19 of 19 gates passed, "Tests: 557 passed, 0 failed, 0
  skipped."
- With the exception left in, the audit gate fails as quoted above; with
  the list itself gone the audit "could not be judged"; with the file
  unformatted the frontend's format check names it.

Order from here: FND-036, FND-035, FND-037, FND-038, FND-039, FND-040,
FND-019. Phase 1 has 40 tasks and the project 232. No requirement was
dropped.

Next task: FND-036 – Remove the audit exception that is no longer needed.

### FND-036 – Remove the audit exception that is no longer needed (2026-11-18)

TASK: FND-036 – Remove the audit exception that is no longer needed

Implementation: Complete (builder thread, pull request #37). The list of
exceptions in `frontend/audit-exceptions.json` is empty, and the changelog
says that the one exception was removed and why. Exactly the 2 planned
files; both are identical to the planner's trial. No test changed: none
depended on the exception.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  557 passed, 0 failed, 0 skipped." The audit gate printed "npm audit
  reports 0 advisories." and "Dependency audit passed."
- Three wrong results, each detected: with the exception left in, the
  audit gate fails with "the exception for GHSA-fc5q-39xc-vjpf (picomatch)
  is no longer needed: remove it"; with the list itself gone the audit
  "could not be judged"; with the file unformatted the frontend's format
  gate fails and names it.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44360270319, the pull request's commit (`f5655b1`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 557 passed, 0 failed, 0 skipped."; "Build the
  site" and "Publish the site" skipped.
- Run 44361547750, for `main` after the merge (`9663dfa`): all four jobs green,
  the gates with the same two closing lines on both machines, and the
  site republished ("Created deployment for
  9663dfa385b5aa0ec0b1ec6869468cb1957a12e4", "Reported success!").
- Run 44359969370, for the planning commit before it (`1a6c18f`): red in
  the audit gate, as expected; nothing was published from it.

Unit and integration tests: 470/470 passed (repository 34, script tests
122, backend 115, frontend 199). Browser tests: 87/87 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the browser tests passed on Linux and
on Windows; the deployment succeeded.

Overall applicable tests: 557/557 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: why the advisory is no longer reported is not known to
the planner (its page cannot be reached from the planning environment). If
it is reported again, the audit gate fails and names it, and the decision
about an exception is made again then. The builder reported no deviation
(Node 22.23.5 locally).

Commit: `9663dfa` (squash merge of pull request #37).

Next task: FND-035 – A check that compares the published site with the
site that was built.

### FND-035 – A check that compares the published site with the site that was built (2026-11-18)

TASK: FND-035 – A check that compares the published site with the site
that was built

Implementation: Complete (builder thread, pull request #38). A script,
`python scripts/live.py <site.tar> <address>`, with the Python standard
library only: it reads the built site from the tar the deployment hands
over, asks the address for every file in it and for the address itself,
and compares the status, the kind of content and every byte. It tries
again every 10 seconds for up to five minutes and sends one line per try
at once. Exactly the 4 planned files (the script, its 42 tests, TESTING.md
and CHANGELOG.md); all are identical to the planner's trial.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  599 passed, 0 failed, 0 skipped." Script tests: 164 (122 before, 42
  new).
- The 164 script tests also on Python 3.12, the version GitHub uses: all
  passed.
- Planted defects: 44 of 44 detected by the script's tests. Among them: a
  redirect is followed, an address without encryption is accepted for
  another computer, a path that leaves the site is accepted, the check
  never tries again, the check tries for ever, wrong files are listed but
  the exit code is 0, a check that could not be carried out passes, the
  lines about waiting are sent only at the end.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44365855699, the pull request's commit (`aece46c`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 599 passed, 0 failed, 0 skipped."; "Build the
  site" and "Publish the site" skipped. The script tests took 6.9 seconds
  on Windows.
- Run 44367232626, for `main` after the merge (`17d1a3e`): all four jobs
  green, the gates with the same two closing lines on both machines, and
  the site republished ("Created deployment for
  17d1a3e2b66c39e64b8752a0aeaa6ac52521ca25", "Reported success!").
- Before the plan, the planner's trial (pull request #36, closed without
  merging) ran the script on GitHub's machine against the real published
  site and a fresh build: 6 of 7 files identical with the right content
  types, and the data manifest different, as it had to be, because the
  trial's export was newer than the published one.

Unit and integration tests: 512/512 passed (repository 34, script tests
164, backend 115, frontend 199). Browser tests: 87/87 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the browser tests passed on Linux and
on Windows; the deployment succeeded.

Overall applicable tests: 599/599 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the script's tests use a stand-in server on the same
computer, and nothing runs the script after a deployment yet; that is the
next task. The planner's environment cannot reach the published address.
The builder reported every prove-it step of the plan and no deviation
(Node 22.23.5 locally).

Commit: `17d1a3e` (squash merge of pull request #38).

Next task: FND-037 – Run the check of the published site after each
deployment.

### FND-037 – Run the check of the published site after each deployment (2026-11-18)

TASK: FND-037 – Run the check of the published site after each deployment

Implementation: Complete (builder thread, pull request #40). The checks
workflow has a fourth job, "Check the published site", after "Publish the
site". It fetches the site this run built, exactly as it was handed to
GitHub Pages, and runs `python scripts/live.py built/artifact.tar
https://bigdaddy284.github.io/MotoSphere/`. It runs for a change to `main`
only and can only read. One more action of GitHub's own,
`actions/download-artifact` v8.0.2, is pinned to a commit. The repository
checks hold the job to all of this (40 checks, 34 before) and tie the
address to the site's path in `frontend/site.ts` and to the address the
README and TESTING.md give. Exactly the 6 planned files; all are identical
to the planner's trial.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  605 passed, 0 failed, 0 skipped." Repository checks: 40.
- Planted defects: 120 of 120 detected by the repository checks, the 82
  from FND-034 and 38 about the new job. Among the new ones: the check
  runs for a pull request, it runs even when publishing failed, it does
  not wait for the deployment, the job may publish, the site of another
  run is taken, a failing check is forgiven, someone else's site is
  checked, the site is checked without encryption, the site's path moves
  and the check still looks at the old place.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44387215403, the pull request's commit (`c9c4999`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 605 passed, 0 failed, 0 skipped."; "Build the
  site", "Publish the site" and "Check the published site" skipped.
- Run 44390229386, for `main` after the merge (`6f68e76`): all five jobs
  green. The gates end with the same two lines on both machines. "Publish
  the site" finished at 20:26:56 UTC. "Check the published site" then
  fetched the built site (the download's digest matched) and its log ends
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7
  of 7 files." at 20:27:02 UTC, at the first try.
- Before the plan, the planner's trial (pull request #39, closed without
  merging) ran the same six files on a pull request: both gates jobs
  green with 605 tests, the three jobs after the gates skipped.

Unit and integration tests: 518/518 passed (repository 40, script tests
164, backend 115, frontend 199). Browser tests: 87/87 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the browser tests passed on Linux and
on Windows; the deployment succeeded and the published site was compared
with the build from GitHub's machine: 7 of 7 files identical.

Overall applicable tests: 605/605 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the check passed at its first try, so its waiting and
trying again has not yet been needed on a real deployment; the script's own
tests cover it. The planner's environment still cannot reach the published
address; this job is how the planner knows what a visitor gets. The builder
reported every prove-it step of the plan and no deviation (Node 22.23.5
locally).

Commit: `6f68e76` (squash merge of pull request #40).

Next task: FND-038 – Phone screens: the globe keeps the screen.

### PLAN-009 – Phone screens in five tasks (2026-11-18)

Not a development task: no application code changed.

What the planner measured on `main` at 390 by 844 pixels, the size of a
common phone: the two side panels take 220 and 360 pixels, so the layout
is 580 pixels wide; the globe stage has a width of 0; the Details button
lies at 724 pixels, outside the screen, and cannot be reached. At 768
pixels (a tablet held upright) the stage has 188 pixels and the Details
button is cut off.

The planner then tried the first two phone tasks one after the other and
found that the first as PLAN-008 wrote it (the panels start closed, and
an open panel lies over the globe) is two things that need a third between
them. A button that cannot be reached cannot be tested honestly; the top
bar cannot fit while the layout is wider than the screen; and the layout
is wider than the screen until the panels stop taking width. So:

1. FND-038 – Narrow screens: an open panel lies over the globe. Where the
   panels are drawn, and nothing else. Style sheet only.
2. FND-039 – Narrow screens: the top bar fits. The buttons come into
   reach. Style sheet only.
3. FND-040 – Narrow screens: the panels start closed, one open at a time.
   The first task with script in it.
4. FND-041 – Touch screens: controls a finger can hit (was part of
   FND-040). The test browser can have a touch screen, so this can be
   measured.
5. FND-042 – Phones: the layout follows the visible height (was the other
   part of FND-040). The test browser has no bars that come and go, so
   the tests can only show that nothing changed there and that the style
   sheet asks for the right height. The rest is for the owner to see on a
   real phone, and will be recorded as that.

A narrow screen is one under 900 pixels wide: a phone, or a tablet held
upright. Below about 810 pixels the top bar's content does not fit on one
line even without the tagline, and at 900 pixels the stage still has 320
pixels between the panels. The smallest width tested is 320 pixels: old
small phones, and a desktop page enlarged to 400%.

Between the first task and the third the published site is no better on a
phone than today (both panels open over the stage); the three follow one
another at once.

What the planner tried for FND-038 (Linux, Python 3.13.18, Node 22.23.4,
npm 10.9.9, uv 0.11.32), on `main` at `6f68e76`:

- 26 new browser tests at 320, 360, 390, 768 and 899 pixels wide, and at
  900: all pass. The full run: 19 of 19 gates passed, "Tests: 631 passed,
  0 failed, 0 skipped." (browser tests 113).
- 11 of 11 planted defects in the style sheet detected.
- In trial pull request #41 (closed without merging), exactly the six
  files below ran on GitHub (run 44391577343): "All gates (Linux)" and
  "All gates (Windows)" green, each log ending `19 of 19 gates passed.`
  and `Tests: 631 passed, 0 failed, 0 skipped.` (browser tests 113 on both
  machines); "Build the site", "Publish the site" and "Check the published
  site" skipped.

For FND-039, on top of it: 28 more browser tests, all passing, and 16 of
16 planted defects detected. For FND-040, on top of both: 12 more unit
tests and 17 more browser tests, all passing, and 17 of 17 planted defects
detected by the unit tests. Each plan is written when the task before it
is verified.

Order from here: FND-038, FND-039, FND-040, FND-041, FND-042, FND-019.
Phase 1 has 42 tasks and the project 234. No requirement was dropped.

Next task: FND-038 – Narrow screens: an open panel lies over the globe.

### FND-038 – Narrow screens: an open panel lies over the globe (2026-11-18)

TASK: FND-038 – Narrow screens: an open panel lies over the globe

Implementation: Complete (builder thread, pull request #42). On a screen
under 900 pixels wide the layout has one column: the top bar and the globe
stage each have the whole width, and an open side panel is drawn over the
stage, the sections panel from the left edge and the details panel from
the right, as tall as the stage and never wider than the screen. One block
in the layout's style sheet; no component changed. Exactly the 6 planned
files (the style sheet, the new `frontend/e2e/narrow.spec.ts` with 26
tests, README.md, ARCHITECTURE.md, TESTING.md, CHANGELOG.md); all are
identical to the planner's trial. No existing test changed.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  631 passed, 0 failed, 0 skipped." Browser tests: 113 (87 before, 26
  new, at 320, 360, 390, 768 and 899 pixels wide and at 900).
- Planted defects: 11 of 11 detected by the browser tests: no narrow
  layout at all; the line drawn at 800 pixels, and at 900; the panels
  under the stage; a panel wider than the screen; the details panel at
  the left; the three columns kept; the old areas kept; the panels in
  areas of their own; a panel half as tall as the stage; a stage that
  scrolls sideways.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44393965951, the pull request's commit (`3dd2bfd`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 631 passed, 0 failed, 0 skipped.", with 113
  browser tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44396093299, for `main` after the merge (`4f2f611`): all five jobs
  green, the gates with the same two closing lines on both machines, the
  site republished, and the log of "Check the published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- Before the plan, the planner's trial (pull request #41, closed without
  merging) ran the same six files on both machines: 631 tests, green.

Unit and integration tests: 518/518 passed (repository 40, script tests
164, backend 115, frontend 199). Browser tests: 113/113 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the browser tests passed on Linux and
on Windows; the deployment succeeded and the published site is the site
that was built.

Overall applicable tests: 631/631 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: this task changes only where an open panel is drawn. On
a phone the published site is not yet better to use: both panels are open
when the page opens and cover the stage, and the top bar is still cut off,
with the Details button out of reach. The next two tasks deal with that.
The tests open the page as a visitor who closed a panel earlier in the
session, because that button cannot be reached yet. The builder reported
every prove-it step of the plan, test for test, and no deviation (Node
22.23.5 locally).

Commit: `4f2f611` (squash merge of pull request #42).

Next task: FND-039 – Narrow screens: the top bar fits.

### FND-039 – Narrow screens: the top bar fits (2026-11-18)

TASK: FND-039 – Narrow screens: the top bar fits

Implementation: Complete (builder thread, pull request #44). On a screen
under 900 pixels wide the top bar takes the lines it needs instead of one
fixed line: first the name between the two panel buttons, Sections at the
left edge and Details at the right, then the data status and the date,
each piece whole, sharing a line where both fit and taking one each where
they do not; the tagline is not shown there. The bar is 99 pixels tall at
phone widths and 78 at 768, and the globe stage starts under it. From 900
pixels on nothing changes. Rules added to the narrow-screen block of the
layout's style sheet; no component changed. Exactly the 5 planned files
(the style sheet, `frontend/e2e/narrow.spec.ts` with 28 more tests,
README.md, TESTING.md, CHANGELOG.md); all are identical to the planner's
trial. No existing test changed: the test file's diff only adds lines.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  659 passed, 0 failed, 0 skipped." Browser tests: 141 (113 before, 28
  new, at 320, 360, 390, 768 and 899 pixels wide and at 900).
- Planted defects: 16 of 16 detected by the browser tests: the bar kept
  to one line; room between the lines; the wide gaps kept on the first
  line; the bar kept to its fixed height; the tagline kept; the
  information before the Details button; the information on the first
  line; pieces of information that wrap; the information as one run of
  text; no room between two pieces on a line; no room under the last
  line; lines of information as tall as the bar; a piece on its own line
  indented; the Details button right after the name; and, on a wide
  screen, a bar that wraps and a bar without its tagline.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44399079910, the pull request's commit (`5efba93`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 659 passed, 0 failed, 0 skipped.", with 141
  browser tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44403512767, for `main` after the merge (`ad55c37`): all five jobs
  green, the gates with the same two closing lines on both machines, the
  site republished, and the log of "Check the published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- Before the plan, the planner's trial (pull request #43, closed without
  merging) ran the same five files on both machines: 659 tests, green. The
  text is drawn with another font on Windows, and the tests hold there.

Unit and integration tests: 518/518 passed (repository 40, script tests
164, backend 115, frontend 199). Browser tests: 141/141 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the browser tests passed on Linux and
on Windows; the deployment succeeded and the published site is the site
that was built.

Overall applicable tests: 659/659 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: on a phone both panels are still open when the page
opens and cover the stage; both buttons are now in reach to close them.
The next task makes them start closed. The builder reported every
prove-it step of the plan, test for test, and no deviation (Node 22.23.5
locally).

Commit: `ad55c37` (squash merge of pull request #44).

Next task: FND-040 – Narrow screens: the panels start closed, one open at a time.

### FND-040 – Narrow screens: the panels start closed, one open at a time (2026-11-18)

TASK: FND-040 – Narrow screens: the panels start closed, one open at a time

Implementation: Complete (builder thread, pull request #46). On a screen
under 900 pixels wide both side panels start closed, whatever the session
remembers, so the page opens with the globe stage in view. A button opens
its panel over the stage and closes it again; opening one panel closes the
other; nothing is remembered there and nothing is written to the session's
memory, so loading the page again shows the globe. When the width crosses
900 pixels the page follows at once, and what was chosen on the wide
screen is there again afterwards. From 900 pixels on nothing changes. New:
`frontend/src/layout/narrowScreen.ts` (what a narrow screen is, for the
script; a unit test fails when it differs from the style sheet's),
`useSidePanels.ts` (the two behaviours) and a stand-in for the width of
the screen for the unit tests. The markup of the layout is unchanged.
Exactly the 12 planned files; all are identical to the planner's trial.

Tests changed: three existing browser tests in
`frontend/e2e/narrow.spec.ts` opened the page as a visitor who had closed
a panel earlier in the session. That memory has no effect on a narrow
screen any more, so they open the panels with the buttons, as a visitor
does; one of them got a new name. No assertion in them was removed or
loosened. Every other existing test is unchanged.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  688 passed, 0 failed, 0 skipped." Frontend unit tests: 211 (199 before,
  12 new). Browser tests: 158 (141 before, 17 new).
- Planted defects: 17, in `narrowScreen.ts`, `useSidePanels.ts`,
  `AppShell.tsx` and the test setup. The unit tests detect 17 of 17. The
  browser tests detect 15 of the 16 that reach the browser; the sixteenth,
  a watcher of the screen that is never removed, cannot be seen in a
  browser and is detected by the unit test "watches the screen only while
  something on the page asks".
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44407441917, the pull request's commit (`4430454`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 688 passed, 0 failed, 0 skipped.", with 211
  frontend unit tests and 158 browser tests on both machines; "Build the
  site", "Publish the site" and "Check the published site" skipped.
- Run 44412568975, for `main` after the merge (`29c6dd2`): all five jobs
  green, the gates with the same two closing lines on both machines, the
  site republished, and the log of "Check the published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- Before the plan, the planner's trial (pull request #45, closed without
  merging) ran the same twelve files on both machines: 688 tests, green.

Unit and integration tests: 530/530 passed (repository 40, script tests
164, backend 115, frontend 211). Browser tests: 158/158 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the browser tests passed on Linux and
on Windows; the deployment succeeded and the published site is the site
that was built.

Overall applicable tests: 688/688 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: nothing closes a panel but its own button and the
other panel's button; what choosing a section does to the panel on a
phone is decided with the first section that shows something. The tests
run in a desktop browser at phone sizes: how the page behaves under a
finger on a real phone is for the owner to see on the published site. The
controls are not yet tall enough for a finger (FND-041), and the layout's
height does not yet follow a phone browser's own bars (FND-042). The
builder reported every prove-it step of the plan, test for test, and no
deviation (Node 22.23.5 locally).

Commit: `29c6dd2` (squash merge of pull request #46).

Next task: FND-041 – Touch screens: controls a finger can hit.

### FND-041 – Touch screens: controls a finger can hit (2026-11-18)

TASK: FND-041 – Touch screens: controls a finger can hit

Implementation: Complete (builder thread, pull request #48). Where the
main way of pointing is a finger (`@media (pointer: coarse)`: a phone or a
tablet, whatever its width), the two buttons in the top bar and the nine
sections are 44 pixels tall instead of 31 and 40: one new token,
`--size-touch-target`, and one small rule in each of the two style sheets.
There the buttons also stand in the middle of the bar's first line, not on
its line of text, so the top bar keeps its height with every font. With a
mouse nothing changes. Style sheets only: no component changed. Exactly
the 9 planned files; all are identical to the planner's trial. No existing
test changed.

What the trial on GitHub found: the planner's first design left the tall
buttons on the bar's line of text. All 696 tests passed locally. On
GitHub's machines, which draw the page with other fonts, the buttons
reached half a pixel out of the bar and made the bar on a phone half a
pixel taller: 3 of 696 tests failed on Linux and on Windows alike (run
44412617685). Where a button stands on a line of text depends on the font.
The buttons were centred instead, the tests now check their exact place,
and the corrected trial passed on both machines (pull request #47, run
44415567218) before the plan was written.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  696 passed, 0 failed, 0 skipped." Frontend unit tests: 211 (unchanged in
  number; the list of agreed tokens got one name). Browser tests: 166 (158
  before, 8 new).
- Planted defects: 10 in the three style sheets, 10 of 10 detected by the
  browser tests, and the token removed, detected by 2 unit tests.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44417318012, the pull request's commit (`edf7300`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 696 passed, 0 failed, 0 skipped.", with 211
  frontend unit tests and 166 browser tests on both machines; "Build the
  site", "Publish the site" and "Check the published site" skipped.
- Run 44418757631, for `main` after the merge (`93150ef`): all five jobs
  green, the gates with the same two closing lines on both machines, the
  site republished, and the log of "Check the published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 530/530 passed (repository 40, script tests
164, backend 115, frontend 211). Browser tests: 166/166 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the browser tests passed on Linux and
on Windows, with and without a touch screen; the deployment succeeded and
the published site is the site that was built.

Overall applicable tests: 696/696 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the tests run in a desktop browser that is told it has a
touch screen: whether a finger hits the controls comfortably on a real phone
is for the owner to see on the published site. A laptop with a touch screen
and a mouse keeps the mouse sizes, because its main way of pointing is the
mouse. The layout's height does not yet follow a phone browser's own bars
(FND-042). The builder reported every prove-it step of the plan, test for
test, and no deviation (Node 22.23.5 locally).

Commit: `93150ef` (squash merge of pull request #48).

Next task: FND-042 – Phones: the layout follows the visible height.

### FND-042 – Phones: the layout follows the visible height (2026-11-18)

TASK: FND-042 – Phones: the layout follows the visible height

Implementation: Complete (builder thread, pull request #50). The
layout's height and the page's least height are `100dvh` instead of
`100vh`: the part of the screen the browser really shows, which follows a
phone browser's own bars as they come and go. There is no `100vh` line as
a fallback: every browser the build is made for knows `dvh`, and the build
removes such a line anyway. A new unit test rejects `vh` in any style
sheet under `frontend/src`. Style sheets only: no component changed.
Exactly the 8 planned files; all are identical to the planner's trial. No
existing test changed. This is the last of the five tasks for narrow
screens (PLAN-009).

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  702 passed, 0 failed, 0 skipped." Frontend unit tests: 212 (211 before,
  1 new). Browser tests: 171 (166 before, 5 new).
- The built style sheet read: `height:100dvh` twice, no `vh` height.
- Planted defects: 10 in the two style sheets, 10 of 10 detected by the
  browser tests; the 3 that bring `vh` back are also detected by the new
  unit test.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44420719471, the pull request's commit (`bc18774`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 702 passed, 0 failed, 0 skipped.", with 212
  frontend unit tests and 171 browser tests on both machines; "Build the
  site", "Publish the site" and "Check the published site" skipped.
- Run 44423224253, for `main` after the merge (`608e741`): all five jobs
  green, the gates with the same two closing lines on both machines, the
  site republished, and the log of "Check the published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- Before the plan, the planner's trial (pull request #49, closed without
  merging) ran the same eight files on both machines: 702 tests, green.

Unit and integration tests: 531/531 passed (repository 40, script tests
164, backend 115, frontend 212). Browser tests: 171/171 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the browser tests passed on Linux and
on Windows; the deployment succeeded and the published site is the site
that was built.

Overall applicable tests: 702/702 passed (100%), all 19 gates passed, on
both machines.

Status: BLOCKED – EXTERNAL DEPENDENCY. Acceptance criteria 1 to 5 are
verified. Criterion 6, the effect on a real phone, needs the owner's phone
and was asked for on 2026-11-18; the task is not counted as verified until
the owner's answer is recorded.

Known limitations: the test browser is a desktop browser. It has no bars
that come and go, and `100dvh` and `100vh` are the same number in it. The
tests show that the style sheets ask for the right height, that the layout
is exactly as tall as the screen at every tested size, and that nothing else
changed. That the lower edge of the layout stays in view on a real phone
while its browser shows its bars is for the owner to confirm on the
published site (acceptance criterion 6); it is recorded as the owner's
confirmation when given, not as a test result. The builder reported every
prove-it step of the plan, test for test, and no deviation (Node 22.23.5
locally).

Commit: `608e741` (squash merge of pull request #50).

Next task: FND-019 – Windows scripts for local use.

### FND-042 – Phones: the layout follows the visible height: the owner's check on a real phone (2026-11-18)

TASK: FND-042 – Phones: the layout follows the visible height

The task was recorded above as BLOCKED – EXTERNAL DEPENDENCY: every test
had passed (702/702, all 19 gates, on both machines), and acceptance
criterion 6, the effect on a real phone, needed the owner's phone.

The owner was asked on 2026-11-18 to open the published site on a phone
and say whether the bottom of the page stays in view while the browser's
own bars are showing, and whether the buttons are easy to hit. The owner
answered the same day, at 23:57 UK time: "Test on mobile looks good".

This is the owner's confirmation, not a test result. No test ran for it and
no file of the application changed. With it every acceptance criterion of
the task is met.

Overall applicable tests: 702/702 passed (100%), unchanged.

Status: PASSED – VERIFIED.

Known limitations: the confirmation is for the owner's phone and browser on
that day; other phones were not looked at.

Commit: `608e741` (the task's commit, unchanged).

Next task: FND-019 – Windows scripts for local use.

### PLAN-010 – Starting MotoSphere on a Windows 11 PC, in four tasks (2026-11-19)

Not a development task: no application code changed.

FND-019, "Windows scripts for local use", was one task: scripts to set up
the tools, run all checks, export the data, open the application and stop
it again, accepted on a real Windows 11 machine. That is four things, and
only the last of them needs that machine. `ARCHITECTURE.md` §12 already
says how they divide: what a user starts on Windows is a thin command, and
the work behind it is Python, written once and tested on Linux and on
GitHub's Windows machine by the gates. So:

1. FND-019 – Local use: a check of the tools a computer needs. One
   command says which of Python, Git, uv, Node.js and npm a computer has,
   and where to get what is missing. It only looks.
2. FND-043 – Local use: the built site served on this computer. The
   published site has no server of its own to start, so local use needs a
   small one, for this computer only, that serves exactly what GitHub
   Pages would. `scripts/live.py` can judge that.
3. FND-044 – Local use: one command builds the site and opens it, and
   Ctrl+C stops it with nothing left running.
4. FND-045 – Local use: the commands for Windows 11, with the README's
   Windows section. It keeps the old task's acceptance: a clean checkout
   on a real Windows 11 machine reaches the application by following the
   README only. It stays BLOCKED – EXTERNAL DEPENDENCY until the owner's
   PC has been reached.

Two things are decided in later plans, after their trials, and not here:
whether the Windows commands are PowerShell files, as §12 says today, or
command files (Windows 11 as installed refuses to run PowerShell files);
and whether FND-044 is small enough as one task.

What changed against the old wording: the scripts do not install Python,
Git, uv or Node.js for the user. The check names what is missing and where
to get it, and the README will give Windows's own commands for it. The
project's own packages are installed by the start command. Running all
checks is `python scripts/check.py`, which exists and runs on Windows
since FND-032.

What the planner tried for FND-019 (Linux, Python 3.13.18, Node 22.23.4,
npm 10.9.9, uv 0.11.32), on `main` at `c0c693a`:

- 42 new script tests, all passing. The full run: 19 of 19 gates passed,
  "Tests: 744 passed, 0 failed, 0 skipped." (script tests 206).
- The script on this computer: five tools found, "5 of 5 tools are
  ready.", exit code 0. With Python 3.11: one plain sentence, exit code 1.
- 26 of 26 planted defects detected. The first try detected 25 (a lone
  number was read as a version), and one test was added. One more test
  was rewritten because it could not fail where "python" on the search
  path is the Python that runs the tests.
- In trial pull request #51 (closed without merging), exactly these six
  files ran on GitHub (run 44426691356): "All gates (Linux)" and
  "All gates (Windows)" green, each log ending `19 of 19 gates passed.`
  and `Tests: 744 passed, 0 failed, 0 skipped.`, with 206 script tests on
  both machines; "Build the site", "Publish the site" and "Check the
  published site" skipped. One of the tests runs the script for real and
  passes only when all five tools are ready, so on the Windows machine the
  script found npm, which is a command file there, and got its version.

Order from here: FND-019, FND-043, FND-044, FND-045. Phase 1 has 45 tasks
and the project 237. No requirement was dropped.

Next task: FND-019 – Local use: a check of the tools a computer needs.

### FND-019 – Local use: a check of the tools a computer needs (2026-11-19)

TASK: FND-019 – Local use: a check of the tools a computer needs

Implementation: Complete (builder thread, pull request #52). A script,
`python scripts/tools.py`, with the Python standard library only. It looks
at Python, Git, uv, Node.js and npm, asks each for its version, and writes
one line for each: found, missing, too old or broken, with the place to
get it. The least versions of Python and Node.js are read from
`backend/pyproject.toml` and `frontend/package.json`. A Python older than
3.12 is told so in one plain sentence. The script installs nothing and is
not a gate. Exactly the 6 planned files; all are identical to the
planner's trial. No existing test changed.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  744 passed, 0 failed, 0 skipped." Script tests: 206 (164 before, 42
  new).
- The script itself: five tools found, "5 of 5 tools are ready.", exit
  code 0. Started with Python 3.11: "MotoSphere needs Python 3.12 or
  newer, and this is Python 3.11." with the place to get a newer one, exit
  code 1.
- Planted defects: 26 in the script, 26 of 26 detected by the new tests,
  the plan's twelve prove-it steps among them.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44428583058, the pull request's commit (`e9650fc`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 744 passed, 0 failed, 0 skipped.", with 206
  script tests on both machines; "Build the site", "Publish the site" and
  "Check the published site" skipped.
- Run 44429659797, for `main` after the merge (`fb8b6ed`), first
  attempt: "All gates (Linux)" green with the same two closing lines. "All
  gates (Windows)" FAILED: "18 of 19 gates passed. FAILED: Browser tests."
  and "Tests: 743 passed, 1 failed, 0 skipped." One browser test, "layout
  at 1920×1080 › the globe stage is the largest region", could not open
  the page: "page.goto: net::ERR_NO_BUFFER_SPACE at
  http://127.0.0.1:4173/MotoSphere/". The other 170 browser tests on that
  machine passed, before and after it. The three jobs after the gates were
  skipped, so nothing was published from that attempt.
- The same run, second attempt (the failed job run once more, nothing
  changed): all five jobs green, "All gates (Windows)" ending "19 of 19
  gates passed." and "Tests: 744 passed, 0 failed, 0 skipped.", the site
  republished, and the log of "Check the published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

What the failed attempt was: Windows's message for a machine that has no
room left for one more network connection, here between the test browser
and the test server on the same machine. The task changed no file that the
browser tests read (two Python files and four documents). The same
frontend files passed on GitHub's Windows machines in four other runs that
night: the planner's trial (44425486127, 44426691356), the pull request's
run (44428583058) and the second attempt. The planner could not find out
more: the machine is gone when the job ends. It is recorded as a failed
attempt, not explained away. The browser tests are not given a second try
(`retries: 0` stays), so if it happens again it will be seen again, and
then it becomes a task of its own.

Unit and integration tests: 573/573 passed (repository 40, script tests
206, backend 115, frontend 212). Browser tests: 171/171 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the script was run for real on Linux
by the planner and, by its tests, on GitHub's Linux and Windows machines;
the deployment succeeded and the published site is the site that was
built.

Overall applicable tests: 744/744 passed (100%), all 19 gates passed, on
both machines; for `main` on the Windows machine at the second attempt.

Status: PASSED – VERIFIED.

Known limitations: the script was not run on a Windows 11 PC, only on
GitHub's Windows machine (Windows Server 2025), and after the owner's
decision below no task asks for that. It looks at the five tools by name and
at no others; the browser the browser tests need is not among them. The
builder reported every prove-it step of the plan with the tests the plan
names, and no deviation (Node 22.23.5 locally).

Commit: `fb8b6ed` (squash merge of pull request #52).

Next task: see PLAN-011 below.

### PLAN-011 – No offline version: Phase 1 ends here (2026-11-19)

Not a development task: no application code changed.

PLAN-010 planned four tasks for starting MotoSphere on the owner's Windows
11 PC. While the first was being built, the owner asked why anything had
to start from that PC, since the site is hosted on GitHub. It does not
have to: the four tasks were a second way to use MotoSphere, a private
copy on a PC without GitHub, read by the planner from the rule that the
application must be easy to start on Windows 11 and from the old FND-019.
The owner was asked whether to keep them, first chose to, and a moment
later wrote: "actually dont build the offline version".

What follows from it:

- FND-043, FND-044 and FND-045 are taken out of the task list. None had
  started; no code, test or plan of theirs exists.
- FND-019 was finished when the decision came (its pull request was open
  and green). The owner was told it would be merged and answered with a
  thumbs-up. It is
  useful without an offline version: it tells anyone working on the
  project which tools their computer lacks.
- `ARCHITECTURE.md` §12 is rewritten in this commit, by the planner: on
  Windows 11 MotoSphere is the published site in a browser; there are no
  PowerShell scripts and no local start command; the commands for working
  on the project are the same on Windows and Linux, and GitHub runs every
  gate on both. The 40 repository checks and 206 script tests pass with
  the rewritten document.
- The owner's PC is not needed for any check.

Phase 1 has 42 tasks again, all 42 verified, and the project 234. The
foundation is complete: a published site on GitHub Pages with the
application's layout, usable on a phone, a data pipeline that publishes a
manifest, one command for every check, and GitHub running it on Linux and
Windows for every change.

Next: Phase 2, the data store and the published data. Its 28 tasks are
named in the roadmap and are written out in full entries, with acceptance
criteria and required tests, before the first of them starts.

Next task: DAT-001 – Data store research and decision record.

### PLAN-012 – Phase 2 written out in full (2026-11-19)

Not a development task: no application code changed.

Phase 2, the data store and the published data, was a list of 28 named
tasks in the roadmap. It now has a full entry for each in `TASKS.md`:
objective, description, acceptance criteria and required tests. The order
and the numbers are the roadmap's; several names were made plainer.
Nothing was added and nothing dropped: 20 tasks for the store (DAT-001 to
DAT-020) and 8 for the published data (PUB-001 to PUB-008).

What the entries settle, beyond the roadmap's names:

- Every task that touches the store is tested against a real SQLite file,
  on Linux and on Windows. The store is never replaced by a mock.
- The store's package is `motosphere.db`, as `ARCHITECTURE.md` §2 names it.
- Sources come before countries, because the countries' reference data
  must name its source. The source's own country is added with the
  countries table (DAT-011).
- Collected records are never deleted or written over: a change goes
  through the history (DAT-009), a doubt through the review queue
  (DAT-010), and both exist before the first collected table.
- No row of reference data enters the store without its source and licence
  recorded first (DAT-012). If no source allows it, the task is blocked,
  not worked around.
- Tests may generate positions and tracks to measure and to exercise the
  export. Generated records are never stored outside a test and never
  published (CLAUDE.md §11).
- Where a choice needs a measurement or a trial (the migration tool, the
  kind of index for positions, the tile scheme), the entry says so, and
  the planner's trial settles it before that task's plan is written.

One correction rides along: `ARCHITECTURE.md` §2 still described
`scripts/` as holding setup and local-run scripts. After PLAN-011 it holds
the check scripts only.

Phase 1 has 42 tasks, all verified; Phase 2 has 28, none started. The
project has 234.

Next task: DAT-001 – Data store research and decision record.

### DAT-001 – Data store research and decision record (2026-11-19)

TASK: DAT-001 – Data store research and decision record

Implementation: Complete (builder thread, pull request #55). A module,
`motosphere.db.sqlite`, with the Python standard library only. It names
the least SQLite version the store works with (3.45.0) and the six
features the store relies on: enforced foreign keys, strict tables,
RETURNING, the JSON functions, R*Tree and FTS5. Its function `missing()`
tries each feature in an empty database of its own in memory and says in
plain words what a given SQLite lacks. `DATABASE.md` is now the decision
record: what each machine's SQLite had, where the store is kept between
runs (text files in a `data` branch; the database file as a release asset
in reserve), GitHub's limits with the pages they were read from, and the
sizes at which the decision is looked at again. `ARCHITECTURE.md` §5 has
no open question left. Exactly the 8 planned files; all are identical to
the planner's trial. No existing test changed. No table and no connection
module yet.

Before the plan (planner, 2026-11-19): a probe ran on GitHub's Linux and
Windows machines (pull request #53, closed without merging, run
44432064695) and on the planner's own. It found SQLite 3.45.1, 3.49.1 and
3.53.1, all with the six features; Geopoly is missing on both of GitHub's
machines and the `dbstat` table on the Windows one, so the store may not
use them. The trial itself ran on both machines in pull request #54
(closed without merging, run 44433808256): both gates jobs green with 780
tests.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  780 passed, 0 failed, 0 skipped." Backend tests: 151 (115 before, 36
  new: 33 unit tests and 3 integration tests).
- Planted defects: 33 in the module and in `DATABASE.md`, 33 of 33
  detected by the new tests, the plan's twelve prove-it steps among them,
  each with the number of failing tests the plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44435455047, the pull request's commit (`e8d9401`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 780 passed, 0 failed, 0 skipped.", with 151
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44436500524, for `main` after the merge (`a71f880`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 609/609 passed (repository 40, script tests
206, backend 151, frontend 212). Browser tests: 171/171 passed.
Database tests: the 3 integration tests ran against the real SQLite of
each machine, and the 33 unit tests against a real SQLite in memory made
to behave like a lesser one; no mock of a database is used.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 780/780 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the runs on GitHub do not print the SQLite version;
that they ran 3.45.1 and 3.49.1 follows from the probe a few minutes
before on the same Pythons (3.12.16 and 3.12.10, read from the logs).
3.45.0 is the least version because nothing older was tried, not because
anything older is known to fail. The planner's trial first detected 30 of
33 planted defects; one test was added and one planted defect replaced
before the plan was written. The job that writes the `data` branch does
not exist yet: it is planned with the first task that collects real
records, and until then the store exists only in tests. The builder
reported no deviation from the plan.

Commit: `a71f880` (squash merge of pull request #55).

Next task: DAT-002 – Store settings and connection module.

### PLAN-013 – The store's settings and connection, in three tasks (2026-11-19)

Not a development task: no application code changed.

"DAT-002 – Store settings and connection module" was one task: a setting
for the store's path, SQLAlchemy and the module that opens the store with
foreign keys on, and units of work that are kept as a whole or not at all.
When the planner began its trial, each of the three turned out to be
something that is built, tested and committed alone, and the rule is to
choose the smaller task (CLAUDE.md §1). So:

1. DAT-002 – Store path setting. The setting, its check, and Git ignoring
   the store's file. No new dependency.
2. DAT-021 – Opening the store. SQLAlchemy 2, the engine, foreign keys on
   every connection, SQLite's own transactions, and the refusal of an
   SQLite that lacks what DAT-001 names.
3. DAT-022 – Units of work. The session a piece of work is done in:
   committed as a whole, or taken back as a whole.

The three follow one another in `TASKS.md`; DAT-003 (a real, separate
store for every test) comes after them and now names DAT-021's module.
Nothing was dropped: every acceptance criterion of the old task is in one
of the three, and two were added (a path that cannot be a store is refused
in plain words; a new table is taken back with a failed piece of work).

What the planner tried for DAT-002 (Linux, Python 3.13.18, Node 22.23.4,
npm 10.9.9, uv 0.11.32), on `main` at `c0d0d1c`:

- 11 new tests (10 in the backend, 1 repository check), all passing. The
  full run: 19 of 19 gates passed, "Tests: 791 passed, 0 failed, 0
  skipped." (repository checks 41, backend tests 161).
- 22 of 22 planted defects detected. The first try detected 21 (a setting
  that made the store's folder while being read went unnoticed for a set
  value), and the test was extended.
- In trial pull request #56 (closed without merging), exactly these nine
  files ran on GitHub (run 44438302924): "All gates (Linux)" and
  "All gates (Windows)" green, each log ending `19 of 19 gates passed.`
  and `Tests: 791 passed, 0 failed, 0 skipped.`, with 41 repository checks
  and 161 backend tests on both machines; "Build the site", "Publish the
  site" and "Check the published site" skipped.

For DAT-021 the planner looked at one thing ahead of its own trial: the
SQLAlchemy that the lock file would take today is 2.1.9, and its own
documentation gives the setting for SQLite's real transactions on Python
3.12 and newer. Nothing of that is in this commit.

Phase 2 has 30 tasks, 1 verified, and the project 236.

Next task: DAT-002 – Store path setting.

### DAT-002 – Store path setting (2026-11-19)

TASK: DAT-002 – Store path setting

Implementation: Complete (builder thread, pull request #57). One new
setting, `store_path` (`MOTOSPHERE_STORE_PATH`), a path, by default
`store/motosphere.sqlite3` in the `backend` folder. An empty value is
refused in plain words when the settings are read, and spaces around a
value are dropped. Reading the settings creates no file and no folder. Git
ignores `backend/store/` and every `*.sqlite3` file with the files SQLite
keeps beside one. A repository check reads the default from
`backend/.env.example` and fails if Git would not ignore it, and a new
test holds the README's table of settings to the code. Exactly the 9
planned files; all are identical to the planner's trial. Nothing opens the
store yet.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  791 passed, 0 failed, 0 skipped." Repository checks: 41 (40 before, 1
  new). Backend tests: 161 (151 before, 10 new).
- Planted defects: 22 in `settings.py`, `backend/.env.example`,
  `.gitignore` and `README.md`, 22 of 22 detected, the plan's ten prove-it
  steps among them, each with the number of failing tests the plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44439304001, the pull request's commit (`2d1803c`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 791 passed, 0 failed, 0 skipped.", with 41
  repository checks and 161 backend tests on both machines; "Build the
  site", "Publish the site" and "Check the published site" skipped.
- Run 44440230084, for `main` after the merge (`8b77706`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 620/620 passed (repository 41, script tests
206, backend 161, frontend 212). Browser tests: 171/171 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 791/791 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the setting is not used by anything yet; the first thing
that opens the store is DAT-021. A path is only checked for being empty
here: whether it can be a store (not a folder, not another kind of file) is
checked when the store is opened. One existing test changed in what it
expects, because it lists the settings. The planner's trial first detected
21 of 22 planted defects, and one test was extended before the plan was
written. The builder reported no deviation from the plan; the plan's diff
applied as written.

Commit: `8b77706` (squash merge of pull request #57).

Next task: DAT-021 – Opening the store.

### DAT-021 – Opening the store (2026-11-19)

TASK: DAT-021 – Opening the store

Implementation: Complete (builder thread, pull request #59). SQLAlchemy
2 joins the pipeline (`sqlalchemy>=2.1`, locked at 2.1.9, no other new
package). One new module, `motosphere.db.store`, with `open_store(path)`
and `StoreError`. The function asks `missing()` of DAT-001 before it
touches the disk and refuses with everything the SQLite lacks in one
sentence. It makes the path whole, makes the folder if it is not there and
returns the engine. Every connection the engine makes switches foreign
keys on and uses SQLite's own transactions (`autocommit=False`), so a new
table is taken back with the rest of a failed piece of work. No connection
is kept after use (`NullPool`). A path that is a folder, a folder that
cannot be made and a file that is not an SQLite database are refused in
plain words, and the file is left as it was. Exactly the 8 planned files;
all are identical to the planner's trial. No existing test changed.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  810 passed, 0 failed, 0 skipped." Backend tests: 180 (161 before, 19
  new). The type check passes with SQLAlchemy's own types and no ignore.
- Planted defects: 28 in the module, 28 of 28 detected by the new tests,
  the plan's eleven prove-it steps among them, each with the number of
  failing tests the plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44443403050, the pull request's commit (`f558e2e`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 810 passed, 0 failed, 0 skipped.", with 180
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44444397196, for `main` after the merge (`d2f71e7`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 639/639 passed (repository 41, script tests
206, backend 180, frontend 212). Browser tests: 171/171 passed.
Database tests: the 19 new tests open a real SQLite file in the test's
own folder through `open_store`, on Linux and on Windows; no mock of a
database is used.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 810/810 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: nothing in the pipeline calls `open_store` yet; the next
tasks do (units of work, the test fixture, migrations). A store that cannot
be opened for a reason of the operating system other than the four that are
named (a folder without the right to write, a full disk) reaches the user as
the fourth sentence with SQLite's own words in it; no test covers such a
case, because it cannot be made the same way on every machine. The
pipeline's packages are checked against published advisories by hand so far
(once, by the planner, on 2026-11-19, with no finding); the gate is PRF-005.
The planner's trial first detected 27 of 28 planted defects, and one test
was changed before the plan was written. The builder's report gives the same
counts for the full run and for each of the eleven prove-it steps, and names
no deviation; it notes that its first quick pass over the steps reused
Python's cached bytecode for one step and was run again without the cache,
which is how the planner's runs are made (PYTHONDONTWRITEBYTECODE=1).

Commit: `d2f71e7` (squash merge of pull request #59).

Next task: DAT-022 – Units of work.

### DAT-022 – Units of work (2026-11-19)

TASK: DAT-022 – Units of work

Implementation: Complete (builder thread, pull request #61). One new
module, `motosphere.db.work`, with `unit_of_work(store)`, used in a `with`
statement on the engine `open_store` returned. It gives an SQLAlchemy
session for one piece of work. When the block ends the work is committed
as a whole, rows that were only added included; when it raises, everything
it did is taken back, a new table included, and the error reaches the
caller as the same object; the connection is closed either way. A unit
that calls `commit()` itself is refused with one plain sentence, and one
that called `rollback()` cannot go on. The session cannot be used after
its unit has ended, and what the work read or wrote can still be read
then. No new package. Exactly the 6 planned files; all are identical to
the planner's trial. No existing test changed.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  828 passed, 0 failed, 0 skipped." Backend tests: 198 (180 before, 18
  new). The type check passes with SQLAlchemy's own types and no ignore.
- Planted defects: 16 in the module, 16 of 16 detected by the new tests,
  the plan's ten prove-it steps among them, each with the number of
  failing tests the plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44447177749, the pull request's commit (`e5595f7`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 828 passed, 0 failed, 0 skipped.", with 198
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44448306339, for `main` after the merge (`ba0dd65`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 657/657 passed (repository 41, script tests
206, backend 198, frontend 212). Browser tests: 171/171 passed.
Database tests: the 18 new tests do units of work on a real SQLite file in
the test's own folder, opened through `open_store`, on Linux and on
Windows; no mock of a database is used.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 828/828 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: nothing in the pipeline calls `unit_of_work` yet; the
first tasks that write to the store do. The guard against a commit part-way
stops `work.commit()` called by mistake, not code that goes around it on
purpose (the method of SQLAlchemy's own class called directly, or a COMMIT
sent as a statement). A unit of work started inside another is not refused:
SQLite lets one connection write at a time, and the pipeline does one unit
at a time. In the planner's trial a seventeenth planted defect (SQLAlchemy's
AUTOCOMMIT option) changed nothing on this store and is not counted. The
builder's report gives the same counts for the full run and for each of the
ten prove-it steps, with the same failing tests, and names no deviation.

Commit: `ba0dd65` (squash merge of pull request #61).

Next task: DAT-003 – A real, separate store for every test.

### DAT-003 – A real, separate store for every test (2026-11-19)

TASK: DAT-003 – A real, separate store for every test

Implementation: Complete (builder thread, pull request #63). One pytest
fixture, `store`, in `backend/tests/conftest.py`. It opens `store.sqlite3`
in the test's own temporary folder through `open_store` and gives the test
the engine: a real, empty store that is nobody else's. It remembers every
connection taken from the engine. When the test has ended, it closes those
that are still open, so that the file can be removed on Windows too, and
fails with "Connections to its store that the test left open: N. They were
closed for it.", which pytest reports as an error at the end of that test.
A connection that was dropped without being closed counts too. pytest's
own `pytester` is switched on to test what the fixture does after a test.
Exactly the 5 planned files; all are identical to the planner's trial. No
existing test changed, and nothing under `backend/src`.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  834 passed, 0 failed, 0 skipped." Backend tests: 204 (198 before, 6
  new). The type check passes with no ignore.
- Planted defects: 15 in the fixture, 15 of 15 detected by the new tests,
  the plan's eleven prove-it steps among them, each with the result the
  plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44451398431, the pull request's commit (`aab379e`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 834 passed, 0 failed, 0 skipped.", with 204
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44452427141, for `main` after the merge (`b555379`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 663/663 passed (repository 41, script tests
206, backend 204, frontend 212). Browser tests: 171/171 passed.
Database tests: the fixture's store is a real SQLite file opened through
`open_store`, on Linux and on Windows; no mock of a database is used. One
of the 6 new tests lets pytest run 16 tests by itself in a process of its
own and reads the outcome: 16 passed, 4 errors, and the four sentences.
Those 16 are not counted among the 834.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 834/834 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the existing tests of the store and of units of work keep
their own helpers and do not use the fixture; they count connections
themselves. The tests are not run in a random order: nothing is shared
between two tests that use the fixture, so their order cannot matter, and no
package for random order was added. A connection that is made around the
engine (Python's `sqlite3` called directly on the file) is not seen by the
fixture. The planner's trial first detected 14 of 15 planted defects, and
one test was extended before the plan was written. The builder's report
gives the same counts for the full run and the same result for each of the
eleven prove-it steps, and names no deviation.

Commit: `b555379` (squash merge of pull request #63).

Next task: DAT-004 – Schema migrations.

### PLAN-014 – Schema migrations in five tasks, and no way back (2026-11-19)

Not a development task: no application code changed.

"DAT-004 – Schema migrations" was one task: choose the migration tool, a
first, empty migration, the store's schema version, two commands of the
command line, and a test that fails when a model and the migrated schema
differ. In the planner's trial each of these turned out to be something
that is built, tested and committed alone, and the last of them cannot be
tested before there is a base for models (DAT-005). The rule is to choose
the smaller task (CLAUDE.md §1). So:

1. DAT-004 – The migration runner. The list of migrations, the store's
   version, and the function that applies what a store lacks, each
   migration in one transaction with its version.
2. DAT-023 – Only a store of MotoSphere's is migrated. A file that is not
   one is refused and left as it is. This is new: the old task did not
   have it.
3. DAT-024 – Command: bring the store to the newest schema.
4. DAT-025 – Command: say which schema a store has.
5. DAT-026 – The models and the migrated schema agree. It follows DAT-005
   in `TASKS.md`.

Three things of the old task were decided otherwise, and why:

- **The tool is a runner of the project's own, not Alembic.** Alembic
  would add three packages (alembic 1.20.1, Mako 1.4.3 and MarkupSafe
  3.0.4 on 2026-11-19, tried in a scratch copy) for abilities the store
  does not use. The runner is about thirty lines on SQLAlchemy, and its
  promises are tested against a real file. The comparison is in
  `DATABASE.md` ("How the schema changes"), which the builder's pull
  request adds.
- **No migration has a way back.** The old task said "every migration can
  be taken back, down to an empty store", and eleven later tasks (DAT-006
  to DAT-018) asked for "the migration up and down". The store is rebuilt
  from its text snapshot on every run (DAT-001's decision, DAT-020), so an
  earlier state of the store is an earlier snapshot in the `data` branch,
  with the code of that day. A way back would be a second function for
  every table that is written and tested and never run on the real store,
  and on SQLite most ways back build the table anew and throw away what
  the newer columns held. Instead, the history only grows, a mistake in a
  merged migration is put right by a new one, and each of those eleven
  tasks now tests its migration "applied to a store at the version before
  it". The three acceptance criteria that named a way back (DAT-006,
  DAT-011, DAT-014) lost that clause and nothing else.
- **No first, empty migration.** A store that has had no migration is at
  version 0, and the list is empty until DAT-006 adds the first table.

What the planner tried for DAT-004 (Linux, Python 3.13.18 with SQLite
3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv
0.11.32), on `main` at `f7b6cd1`:

- 17 new tests, all passing. The full run: 19 of 19 gates passed, "Tests:
  851 passed, 0 failed, 0 skipped." (backend tests 221).
- 34 of 34 planted defects detected.
- SQLite's `user_version`, set inside a transaction that fails, is taken
  back with it; so a migration and its version can be one transaction.
- A migration can build a table anew inside its transaction while rows of
  another table point to it and foreign keys stay on
  (`PRAGMA defer_foreign_keys = ON`; the table is copied aside, dropped,
  made anew under its own name and filled again). Making the new table
  under another name and renaming it afterwards was refused at the commit.
  Three of the new tests do this on every machine the gates run on.
- In trial pull request #64 (closed without merging), exactly these six
  files ran on GitHub (run 44454811190): "All gates (Linux)" and "All gates
  (Windows)" green, each log ending `19 of 19 gates passed.` and `Tests: 851
  passed, 0 failed, 0 skipped.`, with 221 backend tests on both machines;
  "Build the site", "Publish the site" and "Check the published site"
  skipped. So GitHub's SQLite builds (3.45.1 on Linux, 3.49.1 on Windows)
  also take the version back with a failed migration and let a migration
  build a table anew while rows point to it.

Phase 2 has 34 tasks, 5 verified, and the project 240.

Next task: DAT-004 – The migration runner.

### DAT-004 – The migration runner (2026-11-19)

TASK: DAT-004 – The migration runner

Implementation: Complete (builder thread, pull request #65). One new
module, `motosphere.db.migrations`. A migration is a function that is
given a connection; the migrations stand in one tuple, `MIGRATIONS`,
oldest first, and the place of a migration in it is its number. The tuple
is empty: the first table comes with DAT-006. `schema_version(store)`
reads the number of the last migration a store has had from the file
itself (SQLite's `user_version`). `migrate(store)` applies the migrations
the store lacks, in order, each in one transaction together with its
number, and returns the numbers. A store whose version the list does not
know (newer than the code, or below zero) is refused with `SchemaError`
and one plain sentence, and left as it is. The error of a failed migration
reaches the caller unchanged. `DATABASE.md` has the new section "How the
schema changes" with the decision for a runner of the project's own and
against Alembic. Exactly the 6 planned files; all are identical to the
planner's trial. No existing test changed, and no package was added.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  851 passed, 0 failed, 0 skipped." Backend tests: 221 (204 before, 17
  new). The type check passes with no ignore and the lint with no noqa.
- Planted defects: 34 in the module, 34 of 34 detected by the new tests,
  the plan's thirteen prove-it steps among them, each with the result the
  plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44456115927, the pull request's commit (`29fdcae`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 851 passed, 0 failed, 0 skipped.", with 221
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44457687600, for `main` after the merge (`c5e4687`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 680/680 passed (repository 41, script tests
206, backend 221, frontend 212). Browser tests: 171/171 passed.
Database tests: the 17 new tests run the runner on the real SQLite file
the fixture `store` gives each test, on Linux and on Windows; no mock of
a database is used. Three of them build a table anew inside a migration
while rows of another table point to it.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 851/851 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the list of migrations is empty and no command calls
`migrate` yet (DAT-024, DAT-025); the store still has no table. `migrate`
does not yet ask whether the file is a store of MotoSphere's at all
(DAT-023). A migration that commits by itself fails, and what it did before
its commit is kept without a version; the test that brings an empty store to
the newest schema with the real list fails for such a migration, so it
cannot be merged. No migration has a way back: an earlier state of the store
is an earlier snapshot (PLAN-014). The builder reported no deviation in the
files (its Node.js was 22.23.5). Its first full local run failed in one
browser test that this task does not touch, and its second, with nothing
changed, passed; what the planner found is in PLAN-015 below, and repairing
that test is the next task.

Commit: `c5e4687` (squash merge of pull request #65).

Next task: FND-043 – The loading test waits for its request.

### PLAN-015 – A browser test that could fail by chance is repaired first (2026-11-19)

Not a development task: no application code changed.

The builder of DAT-004 reported that its first full local run failed in
one browser test that DAT-004 does not touch, and that the second run,
with no file changed, passed:

    [chromium] › e2e/status.spec.ts:117:3 › data status › says the data
    is loading until it arrives
    Error: expect(received).toHaveLength(expected)
    Expected length: 1
    Received length: 0

What the planner found, on the frontend as it is on `main` (DAT-004
changed nothing under `frontend`):

- The test (from FND-028) holds the request for the manifest back, waits
  until the page says "Loading data…" and then expects, at once and
  without waiting, that the request has arrived. The page says "Loading
  data…" from its first drawing; the request is sent a moment later and
  reaches the test later still. Nearly always the request is there first.
- Repeated 450 times by itself (150 times with the usual workers, 300
  times with 12 workers on 4 processors), the test passed 450 times.
- With the page's request made to start 0.4 seconds late, the test as it
  is failed with exactly the builder's message, and the same test waiting
  for the request passed.

So the page is right and the test can fail by chance. It did not fail in
the planner's run of DAT-004 nor on GitHub's two machines, and DAT-004
stands as verified. But a test that can fail by chance is a defect, and it
is not left for later (CLAUDE.md §3): a new task, FND-043 – The loading test waits for its request,
is the next task, before the store goes on with DAT-023. The other browser
tests are searched for the same pattern in its trial.

Phase 1 has 43 tasks, 42 verified, and the project 241.

Next task: FND-043 – The loading test waits for its request.

### FND-043 – The loading test waits for its request (2026-11-19)

TASK: FND-043 – The loading test waits for its request

Implementation: Complete (builder thread, pull request #67). One browser
test changed, "says the data is loading until it arrives" in
`frontend/e2e/status.spec.ts`: it now waits until the request for the
manifest is held back (`expect.poll`, part of Playwright) and then reads
what the page says in the meantime, where before it read the page first
and expected the request to be there at once. `TESTING.md` has the rule
for checks that do not wait, and `CHANGELOG.md` a section "Fixed". Exactly
the 3 planned files; all are identical to the planner's trial. Nothing
under `frontend/src` changed: the page was right.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18, Node 22.23.4, npm
10.9.9, uv 0.11.32, Playwright 1.63.0):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  851 passed, 0 failed, 0 skipped." Browser tests: 171, as before.
- The changed test repeated 100 times: 100 passed.
- With the page's request made to start 0.4 seconds late: the test as it
  was on `main` failed 3 times of 3 with "Expected length: 1, Received
  length: 0"; the changed test passed.
- Planted faults in the page: 4, and 4 of 4 detected by the changed test
  (another text while loading, "Data unavailable" before the page has
  asked, a request to another address, two requests).
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44460533369, the pull request's commit (`e679a6f`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 851 passed, 0 failed, 0 skipped.", with 171
  browser tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44461468925, for `main` after the merge (`846e470`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 680/680 passed (repository 41, script tests
206, backend 221, frontend 212). Browser tests: 171/171 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 851/851 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: that a test cannot fail by chance cannot be proven by
running it. What is shown is that the one known cause is gone: the changed
test passes with the late request that failed the old one every time, and
the other browser tests were searched for the same fault. The browser tests
are still not run again when they fail (no retries), so another test of this
kind would show itself as a failed gate and not be hidden. The builder
reported no deviation (its Node.js was 22.23.5), and that the planted
request to another address was detected a second time, by the record of the
page's problems, which reported the answer 404.

Commit: `846e470` (squash merge of pull request #67).

Next task: DAT-023 – Only a store of MotoSphere's is migrated.

### DAT-023 – Only a store of MotoSphere's is migrated (2026-11-19)

TASK: DAT-023 – Only a store of MotoSphere's is migrated

Implementation: Complete (builder thread, pull request #69).
`motosphere.db.migrations` has the mark of a MotoSphere data store,
`APPLICATION_ID` (1299141488, the letters "MoSp"), kept in the file's
header in the field SQLite gives applications for this
(`application_id`). `migrate` looks at the file before anything else: a
file with the mark is migrated; a file with no mark and nothing in it is a
new store, and gets the mark in the transaction of its first migration;
every other file is refused with `SchemaError` and one sentence that
names the file and says why, and is left byte for byte as it was. The
mark is looked at before the version. Exactly the 6 planned files; all are
identical to the planner's trial. No new package.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  858 passed, 0 failed, 0 skipped." Backend tests: 228 (221 before, 7
  new).
- Planted defects in the module: 62, and 62 of 62 detected. 34 are those
  of DAT-004, fitted to the new loop; 28 are new, among them the plan's
  fourteen prove-it steps, with the results the plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44464487081, the pull request's commit (`e016857`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 858 passed, 0 failed, 0 skipped."; "Build
  the site", "Publish the site" and "Check the published site" skipped.
- Run 44465474527, for `main` after the merge (`c745c4b`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 687/687 passed (repository 41, script tests
206, backend 228, frontend 212). Browser tests: 171/171 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 858/858 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the list of migrations is still empty, so today the
pipeline marks no file: a new store that lacks no migration is not written
to, and stays a new store. Only `migrate` refuses a file that is not
MotoSphere's; `open_store` opens any SQLite database and `schema_version`
reads any, which harms nothing, and what the command that says which schema
a store has will say about such a file is DAT-025's to settle. A file of
another program in which SQLite keeps its changes beside the file (its
write-ahead log) was not among the files tried. One existing test changed by
one line, because a file with a version and no mark is now refused for its
missing mark. The builder reported the same numbers, all fourteen prove-it
steps with the results the plan names, and no deviation in any file (its
Node was 22.23.5 where the plan names 22.23.4).

Commit: `c745c4b` (squash merge of pull request #69).

Next task: DAT-024 – Command: bring the store to the newest schema.

### DAT-024 – Command: bring the store to the newest schema (2026-11-19)

TASK: DAT-024 – Command: bring the store to the newest schema

Implementation: Complete (builder thread, pull request #71). The
pipeline's command line has a third command, `python -m motosphere
migrate`, in the new module `motosphere.cli.migrate`. It opens the store
the setting `MOTOSPHERE_STORE_PATH` names, which makes the file and its
folder if they are not there, calls `migrate`, and writes one sentence to
standard output with the file's whole path: that a new store was made,
that the store was brought from one schema version to another, or that it
is up to date. A store that cannot be opened or that is refused gives its
own sentence on standard error and the exit code 1, and is left as it is.
An error inside a migration is not caught. Exactly the 10 planned files;
all are identical to the planner's trial. No new package.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  876 passed, 0 failed, 0 skipped." Backend tests: 246 (228 before, 18
  new).
- Planted defects in the command: 40, and 40 of 40 detected, among them
  the plan's fifteen prove-it steps, with the results the plan gives.
- By hand, in an empty folder: the first run made `store/motosphere.sqlite3`
  and said "A new data store was made: … is at schema version 0."; the
  second said "The data store is up to date: …"; a folder and a database
  made by SQLite alone were each refused in one line with the exit code 1.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44468959155, the pull request's commit (`8e64d4a`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 876 passed, 0 failed, 0 skipped."; "Build
  the site", "Publish the site" and "Check the published site" skipped.
- Run 44470574256, for `main` after the merge (`f209739`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 705/705 passed (repository 41, script tests
206, backend 246, frontend 212). Browser tests: 171/171 passed.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the real command was run in a
process of its own by four tests on both machines, and by hand; the
deployment succeeded and the published site is the site that was built.
The task changes nothing a user sees.

Overall applicable tests: 876/876 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the pipeline's list of migrations is still empty, so a
process of its own has only run the command where there is nothing to apply;
that it gives a store the migrations it lacks is tested in the test's
process, with a list of the test's own and a real SQLite file, and the first
task that adds a migration (DAT-006) runs the real command with it. An error
inside a migration is not caught by the command, by decision: it ends the
process with its traceback, and the store stays at the version before that
migration. The command is not yet part of any scheduled run. The builder
reported the same numbers, all fifteen prove-it steps with the results the
plan names, the command by hand with the same sentences, and no change to
the code or the tests (its Node was 22.23.5 where the plan names 22.23.4).

Commit: `f209739` (squash merge of pull request #71).

Next task: DAT-025 – Command: say which schema a store has.

### PLAN-016 – Asking what a store lacks comes before the command that says it (2026-11-19)

Not a development task: no application code changed.

"DAT-025 – Command: say which schema a store has" is a command that
never writes. To say that a store is up to date, that it lacks two
migrations, that it is newer than this code or that it is not MotoSphere's
at all, it needs what `migrate` works out before it applies anything: is
the file MotoSphere's (DAT-023), is its version one the code knows
(DAT-004), and which migrations are still to come. That is the first half
of `migrate`, and nothing can ask for it without migrating.

In the planner's trial the command could be written in two ways. It could
do those checks a second time by itself; then two places must agree for
ever on which store is refused, and nothing but care keeps them agreeing.
Or the checks become one function that `migrate` asks too. The second is
right, but it changes code that is verified, and a change to `migrate`
deserves tests and planted defects of its own, apart from a new command's
sentences and exit codes. The rule is to choose the smaller task
(CLAUDE.md §1). So:

1. DAT-027 – Say which migrations a store lacks. The function `pending`: it
   says which migrations a store lacks, writes nothing, and refuses
   exactly the stores `migrate` refuses, in the same words. `migrate`
   applies exactly what it names. This is new.
2. DAT-025 – Command: say which schema a store has. It follows, and
   asks `pending`.

What the planner tried for DAT-027 (Linux, Python 3.13.18 with SQLite
3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv
0.11.32), on `main` at `082d003`:

- With only the module changed and no test touched, all 246 backend tests
  passed: the change keeps what `migrate` does.
- 10 new tests, all passing. The full run: 19 of 19 gates passed, "Tests:
  886 passed, 0 failed, 0 skipped." (backend tests 256).
- 74 of 74 planted defects detected: 42 of those of DAT-004 and DAT-023
  that still fit the module word for word, and 32 new ones.
- No existing test changed.
- In trial pull request #72 (closed without merging), exactly these five
  files ran on GitHub (run 44472411230): "All gates (Linux)" and "All gates
  (Windows)" green, each log ending `19 of 19 gates passed.` and `Tests: 886
  passed, 0 failed, 0 skipped.`, with 256 backend tests on both machines
  (Python 3.12.16 on Linux, 3.12.10 on Windows); "Build the site", "Publish
  the site" and "Check the published site" skipped.

Phase 2 has 35 tasks, 8 verified, and the project 242.

Next task: DAT-027 – Say which migrations a store lacks.

### DAT-027 – Say which migrations a store lacks (2026-11-19)

TASK: DAT-027 – Say which migrations a store lacks

Implementation: Complete (builder thread, pull request #73).
`motosphere.db.migrations` has a new function, `pending(store)`: it
returns the numbers of the migrations the store lacks, in order, and only
reads. The two refusals of `migrate` moved into it unchanged (a file that
is not a store of MotoSphere's, and a store at a version the history does
not know), and `migrate` now asks `pending` and applies exactly the
migrations it names, each in one transaction with the mark and the
version as before. Exactly the 5 planned files; all are identical to the
planner's trial. No new package, and no existing test changed.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  886 passed, 0 failed, 0 skipped." Backend tests: 256 (246 before, 10
  new).
- Planted defects in the module: 74, and 74 of 74 detected. 42 are those
  of DAT-004 and DAT-023 that still fit the module word for word; 32 are
  new, among them the plan's twelve prove-it steps, with the results the
  plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44473530583, the pull request's commit (`d5b8c2e`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 886 passed, 0 failed, 0 skipped.", with 256
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44474646015, for `main` after the merge (`3a0ed18`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 715/715 passed (repository 41, script tests
206, backend 256, frontend 212). Browser tests: 171/171 passed.
Database tests: the 10 new tests run against the real SQLite file the
fixture `store` gives each test, on Linux and on Windows; no mock of a
database is used.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 886/886 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: nothing calls `pending` yet but `migrate`; the command
that says which schema a store has (DAT-025) is the first that will.
`pending` reads the file as it is at that moment and holds nothing, and
`migrate` asks it once, as it read the version once before this task: two
processes that migrate the same file at the same moment are not guarded
against. The list of migrations is still empty, so for the pipeline's own
list `pending` names nothing today; that it names what a store lacks is
tested with lists of the tests' own and a real SQLite file. The builder
reported the same numbers, all twelve prove-it steps with the results the
plan names, and no change to the code or the tests (its Node was 22.23.5
where the plan names 22.23.4).

Commit: `3a0ed18` (squash merge of pull request #73).

Next task: DAT-025 – Command: say which schema a store has.

### DAT-025 – Command: say which schema a store has (2026-11-19)

TASK: DAT-025 – Command: say which schema a store has

Implementation: Complete (builder thread, pull request #75). The
pipeline's command line has a fourth command, `python -m motosphere
schema`, in the new module `motosphere.cli.schema`. It says in one
sentence on standard output, with the file's whole path, which schema the
store the setting `MOTOSPHERE_STORE_PATH` names has: that it is up to
date, how many migrations it lacks (with its version and the newest), or
that there is no store. It never writes: where there is no file it does
not open one, and otherwise it asks `pending` (DAT-027), which only
reads. A store that cannot be opened, or that `migrate` would refuse,
gives the same sentence as there on standard error and the same exit code
1. Exactly the 10 planned files; all are identical to the planner's
trial. No new package.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  911 passed, 0 failed, 0 skipped." Backend tests: 281 (256 before, 25
  new).
- Planted defects in the command: 62, and 62 of 62 detected, among them
  the plan's seventeen prove-it steps, with the results the plan gives.
  Seven of the 62 are ways of writing where the command must not (making
  the file or its folder, migrating the store, marking it, leaving a file
  beside it).
- By hand, in an empty folder: `schema` said "There is no data store: …
  does not exist." and the folder stayed empty; after `migrate` it said
  "The data store is up to date: … is at schema version 0."; a folder and
  a database made by SQLite alone were each refused in one line with the
  exit code 1, and the database was byte for byte as before.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44479205716, the pull request's commit (`e85b041`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 911 passed, 0 failed, 0 skipped.", with 281
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44481346796, for `main` after the merge (`c590ec0`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 740/740 passed (repository 41, script tests
206, backend 281, frontend 212). Browser tests: 171/171 passed.
Database tests: 16 of the new tests run the command against a real
SQLite file, on Linux and on Windows; no mock of a database is used.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the real command was run in a
process of its own by four tests on both machines, and by hand; the
deployment succeeded and the published site is the site that was built.
The task changes nothing a user sees.

Overall applicable tests: 911/911 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the pipeline's list of migrations is still empty, so a
process of its own has only run the command where no migration is lacking;
that it says how many a store lacks is tested in the test's process, with a
list of the test's own and a real SQLite file, and the first task that adds
a migration (DAT-006) runs the real command with it. Where there is no store
the exit code is 0, by decision: the code 1 means that the file there is
refused, which is what `migrate` would say of it. The command looks whether
the file is there and then opens it; a file made by another process between
the two is opened like any other, and one removed between the two would be
made empty by `open_store`, which this task did not guard against. A
database of another program that is in its write-ahead mode was tried by
hand by the planner (refused, nothing made beside it) but is not a test. The
builder reported the same numbers, all seventeen prove-it steps with the
results the plan names, the commands by hand with the same sentences, and no
deviation from the plan.

Commit: `c590ec0` (squash merge of pull request #75).

Next task: DAT-005 – Model conventions: keys, times and names.

### PLAN-017 – What every table shares is four tasks, not one (2026-11-19)

Not a development task: no application code changed.

"DAT-005 – Model conventions: keys, times and names" was one task for
everything the tables share: strict column types, one naming rule, a
whole-number key, two timestamps set by the store's code, times in UTC
with their offset, and text that must not be empty. In the planner's trial
the first two alone took a module, 18 tests and 41 planted defects, and
each of the others brings a decision of its own that deserves its own
trial. The rule is to choose the smaller task (CLAUDE.md §1). So:

1. DAT-005 – The base of all models: strict tables and one naming rule.
   Every table is strict, its columns are of the types a strict table
   takes, and its constraints and indexes are named by one rule; a test
   holds every table to that. This is the task that is planned now.
2. DAT-028 – Times in the store. A strict table has no type for a time, so
   the store needs one of its own: UTC, stored with its offset, and a time
   without an offset refused.
3. DAT-029 – Every table's key and timestamps. The key `id` and
   `created_at` and `updated_at`, set by the store's code. Its trial
   settles whether a key may be given again after its row is deleted, and
   how a test sets the time; if the key and the timestamps prove to be two
   things to test, it is split again.
4. DAT-030 – Text that must not be empty. A check in the table
   itself, named by the rule of the first task.

"DAT-026 – The models and the migrated schema agree" follows the four, and
then the first table (DAT-006). A type for yes and no (a strict table has
none either) is settled in the trial of the first table that has such a
column, and becomes a task of its own if it is one.

What the planner tried for DAT-005 (Linux, Python 3.13.18 with SQLite
3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv
0.11.32), on `main` at `6977f5f`:

- 18 new tests, all passing; 9 of them make tables in a real SQLite file
  and read the file itself. The full run: 19 of 19 gates passed, "Tests:
  929 passed, 0 failed, 0 skipped." (backend tests 299).
- 41 of 41 planted defects detected.
- SQLite refuses to make a strict table with a column of SQLAlchemy's
  `String`, `Float`, `Boolean` or `DateTime` ("unknown datatype"), so a
  model with such a column cannot reach the store. That is why times and
  yes-and-no need types of the store's own.
- Saying "strict" once on the base of all models is lost by every model
  that says something of its table itself; the base therefore makes each
  table strict when its model is defined.
- No existing test changed.
- In trial pull request #76 (closed without merging), exactly the seven
  files of the trial ran on GitHub (run 44483616466): "All gates (Linux)"
  and "All gates (Windows)" green, each log ending `19 of 19 gates passed.`
  and `Tests: 929 passed, 0 failed, 0 skipped.`, with 299 backend tests on
  both machines (Python 3.12.16 on Linux, 3.12.10 on Windows); "Build the
  site", "Publish the site" and "Check the published site" skipped.

Phase 2 has 38 tasks, 10 verified, and the project 245.

Next task: DAT-005 – The base of all models: strict tables and one naming rule.

### DAT-005 – The base of all models: strict tables and one naming rule (2026-11-19)

TASK: DAT-005 – The base of all models: strict tables and one naming rule

Implementation: Complete (builder thread, pull request #77). One new
module, `motosphere.db.base`. `Base` is the class every model will be a
subclass of. It makes the table of every model strict when the model is
defined, so SQLite refuses a value that is not of its column's type; it
makes a model's `str` TEXT and its `float` REAL, the types a strict table
takes; and its schema names every key, foreign key, unique constraint,
check and index by one rule, `NAMING`. `broken_rules` says in plain
sentences which tables of a schema are not strict and which names were
given by hand, and one test holds the real schema to it. There is no
model and no table yet. Exactly the 7 planned files; all are identical to
the planner's trial. No new package.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  929 passed, 0 failed, 0 skipped." Backend tests: 299 (281 before, 18
  new).
- Planted defects in the module: 41, and 41 of 41 detected, among them
  the plan's fifteen prove-it steps, with the results the plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44485008294, the pull request's commit (`d70bf81`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 929 passed, 0 failed, 0 skipped.", with 299
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44486608897, for `main` after the merge (`7d3c56c`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 758/758 passed (repository 41, script tests
206, backend 299, frontend 212). Browser tests: 171/171 passed.
Database tests: 9 of the new tests make tables in a real SQLite file and
read the file itself, on Linux and on Windows; no mock of a database is
used.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 929/929 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: there is no model yet, so the test that holds the real
schema to the rules has nothing to look at; that it can fail is proven by a
planted table. It sees only the models whose modules have been imported when
it runs, so the first task with a model (DAT-006) must make sure that all
models are. `broken_rules` looks at the models, not at the file: that the
store's tables are what the models say is DAT-026's. A table made without a
model is strict only if it says so, which is why `broken_rules` names one
that is not. The rules for the key and the timestamps, for times and for
text that must not be empty are DAT-028 to DAT-030; a type for yes and no is
settled with the first table that needs one. The builder reported the same
numbers, all fifteen prove-it steps with the results the plan names, and no
deviation from the plan.

Commit: `7d3c56c` (squash merge of pull request #77).

Next task: DAT-028 – Times in the store.

### DAT-028 – Times in the store (2026-11-19)

TASK: DAT-028 – Times in the store

Implementation: Complete (builder thread, pull request #79). One new
module, `motosphere.db.times`. A time is stored as text in one form,
`2026-11-19T08:26:04.123456+00:00`: in UTC, with its offset written out
and the six digits of the fraction of its second, so that the order of
the texts is the order of the times. `to_text` says a time in the form
and refuses what is not a time, a time without an offset and a time UTC
cannot say; `from_text` reads the form as an aware UTC time and refuses
every other; `UtcDateTime` is the column type built from the two, and
`Base` gives it to a model's `datetime` column. There is no model and no
table yet. Exactly the 8 planned files; all are identical to the
planner's trial. No new package.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  976 passed, 0 failed, 0 skipped." Backend tests: 346 (299 before, 47
  new).
- Planted defects in the two modules: 49, and 49 of 49 detected, among
  them the plan's sixteen prove-it steps, with the results the plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44490006014, the pull request's commit (`365a511`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 976 passed, 0 failed, 0 skipped.", with 346
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44491341132, for `main` after the merge (`ce823a0`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 805/805 passed (repository 41, script tests
206, backend 346, frontend 212). Browser tests: 171/171 passed.
Database tests: 15 of the new tests store and read times in a real SQLite
file, on Linux and on Windows; no mock of a database is used.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 976/976 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the table itself does not check the form of a time. Text
in another form can only be written past the models, with plain SQL, and is
refused when a model reads it; whether the table should refuse it when it is
written is settled in the trial of DAT-030, which builds the way a column
gets a check. A time UTC cannot say in the years 1 to 9999 is refused. A
column for a date without a time of day has no type yet; it comes with the
first table that has such a column, as does one for yes and no. The tests
use fixed offsets, not named zones, because Python on Windows has no zone
database of its own. The builder reported the same numbers, all sixteen
prove-it steps with the results the plan names, and no deviation from the
plan.

Commit: `ce823a0` (squash merge of pull request #79).

Next task: DAT-029 – Every table's key and timestamps.

### PLAN-018 – The key first, the timestamps after it (2026-11-19)

Not a development task: no application code changed.

PLAN-017 left "DAT-029 – Every table's key and timestamps" as one task
and said that it would be split if the key and the timestamps proved to be
two things to test. The planner's trial of the key showed that they are:

- The key brings a decision of its own. SQLite, left alone, gives the key
  of a deleted last row to the next new row (tried: two rows stored, the
  second deleted, a third stored, and the third got the key 2 again). The
  store's records will be pointed at by their key, so a key must never be
  given twice, and that is asked of SQLite with AUTOINCREMENT.
- That decision changes a rule of DAT-005. SQLAlchemy writes such a key
  with its column, where it has no name, so the key leaves the naming
  rule; three of DAT-005's tests change with it, and all of DAT-005's
  planted defects that still fit were planted again.
- It reaches into the snapshot. SQLite keeps the last key of each table
  in a table of its own, and a store rebuilt from text files gives old
  keys again unless the snapshot keeps that too. DAT-019 and DAT-020 now
  say so.

None of this has to do with when a row was stored. The rule is to choose
the smaller task (CLAUDE.md §1). So:

1. DAT-029 – Every table's key. The key `id` on every model, never
   given twice, and `broken_rules` naming a table without it. This is the
   task that is planned now.
2. DAT-031 – Every table's timestamps. `created_at` and
   `updated_at`, set by the store's code. It follows, and its trial
   settles how a test sets the time.

"DAT-030 – Text that must not be empty" and "DAT-026 – The models and the
migrated schema agree" follow as before.

What the planner tried for DAT-029 (Linux, Python 3.13.18 with SQLite
3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv
0.11.32), on `main` at `c489298`:

- With only the module changed, 8 of the existing tests failed, all of
  them tests of DAT-005's rules and each for a reason the plan names; the
  other 338 backend tests passed.
- 17 new tests, 12 of them against a real SQLite file. The full run: 19
  of 19 gates passed, "Tests: 993 passed, 0 failed, 0 skipped." (backend
  tests 363).
- 63 of 63 planted defects detected: 39 of DAT-005's 41 (the two
  that gave the key another name have no line left to change) and 24 new
  ones.
- SQLite itself takes a key that is named and never given twice
  (`CONSTRAINT pk_item PRIMARY KEY (id AUTOINCREMENT)`), but SQLAlchemy
  does not write it that way. The name was given up instead of changing
  how SQLAlchemy writes SQL: SQLite cannot change a key by its name, and
  it reports a key that is there twice by table and column, named or not.
- SQLAlchemy leaves AUTOINCREMENT out, and says nothing, for a key of two
  columns, a key that is a foreign key and a key that is text. So
  `broken_rules` looks at the shape of the key and not only at the
  switch.
- In trial pull request #80 (closed without merging), exactly the eight
  files of the trial ran on GitHub (run 44493731572): "All gates (Linux)"
  and "All gates (Windows)" green, each log ending `19 of 19 gates passed.`
  and `Tests: 993 passed, 0 failed, 0 skipped.`, with 363 backend tests on
  both machines (Python 3.12.16 on Linux, 3.12.10 on Windows); "Build the
  site", "Publish the site" and "Check the published site" skipped.

Phase 2 has 39 tasks, 12 verified, and the project 246.

Next task: DAT-029 – Every table's key.

### DAT-029 – Every table's key (2026-11-19)

TASK: DAT-029 – Every table's key

Implementation: Complete (builder thread, pull request #81). `Base`
gives every model its key: the first column `id`, a whole number, which a
model does not name. The table is made with AUTOINCREMENT, in the place
where it is made strict, so SQLite never gives a key twice, not even the
key of a deleted last row. The key is written with its column and has no
name, and the `pk` line left the naming rule. `broken_rules` names a table
that does not have exactly this key. There is no model and no table yet.
Exactly the 8 planned files; all are identical to the planner's trial. No
new package.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  993 passed, 0 failed, 0 skipped." Backend tests: 363 (346 before, 17
  new).
- Planted defects in the module: 63, and 63 of 63 detected, among them
  the plan's fifteen prove-it steps, with the results the plan gives, and
  39 of the 41 that were planted for DAT-005.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44495734597, the pull request's commit (`fcb81e3`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 993 passed, 0 failed, 0 skipped.", with 363
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44497086816, for `main` after the merge (`6916daa`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 822/822 passed (repository 41, script tests
206, backend 363, frontend 212). Browser tests: 171/171 passed.
Database tests: 12 of the new tests store and delete rows in a real
SQLite file, on Linux and on Windows; no mock of a database is used.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 993/993 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: SQLite keeps the last key of each table in a table of its
own, `sqlite_sequence`. A store rebuilt from the text files gives old keys
again unless the snapshot keeps that too; DAT-019 and DAT-020 say so and
will prove it. The key has no name in the file, which SQLAlchemy does not
write for a key of this kind; nothing uses the name. A row may be stored
with a key of its own, which the rebuild needs, so nothing stops code from
doing that elsewhere. The rule looks at the tables of the models that were
imported: the first task with a real table (DAT-006) sees to it that every
model is. The builder's report gave the same counts for the full run and for
each of the fifteen prove-it steps, and named no deviation; its Node was
22.23.5 where the planner's is 22.23.4.

Commit: `6916daa` (squash merge of pull request #81).

Next task: DAT-031 – Every table's timestamps.

### PLAN-019 – The timestamps first, the rule that names a table without them after (2026-11-19)

Not a development task: no application code changed.

PLAN-018 described "DAT-031 – Every table's timestamps" as the two
columns and, with them, a rule in `broken_rules` that names a table
without them. The planner's trial of the columns showed that these are two
things to test:

- The columns bring their own questions, and each took a test to settle:
  which clock the store asks and how a test sets it, that a new row gets
  one reading of the clock and not two, what counts as a change, what a
  statement that stores or changes many rows does, and where the store's
  code is not asked at all.
- Two columns that must be there in every row reach into the tests of
  three earlier tasks, which write rows with plain SQL or list the columns
  of a table: twelve tests (six functions) of DAT-005, DAT-028 and DAT-029
  change.
- The rule would reach into a fourth file of existing tests, the tables
  that the unit tests of `broken_rules` make by hand, and has more than
  ten cases of its own (a column missing, of another type, one that may be
  empty, one the table sets, one nothing sets).

The rule is to choose the smaller task (CLAUDE.md §1). So:

1. DAT-031 – Every table's timestamps. The clock, the two columns on
   `Base`, and what sets them. This is the task that is planned now.
2. DAT-032 – A table without its timestamps is named. The rule in
   `broken_rules`. It follows. Until it is done, nothing but `Base` itself
   sees to it that a table has the two times; there is no table yet.

"DAT-030 – Text that must not be empty" and "DAT-026 – The models and the
migrated schema agree" follow as before.

What the planner tried for DAT-031 (Linux, Python 3.13.18 with SQLite
3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv
0.11.32), on `main` at `a34cfbe`:

- With only the two modules changed, 12 of the existing tests failed, all
  in the three files of tests that write rows with plain SQL or list the
  columns of a table; the other 351 backend tests passed.
- 20 new tests, 18 of them against a real SQLite file. The full run: 19
  of 19 gates passed, "Tests: 1013 passed, 0 failed, 0 skipped." (backend
  tests 383).
- 135 of 135 planted defects detected: 23 new ones, all 63 of
  DAT-029 and all 49 of DAT-028, planted again because their tests
  changed.
- The two times are set by the store's code when the statement runs, with
  SQLAlchemy's `default` and `onupdate` of a column. That covers rows
  stored and changed through a model and through `insert` and `update` of
  a model; each is a test.
- For a new row to get one reading of the clock, the default of
  `updated_at` reads the value `created_at` got. SQLAlchemy's own way of
  reading it (`get_current_parameters`) fails for a statement that stores
  several rows at once (`KeyError`), so the function takes the row's
  values as SQLAlchemy holds them, and three tests store two rows in three
  ways.
- A statement that stores a row or changes the one that is there
  (`INSERT … ON CONFLICT DO UPDATE`) does not set `updated_at` when it
  changes a row: tried, and a test says so. The store's code has no such
  statement; `DATABASE.md` says that the first one has to set it.
- In trial pull request #82 (closed without merging), exactly the twelve
  files of the trial ran on GitHub (run 44501284214): "All gates (Linux)"
  and "All gates (Windows)" green, each log ending `19 of 19 gates passed.`
  and `Tests: 1013 passed, 0 failed, 0 skipped.`, with 383 backend tests on
  both machines (Python 3.12.16 on Linux, 3.12.10 on Windows); "Build the
  site", "Publish the site" and "Check the published site" skipped.

Phase 2 has 40 tasks, 13 verified, and the project 247.

Next task: DAT-031 – Every table's timestamps.

### DAT-031 – Every table's timestamps (2026-11-19)

TASK: DAT-031 – Every table's timestamps

Implementation: Complete (builder thread, pull request #83). The store
has one clock, `now()` in `motosphere.db.times`. `Base` gives every model
the columns `created_at` and `updated_at`, the last two of its table:
times in the store's form, required, with no value from the table
itself. The store's code sets them when a statement stores or changes a
row: a new row gets one reading of the clock in both, a changed row a new
`updated_at`. A test sets the clock with the new fixture `clock`. There is
no model and no table yet. Exactly the 12 planned files; all are identical
to the planner's trial. No new package.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  1013 passed, 0 failed, 0 skipped." Backend tests: 383 (363 before, 20
  new).
- Planted defects in the two modules: 135, and 135 of 135 detected: 23
  new ones, all 63 of DAT-029 and all 49 of DAT-028, among them the
  plan's sixteen prove-it steps, with the results the plan gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44502765544, the pull request's commit (`e1d3ea4`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 1013 passed, 0 failed, 0 skipped.", with 383
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44504725449, for `main` after the merge (`8db8664`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 842/842 passed (repository 41, script tests
206, backend 383, frontend 212). Browser tests: 171/171 passed.
Database tests: 18 of the new tests store and change rows in a real
SQLite file, on Linux and on Windows; no mock of a database is used. The
clock is the one thing a test sets.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 1013/1013 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: `broken_rules` does not yet name a table without the two
times; that is DAT-032, the next task. A change written with plain SQL does
not set `updated_at`, and neither does a statement that stores a row or
changes the one that is there (`INSERT … ON CONFLICT DO UPDATE`) when it
changes a row; the store's code has neither, each has a test that says so,
and `DATABASE.md` says that the first such statement has to set `updated_at`
itself. The clock is the machine's: if it is set back, a row can be last
changed before it was first stored. A caller can give a row times of its
own, which the rebuild needs, so nothing stops code from doing that
elsewhere. For a new row to get one reading of the clock, the code reads the
row's values as SQLAlchemy holds them while a statement runs
(`current_parameters`, `current_column`); the tests that store rows in three
ways cover it. The builder's report gave the same counts for the full run
and for each of the sixteen prove-it steps, and named no deviation; its Node
was 22.23.5 where the planner's is 22.23.4.

Commit: `8db8664` (squash merge of pull request #83).

Next task: DAT-032 – A table without its timestamps is named.

### DAT-032 – A table without its timestamps is named (2026-11-19)

TASK: DAT-032 – A table without its timestamps is named

Implementation: Complete (builder thread, pull request #85).
`broken_rules` has one more rule and one more sentence, between the key
and the names given by hand: it names a table that does not have
`created_at` and `updated_at` as every table has them (each a time in
the store's form, required, with no value from the table itself and with
one from the store's code by a function that is called; `updated_at` set
anew in that way at a change, `created_at` not). The tables that the unit
tests make by hand got the two times. `Base` did not change, and there is
no model and no table yet. Exactly the 6 planned files; all are identical
to the planner's trial. No new package.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  1032 passed, 0 failed, 0 skipped." Backend tests: 402 (383 before, 19
  new).
- Planted defects in the two modules: 159, and 159 of 159 detected: 24
  new ones in the rule, all 86 of DAT-031 and all 49 of DAT-028, among
  them the plan's seventeen prove-it steps, with the results the plan
  gives.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44511476187, the pull request's commit (`780fbd1`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 1032 passed, 0 failed, 0 skipped.", with 402
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44514137973, for `main` after the merge (`8c01ce1`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 861/861 passed (repository 41, script tests
206, backend 402, frontend 212). Browser tests: 171/171 passed.
Database tests: the task adds none; the rule looks at the models, not at
a file. The three integration tests that ask it about models whose
tables are made in a real SQLite file pass unchanged, on Linux and on
Windows; no mock of a database is used.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 1032/1032 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: the rule sees that the store's code sets the two times by
calling a function, not which function: that it is the store's clock is what
a model gets from `Base` by not naming the two columns. It does not look at
the place of the two columns in the table. Like the other rules it looks at
the models and not at a store's file, so a table made past the models is not
seen; that the models and the migrated schema agree is DAT-026. The test
that holds the real schema to the rules sees only the models whose modules
have been read, which the first model (DAT-006) has to see to. The builder's
report matched the planner's results in every count; the builder's Node was
22.23.5 where the planner's is 22.23.4, and every gate passed on both.

Commit: `8c01ce1` (squash merge of pull request #85).

Next task: DAT-030 – Text that must not be empty.

### PLAN-020 – The check for empty text first, the rule that names a column without it after (2026-11-19)

Not a development task: no application code changed.

PLAN-017 described "DAT-030 – Text that must not be empty" as one way for a
model to say that a column's text must not be empty, and left three things
to the planner's trial. The trial settled them, and found that one part of
the work is a task of its own.

What was left open, and what is settled:

- What counts as empty: text with no characters, and text with nothing
  but white space. White space is the 29 characters Python calls so, the
  ones `str.strip` takes off; the space that cannot be broken, which an
  empty field of a web page usually holds, is one of them.
- Whether text is stored without the white space around it: no. The
  store holds what was collected; tidying is the collectors' work, before
  the text is stored.
- Whether a column of a time gets a check of its form: no, and no task
  follows for it. A check in a table is for what the models cannot
  promise. Empty text can come through a model; a time in another form
  cannot, because the store's type writes every time in the one form
  (DAT-028), and text put there past the models is refused when it is
  read.

The split:

- `Base` gives a table its checks when its model is defined. Tried: a
  column that a subclass of a model adds to its parent's table gets none,
  because it is added after the parent was defined, and a table made
  without a model gets none. A column from a mixin gets its check.
- So something has to name a column without its check, as `broken_rules`
  names a table without the key (DAT-029) and without the two times
  (DAT-032). That is one more rule, with cases and planted defects of its
  own, and it changes a module and a file of tests that the check itself
  does not touch.

The rule is to choose the smaller task (CLAUDE.md §1). So:

1. DAT-030 – Text that must not be empty. The type, the check and what
   SQLite refuses. This is the task that is planned now.
2. DAT-033 – A column without its check for empty text is named. The
   rule in `broken_rules`. It follows. Until it is done, nothing names a
   column without its check; there is no table yet.

"DAT-026 – The models and the migrated schema agree" follows as before.

What the planner tried for DAT-030 (Linux, Python 3.13.18 with SQLite
3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv
0.11.32), on `main` at `a06fbb1`:

- 32 new tests, 26 of them against a real SQLite file; no existing test
  changed. The full run: 19 of 19 gates passed, "Tests: 1064 passed, 0
  failed, 0 skipped." (backend tests 434).
- 35 of 35 planted defects detected, and all 159 of
  DAT-032 again, because `base.py` changes.
- SQLite's `trim` with one argument takes off spaces only, so the check
  names the white space, each character by its number in Unicode. The
  numbers are written out in the code and not asked of Python as the
  program runs, so that the check is the same text on every machine; a
  test holds the list to Python's.
- A first form of the check was written with the table's column itself.
  SQLAlchemy gives such a check to the column's table by itself, so the
  line of `Base` that gives it could be taken out and no test could tell.
  The check is now written with the column's name alone and belongs to no
  table until `Base` gives it to one; tests fail without that line.
- A marker written as text inside `Annotated[...]` fails in SQLAlchemy,
  which takes text there for the name of a class. The marker is the
  column type itself.
- The planner's own tools turned a character written as its number into
  the character itself, in a test file; the lint refused it (RUF001). The
  tests write such characters as their numbers, the plan tells the
  builder to check for it, and the script that writes the plan refuses a
  new file with a character beyond ASCII.
- In trial pull request #86 (closed without merging), exactly the eight
  files of the trial ran on GitHub (run 44518449213): "All gates (Linux)"
  and "All gates (Windows)" green, each log ending `19 of 19 gates passed.`
  and `Tests: 1064 passed, 0 failed, 0 skipped.`, with 434 backend tests on
  both machines (Python 3.12.16 on Linux, 3.12.10 on Windows); "Build the
  site", "Publish the site" and "Check the published site" skipped.

Phase 2 has 41 tasks, 15 verified, and the project 248.

Next task: DAT-030 – Text that must not be empty.

### DAT-030 – Text that must not be empty (2026-11-19)

TASK: DAT-030 – Text that must not be empty

Implementation: Complete (builder thread, pull request #87). One new
module, `motosphere.db.texts`. A model says of a column that its text
must not be empty with the column's type, `Mapped[NotEmpty]`; in the
table the column is TEXT, and `Base` gives the table a check for it,
named `ck_<table>_<column>_not_empty` by the naming rule. The check
refuses text with no characters and text of nothing but white space, the
29 characters Python calls so, written into the check by their numbers.
Text that is not empty is stored as it was given. There is no model and
no table yet. Exactly the 8 planned files; all are identical to the
planner's trial. No existing test changed. No new package.

Independent test run (planner, clean checkout of the pull request with
nothing installed beforehand, Linux, Python 3.13.18 with SQLite 3.53.1,
SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32):

- The full run: 19 of 19 gates passed, exit code 0, with the line "Tests:
  1064 passed, 0 failed, 0 skipped." Backend tests: 434 (402 before, 32
  new).
- Planted defects in the two modules: 35, and 35 of 35 detected, among
  them the plan's fifteen prove-it steps, with the results the plan
  gives. The 159 planted defects of DAT-032 again: 159 of 159 detected.
- None of the three new files holds a character beyond ASCII.
- `git status` clean afterwards.

On GitHub, read by the planner from the runs and job logs:

- Run 44520686616, the pull request's commit (`9641913`): "All gates
  (Linux)" and "All gates (Windows)" green, each log ending "19 of 19
  gates passed." and "Tests: 1064 passed, 0 failed, 0 skipped.", with 434
  backend tests on both machines; "Build the site", "Publish the site"
  and "Check the published site" skipped.
- Run 44523329480, for `main` after the merge (`2dba882`): all five
  jobs green at the first attempt, both gates jobs with the same two
  closing lines, the site republished, and the log of "Check the
  published site" ending
  "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."

Unit and integration tests: 893/893 passed (repository 41, script tests
206, backend 434, frontend 212). Browser tests: 171/171 passed.
Database tests: 26 of the new tests make tables in a real SQLite file and
ask the file what it holds and what it refuses, on Linux and on Windows;
no mock of a database is used.
Type checking: passed. Lint and format: passed. Build: passed.
Browser or integration verification: the deployment succeeded and the
published site is the site that was built. The task changes nothing a
user sees.

Overall applicable tests: 1064/1064 passed (100%), all 19 gates passed, on
both machines.

Status: PASSED – VERIFIED.

Known limitations: `broken_rules` does not yet name a column whose text must
not be empty and that has no check; that is DAT-033, the next task. Until
then a column that a subclass of a model adds to its parent's table, and a
table made without a model, get no check and nothing says so; there is no
table yet. White space is what Python calls so: a character that cannot be
seen and is not white space to Python, such as the space without width, is
content to the check, and a test says so. The store does not tidy text: text
with white space around it is stored as it was given, and cleaning it is the
collectors' work. The list of white space is written out in the code; if a
later version of Python calls another character white space, the test that
holds the list to Python's fails and the list and the checks in the store
have to be changed together, by a migration. A column of a time has no check
of its form, by decision (PLAN-020). The builder's report gave the same
numbers as the planner's run, all fifteen prove-it steps with the plan's
results, and no deviation from the plan; the builder's Node was 22.23.5.

Commit: `2dba882` (squash merge of pull request #87).

Next task: DAT-033 – A column without its check for empty text is named.
