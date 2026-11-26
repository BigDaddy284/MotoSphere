# MotoSphere – Tasks

The running task list for the whole build. One task is in progress at a time.
A task is `PASSED – VERIFIED` only when 100% of applicable tests pass in the
planner's independent test run. See `docs/WORKFLOW.md` for the loop and
`docs/plans/<TASK-ID>.md` for each task's implementation plan.

Statuses (CLAUDE.md §4): `NOT STARTED`, `IN PROGRESS`, `TESTING`,
`FAILED – FIX REQUIRED`, `PASSED – VERIFIED`, `BLOCKED – EXTERNAL DEPENDENCY`.

## Summary

| Phase | Scope | Tasks | Verified |
|---|---|---|---|
| 1 | Foundation (FND) | 43 | 43 |
| 2 | Data store and published data (DAT, PUB) | 57 | 35 |
| 3 | Interactive 3D Earth (GLB) | 21 | 0 |
| 4 | Geographic marker system (MRK) | 12 | 0 |
| 5 | Track directory (TRK) | 20 | 0 |
| 6 | Event collection (EVT) | 14 | 0 |
| 7 | Championships (CHP) | 13 | 0 |
| 8 | Race results (RES) | 14 | 0 |
| 9 | Riders and teams (RDR) | 12 | 0 |
| 10 | Automated collection and administration (COL, ADM) | 24 | 0 |
| 11 | Search and comparison (SRC, CMP) | 14 | 0 |
| 12 | News and historical expansion (NWS, HIS) | 10 | 0 |
| 13 | Performance and deployment (PRF, DEP) | 10 | 0 |

**Current task:** DAT-047 – A change is written with its history.

**Hosting decision (owner, 2026-11-17):** GitHub Pages only, with no server.
Scheduled jobs collect the data and publish it as files that the globe reads
(`ARCHITECTURE.md`). Tasks FND-001 to FND-013 were planned before that
decision; everything after FND-013 follows it. Three foundation tasks were
added for it (FND-020 to FND-022).

**No offline version (owner, 2026-11-19):** "actually dont build the offline version". MotoSphere
is the published site and nothing else: there are no commands that build,
serve and open a private copy on a PC, and the owner's PC is not needed
for any check. The commands for working on the project stay the same on
Windows and Linux, and GitHub runs every gate on both (`ARCHITECTURE.md`
§12).

**Visual identity (owner, 2026-11-17):** the owner supplied the Graphite
theme and the Sky Classic icon style (`docs/design/`). Two foundation tasks
were added for them (FND-023 and FND-024).

The layout task was also split into smaller ones: regions (FND-014), section
navigation (FND-025) and the current date (FND-026). The data client task
was split into three: reading the manifest (FND-016), serving real published
data locally (FND-027) and the data status in the top bar (FND-028). One
task was added after it (FND-029), so that the browser tests can also cover
a manifest the server does not have. The check runner task was split into
three: the runner itself (FND-017), test counts and skipped tests (FND-030)
and the Python files outside the pipeline (FND-031). Continuous integration
was split into two: Linux (FND-018) and Windows (FND-032). Where an earlier
entry says the first Windows run is FND-018, that run is now FND-032. The
GitHub Pages task was split into two: the application served from the
site's path (FND-022) and the deployment itself (FND-034). One task was
added before them (FND-033), after a security advisory for a build tool
started failing the dependency audit on 2026-11-17. Checking the published
site after each deployment became a task of its own (FND-035), and then
two: the check itself (FND-035) and the job that runs it (FND-037). One
task was added before them (FND-036), when the advisory was no longer
reported on 2026-11-18 and its exception had to go. Three tasks were added
for phone screens (FND-038 to FND-040), after the owner opened the
published site on a phone; the planner's trial made them five (FND-038 to
FND-042). The first was split into where an open panel is drawn (FND-038)
and which panels are open (FND-040), with the top bar between them
(FND-039), because each needs the one before it. The last was split into
controls a finger can hit (FND-041) and the height of the layout
(FND-042), because only the first of the two can be shown in the test
browser. The Windows task (FND-019) became four (PLAN-010): a check of the
tools a computer needs (FND-019), the built site served on this computer
(FND-043), one command that builds the site and opens it (FND-044), and
the commands a Windows user starts (FND-045). The first three are Python,
written once for every system and tested on Linux and on GitHub's Windows
machine; only the last needs the owner's Windows 11 PC. On 2026-11-19 the
owner decided against an offline version, and the three of them that had
not started (FND-043 to FND-045) were taken out again (PLAN-011); FND-019
was built by then and stays.

Added tasks are listed where they fall in dependency order, so task numbers
in Phase 1 are not strictly ascending.

Phases 1 and 2 are specified in full below (Phase 2 since PLAN-012).
Phases 3–13 are listed as an ordered roadmap of named tasks; each phase is
expanded into full task entries (with acceptance criteria and required
tests) before its first task starts, and any task that turns out too large
to test thoroughly is split further at that point. Task counts above
therefore grow rather than shrink, unless the owner takes work out.

---

# Phase 1 – Foundation (FND)

Goal: an empty-but-real application, live on GitHub Pages. A data pipeline
command that exports a first published data file, a frontend shell with the
final layout regions that reads it, every quality gate wired up, one command
that runs all gates, automatic deployment, and documented local use on
Windows 11. No database and no globe yet.

### FND-001 – Repository hygiene baseline
- **Status:** PASSED – VERIFIED
- **Objective:** Keep the repository clean and consistent on Windows and Linux before any code lands.
- **Description:** Add `.gitignore`, `.gitattributes`, `.editorconfig`, `README.md`, and the remaining required document stubs (`DATA_SOURCES.md`, `DATABASE.md`, `TESTING.md`, `CHANGELOG.md`). Add a dependency-free repository check suite under `tests/repo/`.
- **Acceptance criteria:**
  1. Generated files, virtual environments, caches, build output and `.env` files are ignored; source files, lock files and `.env.example` are not.
  2. Text files are normalised to LF in the repository; `.ps1`, `.bat`, `.cmd` check out as CRLF; common binary types are marked binary.
  3. All nine documents required by CLAUDE.md §16, plus README.md, exist and are non-empty.
  4. README links to every project document and every relative link resolves.
  5. No secret or environment file is tracked.
- **Tests required:** `python -m unittest discover -s tests/repo -v` (9 tests, stdlib only).
- **Tests executed:** Repository checks, 9 tests, on Python 3.13.18 and Python 3.12.3 (Linux, Git 2.43.0), in a clean checkout of pull request #1. Ten deliberate defects (mutation checks) each detected by the suite. Real-file check: `.ps1` checks out CRLF, `.py` checks out LF.
- **Passed / Failed:** 9 / 0
- **Verification status:** Verified by the planner on 2026-11-16. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `9acea2a`
- **Plan:** `docs/plans/FND-001.md`

### FND-002 – Backend project skeleton
- **Status:** PASSED – VERIFIED
- **Objective:** A Python project that installs reproducibly and runs a test.
- **Description:** Create `backend/` as a uv project (`pyproject.toml`, committed `uv.lock`, `requires-python >= 3.12`), `src/motosphere/` package exposing `__version__`, pytest configured, smoke tests.
- **Acceptance criteria:**
  1. `uv sync --locked` succeeds from a clean checkout and installs the project itself.
  2. `uv run pytest` collects and passes exactly the four planned tests.
  3. `motosphere.__version__` equals the version in `pyproject.toml`, which is its only source.
  4. The lock file is committed and current; no virtualenv or cache is tracked.
  5. README, TESTING.md and CHANGELOG.md describe the new gate.
- **Tests required:** backend pytest (4 tests); repository checks (9 tests); `uv lock --check`.
- **Tests executed:** In a clean checkout of pull request #2 (Linux, uv 0.11.32, pytest 9.2.0): `uv lock --check`, `uv sync --locked`, backend pytest on Python 3.13.18 and 3.12.3 (4 tests each, no warnings), repository checks (9 tests). Five deliberate defects (version literal, warning in a test, unknown marker, malformed version, stale lock file) each detected.
- **Passed / Failed:** 13 / 0 (backend 4, repository 9), plus lock check and locked sync passed
- **Verification status:** Verified by the planner on 2026-11-16. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `6daf3ea`
- **Plan:** `docs/plans/FND-002.md`

### FND-003 – Backend linting and formatting
- **Status:** PASSED – VERIFIED
- **Objective:** Enforce one code style for Python automatically.
- **Description:** Add ruff (lint + format) as a locked dev dependency with configuration in `backend/pyproject.toml`, covering `backend/src` and `backend/tests`. Root-level Python (`tests/repo`, later `scripts/`) joins the gate with the check runner in FND-017.
- **Acceptance criteria:**
  1. `uv run ruff check .` passes in `backend/` with the planned rule set, including security rules.
  2. `uv run ruff format --check .` passes in `backend/`.
  3. Both gates fail on a deliberate violation (demonstrated, then removed).
  4. The lock file is current; all earlier gates still pass.
  5. README, TESTING.md and CHANGELOG.md describe the new gates.
- **Tests required:** ruff check; ruff format check; backend pytest (4); repository checks (9); `uv lock --check`.
- **Tests executed:** In a clean checkout of pull request #3 (Linux, uv 0.11.32, ruff 0.17.5): `uv lock --check`, `uv sync --locked`, ruff check, ruff format check, backend pytest on Python 3.13.18 and 3.12.3 (4 tests each), repository checks (9 tests). Seven planted violations (unsorted imports, unused import, shell call, partial executable path, print, naive datetime, `eval`) all reported by lint; planted mis-formatting reported by the format check.
- **Passed / Failed:** 13 / 0 tests (backend 4, repository 9); lint, format and lock gates passed
- **Verification status:** Verified by the planner on 2026-11-16. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `2e3edaf`
- **Plan:** `docs/plans/FND-003.md`

### FND-004 – Backend type checking
- **Status:** PASSED – VERIFIED
- **Objective:** Make static type checking a mandatory gate.
- **Description:** Add mypy (locked dev dependency) in strict mode for `backend/src` and `backend/tests`, configured in `backend/pyproject.toml`.
- **Acceptance criteria:**
  1. `uv run mypy` passes in `backend/` with strict settings and checks both `src` and `tests`.
  2. The gate fails on a deliberate type error and on an unannotated function (demonstrated, then removed).
  3. No `# type: ignore`, no per-module relaxations.
  4. The lock file is current; all earlier gates still pass.
  5. README, TESTING.md and CHANGELOG.md describe the new gate.
- **Tests required:** mypy; ruff check; ruff format check; backend pytest (4); repository checks (9); `uv lock --check`.
- **Tests executed:** In a clean checkout of pull request #4 (Linux, uv 0.11.32, mypy 2.4.1): `uv lock --check`, `uv sync --locked`, mypy on Python 3.13.18 and 3.12.3, ruff check, ruff format check, backend pytest on both Pythons (4 tests each), repository checks (9 tests). Five planted type defects (wrong argument type, unannotated function in `src`, unannotated test, unreachable code, bare `type: ignore`) all reported.
- **Passed / Failed:** 13 / 0 tests (backend 4, repository 9); type-check, lint, format and lock gates passed
- **Verification status:** Verified by the planner on 2026-11-16. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `ebd84ce`
- **Plan:** `docs/plans/FND-004.md`

### FND-005 – Backend settings module
- **Status:** PASSED – VERIFIED
- **Objective:** Environment-based configuration with no secrets in source control.
- **Description:** `motosphere.core.settings` using pydantic-settings: env prefix `MOTOSPHERE_`, optional `backend/.env`, typed immutable fields for environment name, API host, API port and log level. Commit `backend/.env.example` with safe values. Test isolation fixture so a developer's real environment never affects tests. (Allowed origins moved to API-008, where CORS is introduced.)
- **Acceptance criteria:**
  1. Defaults load with no environment and no `.env` file.
  2. Environment variables override defaults; `.env` overrides defaults; real environment overrides `.env`.
  3. Invalid values and unknown keys in `.env` fail at load with an error naming the setting.
  4. Settings are immutable; `get_settings()` is cached.
  5. `backend/.env.example` lists every setting with its default and no secret, and is proven valid by a test.
  6. Tests are isolated from the developer's real environment and `.env`.
  7. README documents configuration; all earlier gates still pass.
- **Tests required:** backend pytest (22: 18 new settings tests + 4 existing); mypy; ruff check; ruff format check; repository checks (9); `uv lock --check`.
- **Tests executed:** In a clean checkout of pull request #5 (Linux, uv 0.11.32, pydantic 2.14.3, pydantic-settings 2.16.3): `uv lock --check`, `uv sync --locked`, mypy and backend pytest on Python 3.13.18 and 3.12.3 (22 tests each, no warnings), ruff check, ruff format check, repository checks (9 tests). Isolation check with a real `backend/.env` and hostile shell variables. Real behaviour from the command line (file value read, environment beats file, misspelt key rejected, out-of-range port rejected). Eleven planted defects all detected.
- **Passed / Failed:** 31 / 0 tests (backend 22, repository 9); type-check, lint, format and lock gates passed
- **Verification status:** Verified by the planner on 2026-11-16. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `dfe2687`
- **Plan:** `docs/plans/FND-005.md`

### FND-006 – Backend logging configuration
- **Status:** PASSED – VERIFIED
- **Objective:** Consistent, configurable logs for the API and, later, the worker.
- **Description:** `motosphere.core.logging_config.configure_logging(settings)`: root level from settings; one named handler writing to standard error; one-line format with UTC timestamp, level, logger name and message; line breaks in messages escaped so untrusted text cannot forge log lines; idempotent.
- **Acceptance criteria:**
  1. The root log level follows `settings.log_level` for all five levels.
  2. Exactly one MotoSphere handler is installed, however often the function is called; handlers it did not create are left alone.
  3. Output lines match the documented format with a UTC timestamp.
  4. Messages below the configured level are not written.
  5. Carriage returns and line feeds inside a message are escaped; exception tracebacks are still written in full.
  6. All earlier gates still pass with no suppressions.
- **Tests required:** backend pytest (36: 14 new logging tests + 22 existing); mypy; ruff check; ruff format check; repository checks (9); `uv lock --check`.
- **Tests executed:** In a clean checkout of pull request #6 (Linux, uv 0.11.32): `uv lock --check`, `uv sync --locked`, mypy and backend pytest on Python 3.13.18 and 3.12.3 (36 tests each, no warnings), ruff check, ruff format check, repository checks (9 tests). Real output from the command line (one escaped line on standard error, nothing on standard output, debug line only at debug level, UTC timestamp under a Tokyo time zone). Seven planted defects all detected.
- **Passed / Failed:** 45 / 0 tests (backend 36, repository 9); type-check, lint, format and lock gates passed
- **Verification status:** Verified by the planner on 2026-11-16. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `de01322`
- **Plan:** `docs/plans/FND-006.md`

### FND-007 – API application factory and health endpoint
- **Status:** PASSED – VERIFIED
- **Objective:** A FastAPI application that answers a health check.
- **Description:** `motosphere.api.app.create_app(settings)` builds an independent application each time; `GET /api/health` returns status, application name and version and is never cached. API documentation is served under `/api/docs` and the schema under `/api/openapi.json`.
- **Acceptance criteria:**
  1. `GET /api/health` returns 200 and exactly `{"status": "ok", "name": "MotoSphere", "version": <package version>}` with `Cache-Control: no-store`.
  2. Other methods on the health path return 405; unknown paths return a JSON 404.
  3. The OpenAPI schema describes the endpoint and its response model; documentation is served only under `/api/`.
  4. `create_app` uses the settings it is given, falls back to `get_settings()`, and returns a new application on each call.
  5. All earlier gates still pass with no suppressions.
- **Tests required:** backend pytest (46: 10 new API tests + 36 existing); mypy; ruff check; ruff format check; repository checks (9); `uv lock --check`.
- **Tests executed:** In a clean checkout of pull request #7 (Linux, uv 0.11.32, fastapi 0.163.1, starlette 1.10.0, httpx2 2.16.2): `uv lock --check`, `uv sync --locked`, mypy and backend pytest on Python 3.13.18 and 3.12.3 (46 tests each, no warnings), ruff check, ruff format check, repository checks (9 tests). Seven planted defects all detected.
- **Passed / Failed:** 55 / 0 tests (backend 46, repository 9); type-check, lint, format and lock gates passed
- **Verification status:** Verified by the planner on 2026-11-16. Verified through the in-process test client only; the first real HTTP check is FND-008. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `70a32c3`
- **Plan:** `docs/plans/FND-007.md`

### FND-008 – Backend run command
- **Status:** PASSED – VERIFIED
- **Objective:** Start the API with one documented command.
- **Description:** `uv run python -m motosphere` loads settings, configures logging and serves the application with uvicorn on the configured host and port. Configuration mistakes produce a one-line message and exit code 2 instead of a traceback.
- **Acceptance criteria:**
  1. The command starts a real server that answers `GET /api/health` over real HTTP on the configured port.
  2. All server output, including uvicorn's own, uses the MotoSphere log format on standard error.
  3. The server stops cleanly on an interrupt.
  4. Invalid configuration exits with code 2 and a one-line message naming the setting; a port already in use exits non-zero with an error line.
  5. README documents how to start and stop the API; all earlier gates still pass with no suppressions.
- **Tests required:** backend pytest (55: 4 new unit + 5 new integration + 46 existing); mypy; ruff check; ruff format check; repository checks (9); `uv lock --check`.
- **Tests executed:** In a clean checkout of pull request #8 (Linux, uv 0.11.32, uvicorn 0.54.0): `uv lock --check`, `uv sync --locked`, backend pytest three times in a row on Python 3.13.18 and once on 3.12.3 (55 tests each, no warnings, no process left behind), mypy on both, ruff check, ruff format check, repository checks (9 tests). Real server exercised with curl: health 200 with `no-store`, documentation 200, unknown path 404, clean stop on interrupt with exit code 0, port and log level taken from `backend/.env`, configuration errors exit with code 2 and one line. Seven planted defects all detected.
- **Passed / Failed:** 64 / 0 tests (backend 55, repository 9); type-check, lint, format and lock gates passed
- **Verification status:** Verified by the planner on 2026-11-17 on Linux. The Windows-only branches of the integration test helper have not been executed; their first run is the Windows CI job in FND-018.
- **Commit:** `219166f`
- **Plan:** `docs/plans/FND-008.md`

### FND-009 – Frontend project skeleton
- **Status:** PASSED – VERIFIED
- **Objective:** A React + TypeScript project that type-checks and builds.
- **Description:** Create `frontend/` with Vite, React and TypeScript in strict mode, a committed `package-lock.json`, and a minimal `App` that renders the application name and tagline. No styling, tests or lint yet.
- **Acceptance criteria:**
  1. `npm ci` succeeds from a clean checkout.
  2. `npm run typecheck` passes with strict settings.
  3. `npm run build` produces `dist/index.html` and a script bundle; the built page, served by `npm run preview`, shows the application name in a real browser with no console errors.
  4. `node_modules`, `dist` and build caches are not tracked; no template demo content remains.
  5. README, TESTING.md and CHANGELOG.md describe the frontend commands; all earlier gates still pass.
- **Tests required:** frontend type check; frontend build; browser check of the built page (planner); repository checks (9); backend gates unchanged (55 tests).
- **Tests executed:** In a clean checkout of pull request #9 (Linux, Node 22.23.4, npm 10.9.9, vite 8.3.8, react 19.3.1, typescript 7.0.2): `npm ci`, type check, build, `npm audit` (0 vulnerabilities), repository checks (9 tests), backend pytest (55 tests). Headless Chromium against both `npm run preview` (built page) and `npm run dev`: title, language, one main landmark, visible heading and tagline, no console errors or warnings, no failed requests. Five planted type defects all reported.
- **Passed / Failed:** 64 / 0 tests (backend 55, repository 9); frontend type-check and build gates passed; browser check passed
- **Verification status:** Verified by the planner on 2026-11-17. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `76b694e`
- **Plan:** `docs/plans/FND-009.md`

### FND-010 – Frontend unit testing
- **Status:** PASSED – VERIFIED
- **Objective:** Component tests run with one command.
- **Description:** Add Vitest, jsdom and Testing Library; `npm test` runs the suite once and exits. First tests cover `App` and the entry point.
- **Acceptance criteria:**
  1. `npm test` runs once, passes the five planned tests and exits 0; it exits non-zero when an assertion fails.
  2. Tests query the page the way a user perceives it (roles and text).
  3. Test files are type-checked by `npm run typecheck` and are not part of the production bundle.
  4. README, TESTING.md and CHANGELOG.md describe the new gate; all earlier gates still pass.
- **Tests required:** frontend unit tests (5); frontend type check; frontend build; repository checks (9); backend gates unchanged (55 tests).
- **Tests executed:** In a clean checkout of pull request #10 (Linux, Node 22.23.4, npm 10.9.9, vitest 5.1.0, jsdom 31.0.1, @testing-library/react 16.3.3, @testing-library/jest-dom 7.0.1): `npm ci`, frontend unit tests (5), type check, build (bundle unchanged at 219.76 kB, no test code in `dist/`), `npm audit` (0 vulnerabilities), repository checks (9 tests). Six planted defects all detected. Backend gates (lock check, mypy, ruff lint and format, 55 tests) re-run on `main` after the merge.
- **Passed / Failed:** 69 / 0 tests (frontend 5, backend 55, repository 9); frontend type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `0914ec5`
- **Plan:** `docs/plans/FND-010.md`

### FND-011 – Frontend linting and formatting
- **Status:** PASSED – VERIFIED
- **Objective:** Make likely bugs, unsafe patterns, accessibility mistakes and code style an automatic gate for the frontend.
- **Description:** oxlint (React hooks, accessibility, import, Vitest and TypeScript rules; raw HTML rendering, `eval`, `any` and console output banned) with `npm run lint`, and Prettier with `npm run format:check`. oxlint replaces the ESLint originally planned because the project uses the native TypeScript 7 compiler (see `ARCHITECTURE.md` §3).
- **Acceptance criteria:**
  1. `npm run lint` exits 0 on the project and non-zero on a violation, naming the rule and file.
  2. `npm run format:check` exits 0 on the project and non-zero on a badly formatted file.
  3. The linter configuration is exactly the planned one; no suppressions anywhere in `frontend/`.
  4. No application or test source file changed; only `tsconfig.json` is reformatted.
  5. README, TESTING.md and CHANGELOG.md describe the new gates; all earlier gates still pass.
- **Tests required:** frontend lint; frontend format check; frontend unit tests (5); frontend type check; frontend build; repository checks (9); backend untouched (55 tests).
- **Tests executed:** In a clean checkout of pull request #11 (Linux, Node 22.23.4, npm 10.9.9, oxlint 1.94.0, prettier 3.10.1): `npm ci`, lint (7 files), format check, frontend unit tests (5), type check, build (bundle unchanged), `npm audit` (0 vulnerabilities), repository checks (9 tests). Eight planted defects all reported. Backend not re-run: no backend file has changed since its 55/55 run on commit `0914ec5`.
- **Passed / Failed:** 14 / 0 tests (frontend 5, repository 9); frontend lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `4aa7988`
- **Plan:** `docs/plans/FND-011.md`

### FND-012 – Browser test infrastructure
- **Status:** PASSED – VERIFIED
- **Objective:** Verify the real built application in a real browser with one command.
- **Description:** Add Playwright (Chromium, version pinned exactly) under `frontend/e2e/`; `npm run e2e` builds the app, serves the build and opens it headlessly. A shared test fixture fails any browser test in which the page logs an error or warning, throws, or has a failed request.
- **Acceptance criteria:**
  1. `npm run e2e` builds, serves and tests the application headlessly, reports 4 passed, and exits non-zero when a browser test fails.
  2. A console error or warning, uncaught error, failed request or HTTP error status fails the test it happens in.
  3. Browser test files pass lint, format check and type check; the unit test run still collects exactly 5 tests.
  4. Nothing under `frontend/src/` changed; no report or result files are left visible to Git.
  5. README, TESTING.md and CHANGELOG.md describe the new gate; all earlier gates still pass.
- **Tests required:** browser tests (4); frontend lint, format check, unit tests (5), type check, build; repository checks (9); backend untouched (55 tests).
- **Tests executed:** In a clean checkout of pull request #12 (Linux, Node 22.23.4, npm 10.9.9, Playwright 1.63.0 with its matching headless Chromium): `npm ci`, lint (10 files), format check, frontend unit tests (5), type check, build, browser tests (4), `npm audit` (0 vulnerabilities), repository checks (9 tests). Eleven planted defects all detected. Backend not re-run: no backend file has changed since its 55/55 run on commit `0914ec5`.
- **Passed / Failed:** 18 / 0 tests (browser 4, frontend 5, repository 9); frontend lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `e806b63`
- **Plan:** `docs/plans/FND-012.md`

### FND-013 – Dark theme design tokens
- **Status:** PASSED – VERIFIED
- **Objective:** One source of truth for colours, type, spacing, shape and motion, proven readable by tests.
- **Description:** CSS custom properties for the dark motorsport theme (surfaces, text, one restrained accent, status colours, focus ring, system fonts and type scale, spacing, radii, motion) and base styles (reset, dark colour scheme, typography, keyboard focus ring, reduced motion). No web fonts.
- **Acceptance criteria:**
  1. Tokens are defined once, in `tokens.css`; every style sheet takes its colours from them, enforced by tests (no raw colours elsewhere, no unknown token names).
  2. Contrast: main text ≥ 7:1, all other text and status colours ≥ 4.5:1, focus ring ≥ 3:1, on all three surfaces.
  3. In the browser the page has the dark background, light text, system font, no page margin, a visible keyboard focus ring, and no motion when reduced motion is requested.
  4. `npm test` reports 46 passed; `npm run e2e` reports 9 passed; all earlier gates pass.
- **Tests required:** frontend unit tests (46, of which 41 new: contrast maths 10, tokens and style sheets 31); browser tests (9, of which 5 new); frontend lint, format check, type check, build; repository checks (9); backend untouched (55 tests).
- **Tests executed:** On pull request #13 merged with `main` in a clean checkout (Linux, Node 22.23.4, npm 10.9.9): `npm ci`, lint, format check, frontend unit tests (46), type check, build, browser tests (9), `npm audit` (0 vulnerabilities), repository checks (9 tests). Eleven planted defects all detected. Backend not re-run: no backend file has changed since its 55/55 run on commit `0914ec5`.
- **Passed / Failed:** 64 / 0 tests (frontend unit 46, browser 9, repository 9); frontend lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. The colours are provisional: the owner's Graphite theme replaces them in FND-023. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `7e04f76`
- **Plan:** `docs/plans/FND-013.md`

### FND-023 – Apply the owner's Graphite theme
- **Status:** PASSED – VERIFIED
- **Objective:** The application uses the colours and font the owner chose.
- **Description:** Replace the provisional colour tokens from FND-013 with the owner's Graphite theme (soft charcoal greys with a sky-blue accent, `docs/design/graphite-theme/`): bar, canvas, panel, window, control and pressed surfaces, borders, text, secondary and disabled text, the blue accent family and selection colour, and the Segoe UI font stack. Status colours stay. Base styles, contrast tests and browser tests follow the new names and values.
- **Acceptance criteria:**
  1. Every Graphite colour appears as a token with exactly the owner's value; no provisional colour remains.
  2. Contrast is tested with the real numbers: main text ≥ 7:1 and secondary text ≥ 4.5:1 on every surface they are used on; link and focus colour ≥ 4.5:1 on bar, canvas, panel and window. White on the accent blue measures 3.89:1, which meets the 3:1 level for large or bold labels only; the test records that limit and the documentation states it.
  3. In the browser the page shows the Graphite canvas colour as its background, the Graphite text colour, the Segoe UI font stack and the sky-blue focus ring.
  4. `npm test` reports 69 passed; `npm run e2e` reports 9 passed; all earlier gates pass.
- **Tests required:** frontend unit tests (69: 47 contrast cases, a check of the 16 Graphite colours against the owner's values, token and style sheet checks, contrast maths, existing tests); browser tests (9); frontend lint, format check, type check, build; repository checks (9); backend untouched (55 tests).
- **Tests executed:** In a clean checkout of pull request #14 (Linux, Node 22.23.4, npm 10.9.9): `npm ci`, lint, format check, frontend unit tests (69, including 47 contrast cases), type check, build, browser tests (9), `npm audit` (0 vulnerabilities), repository checks (9 tests). The 16 Graphite tokens were also compared directly with the owner's reference files. Eight planted defects all detected. Backend not re-run: no backend file has changed since its 55/55 run on commit `0914ec5`.
- **Passed / Failed:** 87 / 0 tests (frontend unit 69, browser 9, repository 9); frontend lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. White on the accent blue is 3.89:1 (the owner's colours, used as supplied; bold button labels only). Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `15a9f59`
- **Plan:** `docs/plans/FND-023.md`

### FND-014 – Application shell layout
- **Status:** PASSED – VERIFIED
- **Objective:** The final screen regions, with the globe area dominant.
- **Description:** Top bar (name and tagline), sections panel on the left, globe stage in the centre and details panel on the right, as semantic landmarks in the Graphite surfaces, sized by layout tokens. Regions only: the section list, collapsing, data status and globe are later tasks, so the sections panel and stage are empty for now and no placeholder controls are added.
- **Acceptance criteria:**
  1. The four regions render as named landmarks, once each, in reading order; the name and tagline are in the top bar; the details panel shows its empty-state sentence.
  2. At 1366×768 and 1920×1080 the regions fill the screen exactly without overlapping, the stage is wider than half the screen and wider than both panels together, and the page does not scroll.
  3. The regions use the Graphite bar, panel and canvas colours through tokens.
  4. `npm test` reports 75 passed; `npm run e2e` reports 16 passed; all earlier gates pass.
- **Tests required:** frontend unit tests (75, of which 6 new component tests); browser tests (16, of which 7 new: three per viewport and one for surfaces); frontend lint, format check, type check, build; repository checks (9); backend untouched (55 tests).
- **Tests executed:** In a clean checkout of pull request #15 (Linux, Node 22.23.4, npm 10.9.9): `npm ci`, lint, format check, frontend unit tests (75), type check, build, browser tests (16), `npm audit` (0 vulnerabilities), repository checks (9 tests). Nine planted defects all detected. Backend not re-run: no backend file has changed since its 55/55 run on commit `0914ec5`.
- **Passed / Failed:** 100 / 0 tests (frontend unit 75, browser 16, repository 9); frontend lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. Desktop sizes only (from 1366×768); no small-screen layout yet. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `0bfd7e1`
- **Plan:** `docs/plans/FND-014.md`

### FND-025 – Section navigation
- **Status:** PASSED – VERIFIED
- **Objective:** The user can see and choose the application's sections.
- **Description:** The sections panel lists Explore, Events, Tracks, Championships, Riders, Teams, Results, News and Statistics as buttons. One section is current (Explore at start); choosing another by mouse or keyboard makes it current. The choice is application state held in `App` that later tasks use to decide what the panels show; nothing else reacts to it yet, and it is not stored in the address bar. Adds one development dependency, `@testing-library/user-event`, so that unit tests can press keys the way a user does.
- **Acceptance criteria:**
  1. The nine sections are listed in that order as buttons in a list inside the sections panel.
  2. Exactly one is marked current with `aria-current="page"`; it is Explore at start.
  3. Clicking a section, or reaching it with Tab and pressing Enter or Space, makes it current.
  4. The current section is shown in the Graphite selection style, other sections show a hover style, and keyboard focus is visible; all colours come from tokens.
  5. At 1366×768 the nine sections fit in the panel without scrolling.
  6. `npm test` reports 86 passed; `npm run e2e` reports 21 passed; all earlier gates pass.
- **Tests required:** frontend unit tests (86, of which 11 new: 3 for the section data, 5 for the list component, 3 for selection in the application); browser tests (21, of which 5 new: list and start state, click and selection style, keyboard and focus ring, hover, fit at 1366×768); frontend lint, format check, type check, build; `npm audit`; repository checks (9); backend untouched (55 tests).
- **Tests executed:** In a clean checkout of pull request #16 (Linux, Node 22.23.4, npm 10.9.9): `npm ci`, lint, format check, frontend unit tests (86), type check, build, browser tests (21, three runs in a row), `npm audit` (0 vulnerabilities), repository checks (9 tests). Twelve planted defects all detected. Backend not re-run: no backend file has changed since its 55/55 run on commit `0914ec5`.
- **Passed / Failed:** 116 / 0 tests (frontend unit 86, browser 21, repository 9); frontend lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. Choosing a section changes only which item is marked current; nothing else reacts yet and the choice is not kept in the address bar. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `385d15e`
- **Plan:** `docs/plans/FND-025.md`

### FND-015 – Collapsible side panels
- **Status:** PASSED – VERIFIED
- **Objective:** Let the user give the globe the whole screen.
- **Description:** A Sections button and a Details button in the top bar close and open the two side panels, by mouse or keyboard. A closed panel stays in the page, hidden, and the globe stage takes its room. The choice is remembered for the browser session (session storage): it survives a reload and ends with the tab. Unknown stored values and unusable storage both mean open. No icons and no animation in this task.
- **Acceptance criteria:**
  1. Each panel closes and opens with its own button, by click, Enter and Space, without affecting the other.
  2. `aria-expanded` on each button matches its panel and `aria-controls` names it.
  3. At 1366×768 the stage runs from 0 to 1006 without the sections panel, from 220 to 1366 without the details panel and from 0 to 1366 with both closed; the page never scrolls.
  4. A closed panel's content cannot be reached with Tab.
  5. The choice survives a reload and does not carry over to a new tab; unknown stored values and unusable storage mean open and the buttons keep working.
  6. With both panels open the layout is unchanged (the FND-014 layout tests pass unmodified).
  7. `npm test` reports 96 passed; `npm run e2e` reports 30 passed; all earlier gates pass.
- **Tests required:** frontend unit tests (96, of which 10 new for the side panels: state, ARIA, keyboard, remembering, bad stored values, storage that throws); browser tests (30, of which 9 new: start state, stage edges for each panel and both, keyboard, keyboard order, reload, new tab, button style); frontend lint, format check, type check, build; `npm audit`; repository checks (9); backend untouched (55 tests).
- **Tests executed:** In a clean checkout of pull request #17 (Linux, Node 22.23.4, npm 10.9.9): `npm ci`, lint, format check, frontend unit tests (96), type check, build, browser tests (30, three runs in a row), `npm audit` (0 vulnerabilities), repository checks (9 tests). Fourteen planted defects all detected. Backend not re-run: no backend file has changed since its 55/55 run on commit `0914ec5`.
- **Passed / Failed:** 135 / 0 tests (frontend unit 96, browser 30, repository 9); frontend lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. The buttons are text only (icons follow the icon task) and the panels open and close without animation. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `98bf3c3`
- **Plan:** `docs/plans/FND-015.md`

### FND-026 – Current date in the top bar
- **Status:** PASSED – VERIFIED
- **Objective:** The top bar shows today's date, as DESIGN.md §12.1 suggests.
- **Description:** Today's date written out in the language of the user's browser, for the day where the user is, in a `time` element at the right-hand end of the top bar. One timer runs to the next local midnight (worked out from the calendar), and the day is also checked whenever the page comes back into view. Only `Date` and `Intl.DateTimeFormat` are used; no date library. The shell gets an `info` slot that the data status will share later.
- **Acceptance criteria:**
  1. The date is shown in a `time` element between the tagline and the Details button, at the right-hand end of the bar, in the secondary text colour.
  2. The wording follows the browser's language (British English, American English and German verified in a real browser).
  3. The day is the day where the user is (Los Angeles: previous day; Tokyo: next day), and `datetime` holds it as `YYYY-MM-DD`.
  4. The date changes at local midnight without a reload, keeps doing so on following days, and catches up when the page comes back into view.
  5. Removing the component leaves no timer and no listener behind.
  6. `npm test` reports 115 passed; `npm run e2e` reports 35 passed; all earlier gates pass.
- **Tests required:** frontend unit tests (115, of which 19 new: 12 for the day functions, 5 for the component with a controlled clock, 1 for the shell slot, 1 for the application), also run in a second time zone; browser tests (35, of which 5 new with emulated language, time zone and clock: London, Los Angeles, Tokyo, midnight change, position and colour); frontend lint, format check, type check, build; `npm audit`; repository checks (9); backend untouched (55 tests).
- **Tests executed:** In a clean checkout of pull request #18 (Linux, Node 22.23.4, npm 10.9.9): `npm ci`, lint, format check, frontend unit tests (115, run with the machine on UTC and again on five other time zones), type check, build, browser tests (35, three runs in a row), `npm audit` (0 vulnerabilities), repository checks (9 tests). First run: 14 of 15 planted defects detected; the task was sent back for one stronger test, and on the fixed pull request all gates were run again and the remaining defect was detected. Backend not re-run: no backend file has changed since its 55/55 run on commit `0914ec5`.
- **Passed / Failed:** 159 / 0 tests (frontend unit 115, browser 35, repository 9); frontend lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. The wording of the date comes from the browser's own language data, so punctuation can differ slightly between browsers. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `5e782de`
- **Plan:** `docs/plans/FND-026.md`

### FND-024 – Application icon in the Sky Classic style
- **Status:** PASSED – VERIFIED
- **Objective:** MotoSphere has its own icon, linked by the page and recognisable at every size it is used.
- **Description:** The owner approved the full design on 2026-11-17: a globe outline with MOTO following the top of the rim and SPHERE the bottom, in Orbitron converted to outlines, on the Sky Classic tile. It is kept unchanged in `docs/design/icon/`, together with a small design for sizes under 64 pixels, where the lettering cannot be read: the same tile and gradients, the outline closed into a full circle, a reduced grid, no lettering and no glow. One script, `npm run icons`, generates the served files from the two designs with the browser the browser tests already use: `favicon.svg` (the small design), `favicon.ico` (16, 32 and 48 pixel images) and `apple-touch-icon.png` (180 pixels, full design). The page links all three. The icon rules, including the owner's preferences and the style for later interface icons, are written down in `docs/design/icon/README.md`.
- **Acceptance criteria:**
  1. The built page links the ICO file (with its size), the SVG file and the touch icon, and all three are served with an image content type.
  2. `favicon.svg` is the small design byte for byte; `favicon.ico` holds 16, 32 and 48 pixel images that show the sky-blue globe outline on the dark tile with see-through corners; `apple-touch-icon.png` is 180 pixels square, shows the full design and has no see-through corners.
  3. Neither design holds a script, an event handler, a link, an embedded image or an outside address, and both use only the Sky Classic colours.
  4. `npm run icons` regenerates the three files, and running it again changes nothing.
  5. `npm run e2e` reports 47 passed and `npm test` 115 passed.
  6. The planner has looked at the icon at 16, 32, 48 and 180 pixels on dark and light backgrounds.
- **Tests required:** browser tests (47, of which 13 new: the page's links, three content types, the vector icon equal to the small design, two checks that the designs hold nothing that runs or loads, the designs' colours, the images inside the ICO file, three checks of decoded pixels at 16, 32 and 48 pixels, the touch icon; one earlier icon test is replaced); frontend unit tests unchanged (115); lint, format check, type check, build, audit; repository checks (9); visual check by the planner at four sizes; backend untouched (115).
- **Tests executed:** In a clean checkout of pull request #21 (Linux, Node 22.23.4, npm 10.9.9): `npm ci`, lint, format check, frontend unit tests (115), type check, build, browser tests (47, three runs in a row), `npm audit` (0 vulnerabilities), repository checks (9 tests). `npm run icons` was run again and changed nothing; the three generated files have the same bytes as in the planner's trial. 23 of 23 planted defects detected. The planner looked at the icon at 16, 32, 48 and 180 pixels on dark and light backgrounds. Backend not re-run: no backend file has changed since its run on pull request #20.
- **Passed / Failed:** 171 / 0 tests (frontend unit 115, browser 47, repository 9); frontend lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. The owner approved the full design; the small design is the planner's reduction of it and was shown to the owner the same day. The PNG and ICO images were drawn by Chromium on Linux; another system may draw slightly different bytes. Which icon a browser picks for its tab was not tested. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `a8cf14d`
- **Plan:** `docs/plans/FND-024.md`

### FND-020 – Replace the API server with the pipeline command line
- **Status:** PASSED – VERIFIED
- **Objective:** Remove the server that the hosting decision made unnecessary, and give the data pipeline its command line.
- **Description:** Remove the FastAPI application, the health endpoint, the server start-up in `python -m motosphere`, the `api_host` and `api_port` settings, their tests and the `fastapi`, `uvicorn` and `httpx2` dependencies. `python -m motosphere` becomes a command-line program with sub-commands, built on the standard library's `argparse` in a new `motosphere.cli` package; the first command is `version`. Arguments are parsed before the settings are loaded, results go to standard output, and logs and errors go to standard error. Settings and logging stay and are used by the command line. README, TESTING.md, `.env.example` and CHANGELOG follow.
- **Acceptance criteria:**
  1. `python -m motosphere version` prints `motosphere 0.1.0` and exits 0; with no command, an unknown command or an unexpected argument it prints the usage and exits 2; `--help` exits 0 even when a setting is invalid; an invalid setting still gives the one-line configuration error and exit code 2, however many settings are wrong.
  2. No server code, server setting or server dependency remains (`uv.lock` no longer contains them, and the old settings are rejected as unknown); nothing listens on a port.
  3. README no longer tells the user to start an API; all remaining backend gates pass.
  4. `uv run pytest` reports 61 passed.
- **Tests required:** backend tests (61: 13 unit tests for the command line, 7 integration tests running the real command as a separate process, 18 for the settings, 9 for the package including checks that the server packages are not installed, 14 for logging); lock check, mypy, ruff check, ruff format check; repository checks (9); frontend untouched (115 unit, 35 browser).
- **Tests executed:** In a clean checkout of pull request #19 (Linux, uv 0.11.32): `uv lock --check`, `uv sync --locked`, mypy (14 source files), ruff check, ruff format check, backend pytest on Python 3.13.18 and on 3.12.3 (61 tests each, no warnings), repository checks (9 tests). The real command was run: `version` (exit 0), no command and an unknown command (usage, exit 2), `--help` (exit 0), two invalid settings (one line, exit 2). The lock file holds 20 packages and none of the server packages. 13 of 14 planted defects detected. Frontend not re-run: no frontend file has changed since its run on pull request #18.
- **Passed / Failed:** 70 / 0 tests (backend 61, repository 9); lock, type-check, lint and format gates passed
- **Verification status:** Verified by the planner on 2026-11-17. One gap, in the plan and not in the builder's work: no test checked that the command line passes a command's exit code on (the only command always returns 0). The code is correct; FND-021 adds the test. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `f80fe8d`
- **Plan:** `docs/plans/FND-020.md`

### FND-021 – Data manifest export command
- **Status:** PASSED – VERIFIED
- **Objective:** Produce the first real published data file from the pipeline.
- **Description:** `python -m motosphere export --out <directory>` writes `manifest.json`: data format version, generation time (UTC, to the second), application version and the number of published records of each kind. Nothing is published yet, so the counts are an empty object rather than invented kinds or numbers. The file is described by an immutable Pydantic model that allows no unknown fields, and is written atomically as deterministic JSON (sorted keys, `\n` line breaks on every system). A new `motosphere.publish` package holds the model, the atomic writer and the export step. The file list with content hashes (PUB-001) and the JSON Schema file (PUB-002) are later tasks.
- **Acceptance criteria:**
  1. The command creates the directory if needed, writes a manifest that validates against the model, prints its path and exits 0.
  2. The same inputs give byte-identical output; two real runs differ only in the generation time.
  3. A failed write never leaves a partial or temporary file and never damages an earlier manifest.
  4. An output path that cannot be written gives one line starting `Export failed: ` and exit code 1; a missing or empty `--out` is a usage error with exit code 2.
  5. The manifest holds no invented data.
  6. `uv run pytest` reports 115 passed (114 in the plan, plus one test added during verification).
- **Tests required:** backend tests (115, of which 54 new: 26 for the manifest model and its JSON form, 8 for the atomic writer, 6 for the export step, 9 for the command, 2 for the command line including the exit-code test missing from FND-020, 3 integration tests running the real command); lock check, mypy, ruff check, ruff format check; repository checks (9); frontend untouched (115 unit, 35 browser).
- **Tests executed:** In a clean checkout of pull request #20 (Linux, uv 0.11.32): `uv lock --check`, `uv sync --locked`, mypy (23 source files), ruff check, ruff format check, backend pytest on Python 3.13.18 and on 3.12.3 (no warnings), repository checks (9 tests). The real command was run: export into a new directory (exit 0, manifest written with `\n` line breaks, path printed), export again (file replaced, only the time differs), export into a path that is a file (one line, exit 1, file untouched), no `--out` and an empty `--out` (usage, exit 2), an invalid setting (one line, exit 2). First run: 114 tests, 32 of 34 planted defects detected; the task was sent back for one more test. Second run on the fixed pull request: all gates again, 115 tests, 33 of 34 detected. Frontend not re-run: no frontend file has changed since its run on pull request #18.
- **Passed / Failed:** 124 / 0 tests (backend 115, repository 9); lock, type-check, lint and format gates passed
- **Verification status:** Verified by the planner on 2026-11-17. The one planted defect not detected cannot be observed in practice: allowing the writer to overwrite an existing temporary file, whose name carries 64 random bits. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `b234233`
- **Plan:** `docs/plans/FND-021.md`

### FND-016 – Manifest reader in the frontend
- **Status:** PASSED – VERIFIED
- **Objective:** The frontend can fetch and check the data manifest the pipeline publishes, and reports every failure as a plain result.
- **Description:** One module, `frontend/src/data/manifest.ts`, with no dependency and no React. `parseManifest` checks a parsed JSON value field by field (published data is treated as untrusted) and returns the manifest or the reason there is none; the format version is checked first, and unknown extra fields are ignored. `loadManifest` fetches `data/manifest.json` under the application's base path, asking the server for the current copy, and never throws: the result is the manifest, `unavailable`, `malformed` or `unsupported`. Nothing is shown on the page yet. This task was split from the original "Frontend data client and data status"; the other parts are FND-027 and FND-028.
- **Acceptance criteria:**
  1. The text the real export command writes is read correctly, with the counts as a map.
  2. A value that is not an object, a missing field, a wrong type or an impossible value (a generation time in another spelling or on a date that does not exist, a negative, fractional or inexact count, a badly named record kind) gives `malformed`.
  3. Another format version gives `unsupported`, even when nothing else in the file can be read.
  4. `loadManifest` uses the base path and `cache: 'no-cache'`, passes a signal on and never throws: a failed or stopped request and an error answer give `unavailable`; an answer that is not JSON or not a manifest gives `malformed`.
  5. `npm test` reports 177 passed in 9 files.
- **Tests required:** frontend unit tests (177, of which 62 new: 48 for checking a manifest, 3 for its address, 11 for fetching it with a stand-in fetch function); lint, format check, type check, build, audit; browser tests unchanged (47); repository checks (9); backend untouched (115).
- **Tests executed:** In a clean checkout of pull request #22 (Linux, Node 22.23.4, npm 10.9.9): `npm ci`, lint, format check, frontend unit tests (177, run on UTC and again on Los Angeles time), type check, build, browser tests (47), `npm audit` (0 vulnerabilities), repository checks (9 tests). 33 of 33 planted defects detected. Backend not re-run: no backend file has changed since its run on pull request #20.
- **Passed / Failed:** 233 / 0 tests (frontend unit 177, browser 47, repository 9); frontend lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. The reader is not used by the page yet, and has only been run against a stand-in fetch function; FND-027 runs it against a manifest served from the built site. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `d42bfe4`
- **Plan:** `docs/plans/FND-016.md`

### FND-027 – Real published data in local development and browser tests
- **Status:** PASSED – VERIFIED
- **Objective:** The development server, the production preview and the browser tests serve a manifest written by the real export command.
- **Description:** One command, `npm run data` in `frontend/`, runs the pipeline's export through uv (from the `backend/` folder, so the pipeline finds its own settings) and writes into `frontend/public/data/`, which Git and Prettier ignore. Vite serves that folder in development and copies it into the build. The browser tests' web server runs the export before the build; a failed export stops the server, so stale data is never tested. The Playwright configuration records when the run started, and a test proves that the served manifest was generated in this run. The tests use the frontend's own manifest reader against the served site. Nothing is shown on the page yet (FND-028).
- **Acceptance criteria:**
  1. `npm run data` writes `frontend/public/data/manifest.json` with the real export command; Git does not list it.
  2. The browser tests' web server exports before it builds; when the export fails, no test runs.
  3. The built site serves `data/manifest.json` as JSON; the frontend's reader accepts it, called from the tests and from inside a page; its application version is the pipeline's; its generation time is not earlier than the start of the test run.
  4. The development server serves the exported manifest too.
  5. `npm run e2e` reports 53 passed; `npm test` 177 passed; the repository checks 9 tests; the backend 115 passed.
- **Tests required:** browser tests (53, of which 6 new: served as JSON, accepted by the reader, exported for this run, from this version of the pipeline, fetched and read inside a page, nothing but the manifest in the data folder); repository checks (9, with two sample paths added); frontend unit tests unchanged (177); lint, format check, type check, build, audit; all backend gates (115 tests); a hand check of the development server.
- **Tests executed:** In a clean checkout of pull request #23 (Linux, Node 22.23.4, npm 10.9.9, uv 0.11.32): `npm ci`, lint, format check (also after an export), frontend unit tests (177), type check, build, browser tests (53, three runs in a row), `npm audit` (0 vulnerabilities); backend lock check, sync, mypy (23 files), ruff check, ruff format check, pytest (115); repository checks (9 tests). The development server was started by hand and served the exported manifest as JSON. 7 of 7 planted defects detected.
- **Passed / Failed:** 354 / 0 tests (frontend unit 177, browser 53, backend 115, repository 9); all lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. The browser tests now need uv as well as Node.js; the continuous integration task (FND-018) must install both. The page does not show the data yet (FND-028). Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `f117964`
- **Plan:** `docs/plans/FND-027.md`

### FND-028 – Data status in the top bar
- **Status:** PASSED – VERIFIED
- **Objective:** The user can see how current the data is, or that it could not be loaded.
- **Description:** A hook, `useManifest`, loads the manifest once when the application starts and reports loading, ready or failed; it stops the request when its component goes away and ignores a late answer. A component, `DataStatus`, shows one line in the top bar's information slot, before the date, in plain language: "Loading data…", "Data updated" with the day the data was generated (written in the language of the user's browser, for the day where the user is, in a `time` element that carries the exact moment), "Data unavailable" for a manifest that cannot be fetched or is not a manifest, and "Reload the page to see the data" when the data is in a newer format than the application reads. The line is an `output` element, so changes are announced to assistive technology. The browser tests of the normal case read the manifest the real export command wrote for the run. A browser test with a manifest the server does not have (HTTP 404) or a failed request is not possible until the browser tests can expect a page problem (FND-029); those cases are covered by unit tests here.
- **Acceptance criteria:**
  1. While the manifest is on its way the top bar says "Loading data…".
  2. With the manifest of the real export it says "Data updated" and the day the data was generated, in the language of the browser and for the day where the user is; the `time` element's `datetime` is the moment in the manifest.
  3. A manifest that cannot be fetched, is a web page or is damaged gives "Data unavailable"; a newer format gives "Reload the page to see the data"; nothing is thrown, the console stays clean and the rest of the page keeps working.
  4. The line has the role `status`, sits between the tagline and the date in the quiet text colour, and the top bar still fits at 1366 pixels.
  5. Leaving the page stops the request, and a late answer changes nothing.
  6. `npm test` reports 199 passed in 12 files; `npm run e2e` reports 62 passed.
- **Tests required:** frontend unit tests (199, of which 22 new: the hook 10, the date 5, the component 6, the application 1); browser tests (62, of which 9 new: the real manifest for a British user, position and colour, the American way for the day in Los Angeles, the German way for the day in Tokyo, loading until the answer arrives, a web page as the answer, a damaged manifest, a newer format, the rest of the page still working); the unit tests once more in another time zone; lint, format check, type check, build, audit; repository checks (9).
- **Tests executed:** In a clean checkout of pull request #24 (Linux, Node 22.23.4, npm 10.9.9, uv 0.11.32): `npm ci`, lint, format check, frontend unit tests (199, and 199 again with the time zone set to Asia/Tokyo), type check, build, browser tests (62, three runs in a row), `npm audit` (0 vulnerabilities); repository checks (9 tests). The top bar was looked at in a browser at 1366 and 1100 pixels. 22 of 22 planted defects detected. The backend gates were not run again: no backend file changed since they passed for FND-027 (115 tests), and the browser tests run the real export.
- **Passed / Failed:** 270 / 0 tests (frontend unit 199, browser 62, repository 9); all lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. A manifest answered with HTTP 404 and a failed request are covered by unit tests only; their browser tests come with FND-029. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `d45e008`
- **Plan:** `docs/plans/FND-028.md`

### FND-029 – Browser tests can expect a page problem
- **Status:** PASSED – VERIFIED
- **Objective:** A browser test can say which page problems it expects, so that the data status can be tested in the browser with a manifest the server does not have.
- **Description:** Every browser test fails when the page reports a console error or warning, an uncaught error, a failed request or an HTTP error (`frontend/e2e/fixtures.ts`). That stays the rule. A test about a failure now names what it expects, inside the test, with `expectProblem(/pattern/)`; it then fails if an expected problem does not happen and still fails on any problem it did not name, so an expectation can never hide another fault. The judgement is one function with no browser in it, `unexplained`. The rule gets tests of its own for the first time; tests that must fail under the rule are marked with `test.fail()` and are reported as passed, never as skipped. With it, the data status is tested in the browser with a manifest answered with HTTP 404 and with a failed request. The application itself does not change.
- **Acceptance criteria:**
  1. A browser test that names no problem behaves as before: it fails on a console error or warning, an uncaught error, a failed request or an HTTP error, and passes on a healthy page.
  2. A test that names its expected problems passes only when every one of them happens and nothing else does.
  3. The data status says "Data unavailable" when the manifest is answered with HTTP 404 and when the request fails, and the rest of the page keeps working.
  4. `npm run e2e` reports 80 passed with none skipped; `npm test` still reports 199 passed in 12 files.
- **Tests required:** browser tests (80, of which 18 new: 7 of the judgement, 9 of the rule in a real page, 2 of the data status); frontend unit tests unchanged (199); lint, format check, type check, build, audit; repository checks (9).
- **Tests executed:** In a clean checkout of pull request #25 (Linux, Node 22.23.4, npm 10.9.9, uv 0.11.32): `npm ci`, lint, format check, frontend unit tests (199), type check, build, browser tests (80, three runs in a row, none skipped), `npm audit` (0 vulnerabilities); repository checks (9 tests). 14 of 14 planted defects detected. The backend gates were not run again: no backend file changed since they passed for FND-027 (115 tests), and the browser tests run the real export.
- **Passed / Failed:** 288 / 0 tests (frontend unit 199, browser 80, repository 9); all lint, format, type-check and build gates passed
- **Verification status:** Verified by the planner on 2026-11-17. The two new data status tests name the manifest's address at the root of the site; the GitHub Pages task (FND-022), which serves the site from a sub-path, must keep them passing there. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `5f4fde1`
- **Plan:** `docs/plans/FND-029.md`

### FND-017 – Unified check runner
- **Status:** PASSED – VERIFIED
- **Objective:** One command that runs every gate in order and says which passed.
- **Description:** `python scripts/check.py` (standard library only, started from any folder) runs the 16 gates of the project in order from a clean checkout: the repository checks, the runner's own tests, the pipeline's lock check, install, type check, lint, format check and tests, and the frontend's install, lint, format check, type check, unit tests, build, browser tests and dependency audit. Every gate runs even when an earlier one failed. A summary names each gate as passed or failed with the time it took; the exit code is 0 only when every gate passed. `--list` shows the gates without running them and `--only` runs the named ones. A program that is not installed is a failed gate with a plain reason, not an error. `TESTING.md` lists the gates, and a test keeps the list and the script the same. This task was split from the original check runner task; the other parts are FND-030 and FND-031.
- **Acceptance criteria:**
  1. Started from any folder, the full run executes the 16 gates in order from a clean checkout and, with everything in order, reports "16 of 16 gates passed." with exit code 0.
  2. A failing gate makes the exit code 1, is marked FAILED with its reason and is named in the verdict; the gates after it still run.
  3. `--list` runs nothing; `--only` runs only the named gates in the order of the table; an unknown name is refused with exit code 2.
  4. A program that is not installed, or a missing folder, gives a failed gate with a plain reason and no Python error.
  5. `TESTING.md` lists every gate exactly as the script has it.
- **Tests required:** the runner's own tests (30, standard library `unittest`: the gate table 7, running one gate 8, the whole run with stand-in gates 11, the script as a separate process 4, always as a copy in a stand-in repository); repository checks (9, with two sample paths added); one full real run of all 16 gates; one real run with a deliberately failing gate.
- **Tests executed:** In a clean checkout of pull request #26 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the runner's tests (30, and 30 again on Python 3.12), repository checks (9), `--list` (16 gates), and the full run started from another folder: 16 of 16 gates passed, exit code 0 (inside it: 9 repository checks, 30 script tests, 115 backend tests, 199 frontend unit tests, 80 browser tests, mypy on 23 files, both lint and format gates, the build, 0 vulnerabilities). A real failing frontend test gave exit code 1 and was named in the summary; without uv on the PATH the gate failed with "uv is not installed"; an unknown gate name gave exit code 2. 30 of 30 planted defects detected.
- **Passed / Failed:** 433 / 0 tests (script tests 30, repository 9, backend 115, frontend unit 199, browser 80); all 16 gates passed
- **Verification status:** Verified by the planner on 2026-11-17. The runner does not yet count tests or fail on skipped tests (FND-030), and the Python files outside the pipeline are not yet under lint, format or type gates (FND-031). Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `0620e94`
- **Plan:** `docs/plans/FND-017.md`

### FND-030 – Test counts and skipped tests in the check runner
- **Status:** PASSED – VERIFIED
- **Objective:** The check runner reports how many tests each gate ran, and fails when any test was skipped.
- **Description:** The five gates that run tests (repository checks and script tests with `unittest`, backend tests with pytest, frontend unit tests with Vitest, browser tests with Playwright) name their tool in the gate table. The runner reads every gate's output while passing it on to the terminal unchanged, and for a test gate reads the number of tests passed, failed and skipped from the tool's own closing lines, with colour codes removed. Every test that neither passed nor failed counts as skipped: skipped, expected to fail, still to do, left out or not run. A test gate fails when its command fails, when a test was skipped, when no test ran or when the counts cannot be found. The summary shows the counts on each test gate's line and a total for the run.
- **Acceptance criteria:**
  1. The full run shows the real counts of the five test gates and ends with "16 of 16 gates passed." and "Tests: 473 passed, 0 failed, 0 skipped.", exit code 0.
  2. A skipped test in any of the five tools makes its gate fail with the reason "tests were skipped", and the exit code is 1.
  3. A test gate where no test ran, or whose counts cannot be read, fails with a plain reason.
  4. Every gate's output still appears on the terminal, also when it is not valid UTF-8 or the console is limited to ASCII.
  5. Gates that do not run tests behave as before.
- **Tests required:** the runner's own tests (70, of which 40 new: reading counts from closing lines copied from real runs of each tool 19, judging a gate 8, and additions to the gate table, running one gate, the whole run and the script as a separate process); repository checks (9); one full real run of all 16 gates; one real run with a skipped test planted in each of the five tools.
- **Tests executed:** In a clean checkout of pull request #27 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the runner's tests (70, and 70 again on Python 3.12), repository checks (9), and the full run started from another folder: 16 of 16 gates passed, "Tests: 473 passed, 0 failed, 0 skipped.", exit code 0. By hand: a skipped test planted in each of the five test tools failed all five gates with "tests were skipped" and the total "473 passed, 0 failed, 5 skipped"; a broken frontend test showed "198 passed, 1 failed"; a console limited to ASCII did not disturb the run. 51 of 51 planted defects detected.
- **Passed / Failed:** 473 / 0 tests (repository 9, script tests 70, backend 115, frontend unit 199, browser 80); all 16 gates passed
- **Verification status:** Verified by the planner on 2026-11-17. From this task on, the totals in these records are the ones the check runner prints. The closing lines for flaky, interrupted and not-run browser tests are taken from Playwright's wording, not from a real run. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `94f0862`
- **Plan:** `docs/plans/FND-030.md`

### FND-031 – Lint and format checks for Python outside the pipeline
- **Status:** PASSED – VERIFIED
- **Objective:** The Python files outside `backend/` (`scripts/`, `tests/repo`, `tests/scripts`) pass the same lint, format and type checks as the pipeline.
- **Description:** A `ruff.toml` at the repository root that extends the pipeline's rules, with only the pytest-style rules off because these tests use standard-library `unittest`; a `mypy.ini` that checks `scripts/` and `tests/` as strictly as the pipeline; and three new gates in the check runner (`tools-types`, `tools-lint`, `tools-format`) that run them from the repository root with the pipeline's locked tools, so that no new dependency is needed. The gates cover the two folders, not a list of files, and a test fails when a Python file appears outside the pipeline in a folder they do not cover. The existing files are brought into line (types, two marked exemptions and formatting in the repository checks).
- **Acceptance criteria:**
  1. The full run ends with "19 of 19 gates passed." and "Tests: 476 passed, 0 failed, 0 skipped.", exit code 0, with the three new gates after the backend tests.
  2. A lint defect, a format defect and a type defect planted in each of `scripts/`, `tests/repo/` and `tests/scripts/` each make the matching gate fail with exit code 1.
  3. A new Python file in `scripts/` or under `tests/` is checked without further change; a Python file in any other folder outside the pipeline makes a test fail.
  4. The gates use the pipeline's locked tools and rules, with only the pytest-style rules off, and a test pins this.
  5. The pipeline's own gates are unchanged.
  6. `TESTING.md` lists the 19 gates exactly as the script has them, and `README.md` gives the three commands.
- **Tests required:** the runner's own tests (73, of which 3 new: the tooling gates use the locked tools, every Python file outside the pipeline is in a covered folder, the two configuration files follow the pipeline's rules); repository checks (9, with two sample paths added); one full real run of all 19 gates; real planted lint, format and type defects in each of the three folders, run through the new gates.
- **Tests executed:** In a clean checkout of pull request #28 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the runner's tests (73, and 73 again on Python 3.12), repository checks (9), `--list` (19 gates), and the full run started from another folder: 19 of 19 gates passed, "Tests: 476 passed, 0 failed, 0 skipped.", exit code 0; the pipeline's type check still covered 23 files and the new one 3. Real lint, format and type defects planted in each of `scripts/`, `tests/repo/` and `tests/scripts/`, and in a new file and a new folder, each failed the matching gate with exit code 1 (20 of 20). Without uv on the PATH the three gates failed with "uv is not installed". 38 of 38 planted defects detected in all.
- **Passed / Failed:** 476 / 0 tests (repository 9, script tests 73, backend 115, frontend unit 199, browser 80); all 19 gates passed
- **Verification status:** Verified by the planner on 2026-11-17. The three gates need the pipeline's environment, which the "Backend install" gate creates before them; run on their own on a fresh checkout, uv installs it first. Not run on Windows 11 (first Windows run is FND-018).
- **Commit:** `df929bf`
- **Plan:** `docs/plans/FND-031.md`

### FND-018 – Continuous integration
- **Status:** PASSED – VERIFIED
- **Objective:** Every pull request and every change to `main` is checked automatically on GitHub, on Linux.
- **Description:** A GitHub Actions workflow (`.github/workflows/checks.yml`) with one job on a Linux machine: it installs Python 3.12 (the oldest version the pipeline supports), uv, Node.js and the browser for the browser tests, then runs `python scripts/check.py`, the same command as on a developer's machine. The workflow is given as little as possible: a token that can only read, no secret, no credentials left by the checkout, every action pinned to a full commit, and only four actions allowed. New repository checks hold every workflow to these rules. The existing check that source paths are not ignored is corrected so that it can also fail for files Git already tracks. Windows is a separate task (FND-032).
- **Acceptance criteria:**
  1. On the task's own pull request the job finishes green, and its log ends with "19 of 19 gates passed." and "Tests: 489 passed, 0 failed, 0 skipped."
  2. A commit with a failing test makes the job fail, and its log names the failed gate.
  3. The token can only read, no secret is used, the checkout keeps no credentials, every action is pinned to a full commit with its release beside it, and only the four known actions are used; repository checks pin each of these for every workflow.
  4. No step can be skipped or allowed to fail, and the only commands are the two that install the browser and `python scripts/check.py`.
  5. An ignore rule that would hide a tracked source file fails the repository checks.
  6. After the merge, the run for `main` is green.
- **Tests required:** repository checks (22, of which 13 new, on the workflows); the full local run of all 19 gates; the real workflow run on the pull request (green on the final commit, red on a commit with a failing test); the run for `main` after the merge.
- **Tests executed:** In a clean checkout of pull request #29 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: repository checks (22, and 22 again on Python 3.12), the runner's tests (73), and the full run started from another folder: 19 of 19 gates passed, "Tests: 489 passed, 0 failed, 0 skipped.", exit code 0. 32 of 32 planted defects in the workflow detected. On GitHub (Ubuntu 24.04, Python 3.12.16), read by the planner from the job logs: run 44125941639 on the final commit of the pull request, green, "19 of 19 gates passed." and "Tests: 489 passed, 0 failed, 0 skipped."; run 44125492578 on a commit with a planted failing test, red, "FAILED  Frontend unit tests  198 passed, 1 failed" and "18 of 19 gates passed."; run 44126685964 for `main` after the merge, green, with the same closing lines as the first.
- **Passed / Failed:** 489 / 0 tests (repository 22, script tests 73, backend 115, frontend unit 199, browser 80); all 19 gates passed, locally and on GitHub
- **Verification status:** Verified by the planner on 2026-11-17. The workflow went green on its first real run, with no change to the plan. Whether GitHub blocks a merge when the run is red is a repository setting and is not switched on. Linux only: the first Windows run is FND-032.
- **Commit:** `a743a64`
- **Plan:** `docs/plans/FND-018.md`

### FND-032 – Continuous integration on Windows
- **Status:** PASSED – VERIFIED
- **Objective:** Every pull request and every change to `main` is also checked on Windows.
- **Description:** The checks workflow runs its one set of steps on two machines, Linux (`ubuntu-24.04`) and Windows (`windows-2025`). Each gives its own result, and one failing does not stop the other. The browser install becomes two steps of one command each, because on Windows a step with several commands only fails on its last one; a repository check forbids such steps. The planner's trial on GitHub (pull request #30, closed without merging) showed that the project passes every gate on Windows as it is, so no fix for Windows is part of the plan. Split from FND-018.
- **Acceptance criteria:**
  1. On the task's own pull request both jobs finish green, and each log ends with "19 of 19 gates passed." and "Tests: 492 passed, 0 failed, 0 skipped."
  2. A failure on one machine only turns that machine's job red and leaves the other green; both run to the end.
  3. The machines are named images; repository checks pin the two machines, the job names, that one failing does not stop the other, and one command to a step.
  4. Every rule from FND-018 still holds.
  5. After the merge, the run for `main` is green on both machines.
- **Tests required:** repository checks (25, of which 3 new and 1 replaced); the full local run of all 19 gates; the real workflow run on the pull request (both jobs green on the final commit; with a test that fails on Windows only, Windows red and Linux green); the run for `main` after the merge.
- **Tests executed:** In a clean checkout of pull request #31 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: repository checks (25, and 25 again on Python 3.12) and the full run started from another folder: 19 of 19 gates passed, "Tests: 492 passed, 0 failed, 0 skipped.", exit code 0. 41 of 41 planted defects in the workflow detected. On GitHub, read by the planner: run 44132384609 on the final commit of the pull request, both jobs green ("All gates (Linux)" on ubuntu-24.04 and "All gates (Windows)" on windows-2025 with Python 3.12.10; the Windows log ends with "19 of 19 gates passed." and "Tests: 492 passed, 0 failed, 0 skipped."); run 44131523747 on a commit with a test that fails on Windows only: the Windows job red at the step that runs the gates, the Linux job green, both run to the end; run 44133777708 for `main` after the merge, both jobs green. The planner's own trial (pull request #30, closed without merging) gave the same results before the task was handed over.
- **Passed / Failed:** 492 / 0 tests (repository 25, script tests 73, backend 115, frontend unit 199, browser 80); all 19 gates passed, locally and on both machines on GitHub
- **Verification status:** Verified by the planner on 2026-11-17. This is the first time the project ran on Windows, and it passed every gate without a change to the application, the tests or the check runner. The machine is Windows Server 2025 on GitHub, not the owner's Windows 11 PC (that is FND-019). The plan said prove-it step 7 fails 2 tests; as worded it fails 1, and the defect is detected either way.
- **Commit:** `9e0c57a`
- **Plan:** `docs/plans/FND-032.md`

### FND-033 – Dependency audit with recorded exceptions
- **Status:** PASSED – VERIFIED
- **Objective:** The dependency audit fails on every security advisory except the ones recorded with a reason and a review date, and fails again by itself when a recorded exception has run out or is no longer needed.
- **Description:** On 2026-11-17 an advisory was published for `picomatch` (GHSA-fc5q-39xc-vjpf, high, a pattern that is slow to match). The project gets it only through its build and test tools (vite and vitest), every version is affected including the newest (4.0.7), and production dependencies are not affected (`npm audit --omit=dev`: 0). The last gate, `npm audit`, has failed since then on `main` and on every pull request, with nothing changed in the repository. A new script, `python scripts/audit.py` (standard library only), runs `npm audit --json` in `frontend/` and compares the advisories with `frontend/audit-exceptions.json`. An exception names one advisory id and its package, with a reason of at least 40 characters, the day it was accepted and a review day at most 31 days later; every exception in use is printed on every run. The gate `frontend-audit` runs the script. One exception is recorded, for the advisory above, accepted on 2026-11-17 and **to be reviewed by 2026-12-17**: from 2026-12-18 the gate fails again until somebody has looked (a fixed version installed and the exception removed, or the exception renewed with its reason). Rejected: leaving build tools out of the audit, a severity threshold, and going back two major versions of vite and vitest.
- **Acceptance criteria:**
  1. `python scripts/check.py` reports 19 of 19 gates and 541 tests, and the audit gate's output shows the recorded exception with its reason and review day.
  2. With the exception taken out, the audit gate fails and names the picomatch advisory with its address.
  3. An exception past its review day, one that is no longer needed, one for another package and one dated in the future each fail the check; so do a faulty exceptions file and an answer from npm that is not a report.
  4. An exception cannot be recorded without a reason of at least 40 characters, for longer than 31 days, or for anything but one advisory id.
  5. The gate keeps its key, name and place; the gate table in `TESTING.md` matches the script.
  6. On the pull request both jobs are green (Linux and Windows), each with 19 of 19 gates and 541 tests; after the merge the run for `main` is green again.
- **Tests required:** script tests (122, of which 49 new: 13 for reading the exceptions, 8 for reading npm's report, 9 for judging, 6 for running the audit command, 9 for the script's result and output, 3 for the repository's own files, 1 in the runner's tests); the full run of all 19 gates; the real audit without the exception, with an expired one, with a wrong one and without a lock file; the workflow run on the pull request on both machines; the run for `main` after the merge.
- **Tests executed:** In a clean checkout of pull request #32 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 541 passed, 0 failed, 0 skipped.", exit code 0, the audit gate printing "npm audit reports 1 advisory.", the recorded exception with its reason and review day, and "Dependency audit passed."; the script tests again on Python 3.12 (122). The real audit with the exception taken out (the gate fails and names the picomatch advisory with its address) and with the dates moved back (fails with "was due for review on 2026-10-31"). 53 of 53 planted defects in the script, the gate, the gate table and the exceptions file detected by the script tests. On GitHub, read by the planner: run 44138689020 on the pull request's commit, both jobs green, each log ending "19 of 19 gates passed." and "Tests: 541 passed, 0 failed, 0 skipped."; run 44138077506 for `main` before the merge, both jobs red in the audit gate only ("18 of 19 gates passed. FAILED: Frontend dependency audit."), which is the failure this task answers; run 44140586126 for `main` after the merge, green.
- **Passed / Failed:** 541 / 0 tests (repository 25, script tests 122, backend 115, frontend unit 199, browser 80); all 19 gates passed, locally and on both machines on GitHub
- **Verification status:** Verified by the planner on 2026-11-17. Eight of the nine files are identical to the planner's trial; the ninth, `ARCHITECTURE.md`, differs only by the line the plan commit itself changed. The exception for GHSA-fc5q-39xc-vjpf must be looked at again by 2026-12-17: from 2026-12-18 the audit gate fails until it is removed (a fixed picomatch installed) or renewed with its reason. The pipeline's Python dependencies are not audited yet (PRF-005).
- **Commit:** `4962ae1`
- **Plan:** `docs/plans/FND-033.md`

### FND-022 – The application served from the site's path
- **Status:** PASSED – VERIFIED
- **Objective:** The application works when it is served from `/MotoSphere/`, the path it will have on GitHub Pages, and the tests prove it there.
- **Description:** The site's path is written once (`frontend/site.ts`) and read by the build and by the browser tests. The browser tests run against the production build served under that path, write every address relative to it, and check that everything the page loads comes from under it and that its files are not at the root of the server. The development server uses the same path. The application code does not change: it already takes its base path from the build; the unit test for the manifest's address now gives the build another path, so that no fixed address can pass. Split from the GitHub Pages task (PLAN-006).
- **Acceptance criteria:**
  1. The production build, served locally, answers at `/MotoSphere/` with the application; its script, style sheet, three icon files and the data manifest load from under that path with no console error.
  2. The icon files and the data manifest are not served at the root of the test server.
  3. The path is written in one place, and the build and the browser tests read it there.
  4. The unit test for the manifest's address fails when the application names a fixed address, whether `/` or `/MotoSphere/`.
  5. `npm run dev` serves the application at `http://localhost:5173/MotoSphere/`, and the README says so.
  6. `python scripts/check.py` reports 19 of 19 gates and 548 tests; on the pull request both jobs are green (Linux and Windows).
- **Tests required:** browser tests against the build served from the sub-path (87, of which 7 new: the path's name, the application served there, everything the page loads under the path, four files under the path and not at the root); frontend unit tests (199, one made stricter); the full run of all 19 gates; the development server's addresses by hand; planted defects; the workflow run on the pull request on both machines; the run for `main` after the merge.
- **Tests executed:** In a clean checkout of pull request #33 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 548 passed, 0 failed, 0 skipped.", exit code 0 (frontend unit tests 199, browser tests 87). The development server by hand: `/MotoSphere/` 200, `/` 302, `/favicon.svg` 404, `/MotoSphere/favicon.svg` and `/MotoSphere/data/manifest.json` 200. Planted defects, each run through the type check, the unit tests and the browser tests: 10 of 10 detected in the pull request (11 of 11 in the planner's trial, which also had the build using relative addresses). On GitHub, read by the planner: run 44143905377 on the pull request's commit, both jobs green, each log ending "19 of 19 gates passed." and "Tests: 548 passed, 0 failed, 0 skipped."; run 44158699104 for `main` after the merge, green.
- **Passed / Failed:** 548 / 0 tests (repository 25, script tests 122, backend 115, frontend unit 199, browser 87); all 19 gates passed, locally and on both machines on GitHub
- **Verification status:** Verified by the planner on 2026-11-17. All 18 files are identical to the planner's trial. One planted defect, the data's address written out in the application as `/MotoSphere/`, passes every browser test and is detected only by the unit test that gives the build another path. The site is not published yet: that is FND-034.
- **Commit:** `f1b9897`
- **Plan:** `docs/plans/FND-022.md`

### FND-034 – GitHub Pages deployment
- **Status:** PASSED – VERIFIED
- **Objective:** Every change to `main` that passes every gate is published on GitHub Pages, by itself, and nothing else ever is.
- **Description:** The checks workflow gets two more jobs after the gates. "Build the site" waits for the gates on both machines, exports the published data, builds the application and hands `frontend/dist` over; it can only read the repository. "Publish the site" is the only job with the right to publish; it checks out nothing and runs no command of its own, and goes through the `github-pages` environment. Both run for a change to `main` only, never for a pull request. Runs for `main` go one at a time, in order, so an older commit never replaces a newer one. Two actions of GitHub's own are added, pinned to a commit. The repository checks hold the workflow to all of this. The planner's trial on GitHub (pull request #34, closed without merging) showed the two jobs skipped on a pull request and the site built and handed over correctly. Publishing itself can only run from `main`, so its first real run is the run for `main` after the merge. Split from FND-022 (PLAN-006); the check of the published site is FND-035 (PLAN-007).
- **Acceptance criteria:**
  1. On the task's pull request the gates are green on both machines (19 of 19 gates, 557 tests) and the two publishing jobs are skipped.
  2. Only the job that publishes has a right to write anything, and that right is to publish to GitHub Pages; it checks out nothing and runs no command of its own.
  3. The site is built only after the gates passed on both machines, and published only after it was built.
  4. The workflow starts for pull requests and changes to `main` and nothing else, and the two publishing jobs run for a change to `main` only.
  5. Every rule from FND-018 and FND-032 still holds, for all three jobs.
  6. After the merge, the run for `main` builds and publishes the site: all four jobs green.
- **Tests required:** repository checks (34, of which 9 new: the jobs, the order they wait in, a pull request never publishes, only the deployment may publish, the publishing job runs nothing of its own, the Pages environment, what the site is made of, where it is built, named machines); the full run of all 19 gates; planted defects; the workflow run on the pull request; the run for `main` after the merge, with its deployment. The owner reported on 2026-11-17 that GitHub Pages is switched on for the repository with GitHub Actions as its source; the run for `main` will confirm it. If that run shows Pages is not available, the task is `BLOCKED – EXTERNAL DEPENDENCY`, not passed.
- **Tests executed:** In a clean checkout of pull request #35 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 557 passed, 0 failed, 0 skipped.", exit code 0 (repository checks 34); the 34 repository checks again on Python 3.12.3. Planted defects in the workflow: 82 of 82 detected by the repository checks. On GitHub, read by the planner from the runs and job logs: run 44160652237 on the pull request's commit, "All gates (Linux)" and "All gates (Windows)" green, each log ending "19 of 19 gates passed." and "Tests: 557 passed, 0 failed, 0 skipped.", "Build the site" and "Publish the site" skipped; run 44162680770 for `main` after the merge, all four jobs green: the gates on both machines with the same two closing lines, "Build the site" (the site handed over: `index.html`, three icon files, `data/manifest.json`, one script and one style sheet, 110550 bytes), and "Publish the site" (its token: "Metadata: read", "Pages: write"; "Created deployment for fbfe689f075f1f162783e4b26b39f6ec473bd72a"; "Reported success!").
- **Passed / Failed:** 557 / 0 tests (repository 34, script tests 122, backend 115, frontend unit 199, browser 87); all 19 gates passed, locally and on both machines on GitHub; the first deployment succeeded
- **Verification status:** Verified by the planner on 2026-11-17. All 6 files are identical to the planner's trial. "Published" here means that GitHub Pages accepted the deployment and reported success. The planner could not open <https://bigdaddy284.github.io/MotoSphere/> to look (the planner's network policy refuses the address); checking what a visitor gets, after every deployment, is FND-035.
- **Commit:** `fbfe689`
- **Plan:** `docs/plans/FND-034.md`

### FND-036 – Remove the audit exception that is no longer needed
- **Status:** PASSED – VERIFIED
- **Objective:** The dependency audit passes again because the exception it no longer needs is gone, and no other exception takes its place.
- **Description:** On 2026-11-18 `npm audit` no longer reports the picomatch advisory (GHSA-fc5q-39xc-vjpf) for which an exception was recorded a day earlier (FND-033): its report holds 0 advisories for the same lock file, and the npm registry's list of advisories for picomatch no longer holds it. The audit fails on an exception that nothing reports any more, as designed, so the last gate fails on `main` and on every pull request until the exception is removed. `main` was green at `c04a5db`; nothing in the repository changed. The list of exceptions becomes empty and the changelog says so. Added by PLAN-008.
- **Acceptance criteria:**
  1. `frontend/audit-exceptions.json` holds an empty list of exceptions and nothing else.
  2. `python scripts/check.py` reports 19 of 19 gates and 557 tests, and the audit gate prints "npm audit reports 0 advisories." and "Dependency audit passed."
  3. On the pull request both gates jobs are green (Linux and Windows) and the two publishing jobs are skipped.
  4. Only `frontend/audit-exceptions.json` and `CHANGELOG.md` changed.
- **Tests required:** the full run of all 19 gates (no test changes: none depends on the exception); three wrong results tried by hand (the exception left in, the list itself gone, the file unformatted); the workflow run on the pull request; the run for `main` after the merge, which also republishes the site.
- **Tests executed:** In a clean checkout of pull request #37 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 557 passed, 0 failed, 0 skipped.", exit code 0; the audit gate printed "npm audit reports 0 advisories." and "Dependency audit passed." Three wrong results tried by hand, each detected: the exception left in (the audit gate fails with "is no longer needed: remove it"), the list itself gone ("could not be judged"), the file unformatted (the frontend's format gate names it). On GitHub, read by the planner from the runs and job logs: run 44360270319 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 557 passed, 0 failed, 0 skipped.", the two publishing jobs skipped; run 44361547750 for `main` after the merge, all four jobs green, the site republished ("Reported success!").
- **Passed / Failed:** 557 / 0 tests (repository 34, script tests 122, backend 115, frontend unit 199, browser 87); all 19 gates passed, locally and on both machines on GitHub
- **Verification status:** Verified by the planner on 2026-11-18. Both files are identical to the planner's trial. Between the planning commit and this merge the run for `main` was red in the audit gate (run 44359969370), as expected, and nothing was published from it.
- **Commit:** `9663dfa`
- **Plan:** `docs/plans/FND-036.md`

### FND-035 – A check that compares the published site with the site that was built
- **Status:** PASSED – VERIFIED
- **Objective:** One command says whether an address serves exactly the site that was built, and says what differs when it does not.
- **Description:** A script, `python scripts/live.py <site.tar> <address>`, with the Python standard library only. It reads the built site from the tar the deployment hands over, asks the address for every file in it (and for the address itself, which must be the page), and compares each answer with the built file: the status, the kind of content and every byte. A site that is missing a file, serves an older one or serves the wrong kind of content fails, with each difference named. It tries again every 10 seconds for up to five minutes, because a new deployment takes a moment to reach visitors, and sends one line per try at once. Narrowed by PLAN-008 from "Check the published site after each deployment": the job that runs it is FND-037. The planner's trial has 42 tests against a stand-in server on this computer and detects 44 of 44 planted defects. In a trial on GitHub (pull request #36, closed without merging) the script compared the real published site with a fresh build: 6 of 7 files identical with the right content types, and the data manifest different, as it had to be, because the trial's export was newer. The same trial made the tests eight times faster on Windows (26 seconds to 3).
- **Acceptance criteria:**
  1. Against a stand-in server the script passes for the built site and says how many files it compared.
  2. It fails, naming the file, for a missing file, a moved file (a redirect), a changed file, an older data manifest, a script served as text, and an address that shows another page.
  3. It tries again every 10 seconds for up to 5 minutes, one line per try, each sent at once; when the time is over it fails.
  4. It fails in a plain sentence, with exit code 1 and no traceback, when the address is not `https` (other than this computer's own) or carries more than an address, when the tar is not a built site, and when the site gives no answer for the whole waiting time. It reads nothing outside the tar's own list of files.
  5. `python scripts/check.py` reports 19 of 19 gates and 599 tests (script tests 164); on the pull request both gates jobs are green (Linux and Windows) and the two publishing jobs are skipped.
- **Tests required:** script tests against a local stand-in server (164 in all, 42 new); the tooling type check, lint and format; planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge.
- **Tests executed:** In a clean checkout of pull request #38 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 599 passed, 0 failed, 0 skipped.", exit code 0; the 164 script tests also on Python 3.12, the version GitHub uses; 44 of 44 planted defects detected by the script's tests (among them a followed redirect, an unencrypted address accepted, a path that leaves the site accepted, a check that never tries again, one that tries for ever, wrong files listed but exit code 0). On GitHub, read by the planner from the runs and job logs: run 44365855699 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 599 passed, 0 failed, 0 skipped.", the two publishing jobs skipped, the script tests in 6.9 seconds on Windows; run 44367232626 for `main` after the merge, all four jobs green with the same two closing lines on both machines, the site republished ("Reported success!").
- **Passed / Failed:** 599 / 0 tests (repository 34, script tests 164, backend 115, frontend unit 199, browser 87); all 19 gates passed, locally and on both machines on GitHub; 44 / 0 planted defects detected
- **Verification status:** Verified by the planner on 2026-11-18. All 4 files are identical to the planner's trial. The tests use a stand-in server on the same computer; the script met the real published site once, in the planner's trial on GitHub (pull request #36, closed without merging). Running it against the published site after every deployment is FND-037.
- **Commit:** `17d1a3e`
- **Plan:** `docs/plans/FND-035.md`

### FND-037 – Run the check of the published site after each deployment
- **Status:** PASSED – VERIFIED
- **Objective:** A deployment that leaves the published site broken, incomplete or stale turns the run red.
- **Description:** After "Publish the site", a fourth job, "Check the published site", takes the site this run built, exactly as it was handed to GitHub Pages, and runs FND-035's check against the live address (`https://bigdaddy284.github.io/MotoSphere/`) from GitHub's machine. It can only read: no rights of its own, no environment. It runs for a change to `main` only. One action of GitHub's own is added, pinned to a commit, to fetch the built site. The repository checks hold the workflow to all of this and tie the address to the site's path in `frontend/site.ts` and to the address the documents give. Split from FND-035 by PLAN-008. FND-034 proves that GitHub accepted the deployment, not what a visitor gets, and the planner's environment cannot reach the address to look. The planner's trial has 40 repository checks (34 before) and detects 120 of 120 planted defects; on GitHub (pull request #39, closed without merging) both gates jobs were green with 605 tests and the three jobs after the gates were skipped. The job can only pass for the build that was just published, so its first real run is the run for `main` after the merge.
- **Acceptance criteria:**
  1. On the pull request both gates jobs are green (Linux and Windows) with 19 of 19 gates and 605 tests, and "Build the site", "Publish the site" and "Check the published site" are skipped.
  2. The new job runs for a change to `main` only, after the deployment, and has no right to write anything.
  3. It takes the site this run built and runs `python scripts/live.py` on it against the published address, and nothing else.
  4. The address it checks ends with the site's path from `frontend/site.ts` and is the address the README and TESTING.md give.
  5. Every rule from FND-018, FND-032 and FND-034 still holds, for all four jobs.
  6. In the run for `main` after the merge all five jobs are green, and the log of "Check the published site" ends with "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Tests required:** repository checks for the new job's rules (40 in all, 6 new); planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, where the job runs for the first time.
- **Tests executed:** In a clean checkout of pull request #40 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 605 passed, 0 failed, 0 skipped.", exit code 0; 120 of 120 planted defects in the workflow, the documents and the site's path detected by the repository checks (the 82 from FND-034 and 38 about the new job). On GitHub, read by the planner from the runs and job logs: run 44387215403 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 605 passed, 0 failed, 0 skipped.", the three jobs after the gates skipped; run 44390229386 for `main` after the merge, all five jobs green, the gates with the same two closing lines on both machines, the site republished, and "Check the published site", running for the first time, ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 605 / 0 tests (repository 40, script tests 164, backend 115, frontend unit 199, browser 87); all 19 gates passed, locally and on both machines on GitHub; 120 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-18. All 6 files are identical to the planner's trial. The check passed at its first try, about six seconds after GitHub Pages reported the deployment, so its waiting and trying again has not yet been needed on a real deployment (the script's own tests cover it). From now on every change to `main` is checked this way.
- **Commit:** `6f68e76`
- **Plan:** `docs/plans/FND-037.md`

### FND-038 – Narrow screens: an open panel lies over the globe
- **Status:** PASSED – VERIFIED
- **Objective:** On a narrow screen the globe stage is never squeezed by the side panels: it keeps the whole width, and an open panel lies over it.
- **Description:** A screen under 900 pixels wide is a narrow one: a phone, or a tablet held upright. There the layout has one column: the top bar and the globe stage each have the whole width, and an open side panel is drawn over the stage, the sections panel from the left edge and the details panel from the right, as tall as the stage and never wider than the screen. From 900 pixels on nothing changes. Style sheet only. Measured by the planner on `main` at 390 by 844 pixels before this task: the layout is 580 pixels wide, the stage has a width of 0 and the Details button lies outside the screen. Added by PLAN-008 after the owner opened the published site on a phone on 2026-11-17 and found it not usable there; narrowed by PLAN-009 to where an open panel is drawn. After this task alone, on a phone, both panels are still open when the page opens and cover the stage, and the top bar is still cut off: FND-039 and FND-040 follow at once. The planner's trial has 26 browser tests at five narrow widths and at 900 pixels, and detects 11 of 11 planted defects.
- **Acceptance criteria:**
  1. At 320, 360, 390, 768 and 899 pixels wide, the top bar and the globe stage each have the whole width of the screen, with both panels open, with one open and with none.
  2. There, an open sections panel lies over the stage from the left edge and an open details panel from the right edge, each as tall as the stage, on top of it, and never wider than the screen.
  3. There, the page itself does not scroll, sideways or down.
  4. At 900 pixels wide the panels stand beside the stage, as on any wider screen.
  5. No existing test changed, and all pass.
  6. `python scripts/check.py` reports 19 of 19 gates and 631 tests (browser tests 113); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** browser tests at five narrow widths and at 900 pixels (26 new, 113 in all); the existing desktop tests unchanged; planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #42 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 631 passed, 0 failed, 0 skipped.", exit code 0 (browser tests 113); 11 of 11 planted defects in the style sheet detected by the browser tests (no narrow layout, the line at 800 or at 900 pixels, the panels under the stage, a panel wider than the screen, the details panel at the left, the panels in columns of their own, a panel half as tall as the stage, a stage that scrolls sideways). On GitHub, read by the planner from the runs and job logs: run 44393965951 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 631 passed, 0 failed, 0 skipped." with 113 browser tests, the three jobs after the gates skipped; run 44396093299 for `main` after the merge, all five jobs green, the gates with the same two closing lines on both machines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 631 / 0 tests (repository 40, script tests 164, backend 115, frontend unit 199, browser 113); all 19 gates passed, locally and on both machines on GitHub; 11 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-18. All 6 files are identical to the planner's trial. On a phone the published site is not yet better to use: both panels are open when the page opens and cover the stage, and the top bar is still cut off. FND-039 and FND-040 follow at once.
- **Commit:** `4f2f611`
- **Plan:** `docs/plans/FND-038.md`

### FND-039 – Narrow screens: the top bar fits
- **Status:** PASSED – VERIFIED
- **Objective:** On a narrow screen nothing in the top bar is cut off or out of reach.
- **Description:** On a narrow screen (under 900 pixels) the top bar takes the lines it needs instead of one fixed line: first the name between the two panel buttons, Sections at the left edge and Details at the right, then the data status and the date on a line of their own, each piece whole, sharing a line where both fit (a tablet held upright) and taking one each where they do not (a phone); the tagline gives way. The globe stage starts under the bar, however tall it is (99 pixels at phone widths, 78 at 768). From 900 pixels on the bar is unchanged: one line of 48 pixels, with the tagline. Style sheet only; the order of the elements in the page does not change. Added by PLAN-008, placed by PLAN-009 between FND-038 and FND-040: it needs a layout no wider than the screen, and FND-040's buttons must be in reach. Before this task the Details button lies outside the screen at 390 pixels. After it, on a phone, both panels are still open when the page opens: FND-040 follows at once. The planner's trial has 28 browser tests at five narrow widths and at 900 pixels, and detects 16 of 16 planted defects.
- **Acceptance criteria:**
  1. At 320, 360, 390, 768 and 899 pixels wide, each of the two buttons, the name, the data status and the date is whole, on one line, inside the top bar and inside the screen, and none lies over another.
  2. There, the tagline is not shown.
  3. From 360 pixels on, the first line holds the name between the two buttons, with the Sections button at the left edge and the Details button at the right edge, and the information starts right under that line at the left edge.
  4. At 360 and 390 pixels the data status and the date each have a line; at 768 and 899 pixels they share one.
  5. At 900 pixels the bar has one line, 48 pixels tall, with the tagline, in the order Sections, name, data status, date, Details.
  6. No test that exists today changed, and all pass.
  7. `python scripts/check.py` reports 19 of 19 gates and 659 tests (browser tests 141); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** browser tests at five narrow widths and at 900 pixels that measure every piece of the top bar (28 new, 141 in all); the existing tests unchanged; planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines, because the text is drawn with another font on Windows; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #44 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 659 passed, 0 failed, 0 skipped.", exit code 0 (browser tests 141); 16 of 16 planted defects in the style sheet detected by the browser tests (the bar kept to one line or to its fixed height, room between the lines, the wide gaps kept, the tagline kept, the information before the Details button or on the first line, pieces that wrap or run together, no room between or under them, lines as tall as the bar, an indented piece, the Details button right after the name, and two that change the wide bar). On GitHub, read by the planner from the runs and job logs: run 44399079910 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 659 passed, 0 failed, 0 skipped." with 141 browser tests, the three jobs after the gates skipped; run 44403512767 for `main` after the merge, all five jobs green, the gates with the same two closing lines on both machines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 659 / 0 tests (repository 40, script tests 164, backend 115, frontend unit 199, browser 141); all 19 gates passed, locally and on both machines on GitHub; 16 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-18. All 5 files are identical to the planner's trial. On a phone both panels are still open when the page opens and cover the stage; both buttons are now in reach to close them. FND-040 follows at once.
- **Commit:** `ad55c37`
- **Plan:** `docs/plans/FND-039.md`

### FND-040 – Narrow screens: the panels start closed, one open at a time
- **Status:** PASSED – VERIFIED
- **Objective:** On a narrow screen the page opens with the globe in view, and a panel covers it only when the user asks for it.
- **Description:** On a narrow screen (under 900 pixels) both side panels start closed, whatever was chosen on a wide screen. A button opens its panel over the globe stage and closes it again, and opening one panel closes the other. Nothing is remembered there and nothing is written to the session's memory, so loading the page again shows the globe. On a wide screen nothing changes: the panels start open and the session remembers the choice. Changing the width across 900 pixels (turning a tablet) switches between the two at once, and what was chosen on the wide screen is there again afterwards. One module tells the script what a narrow screen is (`frontend/src/layout/narrowScreen.ts`), and a unit test ties it to the style sheet's; a new hook (`useSidePanels.ts`) holds both behaviours, and the markup is unchanged. The unit tests get a stand-in for the width of the screen. Nothing closes a panel but its own button and the other panel's: what choosing a section does to the panel on a phone is decided with the first section that shows something. Split from FND-038 by PLAN-009. The planner's trial has 12 new unit tests and 17 new browser tests, and detects 17 of 17 planted defects.
- **Acceptance criteria:**
  1. At 320, 360, 390, 768 and 899 pixels wide the page opens with both panels closed, both buttons saying so, and the globe stage on top in the middle of the screen, also when the session remembers both panels open.
  2. There, each button opens its panel over the stage and closes it again.
  3. There, opening one panel closes the other, and its button says so.
  4. There, after the page is loaded again both panels are closed, and nothing was written to the session's memory.
  5. When the width crosses 900 pixels the page follows at once, in both directions, without being loaded again.
  6. What was chosen on a wide screen is untouched by anything done on a narrow one: it is there again when the screen is wide again, and after the page is loaded again.
  7. At 900 pixels and more nothing changes: every existing unit test and every browser test in the other files passes unchanged. In `frontend/e2e/narrow.spec.ts` three existing tests open the panels with the buttons instead of through the session's memory, which has no effect on a narrow screen any more; no assertion in them is removed or loosened.
  8. The line between narrow and wide is written once for the script, and a unit test fails when it differs from the style sheet's.
  9. `python scripts/check.py` reports 19 of 19 gates and 688 tests (frontend unit tests 211, browser tests 158); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** unit tests for the panel state and for the hook that follows the screen, with a stand-in for the width of the screen (12 new, 211 in all); browser tests at five narrow widths, at desktop size and across a change of width (17 new, 158 in all); planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #46 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 688 passed, 0 failed, 0 skipped.", exit code 0 (frontend unit tests 211, browser tests 158); 17 planted defects in the three source files and the test setup: 17 of 17 detected by the unit tests, and 15 of the 16 that reach the browser also by the browser tests (the sixteenth, a watcher of the screen that is never removed, can only be seen by a unit test, which detects it). On GitHub, read by the planner from the runs and job logs: run 44407441917 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 688 passed, 0 failed, 0 skipped." with 211 frontend unit tests and 158 browser tests, the three jobs after the gates skipped; run 44412568975 for `main` after the merge, all five jobs green, the gates with the same two closing lines on both machines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 688 / 0 tests (repository 40, script tests 164, backend 115, frontend unit 211, browser 158); all 19 gates passed, locally and on both machines on GitHub; 17 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-18. All 12 files are identical to the planner's trial. Three existing browser tests in `frontend/e2e/narrow.spec.ts` open the panels with the buttons instead of through the session's memory, which has no effect on a narrow screen any more; no assertion in them was removed or loosened. How the page behaves under a finger on a real phone is for the owner to see on the published site.
- **Commit:** `29c6dd2`
- **Plan:** `docs/plans/FND-040.md`

### FND-041 – Touch screens: controls a finger can hit
- **Status:** PASSED – VERIFIED
- **Objective:** On a touch screen every control is big enough to be hit with a finger.
- **Description:** Where the main way of pointing is a finger (`@media (pointer: coarse)`: a phone or a tablet, whatever its width), the two panel buttons and the nine sections are at least 44 pixels tall: one new token, `--size-touch-target`, and one small rule in each of the two style sheets. There the buttons also stand in the middle of the bar's first line instead of on its line of text: the line is 48 pixels tall, and the planner's first trial showed on GitHub's machines that a tall button set on the line of text reaches out of the bar with some fonts. So the bar keeps its height. With a mouse nothing changes (buttons 31 pixels, sections 40). Style sheets only. Added by PLAN-008 as part of FND-040; a task of its own since PLAN-009. The planner's trial has 8 new browser tests, with and without a touch screen, and detects 10 of 10 planted defects.
- **Acceptance criteria:**
  1. With a touch screen, at 390 by 844 and at 1366 by 768 pixels, each of the two buttons in the top bar is 44 pixels tall, at least 44 wide, and exactly in the middle of the first line of the bar.
  2. There, each of the nine sections is 44 pixels tall, at least 44 wide, and follows right under the one before.
  3. With a touch screen the top bar is no taller than with a mouse: 48 pixels on a wide screen, and on a phone the same height as with a mouse.
  4. With a mouse, at both sizes, the buttons are 31 pixels tall and the sections 40, as before.
  5. The height is one token, `--size-touch-target`, and the unit test of the agreed tokens knows it.
  6. No existing test changed, and all pass.
  7. `python scripts/check.py` reports 19 of 19 gates and 696 tests (frontend unit tests 211, browser tests 166); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** browser tests with and without a touch screen, at phone and at desktop size, that measure each control and the top bar (8 new, 166 in all); the unit test of the agreed tokens; the existing tests unchanged; planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #48 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 696 passed, 0 failed, 0 skipped.", exit code 0 (frontend unit tests 211, browser tests 166); 10 planted defects in the three style sheets, 10 of 10 detected by the browser tests; the token removed, detected by 2 unit tests. On GitHub, read by the planner from the runs and job logs: run 44417318012 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 696 passed, 0 failed, 0 skipped." with 211 frontend unit tests and 166 browser tests, the three jobs after the gates skipped; run 44418757631 for `main` after the merge, all five jobs green, the gates with the same two closing lines on both machines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 696 / 0 tests (repository 40, script tests 164, backend 115, frontend unit 211, browser 166); all 19 gates passed, locally and on both machines on GitHub; 11 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-18. All 9 files are identical to the planner's trial. No existing test changed. The planner's first trial failed on GitHub's machines only (3 of 696 tests, on Linux and on Windows): with their fonts the tall buttons, set on the bar's line of text, reached half a pixel out of the bar. The design was corrected before the plan was written, and the tests now check the exact place of the buttons. Whether a finger hits the controls comfortably on a real phone is for the owner to see on the published site.
- **Commit:** `93150ef`
- **Plan:** `docs/plans/FND-041.md`

### FND-042 – Phones: the layout follows the visible height
- **Status:** PASSED – VERIFIED
- **Objective:** On a phone the layout is as tall as the part of the screen the browser really shows, so its lower edge is never under the browser's own bars.
- **Description:** A phone's browser shows and hides its own bars, and the height the layout used until now (`100vh`) is measured as if they were hidden. The layout's height and the page's least height become `100dvh`, the height that follows the bars. There is no `100vh` line as a fallback, although this task's first wording asked for one: the planner's trial showed that the build is made for browsers that all know `dvh` (Vite's default list: Chrome and Edge 111, Firefox 114, Safari and iOS 16.4), that its minifier therefore removes such a line as dead code, and that a browser old enough to need it would not run the application's script either. A unit test rejects `vh` in any style sheet under `frontend/src`. Style sheets only. Added by PLAN-008 as part of FND-040; a task of its own since PLAN-009, because the test browser has no bars that come and go: there the two heights are equal, so the tests can show that the style sheets ask for the right height and that nothing else changed, and only a real phone can show the rest. The planner's trial has 1 new unit test and 5 new browser tests, and detects 10 of 10 planted defects.
- **Acceptance criteria:**
  1. The style sheets, as the browser received them, ask for `100dvh` as the layout's height and as the page's least height.
  2. At 390 by 844, 844 by 390 and 1366 by 768 pixels the layout starts at the top left corner and is exactly as wide and as tall as the screen.
  3. No style sheet under `frontend/src` measures in `vh`, and a unit test fails when one does.
  4. No existing test changed, and all pass.
  5. `python scripts/check.py` reports 19 of 19 gates and 702 tests (frontend unit tests 212, browser tests 171); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
  6. The effect on a real phone is confirmed by the owner on the published site and recorded as such, not as a test result.
- **Tests required:** a unit test that reads every style sheet (1 new, 212 in all); browser tests that read the rules the browser received and measure the layout at phone size, turned on its side, and at desktop size (5 new, 171 in all); the existing tests unchanged; planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #50 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 702 passed, 0 failed, 0 skipped.", exit code 0 (frontend unit tests 212, browser tests 171); the built style sheet read: it holds `height:100dvh` twice (the layout's height and the page's least height) and no `vh` height; 10 planted defects in the two style sheets, 10 of 10 detected by the browser tests, and the 3 of them that bring `vh` back also by the new unit test. On GitHub, read by the planner from the runs and job logs: run 44420719471 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 702 passed, 0 failed, 0 skipped." with 212 frontend unit tests and 171 browser tests, the three jobs after the gates skipped; run 44423224253 for `main` after the merge, all five jobs green, the gates with the same two closing lines on both machines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 702 / 0 tests (repository 40, script tests 164, backend 115, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 10 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Criteria 1 to 5 verified by the planner on 2026-11-18: every applicable test passed, all 8 files are identical to the planner's trial, and no existing test changed. Acceptance criterion 6, the effect on a real phone, was open at first. The blocker: the test browser has no bars that come and go, so only the owner, with a real phone, can confirm on the published site that the lower edge of the layout stays in view while the browser shows its bars. The owner was asked on 2026-11-18 to open the published site on a phone and say whether the bottom of the page stays in view while the browser's own bars are showing, and whether the buttons are easy to hit. Criterion 6 confirmed by the owner the same day, at 23:57 UK time, in these words: "Test on mobile looks good". This is the owner's confirmation, not a test result. With it every acceptance criterion is met and the task is verified.
- **Commit:** `608e741`
- **Plan:** `docs/plans/FND-042.md`

### FND-019 – Local use: a check of the tools a computer needs
- **Status:** PASSED – VERIFIED
- **Objective:** One command says whether a computer has the tools MotoSphere needs, which version of each it found, and where to get one that is missing, too old or broken.
- **Description:** A script, `python scripts/tools.py`, with the Python standard library only. It looks at five tools in the order a new computer needs them (Python, Git, uv, Node.js, npm), asks each for its version by its full path, and writes one line for each: found, missing, too old or broken, with the place to get it. Python's least version is read from `backend/pyproject.toml` and Node.js's from `frontend/package.json`, the files where uv and npm read them, so each is written once. "Python" is the Python that runs the script. A Python older than 3.12 is told so in one plain sentence before it reaches lines it cannot run. The script installs nothing and changes nothing, and it is not a gate: a gate whose tool is missing fails by itself. Narrowed by PLAN-010 from "Windows scripts for local use", which became four tasks; this one is Python and is tested on Linux and on GitHub's Windows machine. The planner's trial has 42 new tests and detects 26 of 26 planted defects.
- **Acceptance criteria:**
  1. `python scripts/tools.py` lists Python, Git, uv, Node.js and npm, in that order, each with the version it found, and Python and Node.js with the least version the project asks for; it ends with how many of the five are ready. The exit code is 0 only when all five are.
  2. A tool that is missing, older than its least version or broken (it cannot be started, stops with an error, gives no answer within 30 seconds or does not say its version) is named as such, with the place to get it, and the exit code is 1.
  3. The least versions are read from `backend/pyproject.toml` and `frontend/package.json`. A file that is missing or unreadable, or that names no least version in the form `>=1.2`, ends the check with one plain sentence and exit code 1.
  4. A Python older than 3.12 gets one plain sentence and exit code 1, not an error trace.
  5. The script uses the Python standard library only, installs nothing and changes nothing.
  6. No existing test changed, and all pass.
  7. `python scripts/check.py` reports 19 of 19 gates and 744 tests (script tests 206); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** script tests (42 new, 206 in all): lines the real tools printed, the real Python asked for its version, stand-ins for a tool that is missing, too old or broken, the script run for real on the computer that runs the tests (all five tools ready) and once with a search path that holds no tool, and an older Python; the existing tests unchanged; planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #52 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 744 passed, 0 failed, 0 skipped.", exit code 0 (script tests 206); the script itself, five tools found, "5 of 5 tools are ready.", exit code 0, and started with Python 3.11 one plain sentence and exit code 1; 26 planted defects in the script, 26 of 26 detected, the plan's twelve prove-it steps among them. On GitHub, read by the planner from the runs and job logs: run 44428583058 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 744 passed, 0 failed, 0 skipped." with 206 script tests, the three jobs after the gates skipped; run 44429659797 for `main` after the merge: on its first attempt "All gates (Linux)" was green and "All gates (Windows)" failed with "18 of 19 gates passed. FAILED: Browser tests." and "Tests: 743 passed, 1 failed, 0 skipped.", because one browser test ("layout at 1920×1080 › the globe stage is the largest region") could not open the page, the browser on that machine reporting `net::ERR_NO_BUFFER_SPACE` for the test server's address, and the three jobs after the gates were skipped; the failed job was run once more, and on the second attempt all five jobs were green, the Windows gates ending "19 of 19 gates passed." and "Tests: 744 passed, 0 failed, 0 skipped.", the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 744 / 0 tests (repository 40, script tests 206, backend 115, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub, on the Windows machine for `main` at the second attempt (743 / 1 at the first); 26 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 6 files are identical to the planner's trial. No existing test changed. The planner's trial first detected 25 of 26 planted defects, and one test was added; one more test was rewritten before the plan, because it could not fail where `python` on the search path is the Python that runs the tests. The script was run on Linux and, by its tests, on GitHub's Windows machine (Windows Server 2025); it was not run on a Windows 11 PC, and after the owner's decision of the same day (PLAN-011) no task asks for that. The one failure on GitHub's Windows machine is recorded as a failure of that attempt: the browser could not reach the test server on the same machine, the task changed no file the browser tests read, and the same frontend files passed on that kind of machine in four other runs that night (44425486127, 44426691356, 44428583058 and the second attempt). It was seen once; if it is seen again it becomes a task of its own.
- **Commit:** `fb8b6ed`
- **Plan:** `docs/plans/FND-019.md`

### FND-043 – The loading test waits for its request
- **Status:** PASSED – VERIFIED
- **Objective:** The browser test "says the data is loading until it arrives" passes or fails for what the page does, never for the moment at which it looks.
- **Description:** Added on 2026-11-19 (PLAN-015), after the builder of DAT-004 saw this test of FND-028 fail once in a full local run and pass in the next, with nothing changed. The test holds the request for the manifest back, waits for "Loading data…" and then, at once, expects that the request has arrived. The page says "Loading data…" from its first drawing and sends the request a moment later, so the test can look before the request is there ("Expected length: 1, Received length: 0"). The test now waits for the request (`expect.poll`, part of Playwright) and then reads what the page says while the request is held back. Only the test changes: the page is right, and nothing under `frontend/src` changes. `TESTING.md` gains the rule: a check that does not wait is right only for what must have happened before the thing the test waited for last. The planner searched the other browser tests for the same fault and found none. No new package and no retries.
- **Acceptance criteria:**
  1. With a request that starts late, the test as it is on `main` fails every time with "Expected length: 1, Received length: 0", and the changed test passes.
  2. The changed test passes 100 times of 100 when it is repeated.
  3. The changed test fails when the page says something else while the request is held back, when the page does not ask for the manifest where it should, and when it asks twice.
  4. No file under `frontend/src` changed, no other test changed, and the number of browser tests is the same (171).
  5. `python scripts/check.py` reports 19 of 19 gates and 851 tests; on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** the test as it is and the changed test, each with a request that starts 0.4 seconds late; the changed test repeated 100 times; four planted faults in the page (another text while loading, "Data unavailable" before the page has asked, a request to another address, two requests); the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #67 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32, Playwright 1.63.0), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 851 passed, 0 failed, 0 skipped.", exit code 0 (browser tests 171); the changed test repeated 100 times, 100 passed; with a request that starts 0.4 seconds late, the test as it was on `main` failed 3 times of 3 with "Expected length: 1, Received length: 0" and the changed test passed; four planted faults in the page, 4 of 4 detected by the changed test. On GitHub, read by the planner from the runs and job logs: run 44460533369 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 851 passed, 0 failed, 0 skipped." with 171 browser tests, the three jobs after the gates skipped; run 44461468925 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 851 / 0 tests (repository 41, script tests 206, backend 221, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 100 / 0 repeats of the changed test; 4 / 0 planted faults detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 3 files are identical to the planner's trial. Nothing under `frontend/src` changed, no other test changed, and no test was added, removed or skipped. The fault was a race in the test, not in the page: the page says "Loading data…" before it asks for the data, and the test expected the request to be there as soon as the page said so. It could not be met by repeating the test (450 passes of 450) and was met every time with a late request. The other browser tests were searched for the same fault, and none has it. That a test cannot fail by chance cannot be proven by running it; what is shown is that the one known cause is gone.
- **Commit:** `846e470`
- **Plan:** `docs/plans/FND-043.md`

---

# Phase 2 – Data store and published data (DAT, PUB)

Written out in full by PLAN-012. The pipeline gets a real store (SQLite) and
publishes real files from it. Every task that touches the store is tested
against a real SQLite file, never a mock. A task's details are settled by
the planner's trial before its plan is written, and a task that proves too
large to test thoroughly is split then. The first such split (PLAN-013):
the old DAT-002 is DAT-002, DAT-021 and DAT-022, which follow one another
here although their numbers do not. The second (PLAN-014): the old DAT-004
is DAT-004, DAT-023, DAT-024, DAT-025 and, after DAT-005, DAT-026.
PLAN-014 also decided that no migration has a way back; the tasks that add
tables test their migration from the version before it. The third
(PLAN-016): DAT-025 needs a way to ask which migrations a store lacks
without migrating it, and that is DAT-027, which stands before it. The
fourth (PLAN-017): the old DAT-005 is DAT-005, DAT-028, DAT-029 and
DAT-030, and DAT-026 follows the four. The fifth (PLAN-018): DAT-029 is
the key alone, and the timestamps are DAT-031, which follows it. The sixth
(PLAN-019): DAT-031 is the timestamps themselves, and naming a table
without them is DAT-032, which follows it. The seventh (PLAN-020): DAT-030
is the check for text that must not be empty, and naming a column without
that check is DAT-033, which follows it. Four tasks were added before the
first table (PLAN-021): DAT-034 lets any column type bring the check for
its column, and DAT-035, DAT-036 and DAT-037 are the three kinds of column
the first table needs and the store did not have. One more was added
before the first table (PLAN-022): DAT-038, a rule against two constraints
of one name in a table, which the trial of DAT-037 showed to be missing.

The task of the first table, DAT-006, was then cut into smaller ones
(PLAN-023): DAT-039 has the two lists a source is described by; DAT-006
keeps the table, with who a source is and how it may be used; DAT-040 has
the kinds of information a source offers; and DAT-041, after the table of
the runs (DAT-007), says how a source is doing.

The trial of DAT-041 showed which index the table of the runs needs, and
the index was cut out as a task of its own (PLAN-024): DAT-042.

The task that gives every collected record its provenance, DAT-008, was
cut before its trial (PLAN-025): DAT-043 has the two lists that say how
far a record can be trusted, and DAT-008 keeps the columns. Its trial
then showed that one of those columns, the day a record was published,
needs a type the store did not have, and the type was put in front of it
as a task of its own (PLAN-026): DAT-044. The trial of the columns then
cut two more things out of DAT-008 (PLAN-027): the index for the records
of one source, DAT-045, and the rule that names a table of collected
records made without the columns, DAT-046.

The trial of the change history, DAT-009, cut it down to the table of
the changes (PLAN-028). The function that writes a change with its
history is DAT-047, that a row of the history is neither edited nor
deleted is DAT-048, and the indexes of the history are DAT-049.

### DAT-001 – Data store research and decision record
- **Status:** PASSED – VERIFIED
- **Objective:** Decide, with evidence, what the data store may rely on: which SQLite features every machine that runs the pipeline has, where the store is kept between scheduled runs, and which size limits bound it.
- **Description:** A module, `motosphere.db.sqlite`, names the least SQLite version (3.45.0) and the six features the store relies on (enforced foreign keys, strict tables, RETURNING, the JSON functions, R*Tree, FTS5), and its function `missing()` says in plain words what a given SQLite lacks. Each feature is proven by statements a database must accept and, for two, one it must then refuse, in an empty database of its own in memory. Its tests run against the real SQLite of the Python that runs the pipeline, so the gates prove it on Linux and on Windows for every change; a lesser SQLite is stood in for by the real one made to behave like it, never by a mock. `DATABASE.md` becomes the decision record, with its sources: what the planner's probe found on each machine (SQLite 3.45.1 on GitHub's Linux, 3.49.1 on GitHub's Windows, 3.53.1 on the planner's; Geopoly and the `dbstat` table are not everywhere), where the store is kept between runs (text files in a `data` branch, with the database file as a release asset in reserve; a workflow cache or artifact does not last), GitHub's documented limits, and the sizes at which the decision is looked at again. `ARCHITECTURE.md` §5 loses its open question. No table and no connection module yet. The planner's trial has 36 new tests and detects 33 of 33 planted defects.
- **Acceptance criteria:**
  1. `missing()` returns an empty list for the SQLite of GitHub's Linux machine, of GitHub's Windows machine and of the planner's.
  2. An SQLite older than 3.45.0 is reported with its version and the least version, compared as numbers; 3.45.0 itself is not.
  3. Each of the six features is reported by name when a build lacks it, and foreign keys and strict tables also when the build accepts the statements and enforces nothing.
  4. Everything lacking is reported together, the version first.
  5. Each feature is tried in an empty database of its own in memory, every one is closed, and no file is written.
  6. `DATABASE.md` gives the least version and the six features the module names, and a test fails when the two differ.
  7. `DATABASE.md` records, each with the page it was read from and the day, what each machine's SQLite had, where the store is kept between runs and why, GitHub's limits, and the sizes at which the decision is looked at again; `ARCHITECTURE.md` §5 no longer has an open question.
  8. No existing test changed, and all pass.
  9. `python scripts/check.py` reports 19 of 19 gates and 780 tests (backend tests 151); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** backend unit tests with the real SQLite made to behave like a lesser one (33 new): an older version, a build without each feature, one that enforces nothing, everything lacking at once, a database of its own for each feature, the decision record compared with the module; backend integration tests against the machine's own SQLite (3 new); the existing tests unchanged; planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #55 (Linux, Python 3.13.18 with SQLite 3.53.1, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 780 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 151: 115 before, 36 new); 33 planted defects in the module and the decision record, 33 of 33 detected by the new tests, the plan's twelve prove-it steps among them with the counts the plan gives. On GitHub, read by the planner from the runs and job logs: run 44435455047 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 780 passed, 0 failed, 0 skipped." with 151 backend tests, the three jobs after the gates skipped; run 44436500524 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 780 / 0 tests (repository 40, script tests 206, backend 151, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 33 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 8 files are identical to the planner's trial. No existing test changed. The three integration tests ran against each machine's own SQLite: 3.53.1 on the planner's, and on GitHub's machines the Pythons of the planner's probe (3.12.16 on Linux, 3.12.10 on Windows, read from the logs), whose SQLite the probe read as 3.45.1 and 3.49.1; the runs themselves do not print the SQLite version. The planner's trial first detected 30 of 33 planted defects: the statements for RETURNING and for the JSON functions could be replaced unnoticed, so one parametrized test was added (a build without each feature), and one planted defect that changed nothing was replaced by one that does. Every figure in `DATABASE.md` about GitHub's limits was read by the planner from GitHub's documentation on 2026-11-19 and names its page. The job that writes the `data` branch does not exist yet; it is planned with the first task that collects real records.
- **Commit:** `a71f880`
- **Plan:** `docs/plans/DAT-001.md`

### DAT-002 – Store path setting
- **Status:** PASSED – VERIFIED
- **Objective:** The pipeline knows where its data store's file is from one validated setting, and a store's file can never be committed by accident.
- **Description:** One new setting, `store_path` (`MOTOSPHERE_STORE_PATH` in the environment or in `backend/.env`), a path, by default `store/motosphere.sqlite3` in the `backend` folder. An empty value is refused in plain words when the settings are read; spaces around a value are dropped. Reading the settings creates no file and no folder. Git ignores `backend/store/` and every `*.sqlite3` file with the files SQLite keeps beside one, anywhere; a repository check reads the default from `backend/.env.example` and fails if Git would not ignore it. A new test holds the README's table of settings to the code. Nothing opens the store yet (DAT-021). This is the first third of the old "DAT-002 – Store settings and connection module" (PLAN-013). The planner's trial has 11 new tests and detects 22 of 22 planted defects.
- **Acceptance criteria:**
  1. `Settings().store_path` is the path `store/motosphere.sqlite3` when nothing is set, and the value of `MOTOSPHERE_STORE_PATH` from the environment or from `backend/.env` when it is.
  2. An empty value, or one of spaces only, is refused when the settings are read, with a message that names `store_path` and says the path must not be empty. Spaces around a value are dropped; spaces inside it stay.
  3. Reading the settings creates no file and no folder, with the default and with a set value.
  4. `backend/.env.example` and the README's table list the setting with its default, and tests fail when either differs from the code.
  5. Git ignores `backend/store/` and everything in it, every `*.sqlite3` file and every `*.sqlite3-*` file, anywhere in the repository; a repository check fails if the default in `backend/.env.example` is a place Git does not ignore.
  6. `python scripts/check.py` reports 19 of 19 gates and 791 tests (repository checks 41, backend tests 161); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
  7. Only the nine planned files changed; of the existing tests only `test_settings_are_exactly_the_documented_ones` changed, in what it expects.
- **Tests required:** backend unit tests of the setting (10 new: the default, the environment, the `.env` file, spaces, an empty value in three forms, nothing created with the default and with a set value, the README's table); one new repository check (the default place is ignored) and four more sample paths in an existing one; the existing tests; planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #57 (Linux, Python 3.13.18, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 791 passed, 0 failed, 0 skipped.", exit code 0 (repository checks 41: 40 before, 1 new; backend tests 161: 151 before, 10 new); 22 planted defects in the setting, the example file, the ignore file and the README, 22 of 22 detected, the plan's ten prove-it steps among them with the counts the plan gives. On GitHub, read by the planner from the runs and job logs: run 44439304001 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 791 passed, 0 failed, 0 skipped." with 41 repository checks and 161 backend tests, the three jobs after the gates skipped; run 44440230084 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 791 / 0 tests (repository 41, script tests 206, backend 161, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 22 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 9 files are identical to the planner's trial. One existing test changed, in what it expects: `test_settings_are_exactly_the_documented_ones` lists the settings and gained the new one. The planner's trial first detected 21 of 22 planted defects: a setting that made the store's folder while being read went unnoticed for a set value, and the test was extended to read one. Nothing opens the store yet, so no file is made by anything in the project.
- **Commit:** `8b77706`
- **Plan:** `docs/plans/DAT-002.md`

### DAT-021 – Opening the store
- **Status:** PASSED – VERIFIED
- **Objective:** The pipeline opens its store through one function; every connection enforces foreign keys, work that fails is taken back as a whole, and an SQLite that lacks what the store relies on is refused before anything is written.
- **Description:** Adds SQLAlchemy 2 to the pipeline (`sqlalchemy>=2.1`, locked at 2.1.9; no other new package). One module, `motosphere.db.store`, with `open_store(path)` and `StoreError`. The function asks `missing()` of DAT-001 first and refuses with everything the SQLite lacks in one sentence, before it touches the disk. It makes the path whole, makes the store's folder if it is not there, and returns the engine. Foreign keys are switched on for every connection in the engine's `connect` event. Transactions are SQLite's own (`autocommit=False`, the setting SQLAlchemy documents for Python 3.12 and newer), so a new table is taken back with the rest of a failed piece of work. No connection is kept open after use (`NullPool`). A path that is a folder, a folder that cannot be made and a file that is not an SQLite database are refused in plain words. No session, no fixture, no table of the application yet. The second third of the old DAT-002 (PLAN-013). The planner's trial has 19 new tests against a real SQLite file and detects 28 of 28 planted defects.
- **Acceptance criteria:**
  1. `open_store(path)` returns an engine for the SQLite file at `path`. A file that is not there is created with its folder; a relative path is taken from the current folder at that moment and the engine keeps to that file.
  2. A row that breaks a foreign key is refused on the first connection, on every later one, on two that are open at once, and after the store has been opened again. A row that keeps it is accepted.
  3. Work on a connection that fails part-way leaves nothing behind, neither a row nor a new table. Work that is not committed is not kept. Committed work is there when the store is opened again.
  4. Every connection is closed when its work is done, and the file can be removed afterwards, on Windows too.
  5. An SQLite that lacks what DAT-001 names is refused with one sentence that holds everything it lacks, and no file and no folder is made.
  6. A path that is a folder, a folder that cannot be made, and a file that is not an SQLite database are each refused with one plain sentence that names the whole path; the file that is not a database is left as it was.
  7. The type check passes with SQLAlchemy's own types and no `ignore`.
  8. No existing test changed, and all pass. `python scripts/check.py` reports 19 of 19 gates and 810 tests (backend tests 180); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** backend integration tests against a real SQLite file in the test's own folder (19 new): the file and its folder, a relative path, foreign keys on the first, later, simultaneous and reopened connections, a row that is accepted, committed work, a row and a new table of failed work, uncommitted work, every connection closed, the file removed after use, and the four refusals with their sentences; the existing tests unchanged; planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #59 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 810 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 180: 161 before, 19 new); 28 planted defects in the module, 28 of 28 detected by the new tests, the plan's eleven prove-it steps among them with the counts the plan gives. On GitHub, read by the planner from the runs and job logs: run 44443403050 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 810 passed, 0 failed, 0 skipped." with 180 backend tests, the three jobs after the gates skipped; run 44444397196 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 810 / 0 tests (repository 41, script tests 206, backend 180, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 28 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 8 files are identical to the planner's trial, the lock file included. No existing test changed. The 19 new tests run against a real SQLite file in the test's own folder, on Linux and on Windows; none uses a mock. The planner's trial first detected 27 of 28 planted defects (a path that was not made whole changed only the messages, and the test of the refused folder now passes a relative path), and one line that did nothing was found by the planted defects and the design corrected before the plan. A connection pool that keeps connections is detected on every run by one test; a second test fails beside it, a different one from run to run, so it is not among the prove-it steps. The pipeline's 8 locked run-time packages were checked once with `pip-audit` on 2026-11-19 ("No known vulnerabilities found"); the gate for that is PRF-005. Nothing in the pipeline calls `open_store` yet.
- **Commit:** `d2f71e7`
- **Plan:** `docs/plans/DAT-021.md`

### DAT-022 – Units of work
- **Status:** PASSED – VERIFIED
- **Objective:** Everything the pipeline writes to the store is written in units of work, each of which is kept as a whole or not at all.
- **Description:** One new module, `motosphere.db.work`, with one function, `unit_of_work(store)`, used in a `with` statement on the engine `open_store` returned (DAT-021). It gives an SQLAlchemy session for one piece of work. When the block ends the work is committed as a whole; when it raises, everything it did is taken back and the error reaches the caller as it was raised; the connection is closed either way. A unit that calls `commit()` itself is refused in one plain sentence, and one that called `rollback()` cannot go on. The session cannot be used after its unit has ended, and what the work read or wrote can still be read then. No new package, no fixture, no table or model of the application. The last third of the old DAT-002 (PLAN-013). The planner's trial has 18 new tests against a real SQLite file and detects 16 of 16 planted defects.
- **Acceptance criteria:**
  1. Work done in `with unit_of_work(store) as work:` is committed when the block ends, rows that were only added included. It is there for the next unit of work and when the store is opened again.
  2. Work that raises leaves nothing behind, neither a row nor a new table, whether an ordinary exception ended it or one that is not (as Ctrl+C is). The store can be worked on afterwards.
  3. The error that ended the work reaches the caller as the same object.
  4. A row that breaks a foreign key ends the whole unit, whether its statement was sent at once or the row is written when the unit ends.
  5. A unit of work uses one connection and closes it, when the work ends and when it fails; the file can be removed afterwards, on Windows too.
  6. A unit that calls `commit()` is refused with "A unit of work is kept as a whole when it ends; it cannot be committed part-way." and nothing of it is kept. A unit that called `rollback()` cannot go on, and nothing of it is kept.
  7. After the unit has ended, what it read or wrote can be read without a new connection, and the session refuses to be used.
  8. The type check passes with SQLAlchemy's own types and no `ignore`.
  9. No existing test changed, and all pass. `python scripts/check.py` reports 19 of 19 gates and 828 tests (backend tests 198); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** backend integration tests against a real SQLite file in the test's own folder (18 new): work kept for the next unit and for a reopened store, rows that were only added, a row and a new table of failed work, the store after failed work, the error unchanged, work stopped from outside, a broken foreign key at once and at the end, one connection closed after work that ends and work that fails, the file removed afterwards, a commit part-way, work that took itself back, what was written and read still readable, the session after its unit; the existing tests unchanged; planted defects; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #61 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 828 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 198: 180 before, 18 new); 16 planted defects in the module, 16 of 16 detected by the new tests, the plan's ten prove-it steps among them with the counts the plan gives. On GitHub, read by the planner from the runs and job logs: run 44447177749 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 828 passed, 0 failed, 0 skipped." with 198 backend tests, the three jobs after the gates skipped; run 44448306339 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 828 / 0 tests (repository 41, script tests 206, backend 198, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 16 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 6 files are identical to the planner's trial. No existing test changed and no package was added. The 18 new tests do units of work on a real SQLite file in the test's own folder, on Linux and on Windows; none uses a mock, and their two small tables are the tests' own. In the planner's trial a seventeenth planted defect changed nothing and is not counted: SQLAlchemy's option `isolation_level="AUTOCOMMIT"` has no effect on this store's connections, which use SQLite's own transactions (DAT-021), so failed work is still taken back. One test of the trial was wrong at first and showed that a call of `Session.commit(work)`, the method of SQLAlchemy's own class, passes the guard by; the guard is against `work.commit()` called by mistake. A session bound to a connection that is never given back is detected by two tests, and is not a prove-it step because it leaves a connection open. Nothing in the pipeline calls `unit_of_work` yet.
- **Commit:** `ba0dd65`
- **Plan:** `docs/plans/DAT-022.md`

### DAT-003 – A real, separate store for every test
- **Status:** PASSED – VERIFIED
- **Objective:** Every database test gets its own real SQLite file and can never see another test's data, and a test that leaves a connection to its store open fails for that reason itself.
- **Description:** One pytest fixture, `store`, in `backend/tests/conftest.py`. It opens `store.sqlite3` in the test's own temporary folder through `open_store` (DAT-021) and gives the test the engine: a real, empty store that is nobody else's, never a mock (CLAUDE.md §3, `ARCHITECTURE.md` §5). The fixture remembers every connection taken from the engine. When the test has ended, it closes those that are still open, so that the file can be removed on Windows too, and fails with "Connections to its store that the test left open: N. They were closed for it.", which pytest reports as an error at the end of that test. What the fixture does after a test is tested by letting pytest run a small file of tests in a process of its own (pytest's `pytester`, no new package). No existing test changes. The planner's trial has 6 new tests and detects 15 of 15 planted defects.
- **Acceptance criteria:**
  1. A test that asks for `store` gets the engine of a real SQLite file, `store.sqlite3` in its own temporary folder, opened through `open_store` (a row without its parent is refused), and empty.
  2. Three tests that each expect an empty store and write the same key all pass. Nothing is shared between them, so their order cannot matter.
  3. A test that leaves connections open, one or two, through a session, or by dropping a connection without closing it, is reported by pytest as an error at the end of that test, with the sentence and the right number; a connection the test closed itself is not counted.
  4. Every connection that was left open is closed by the time the next test runs, and the store's file can be removed, on Windows too. The next test has a store of its own.
  5. A test that closes what it opened is not reported.
  6. The type check passes with no `ignore`.
  7. No existing test changed, and all pass. `python scripts/check.py` reports 19 of 19 gates and 834 tests (backend tests 204); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** tests of the fixture itself against a real SQLite file (6 new): an empty store and the same key three times, the file in the test's own folder, the store opened the pipeline's way, and one test in which pytest runs 16 tests by itself (four that leave connections open, one that follows a leaking test, one that closes what it opened, and ten that say each connection was closed and each file can be removed); the existing tests unchanged; planted defects (a shared file, connections not closed, a test not reported, among others); the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #63 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 834 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 204: 198 before, 6 new); 15 planted defects in the fixture, 15 of 15 detected by the new tests, the plan's eleven prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 44451398431 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 834 passed, 0 failed, 0 skipped." with 204 backend tests, the three jobs after the gates skipped; run 44452427141 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 834 / 0 tests (repository 41, script tests 206, backend 204, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 15 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 5 files are identical to the planner's trial. No existing test changed and no package was added (`pytester` is part of pytest). The store the fixture gives is a real SQLite file opened through `open_store`, on Linux and on Windows; nothing is a mock. One of the 6 tests lets pytest run 16 tests by itself in a process of its own, four of which leave connections open, and reads the outcome (16 passed, 4 errors, the four sentences); those 16 are not counted among the 834. The planner's trial first detected 14 of 15 planted defects (a sentence that gave the number of all connections taken, not of those left open), and one of those tests was extended. The acceptance criterion "in either order" of the first task entry became "nothing is shared between them, so their order cannot matter": the tests are not run in a random order, and no package for that was added. The existing tests of the store and of units of work keep their own helpers.
- **Commit:** `b555379`
- **Plan:** `docs/plans/DAT-003.md`

### DAT-004 – The migration runner
- **Status:** PASSED – VERIFIED
- **Objective:** The store's schema is built and changed only by numbered migrations, each kept as a whole with the store's new version or not at all.
- **Description:** One new module, `motosphere.db.migrations`. A migration is a function that is given a connection and changes the schema. The migrations stand in one tuple, `MIGRATIONS`, oldest first, and the place of a migration in it is its number; the tuple is empty until the first table (DAT-006). `schema_version(store)` reads the number of the last migration a store has had, which is kept in the file itself (SQLite's `user_version`; a new store is at 0). `migrate(store)` applies the migrations the store lacks, in order, each in one transaction together with its number, and returns the numbers. A store whose version the list does not know is refused with `SchemaError` and one plain sentence, and left as it is. The tool was chosen in the planner's trial: a runner of the project's own, not Alembic, which would add three packages for abilities the store does not use (the comparison is in `DATABASE.md`, "How the schema changes"). No migration has a way back: an earlier state of the store is an earlier snapshot in the `data` branch (PLAN-014). No command (DAT-024, DAT-025), no check that the file is a store of MotoSphere's (DAT-023), no model (DAT-005), no new package. The planner's trial has 17 new tests and detects 34 of 34 planted defects.
- **Acceptance criteria:**
  1. A new store is at version 0. `migrate` applies every migration in order and returns their numbers; the store is then at the newest version, and still is when it is opened again.
  2. Migrating a second time applies nothing and changes nothing. A store that has had some of the migrations is given only those it lacks.
  3. A migration that fails, with an ordinary error or one that is not (as Ctrl+C is), leaves the store at the version before it, with nothing of the failed migration kept; the migrations before it stay applied; the error reaches the caller as the same object; and the store goes on from there once the migration is mended.
  4. Each migration is one transaction together with its version: three migrations are three commits.
  5. A store newer than the list, or at a version below zero, is refused with `SchemaError` and "The data store cannot be brought up to date: its schema is version N, and this MotoSphere knows only the versions 0 to M.", and is left as it is.
  6. `migrate(store)` without a list uses `MIGRATIONS` as it is at that moment, and one test brings an empty store to the newest schema with the real list.
  7. A migration that commits by itself fails, and the store's version does not move.
  8. A migration can build anew a table that rows of another table point to, inside its transaction and with foreign keys on; foreign keys are enforced afterwards; and if it loses a row that is pointed to, it is refused and the store is as it was before.
  9. The type check passes with no `ignore` and the lint with no `noqa`. No existing test changed, and all pass. `python scripts/check.py` reports 19 of 19 gates and 851 tests (backend tests 221); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** integration tests against the real SQLite file the fixture `store` gives each test (17 new), with migrations of the tests' own: order, repetition, a store that lacks only some, the version after the store is opened again, a migration that fails (two ways) and the store going on afterwards, one commit for each migration, both refusals with their sentence, a migration that commits by itself, the real list, and a table built anew while rows point to it (kept, enforced afterwards, refused when a row is lost); the existing tests unchanged; planted defects (migrations applied again or in the wrong order, the version not written or written apart from its migration, a failed migration kept or passed over, a store that should be refused and is not, among others); the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #65 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 851 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 221: 204 before, 17 new); 34 planted defects in the module, 34 of 34 detected by the new tests, the plan's thirteen prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 44456115927 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 851 passed, 0 failed, 0 skipped." with 221 backend tests, the three jobs after the gates skipped; run 44457687600 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 851 / 0 tests (repository 41, script tests 206, backend 221, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 34 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 6 files are identical to the planner's trial. No existing test changed and no package was added. The 17 new tests run the runner on the real SQLite file the fixture `store` gives each test, on Linux and on Windows; nothing is a mock, and the fixture reported no connection left open. The list of migrations is empty, so the store still has no table; the test that brings an empty store to the newest schema with the real list passes with nothing to apply and will test every migration that is added. A migration that commits by itself fails and leaves what it did before its commit without a version; one test pins that, and the test with the real list keeps such a migration from being merged. Three tests build a table anew inside a migration while rows point to it, on GitHub's SQLite 3.45.1 and 3.49.1 too. No migration has a way back (PLAN-014).
- **Commit:** `c5e4687`
- **Plan:** `docs/plans/DAT-004.md`

### DAT-023 – Only a store of MotoSphere's is migrated
- **Status:** PASSED – VERIFIED
- **Objective:** A file that is not a MotoSphere data store is never migrated: it is refused in plain words and left as it is.
- **Description:** A store's file carries a mark: the number 1299141488 (the letters "MoSp", `APPLICATION_ID` in `motosphere.db.migrations`), in the field SQLite gives applications to say whose a database is (`application_id`). `migrate` looks at the file before anything else. A file with the mark is migrated. A file with no mark and nothing in it (no table, no view, version 0) is a new store, and gets the mark in the transaction of its first migration, so a file has the mark and its first version together or neither. Every other file is refused with `SchemaError` and one sentence that names the file and says why, before anything is written: a file with the mark of another application, and a file with no mark that has a table, a view or a version. The mark is looked at before the version, so the file of another program is never taken for a newer store. A new store that lacks no migration is still not written to. Marking a new file in a transaction of its own, before the first migration, was weighed and not taken. `open_store` and `schema_version` do not change. No new package.
- **Acceptance criteria:**
  1. The first migration of a new store marks the file: bytes 68 to 71 of the file are "MoSp". A store that carries the mark is migrated, also after it was opened again.
  2. The mark is written in the transaction of the first migration: three migrations of a new store are three commits, and a first migration that fails leaves the file byte for byte as it was. A new store that lacks no migration is not written to.
  3. A file with no mark that has a table, a view or a version, and a file with the mark of another application, are each refused with `SchemaError` and one exact sentence that names the file and says why, and each is byte for byte as before.
  4. A file with a version beyond the history and no mark is told that it is not MotoSphere's, not that it is newer; a marked store at a version the history does not know is refused as before.
  5. No existing test changed but one line of one test (it marks its file first), and all pass.
  6. `python scripts/check.py` reports 19 of 19 gates and 858 tests (backend tests 228); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 7 new integration tests against a real SQLite file, in which the files that are not MotoSphere's are made with SQLite alone; fourteen planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #69 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 858 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 228: 221 before, 7 new); 62 planted defects in the module, 62 of 62 detected (the 34 of DAT-004, fitted to the new loop, and 28 new ones, the plan's fourteen prove-it steps among them with the results the plan gives). On GitHub, read by the planner from the runs and job logs: run 44464487081 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 858 passed, 0 failed, 0 skipped.", the three jobs after the gates skipped; run 44465474527 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 858 / 0 tests (repository 41, script tests 206, backend 228, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 62 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 6 files are identical to the planner's trial. No package was added. One existing test changed by one line (it marks its file before it gives it the version -1, because a file with a version and no mark is now refused for its missing mark); no other existing test changed. The 7 new tests run against the real SQLite file the fixture `store` gives each test, on Linux and on Windows; the files that are not MotoSphere's are made with SQLite alone, and each is compared byte for byte before and after the refusal. The list of migrations is still empty, so today no file is marked by the pipeline: a new store that lacks no migration is not written to. `open_store` still opens any SQLite database, and `schema_version` reads any; only `migrate` refuses. What the command that says which schema a store has will say about a file that is not MotoSphere's is DAT-025's to settle.
- **Commit:** `c745c4b`
- **Plan:** `docs/plans/DAT-023.md`

### DAT-024 – Command: bring the store to the newest schema
- **Status:** PASSED – VERIFIED
- **Objective:** One command of the pipeline's command line brings the store the settings name to the newest schema and says what it did.
- **Description:** The command is `python -m motosphere migrate`, in one new module, `motosphere.cli.migrate`, built like the `export` command. It takes no argument: the store is the file `MOTOSPHERE_STORE_PATH` names. It makes the path whole, opens the store with `open_store` (which makes the file and its folder if they are not there), calls `migrate`, and writes one sentence to standard output, with the file's whole path: "A new data store was made: … is at schema version N.", "The data store was brought up to date: … went from schema version A to B." or "The data store is up to date: … is at schema version N." The sentences are one function by itself, `report`. A store that cannot be opened (`StoreError`) or that is refused (`SchemaError`) gives its own sentence on standard error, with nothing before or after it, nothing on standard output and the exit code 1, and is left as it is. An error inside a migration is not caught: it is a fault in the code, and the store stays at the version before that migration. It is the first command that uses the store and the first code that reads `MOTOSPHERE_STORE_PATH`. The pipeline's list of migrations is still empty, so today the command makes an empty file at version 0. No log line and no new package.
- **Acceptance criteria:**
  1. The command is in the command line's help, has a help of its own that names `MOTOSPHERE_STORE_PATH`, and takes no argument.
  2. Where there is no file, the store is made, with its folder, at the newest schema, and the command says so on standard output; exit code 0 and nothing on standard error. A second run says the store is up to date, and the file is byte for byte as before.
  3. A store that lacks migrations is given them, and the command says from which version to which. The file is named with its whole path, also when the setting is a relative path.
  4. The database of another program, a store newer than the code and a file that is no database each give exactly one line on standard error, their own sentence, nothing on standard output and the exit code 1, and the file is byte for byte as before.
  5. An error inside a migration reaches the caller as it was raised, and the store stays at the version before that migration.
  6. No existing test changed, and all pass. `python scripts/check.py` reports 19 of 19 gates and 876 tests (backend tests 246); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 18 new tests: 4 that run the real command in a process of its own against a real SQLite file, with the pipeline's own list of migrations; 6 that call the command in the test's process with a list of migrations of the test's own (the pipeline's is empty), against a real SQLite file; 8 unit tests of what it says and of its help. Fifteen planted defects by the builder and the planner's own; the command run by hand; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #71 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 876 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 246: 228 before, 18 new); 40 planted defects in the command, 40 of 40 detected, the plan's fifteen prove-it steps among them with the results the plan gives; the command run by hand in an empty folder, twice, and against a folder and against a database made by SQLite alone. On GitHub, read by the planner from the runs and job logs: run 44468959155 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 876 passed, 0 failed, 0 skipped.", the three jobs after the gates skipped; run 44470574256 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 876 / 0 tests (repository 41, script tests 206, backend 246, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 40 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 10 files are identical to the planner's trial. No existing test changed and no package was added. Four of the new tests run the real command in a process of its own, on Linux and on Windows, with the pipeline's own list of migrations, which is still empty: there the command makes an empty file at version 0. That the command gives a store the migrations it lacks, and says from which version to which, is tested in the test's process with a list of the test's own in the place of the pipeline's, against a real SQLite file; no process of its own has run the command with migrations yet, and the first task that adds one (DAT-006) will. An error inside a migration is not caught by the command, by decision. The command is not yet part of any scheduled run.
- **Commit:** `f209739`
- **Plan:** `docs/plans/DAT-024.md`

### DAT-027 – Say which migrations a store lacks
- **Status:** PASSED – VERIFIED
- **Objective:** One function says which migrations a store lacks, writes nothing, and refuses exactly the stores `migrate` refuses.
- **Description:** A new function, `pending(store)`, in `motosphere.db.migrations`. It returns the numbers of the migrations the store lacks, in order: all of them for a new store, none for a store that is up to date. It only reads. It refuses what `migrate` refused until now, with `SchemaError` and the same two sentences, which move into it unchanged: a file that is not a store of MotoSphere's (DAT-023), and a store at a version the history does not know (DAT-004). `migrate` asks `pending` and applies exactly the migrations it names; its transaction, the mark and the version are as before, and nothing it does changes. So the question "would this store be migrated, and by what?" has one answer in one place, and the command that says which schema a store has (DAT-025) can ask it without writing. No command, no sentence and no existing test changes. No new package. The planner's trial has 10 new tests and detects 74 of 74 planted defects.
- **Acceptance criteria:**
  1. `pending` names all migrations for a new store, those after the ones a store has had for a store that has had some, and none for a store that is up to date. Without a history it asks the store's own, `MIGRATIONS`, as it is at that moment.
  2. Asking commits nothing, and the file is byte for byte as before.
  3. `migrate` applies exactly the migrations `pending` named.
  4. A store `migrate` refuses (a table and no mark, the mark of another application, a newer store, a version below zero) is refused by `pending` with `SchemaError` in the same words, and is byte for byte as before.
  5. No existing test changed, and all pass. The type check passes with no `ignore` and the lint with no `noqa`.
  6. `python scripts/check.py` reports 19 of 19 gates and 886 tests (backend tests 256); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 10 new integration tests against a real SQLite file (what a new store lacks, one that has had some, one that is up to date; that asking writes nothing; the store's own history; that migrating applies what was named; four stores that are refused, each in the words `migrate` uses and each left as it is); all existing tests of the runner and of the command `migrate` unchanged; twelve planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #73 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 886 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 256: 246 before, 10 new); 74 planted defects in the module, 74 of 74 detected (42 of those of DAT-004 and DAT-023 that still fit the module word for word, and 32 new ones, the plan's twelve prove-it steps among them with the results the plan gives). On GitHub, read by the planner from the runs and job logs: run 44473530583 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 886 passed, 0 failed, 0 skipped.", with 256 backend tests on both machines, the three jobs after the gates skipped; run 44474646015 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 886 / 0 tests (repository 41, script tests 206, backend 256, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 74 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 5 files are identical to the planner's trial. No package was added and no existing test changed: the 24 earlier tests of the runner and the 18 of the command `migrate` pass as they were, so `migrate` does what it did. The 10 new tests run against the real SQLite file the fixture `store` gives each test, on Linux and on Windows; the four stores that are refused are each compared byte for byte before and after, and each refusal is compared word for word with what `migrate` says of the same store. Nothing calls `pending` yet but `migrate`; the command that says which schema a store has (DAT-025) is the first that will.
- **Commit:** `3a0ed18`
- **Plan:** `docs/plans/DAT-027.md`

### DAT-025 – Command: say which schema a store has
- **Status:** PASSED – VERIFIED
- **Objective:** One command says which schema the store has and whether it is the newest the code knows, and changes nothing.
- **Description:** The command is `python -m motosphere schema`, in one new module, `motosphere.cli.schema`, built like the `migrate` command. It takes no argument: the store is the file `MOTOSPHERE_STORE_PATH` names. It never writes. Where the path names nothing it says "There is no data store: … does not exist." and makes none (it does not call `open_store`, which would). Otherwise it opens the store, asks `pending` (DAT-027), and writes one sentence to standard output, with the file's whole path: "The data store is up to date: … is at schema version N." or "The data store lacks 2 migrations: … is at schema version 3, and the newest is version 5." In these three cases the exit code is 0. A store that cannot be opened, or that `migrate` would refuse (not MotoSphere's, newer than the code), gives the same sentence as there on standard error and the same exit code 1; the two commands ask the same function, so they cannot come to disagree about a store. The exit code 2 stays what it is everywhere: wrong arguments or wrong settings. No log line, no new package. The planner's trial has 25 new tests and detects 62 of 62 planted defects.
- **Acceptance criteria:**
  1. The command is in the command line's help, has a help of its own that names `MOTOSPHERE_STORE_PATH`, and takes no argument.
  2. Where there is no file, the command says so on standard output, with the exit code 0 and nothing on standard error, and afterwards there is no file and no folder for it either.
  3. A store at the newest schema is said to be up to date; a store that lacks migrations is told how many, its version and the newest, and is not given them; exit code 0. The file is named with its whole path, also when the setting is a relative path.
  4. A store that `migrate` would refuse gives, on standard error, exactly what `migrate` gives for it, nothing on standard output, and the exit code 1. A file that is no database, and a folder where the file should be, each give their one line and the exit code 1.
  5. In every case with a file, the file is byte for byte as before, and nothing is made beside it.
  6. No existing test changed, and all pass. `python scripts/check.py` reports 19 of 19 gates and 911 tests (backend tests 281); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 25 new tests: 4 that run the real command in a process of its own against a real SQLite file, with the pipeline's own list of migrations; 12 that call the command in the test's process with a list of migrations of the test's own (the pipeline's is empty), against a real SQLite file, four of which give a refused file to both commands and compare what they say; 9 unit tests of what it says and of its help. Seventeen planted defects by the builder and the planner's own (a command that makes the file or its folder, one that migrates, one that leaves a file beside the store, among others); the command run by hand; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #75 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 911 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 281: 256 before, 25 new); 62 planted defects in the command, 62 of 62 detected, the plan's seventeen prove-it steps among them with the results the plan gives; the command run by hand in an empty folder before and after `migrate`, and against a folder and against a database made by SQLite alone. On GitHub, read by the planner from the runs and job logs: run 44479205716 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 911 passed, 0 failed, 0 skipped.", with 281 backend tests on both machines, the three jobs after the gates skipped; run 44481346796 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 911 / 0 tests (repository 41, script tests 206, backend 281, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 62 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 10 files are identical to the planner's trial. No existing test changed and no package was added. Every test that gives the command a file compares the file byte for byte afterwards, and the tests without a file look for the file and its folder afterwards; seven of the planted defects are ways of writing where the command must not, and all seven are detected. Four files that `migrate` refuses are given to both commands, and what `schema` says is what `migrate` says, word for word. Four of the new tests run the real command in a process of its own, on Linux and on Windows, with the pipeline's own list of migrations, which is still empty: there the command says that there is no store, or that the store is up to date at version 0. That it says how many migrations a store lacks is tested in the test's process with a list of the test's own, against a real SQLite file; the first task that adds a migration (DAT-006) runs the real command with it.
- **Commit:** `c590ec0`
- **Plan:** `docs/plans/DAT-025.md`

### DAT-005 – The base of all models: strict tables and one naming rule
- **Status:** PASSED – VERIFIED
- **Objective:** Every table of the data store is strict, has columns of the types a strict table takes, and has its constraints and indexes named by one rule; and a test holds every table to that.
- **Description:** The first quarter of the old "DAT-005 – Model conventions: keys, times and names" (PLAN-017). One new module, `motosphere.db.base`. `Base` is the class every model is a subclass of; there is no model yet, the first comes with DAT-006. `Base` makes the table of every model strict when the model is defined, so SQLite refuses a value that is not of its column's type, and a model cannot leave that out, also not by saying something else of its table. A strict table takes INTEGER, REAL, TEXT and BLOB: `Base` makes a model's `str` TEXT and its `float` REAL (SQLAlchemy's own types for them are refused by SQLite in a strict table); `int` and `bytes` are INTEGER and BLOB already. One naming rule, `NAMING`: `pk_<table>`, `fk_<table>_<columns>_<table it points to>`, `uq_<table>_<columns>`, `ck_<table>_<what the model calls it>`, `ix_<table>_<columns>`, so a migration can name what it changes; a check without a name is refused when its table is defined. `broken_rules(schema)` says in plain sentences which tables are not strict and which constraints and indexes were named by hand, table by table and name by name. One test holds the real schema to it, and passes today because there is no table. The tests' own models are subclasses of `Base` with a schema of their own, so the real schema never holds them. No table, no migration, no new package. Times (DAT-028), the key and the timestamps (DAT-029) and text that must not be empty (DAT-030) follow. The planner's trial has 18 new tests and detects 41 of 41 planted defects.
- **Acceptance criteria:**
  1. The table of a model is strict in the store, also when the model says something of its table itself; a value that is not of its column's type is refused by SQLite.
  2. A model's `int`, `str`, `float` and `bytes` columns are INTEGER, TEXT, REAL and BLOB in the store, and values come back as they were stored.
  3. In the store, the key, a foreign key, a unique constraint, a check and two indexes of the tests' models have exactly the names the rule gives, on Linux and on Windows. A check without a name is refused when its table is defined.
  4. `broken_rules` gives an empty list for a schema that keeps the rules, and otherwise one sentence for each table that is not strict and for each key, unique constraint, foreign key or index named by hand, table by table and name by name.
  5. `broken_rules(Base.metadata)` is empty, and `Base.metadata` holds no table of the tests'. The type check passes with no `ignore` and the lint with no `noqa`.
  6. No existing test changed, and all pass. `python scripts/check.py` reports 19 of 19 gates and 929 tests (backend tests 299); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 18 new tests: 9 unit tests of `broken_rules` and of the naming rule (the real schema; a schema that keeps the rules; a table that is not strict; a key, a unique constraint, a foreign key and an index named by hand; the order of the sentences; a check without a name) and 9 integration tests that make two models' tables in a real SQLite file and read the file itself (the tables are strict; four values of the wrong type refused; the column types; values back as stored; the eight names). Fifteen planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #77 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 929 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 299: 281 before, 18 new); 41 planted defects in the module, 41 of 41 detected, the plan's fifteen prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 44485008294 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 929 passed, 0 failed, 0 skipped.", with 299 backend tests on both machines, the three jobs after the gates skipped; run 44486608897 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 929 / 0 tests (repository 41, script tests 206, backend 299, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 41 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 7 files are identical to the planner's trial. No existing test changed and no package was added. Nine of the new tests make the tables of two models of the tests' own in a real SQLite file, on Linux and on Windows, and read the file itself: SQLite says the tables are strict and refuses four values of the wrong type, the columns have the types a strict table takes, and the eight names of the key, the foreign key, the unique constraints, the check and the indexes are the ones the rule gives, on both machines. The real schema has no table yet, so the test that holds it to the rules passes with nothing to look at; a planted table that breaks a rule fails it. That test sees only models whose modules have been imported, which the first task with a model (DAT-006) must see to.
- **Commit:** `7d3c56c`
- **Plan:** `docs/plans/DAT-005.md`

### DAT-028 – Times in the store
- **Status:** PASSED – VERIFIED
- **Objective:** A time is stored in one way in every table: in UTC and with its offset; it comes back as an aware UTC time, and a time without an offset is refused.
- **Description:** Added on 2026-11-19 (PLAN-017): the second quarter of the old "DAT-005 – Model conventions: keys, times and names". A strict table has no type for a time (DAT-005: SQLite refuses SQLAlchemy's DATETIME there), so the store keeps a time as text in one form, `2026-11-19T08:26:04.123456+00:00`: always in UTC, always with its offset written out, always with the six digits of the fraction of its second. Every text has the same length, so the order of the texts is the order of the times, and the text can be read without the code, by a person and by SQLite's own date functions. One new module, `motosphere.db.times`: `to_text` says a time in the form and refuses what is not a time, a time without an offset (also one whose zone gives none) and a time UTC cannot say in the years 1 to 9999, each with one plain sentence; `from_text` reads text in the form as an aware UTC time and refuses text in any other form, also when it could be read as a time; `UtcDateTime` is the column type built from the two, TEXT in the table. `Base` gives the type to every column a model says is a `datetime`. Settled in the planner's trial: a time is kept to the microsecond, as Python has it, so nothing is lost; and the table itself does not check the form in this task: text in another form can only be written past the models, is refused when it is read, and whether the table should refuse it too is settled with the checks of DAT-030. Models of the tests' own prove it; no table is added. No new package. The planner's trial has 47 new tests and detects 49 of 49 planted defects.
- **Acceptance criteria:**
  1. A time is stored as text in the one form, in UTC, whatever offset it was given with; the text in the file, read with plain SQL, is exactly that text. What comes back is an aware UTC time equal to the one stored, and no time stays no time.
  2. A time without an offset is refused with its sentence, also in a question, and the unit of work it was part of stores nothing.
  3. Rows sorted or found by a time in the database come out by the order of the times, whatever offsets the times were given with, and SQLite's own date functions read the text as the same moment.
  4. Text in another form in a column of a time is refused when a model reads it, with the text in the sentence.
  5. A model's `Mapped[datetime]` column has the store's type and is TEXT in a strict table. The type check passes with no `ignore` and the lint with no `noqa`.
  6. No existing test changed, and all pass. `python scripts/check.py` reports 19 of 19 gates and 976 tests (backend tests 346); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 47 new tests: 32 unit tests of the form (a UTC time; four other offsets; the length of every text; the order of the texts; a time without an offset and a zone that gives none; a time UTC cannot say; a date, text and a number given as a time; reading; the first and the last time; twelve texts nearly in the form; what is not text; the column type) and 15 integration tests with a model of the tests' own in a real SQLite file (the column's type in the strict table; the stored text read with plain SQL, in five offsets; no time; a refused time and its unit of work; sorting and finding in the database; a question with a time without an offset; SQLite's own date functions; text of another form written with plain SQL). Sixteen planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #79 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 976 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 346: 299 before, 47 new); 49 planted defects in the two modules, 49 of 49 detected, the plan's sixteen prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 44490006014 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 976 passed, 0 failed, 0 skipped.", with 346 backend tests on both machines, the three jobs after the gates skipped; run 44491341132 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 976 / 0 tests (repository 41, script tests 206, backend 346, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 49 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 8 files are identical to the planner's trial. No existing test changed and no package was added. Fifteen of the new tests store times through a model of the tests' own in a real SQLite file, on Linux and on Windows, and read the text the file holds with plain SQL: it is the one form, in UTC, for the same moment given in five offsets. A time without an offset is refused and takes its unit of work with it. SQLite's own date functions read the text as the same moment on both machines, whose SQLite differs. The table itself does not check the form: text of another form written past the models is refused when it is read, which three tests show, and whether the table should refuse it too is settled with DAT-030.
- **Commit:** `ce823a0`
- **Plan:** `docs/plans/DAT-028.md`

### DAT-029 – Every table's key
- **Status:** PASSED – VERIFIED
- **Objective:** Every table has the same key, one whole-number column `id` that a model gets without naming it, and SQLite never gives a key twice; a test holds every table to that.
- **Description:** Added on 2026-11-19 (PLAN-017) as "DAT-029 – Every table's key and timestamps"; the key alone since PLAN-018, with the timestamps as DAT-031. Records will be pointed at by their key: by their history, by where they were collected from, by the review queue. SQLite, left alone, gives the key of a deleted last row to the next new row, and the history of the deleted row would become the history of a row it has nothing to do with. So `Base` gives every model its key, the first column `id`, and asks SQLite for keys that are never given twice (AUTOINCREMENT), in the place where it makes the table strict, so that a model cannot leave it out. SQLAlchemy writes such a key with its column, where it has no name; the `pk` line of the naming rule goes, and nothing is lost by it, since SQLite cannot change a key by name and reports a broken key by table and column. `broken_rules` gets one more rule and one more sentence: a table must have exactly this key (not none, not one of another name, of several columns, not a whole number, not the key of another table, not one that may be given twice). A row may be stored with a key of its own, and later keys come after it, which the rebuild from a snapshot needs. SQLite keeps the last key of each table in `sqlite_sequence`; DAT-019 and DAT-020 keep it across a snapshot. Three tests of DAT-005 change with the rule, for reasons the plan gives one by one. No table, no migration, no new package. The planner's trial has 17 new tests and detects 63 of 63 planted defects.
- **Acceptance criteria:**
  1. A model that names no key has the column `id`, a whole number, as the first column and the key of its table, also when the model says something of its table itself; in the file the key is written `id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT`.
  2. A key is not given again: not the key of a deleted last row, not any key after every row is deleted, not after the store was closed, and not to a row written with plain SQL past the model.
  3. A row stored with a key of its own keeps it, and later keys come after it. Every table counts its own keys.
  4. `broken_rules` names, with one sentence each, a table that has no key, a key of another name, of two columns, of text, one that is the key of another table, or one that may be given twice; it gives an empty list for the real schema and for the models of the tests.
  5. Constraints other than the key, and indexes, are held to the naming rule as before. The type check passes with no `ignore` and the lint with no `noqa`.
  6. `python scripts/check.py` reports 19 of 19 gates and 993 tests (backend tests 363); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 12 new integration tests with two models of the tests' own that name no key, in a real SQLite file (which column is the key; how the file writes it; the next key; a deleted last row; every row deleted; the store closed; a row written with plain SQL; a row with a key of its own; each table's own count); the unit tests of `broken_rules` brought in line with the rule, 14 where there were 9, six of them tables without the key; the 9 integration tests of DAT-005 less two lines that expected the key's name. Fifteen planted defects by the builder and the planner's own, DAT-005's among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #81 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 993 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 363: 346 before, 17 new); 63 planted defects in the module, 63 of 63 detected, the plan's fifteen prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 44495734597 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 993 passed, 0 failed, 0 skipped.", with 363 backend tests on both machines, the three jobs after the gates skipped; run 44497086816 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 993 / 0 tests (repository 41, script tests 206, backend 363, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 63 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 8 files are identical to the planner's trial. No package was added. Three tests of DAT-005 changed with the rule, as the plan says and for the reasons it gives, and 39 of DAT-005's 41 planted defects were planted again and detected (the other two gave the key another name, and the key has no name now). Twelve of the new tests store rows through two models of the tests' own in a real SQLite file, on Linux and on Windows: the key is the first column, the file writes it `id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT`, and a key is not given again after the last row was deleted, after every row was deleted, after the store was closed, or to a row written with plain SQL. `broken_rules` names a table without the key in each of six shapes.
- **Commit:** `6916daa`
- **Plan:** `docs/plans/DAT-029.md`

### DAT-031 – Every table's timestamps
- **Status:** PASSED – VERIFIED
- **Objective:** Every row of every table says when it was first stored and when it was last changed, in two columns a model gets without naming them, and the store's code sets them from one clock that a test can set.
- **Description:** Added on 2026-11-19 (PLAN-018): the second half of what PLAN-017 called "DAT-029 – Every table's key and timestamps"; the timestamps themselves since PLAN-019, with the rule that names a table without them as DAT-032. The store gets one clock, `now()` in `motosphere.db.times`. `Base` gives every model the columns `created_at` and `updated_at`, the last two of its table: times as DAT-028 stores them, required, with no value from the table itself. The store's code sets them when the statement runs that stores or changes a row: a new row gets one reading of the clock in both columns, a changed row gets a new `updated_at` and keeps its `created_at`, and a row whose values are set to what they already are keeps both. A row may be stored with times of its own, which the rebuild from a snapshot (DAT-020) needs. A test sets the clock with the new fixture `clock`, which is the list of the moments the clock said, a second apart. Where it ends is tested and written down: a row written with plain SQL without its times is refused, and a change written with plain SQL or by `INSERT … ON CONFLICT DO UPDATE` leaves `updated_at` as it was; the store's code uses neither. Twelve tests (six functions) of DAT-005, DAT-028 and DAT-029 change, because they write rows with plain SQL or list the columns of a table; the plan gives the reason for each. No table, no migration, no new package. The planner's trial has 20 new tests and detects 135 of 135 planted defects.
- **Acceptance criteria:**
  1. A model that names no time has `created_at` and `updated_at` as the last two columns of its table: TEXT, required, and the table gives them no value of its own.
  2. A new row has the one moment the clock said in both columns, in the store's form, and the clock was asked once; read through the model, both are aware UTC times.
  3. A changed row has a new `updated_at` and its old `created_at`; a row stored again as it was keeps both and the clock is not asked; only the row that changed gets a new time.
  4. Rows stored together in each of three ways get one moment of their own each, in both columns; rows changed in one unit of work each get a moment of their own; rows changed by one statement all get that statement's moment.
  5. A row stored with times of its own keeps them; with only a `created_at` of its own, its `updated_at` is the same.
  6. A row written with plain SQL without its times is refused; a change written with plain SQL, and one by `INSERT … ON CONFLICT DO UPDATE`, leave `updated_at` as it was, and the tests say so.
  7. `now()` says the moment it is, in UTC; with the fixture `clock` it says what the fixture promises, and without it a row gets the moment it is. The type check passes with no `ignore` and the lint with no `noqa`.
  8. `python scripts/check.py` reports 19 of 19 gates and 1013 tests (backend tests 383); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 18 new integration tests with a model of the tests' own that names no time, in a real SQLite file, read with plain SQL (the columns; a new row; a changed row; a row stored again as it was; rows stored together in three ways; rows changed in one unit of work and by one statement; times of a row's own; plain SQL without the times; a change with plain SQL and by `ON CONFLICT DO UPDATE`; the real clock); 2 new unit tests of the clock; the twelve existing tests that change, brought in line. Sixteen planted defects by the builder and the planner's own, all of DAT-028's and DAT-029's among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #83 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1013 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 383: 363 before, 20 new); 135 planted defects in the two modules, 135 of 135 detected, the plan's sixteen prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 44502765544 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1013 passed, 0 failed, 0 skipped.", with 383 backend tests on both machines, the three jobs after the gates skipped; run 44504725449 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1013 / 0 tests (repository 41, script tests 206, backend 383, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 135 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 12 files are identical to the planner's trial. No package was added. Twelve tests of DAT-005, DAT-028 and DAT-029 changed, as the plan says and for the reasons it gives, and all 63 planted defects of DAT-029 and all 49 of DAT-028 were planted again and detected. Eighteen of the new tests store and change rows through a model of the tests' own in a real SQLite file, on Linux and on Windows, with the clock set, and read the two times the file holds with plain SQL: a new row has one reading of the clock in both columns, a changed row a new `updated_at` and its old `created_at`, and a row stored again as it was keeps both. Four of them show where this ends: plain SQL, and `INSERT … ON CONFLICT DO UPDATE`.
- **Commit:** `8db8664`
- **Plan:** `docs/plans/DAT-031.md`

### DAT-032 – A table without its timestamps is named
- **Status:** PASSED – VERIFIED
- **Objective:** `broken_rules` names a table that does not have the two times every table has, and so the test that holds the real schema to the rules fails on such a table.
- **Description:** Added on 2026-11-19 (PLAN-019): the second half of what PLAN-018 called "DAT-031 – Every table's timestamps". A model gets `created_at` and `updated_at` from `Base` (DAT-031), but a model can name them itself, and a table can be made without a model. `broken_rules` gets one more rule and one more sentence, between the key and the names given by hand. A table has the two times if it has both columns and each is a time as the store keeps one, must be there in every row, gets no value from the table itself and gets its value from the store's code by a function that is called when the row is stored; `created_at` must not be set anew when a row changes, and `updated_at` must be, again by a function that is called. Settled in the planner's trial: SQLAlchemy says of a column's default whether it is a function to call, and one fixed value and an SQL expression (`func.now()`) are not, so a time that the statement asks SQLite for is named too; the rule does not see which function is called (that it is the store's clock is what a model gets from `Base` by not naming the columns, and `DATABASE.md` says so), and it does not look at the place of the two columns. The tables that the unit tests of `broken_rules` make by hand get the two times from two new helpers, as they got the key in DAT-029: 12 existing tests (five functions) change for that, and the plan gives the reason for each. `Base` does not change. No table, no migration, no new package. The planner's trial has 19 new tests and detects 159 of 159 planted defects.
- **Acceptance criteria:**
  1. `broken_rules` gives one plain sentence for a table without the two times, in each of 19 ways: neither column; one of the two missing; for each of the two: of another type, one that may be empty, one the table sets itself, one the store's code does not set, one that is one fixed moment, one that SQLite is asked for; a `created_at` that is set anew at a change; an `updated_at` that is not, one that a change sets to one fixed moment, and one that a change asks SQLite for.
  2. A table with the two times that keeps the other rules gives an empty list, and so do the real schema and the models of the integration tests.
  3. A table that breaks all four rules gets its sentences in one order: not strict, the key, the times, the names given by hand.
  4. The type check passes with no `ignore` and the lint with no `noqa`.
  5. `python scripts/check.py` reports 19 of 19 gates and 1032 tests (backend tests 402); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 19 new unit tests (one function, one case for each way of being without the times); the 12 existing unit tests of `broken_rules` that change, brought in line, one of them now pinning the order of all four sentences; the models of the integration tests break no rule, unchanged. Seventeen planted defects by the builder and the planner's own, all of DAT-031's and DAT-028's among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #85 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1032 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 402: 383 before, 19 new); 159 planted defects in the two modules, 159 of 159 detected, the plan's seventeen prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 44511476187 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1032 passed, 0 failed, 0 skipped.", with 402 backend tests on both machines, the three jobs after the gates skipped; run 44514137973 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1032 / 0 tests (repository 41, script tests 206, backend 402, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 159 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 6 files are identical to the planner's trial. No package was added, and `Base` did not change. Twelve unit tests of `broken_rules` (five functions) changed, as the plan says and for the reasons it gives: their tables made by hand got the two times, and one test now expects all four sentences of a table in their order. All 86 planted defects of DAT-031 and all 49 of DAT-028 were planted again and detected. The 19 new tests are one function with one table for each way of being without the two times; the three integration tests that ask `broken_rules` about models of the tests' own pass unchanged, on Linux and on Windows.
- **Commit:** `8c01ce1`
- **Plan:** `docs/plans/DAT-032.md`

### DAT-030 – Text that must not be empty
- **Status:** PASSED – VERIFIED
- **Objective:** A column whose text must not be empty refuses empty text in the store itself, and every model says so in the same way.
- **Description:** Added on 2026-11-19 (PLAN-017): the last quarter of the old "DAT-005 – Model conventions: keys, times and names"; the check itself since PLAN-020, with the rule that names a column without it as DAT-033. One new module, `motosphere.db.texts`. A model says of a column that its text must not be empty with the column's type, `Mapped[NotEmpty]`; to Python it is a `str`, in the table it is TEXT, and `Base` gives the table a check for it when the model is defined, named `ck_<table>_<column>_not_empty` by the naming rule (DAT-005), so that SQLite itself refuses the row, whoever writes it. Settled in the planner's trial: empty is text with no characters and text with nothing but white space, and white space is the 29 characters Python calls so (the ones `str.strip` takes off, the space that cannot be broken among them), written into the check by their numbers in Unicode, so that the check is the same text on every machine; text that is not empty is stored as it was given, with the white space around it, because the store does not tidy text; a column that may be without a value (`Mapped[NotEmpty | None]`) gets the same check and holds no value or text that is not empty; a column of a time gets no check of its form, and no task follows for it, because a check in a table is for what the models cannot promise and through the models a time cannot have another form (DAT-028). Where it ends is tested or written down: a character Python does not call white space is content to the check, also one that cannot be seen; a column that a subclass of a model adds to its parent's table and a table made without a model get no check from `Base`, which is what DAT-033 names. No existing test changes. No table, no migration, no new package. The planner's trial has 32 new tests and detects 35 of 35 planted defects.
- **Acceptance criteria:**
  1. A column a model calls `Mapped[NotEmpty]` is TEXT in a strict table and must be there; one called `Mapped[NotEmpty | None]` may be without a value. The file has one check for each such column, named by the naming rule, with exactly the text the tests expect, and none for any other column.
  2. Text that is not empty is stored as it was given, also with white space around it.
  3. Empty text (no characters, or nothing but white space) is refused by SQLite with the name of the check, and the unit of work it was part of stores nothing; each of the 29 white space characters alone is refused.
  4. A row written with plain SQL and a change to empty text, in three ways, are refused, and the row stays as it was.
  5. A column that may be without a value takes none and refuses empty text; a column whose model says more of it, one named with a word of SQL and one of a model that says something of its table each have their check.
  6. A `Mapped[str]` column takes empty text, as before. `WHITE_SPACE` is exactly the characters Python calls white space.
  7. No existing test changed. The type check passes with no `ignore` and the lint with no `noqa`. `python scripts/check.py` reports 19 of 19 gates and 1064 tests (backend tests 434); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 32 new tests: 6 unit tests (the list of white space against Python's; the text of the check, also for a column named with a word of SQL; its name before and after the naming rule; the type in a table) and 26 integration tests with two models of the tests' own in a real SQLite file (the columns and the checks as the file says them; text that is not empty, in six kinds; empty text, in nine kinds, with its unit of work; each white space character alone and around text; plain SQL; a change in three ways; a column that may be without a value; a check for every such column; a model that says something of its table; text that may be empty). Fifteen planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #87 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1064 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 434: 402 before, 32 new); 35 planted defects in the two modules, 35 of 35 detected, the plan's fifteen prove-it steps among them with the results the plan gives; the 159 planted defects of DAT-032 again, 159 of 159 detected. On GitHub, read by the planner from the runs and job logs: run 44520686616 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1064 passed, 0 failed, 0 skipped.", with 434 backend tests on both machines, the three jobs after the gates skipped; run 44523329480 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1064 / 0 tests (repository 41, script tests 206, backend 434, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 194 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 8 files are identical to the planner's trial. No existing test changed and no package was added. Twenty-six of the new tests make the tables of two models of the tests' own in a real SQLite file, on Linux and on Windows, and ask the file: it has one check for each column whose text must not be empty, named by the naming rule and letter for letter the text the tests expect; it refuses text with no characters and text of nothing but white space, each of the 29 white space characters alone among them, through a model and with plain SQL, on storing and on changing, and names the check; and it stores text that is not empty as it was given. No new file of the task holds a character beyond ASCII.
- **Commit:** `2dba882`
- **Plan:** `docs/plans/DAT-030.md`

### DAT-033 – A column without its check for empty text is named
- **Status:** PASSED – VERIFIED
- **Objective:** `broken_rules` names a column whose text must not be empty and whose table does not have the check for it, and so the test that holds the real schema to the rules fails on such a column.
- **Description:** Added on 2026-11-19 (PLAN-020): the second half of what PLAN-017 called "DAT-030 – Text that must not be empty". `Base` gives the table of a model a check for every column whose text must not be empty (DAT-030), when the model is defined. Two kinds of column get none: one that a subclass of a model adds to its parent's table, and one of a table made without a model. `broken_rules` gets one more rule and one more sentence, between the times and the names given by hand: every column of the type `NotEmptyText` must have the check `not_empty` gives for it. Settled in the planner's trial: the check must be of the name the naming rule gives it (`ck_<table>_<column>_not_empty`) and of the same text as `not_empty` writes, as SQLite is given it when the table is made, so a check of another name does not count and neither does one of that name that says something else (that one looks right by its name and lets empty text in); how the check was written does not matter, so the same check written with the table's own column, or as text, counts; the columns of a table are named in their order in the table. `Base` does not change and gives no check to a subclass's column itself: the column is named, and its table is given the check by hand, `table.append_constraint(not_empty(...))`, which `DATABASE.md` says and a test does with a real SQLite file. One existing unit test gets one more column and one more sentence, to pin where the new sentence stands; with only `base.py` changed, every existing test passed. No table, no migration, no new package. The planner's trial has 10 new tests and detects 220 of 220 planted defects.
- **Acceptance criteria:**
  1. `broken_rules` gives one plain sentence that names the table and the column, for a column whose text must not be empty and whose table is without its check, in each of five ways: no check; the check under another name; a check of the right name that refuses only text with no characters, one that takes off spaces only, and one that is of another column.
  2. The column is named until its table has the check, and no longer once it has, in each of three ways of writing it: as `not_empty` gives it, with the table's own column, and as text.
  3. The columns of a table are named in their order in the table; a column that may be without a value and one that may not are both named, and a column of ordinary text is not.
  4. A table that breaks all five rules gets its sentences in one order: not strict, the key, the times, the column without its check, the names given by hand.
  5. A column that a subclass of a model adds to its parent's table is named; once the table is given the check, nothing is named, the real SQLite file has the check by its name, refuses empty text in the column and takes text that is not empty and no value.
  6. The real schema and the models of the integration tests give an empty list. The type check passes with no `ignore` and the lint with no `noqa`.
  7. `python scripts/check.py` reports 19 of 19 gates and 1074 tests (backend tests 444); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 9 new unit tests in three functions (five ways of being without the check, three ways of writing the check that count, the order of the columns); the existing unit test of the order of the sentences, with one more column and one more sentence; 1 new integration test with two models of its own that share one table, against a real SQLite file; the models of the other integration tests break no rule, unchanged. Fifteen planted defects by the builder and the planner's own, all of DAT-030's and DAT-032's among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #89 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1074 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 444: 434 before, 10 new); 26 planted defects in the new rule, 26 of 26 detected, the plan's fifteen prove-it steps among them with the results the plan gives; the 194 planted defects of DAT-030 again, 194 of 194 detected. On GitHub, read by the planner from the runs and job logs: run 44530337496 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1074 passed, 0 failed, 0 skipped.", with 444 backend tests on both machines, the three jobs after the gates skipped; run 44534139253 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1074 / 0 tests (repository 41, script tests 206, backend 444, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 220 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 7 files are identical to the planner's trial. One existing test got one more column and one more sentence, to pin where the new sentence stands; nothing was taken out of a test, and no package was added. Nine new unit tests ask the rule about tables made by hand, and one new integration test asks it about a column that a subclass of a model adds to its parent's table, gives the table the check, and then asks a real SQLite file, on Linux and on Windows: the file has the check by its name, refuses empty text in the column, and takes text that is not empty and no value.
- **Commit:** `6739c16`
- **Plan:** `docs/plans/DAT-033.md`

### DAT-026 – The models and the migrated schema agree
- **Status:** PASSED – VERIFIED
- **Objective:** A test fails whenever the models describe a schema other than the one the migrations build, and its message says in plain words where the two differ.
- **Description:** One test brings an empty store to the newest schema with `migrate`, makes the tables of the models in a second real file, and asks one new function, `differences` in `motosphere.db.compare`, where the two differ. It runs with every change from then on, so a model cannot change without a migration, nor a migration without its model. Settled in the planner's trial: what is compared are the statements SQLite itself keeps in the file for each table, index, view and trigger (`sqlite_master`), by kind and name, because everything a table is stands in its statement (also that it is strict, that a key is never given twice, a value of its own, the text of a check, what a foreign key does, over which rows an index is), so the comparison forgets nothing and needs no list of the parts of a table; two statements are the same when they are the same words in the same order, where white space, comments, large and small letters and quotes around a name make no difference and text in single quotes is compared letter for letter; what SQLite keeps for itself (every name that begins with `sqlite_`) is left out. The sentences: `Only the models have the table X.`, `Only the migrations have the index Y.`, and for one that both have, `The table X is not the same in both. Where they first differ, the models say ... and the migrations say ....`, with the words of both from where the column or constraint begins that differs to five words after the first that differs. The order of the columns and of the constraints counts, so that a store built in one go and one brought there step by step are the same; it follows, and `DATABASE.md` says so, that a migration writes a table as its model makes it (the statements SQLAlchemy writes for a model, run as text, build the same, and a test does that) and adds a column by building the table anew, because a column SQLite adds in place stands after the two times. Until DAT-006 adds the first table both stores are empty, so that the comparison can fail is proven with two models and migrations of the tests' own. No existing file of code or tests changes. No table, no migration, no new package. The planner's trial has 48 new tests, all against real SQLite files, and detects 77 of 77 planted defects.
- **Acceptance criteria:**
  1. A table, an index, a view or a trigger that only the models or only the migrations have is named, with its kind, in one sentence each; the tables and indexes SQLite keeps for itself are never named.
  2. A table or an index that both have and that differs is named in one sentence, with the words of both from where the column or constraint begins that differs, in each of twenty ways: a column that only one has, of another type, that may be without a value in one only, with a value of its own; a key that may be given twice; two columns the other way round; a constraint that only one has, over the same columns the other way round, of another name; a check that says something else; text in single quotes in other letters and with another space; a foreign key that does more, and one that only the models have; a table that is not strict; an index that lets no two rows be alike, over the same columns the other way round, and over some rows only.
  3. How a statement is written makes no difference, in eight ways, and a table that was given its name later is the same table; a quote written twice inside quotes does not end them.
  4. A migration written by hand builds what the models say, and so do the statements SQLAlchemy writes for the models, run as text. A column added to a table in place is named as a difference.
  5. The sentences come kind by kind and name by name, and comparing leaves both files byte for byte as they were.
  6. The real models and the real migrations agree. The type check passes with no `ignore` and the lint with no `noqa`.
  7. `python scripts/check.py` reports 19 of 19 gates and 1122 tests (backend tests 492); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 48 new integration tests in 12 functions, every one with two real SQLite files: the real models against the real migrations; a migration written by hand and one written by SQLAlchemy that build what two models of the tests' own say; eight ways of writing a statement that make no difference; nine things only one of the two has; twenty single changes to a table or an index, each with its sentence written out; a column added in place; the order of the sentences; and that nothing is written. Eighteen planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #91 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1122 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 492: 444 before, 48 new); 77 planted defects in the new module, 77 of 77 detected, the plan's eighteen prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 44541345042 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1122 passed, 0 failed, 0 skipped.", with 492 backend tests on both machines, the three jobs after the gates skipped; run 44544063577 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1122 / 0 tests (repository 41, script tests 206, backend 492, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 77 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 6 files are identical to the planner's trial. No existing file of code or tests changed, and no package was added. Every one of the 48 new tests compares two real SQLite files, on Linux and on Windows: one whose tables SQLAlchemy made from the models and one that `migrate` built. The real models and the real migrations agree, both being empty; that the comparison can fail is proven with two models and migrations of the tests' own.
- **Commit:** `3ea9b4f`
- **Plan:** `docs/plans/DAT-026.md`

### DAT-034 – A column type brings its check
- **Status:** PASSED – VERIFIED
- **Objective:** Any column type can bring the check for its column: `Base` gives that check to the table and `broken_rules` names a column whose table is without it, for every such type, so that a new type of this kind needs no change to either.
- **Description:** Added on 2026-11-19 (PLAN-021), before the first table. Today `Base` and `broken_rules` know one type by its name, `NotEmptyText` (DAT-030, DAT-033); the first table needs three more kinds of column that are kept by a check (DAT-035 to DAT-037). One new module, `motosphere.db.checks`, with one class: a column type that brings a check is a subclass of `WithItsCheck`, beside its SQLAlchemy type, and says `check_for(name)`, the check for the column of that name, and two words for the sentence of `broken_rules`, `refuses` and `given_by`. `NotEmptyText` becomes such a type and gives the check of `not_empty`, which stays as it is. `Base` gives `column.type.check_for(column.name)` to the table of a model for every column whose type is a `WithItsCheck`, and `broken_rules` asks for the same and writes its sentence with the type's two words. Settled in the planner's trial: no existing test changes, and with only the code changed all 492 backend tests passed, which is the proof that the change keeps what was there; for text that must not be empty the sentence is letter for letter what it was; a type that says it brings a check and gives none is an error (`NotImplementedError`), when a model with a column of it is defined and when `broken_rules` is asked; the new rule is proven with a column type of the tests' own (text in large letters only), with tables made by hand and with a model in a real SQLite file. No table, no migration, no new package. The planner's trial has 12 new tests and detects 243 of 243 planted defects.
- **Acceptance criteria:**
  1. `Base` gives the table of a model the check of every column whose type is a `WithItsCheck`, whatever the type: the real SQLite file has the checks by name, in the order of the columns, and refuses what the type's check refuses, in a column that must have a value and in one that may be without.
  2. `broken_rules` names a column of any such type whose table is without the check the type gives, with that type's two words, until the table has the check.
  3. The check of one type does not count for a column of another, in four ways, and columns of several types in one table are named in their order, each in its own type's words.
  4. A type that says it brings a check and gives none is an error, for `broken_rules` and when a model with a column of it is defined.
  5. `NotEmptyText` brings exactly the check `not_empty` gives, and its `given_by` is the name of that function.
  6. No existing test changed, and all of them pass. The type check passes with no `ignore` and the lint with no `noqa`.
  7. `python scripts/check.py` reports 19 of 19 gates and 1134 tests (backend tests 504); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 7 new unit tests of `broken_rules` in four functions, with two column types of the tests' own; 1 new unit test of `NotEmptyText`; 4 new integration tests in three functions, with a model that has columns of two such types, against a real SQLite file; every existing test, unchanged. Twelve planted defects by the builder and the planner's own, all of DAT-033's among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #93 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1134 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 504: 492 before, 12 new); 23 planted defects in the new rule, 23 of 23 detected, the plan's twelve prove-it steps among them with the results the plan gives; and the 220 planted defects of DAT-033 again, brought in line with the new code where they touch the changed lines, 220 of 220 detected. On GitHub, read by the planner from the runs and job logs: run 44551068881 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1134 passed, 0 failed, 0 skipped.", with 504 backend tests on both machines, the three jobs after the gates skipped; run 44554986625 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1134 / 0 tests (repository 41, script tests 206, backend 504, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 243 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 10 files are identical to the planner's trial. No existing test changed, and no package was added. For text that must not be empty nothing that can be observed is different: all 492 earlier backend tests pass as they were. The new rule is proven with a column type of the tests' own: in the unit tests with tables made by hand, and in 4 integration tests with a model and a real SQLite file, on Linux and on Windows.
- **Commit:** `590986c`
- **Plan:** `docs/plans/DAT-034.md`

### DAT-035 – A column that is yes or no
- **Status:** PASSED – VERIFIED
- **Objective:** A model can say that a column is yes or no, and the store refuses anything else in it.
- **Description:** Added on 2026-11-19 (PLAN-021). A strict table has no type for yes and no, and SQLite refuses to make one with SQLAlchemy's own (`DATABASE.md`), so a model that says `Mapped[bool]` gets a table that cannot be made. One new module, `motosphere.db.yes_no`, with the column type `YesOrNo`, the second type that brings its check (DAT-034): INTEGER in the table, with the check `<column> IN (0, 1)`, named `ck_<table>_<column>_yes_or_no`; 1 is yes and 0 is no. The first table needs it for "is this source switched on" (DAT-006). Settled in the planner's trial: a model says the plain Python type, `Mapped[bool]`, and `Base` gets one entry in the list by which a Python type becomes a column type, so no model can get SQLAlchemy's own type by leaving a word out; the rule by which `Base` gives checks, and `broken_rules`, do not change. Only `True` and `False` are stored: a number and a word are refused before anything is written, with a `TypeError` that says what was given, because Python takes much for true that is not, the word "no" among it; a question is held to the same. Only the whole numbers 1 and 0 are read: anything else that comes back through the type is refused, which happens for a sum over such a column, never for a row. A column that may be without a value holds none, yes or no, and none means "not known". What SQLite takes for one of the two numbers (the text '1', the number 1.0) a strict table stores as that whole number, so the file never holds anything else. No existing test changes, no table, no migration, no new package. The planner's trial has 47 new tests and detects 290 of 290 planted defects.
- **Acceptance criteria:**
  1. A model that says `Mapped[bool]` of a column gets a whole-number column with the check `<column> IN (0, 1)`, named by the naming rule: the real SQLite file has the checks by name and letter for letter, for each such column and for no other.
  2. Yes and no are stored as the whole numbers 1 and 0 and come back as `True` and `False`; a column that may be without a value holds none, yes or no; a value of the model's own is stored as its number; a change is stored.
  3. What is neither `True` nor `False` is refused before anything is written, with a sentence that says what it was given, in five kinds, in a row and in a question.
  4. Another number is refused by SQLite with the name of the check: in a row written with plain SQL, in five ways, and in a change. What SQLite takes for one of the two numbers is stored as that number, and what cannot be a whole number is refused by the strict table.
  5. What is read through the type and is not the whole number 1 or 0 is refused, in five kinds, and a sum over such a column is read as yes or no, or refused.
  6. `broken_rules` names such a column whose table is without the check, in the type's words, until the table has it; the rule by which `Base` gives checks, and `broken_rules`, are unchanged.
  7. No existing test changed, and all of them pass. The type check passes with no `ignore` and the lint with no `noqa`.
  8. `python scripts/check.py` reports 19 of 19 gates and 1181 tests (backend tests 551); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 20 new unit tests in twelve functions, of the two functions that say and read the number, of the type and of its check; 27 new integration tests in fifteen functions, with a model that has three such columns, against a real SQLite file that is read with plain SQL, past the model; every existing test, unchanged. Twelve planted defects by the builder and the planner's own, all of DAT-034's among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #95 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1181 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 551: 504 before, 47 new); 47 planted defects in the new module and the new line of `base.py`, 47 of 47 detected, the plan's twelve prove-it steps among them with the results the plan gives; and the 243 planted defects of DAT-034 again, 243 of 243 detected. On GitHub, read by the planner from the runs and job logs: run 44563274824 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1181 passed, 0 failed, 0 skipped.", with 551 backend tests on both machines, the three jobs after the gates skipped; run 44567782784 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1181 / 0 tests (repository 41, script tests 206, backend 551, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 290 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 8 files are identical to the planner's trial. No existing test changed, and no package was added. The 27 integration tests make the table of a model in a real SQLite file and read with plain SQL, past the model, what the file holds and of which kind it is, on Linux and on Windows: yes and no are the whole numbers 1 and 0, and SQLite itself refuses any other number.
- **Commit:** `0277051`
- **Plan:** `docs/plans/DAT-035.md`

### DAT-036 – A column whose value is one of a list
- **Status:** PASSED – VERIFIED
- **Objective:** A model can say that a column's value is one of a fixed list, and the store refuses any other.
- **Description:** Added on 2026-11-19 (PLAN-021). The first table has two columns that are each one of a short list the code knows, the category of a source and the way it is collected (DESIGN §7.1, §7.2), and the tables after it have more; as plain text, a misspelled word would be stored like any other. One new module, `motosphere.db.lists`, with the column type `OneOf`, the third type that brings its check (DAT-034): TEXT in the table, with a check that names the texts of the list in their order, `<column> IN ('sand', 'hard pack')`, named `ck_<table>_<column>_one_of`. A list is a `StrEnum`, said once, in the code, and its values are the texts that are stored. Settled in the planner's trial: a model names the type and the list, `mapped_column(OneOf(Surface))`, because there is one type for each list and SQLAlchemy makes the plain `Mapped[Surface]` enough only through a method it keeps to itself; a model that forgets gets a table SQLite refuses to make, so the slip cannot go unnoticed. Only a value of the column's own list is stored: text, also text spelled like a value, and a value of another list are refused before anything is written, with a `TypeError` that says what was given. What is read comes back as the value of the list, and text that is not on the list is refused when it is read. What is not a list is refused when the type is made: anything that is not a `StrEnum`, a list with nothing on it and a list with an empty value. A change to a list is a change to the schema, which the test that holds the models and the migrations together (DAT-026) will notice. No existing file of code or tests changes, no table, no migration, no new package. The planner's trial has 58 new tests and detects 50 of 50 planted defects, after one gap they found was closed.
- **Acceptance criteria:**
  1. A model that says `mapped_column(OneOf(TheList))` of a column gets a text column with a check that names the list's texts in their order, named by the naming rule: the real SQLite file has the checks by name and letter for letter, each with the texts of its own column's list.
  2. Every value of a list is stored as its text and comes back as the value itself, whatever characters the text has; a column that may be without a value holds none or a value of its list; a change is stored.
  3. Two columns each keep their own list, also where the two lists have a text in common, and two statements that differ in the list only each keep their own.
  4. What is not a value of the column's list is refused before anything is written, with a sentence that says what it was given, in four kinds, in a row and in a question.
  5. Text that is not on the list is refused by SQLite with the name of the check: in a row written with plain SQL, in seven kinds, and in a change. Text that is read and is not on the list is refused, in six kinds, and so is the row of a value the list no longer has.
  6. What is not a list is refused when the type is made: five kinds of thing that are not a `StrEnum`, a list with nothing on it, and a list with an empty value in four kinds.
  7. `broken_rules` names such a column whose table is without the check, in the type's words, until the table has the check for that list; the check for another list does not count. A model that names its list and not the type gets a table SQLite refuses to make.
  8. No existing file of code or tests changed. The type check passes with no `ignore` and the lint with no `noqa`.
  9. `python scripts/check.py` reports 19 of 19 gates and 1239 tests (backend tests 609); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 32 new unit tests in seventeen functions, of the type, of what it stores and reads, of what it refuses to be made with, and of its check; 26 new integration tests in seventeen functions, with a model that has three such columns, against a real SQLite file that is read with plain SQL, past the model; every existing test, unchanged. Thirteen planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #97 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1239 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 609: 551 before, 58 new); 50 planted defects in the new module, 50 of 50 detected, the plan's thirteen prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 44574108174 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1239 passed, 0 failed, 0 skipped.", with 609 backend tests on both machines, the three jobs after the gates skipped; run 44575972489 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1239 / 0 tests (repository 41, script tests 206, backend 609, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 50 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 7 files are identical to the planner's trial. No existing file of code or tests changed, and no package was added. The 26 integration tests make the table of a model in a real SQLite file and read with plain SQL, past the model, what the file holds and of which kind it is, on Linux and on Windows: a value of a list is its text, and SQLite itself refuses any text that is not on the column's own list.
- **Commit:** `d2b1d54`
- **Plan:** `docs/plans/DAT-036.md`

### DAT-037 – A column that is a web address
- **Status:** PASSED – VERIFIED
- **Objective:** A model can say that a column holds a web address, and the store refuses text that is not one.
- **Description:** Added on 2026-11-19 (PLAN-021). A source has a website (DAT-006), every collected record says at which address it was found (DAT-008), and a page makes a link of such an address. One new module, `motosphere.db.web`, with the column type `WebAddressText`, the fourth type that brings its check (DAT-034) and built like text that must not be empty: TEXT in the table, with a check named `ck_<table>_<column>_web_address`. A model says the column's Python type, `Mapped[WebAddress]`, and `Base` gets one entry in the list by which a Python type becomes a column type; the rule by which `Base` gives checks, and `broken_rules`, do not change. Settled in the planner's trial, exactly what the check refuses: text that does not begin with `https://` or `http://`, in small or in large letters; text that does not go on with the name of a site, with at least one character that is not `/`, `?` or `#`; text with white space anywhere, by the store's own list of white space; and text with a character that has the number 0, behind which SQLite's `GLOB` does not look, which the trial found. The check is written with `GLOB`, which tells small letters from large ones on every machine, and not with `LIKE`, whose way with them can be changed for a connection. An address is stored as it was given: the store does not tidy it and does not ask the network whether it leads anywhere, so `https://.` passes, and two spellings of one address are two addresses; `DATABASE.md` says where the check ends and tests hold it there. Nothing is checked in Python: there is one rule, in the table. No existing test changes, no table, no migration, no new package. The planner's trial has 70 new tests and detects 343 of 343 planted defects.
- **Acceptance criteria:**
  1. A model that says `Mapped[WebAddress]` of a column gets a text column with the check, named by the naming rule: the real SQLite file has the checks by name and letter for letter, for each such column and for no other.
  2. A web address is stored and read back as it was given, in thirteen kinds: with `https` and with `http`, in small and in large letters, with a port, a path, a question and a place on the page, and with characters that `GLOB` and SQL have a use for.
  3. Text that is not a web address is refused by SQLite with the name of the check, and nothing is stored with it, in 35 kinds: no scheme, another scheme, a scheme and nothing after it, a name that does not begin, white space before, after and in it, and a character with the number 0. Each of the 29 white space characters is refused in three places of an address.
  4. Text that is not a web address is refused in a row written with plain SQL, in four kinds, and in a change, in three ways, and the row stays as it was. A change to another address is stored.
  5. A column that may be without a value holds none or a web address; a column of which the model says more has its check and what the model said; a text column of any kind is as before.
  6. `broken_rules` names such a column whose table is without the check, in the type's words, until the table has it; the rule by which `Base` gives checks, and `broken_rules`, are unchanged.
  7. Where the check ends is held by tests: four addresses that lead nowhere are stored, and two spellings of one address are two addresses.
  8. No existing test changed, and all of them pass. The type check passes with no `ignore` and the lint with no `noqa`.
  9. `python scripts/check.py` reports 19 of 19 gates and 1309 tests (backend tests 679); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 8 new unit tests, of the check as SQLite is given it, of its name, of the type and of the entry in the list of `Base`; 62 new integration tests in thirteen functions, with a model that has three such columns, against a real SQLite file that is read with plain SQL, past the model; every existing test, unchanged. Thirteen planted defects by the builder and the planner's own, all of DAT-034's and DAT-035's among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #99 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1309 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 679: 609 before, 70 new); 53 planted defects in the new module and the new line of `base.py`, 53 of 53 detected, the plan's thirteen prove-it steps among them with the results the plan gives; and the 243 planted defects of DAT-034 and the 47 of DAT-035 again, 290 of 290 detected. On GitHub, read by the planner from the runs and job logs: run 44583394967 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1309 passed, 0 failed, 0 skipped.", with 679 backend tests on both machines, the three jobs after the gates skipped; run 44587743156 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1309 / 0 tests (repository 41, script tests 206, backend 679, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 343 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 8 files are identical to the planner's trial. No existing test changed, and no package was added. The 62 integration tests make the table of a model in a real SQLite file and read with plain SQL, past the model, what the file holds, on Linux and on Windows: a web address is stored as it was given, and SQLite itself refuses text that does not begin as one or has white space in it.
- **Commit:** `a029d83`
- **Plan:** `docs/plans/DAT-037.md`

### DAT-038 – No two constraints of one name in a table
- **Status:** PASSED – VERIFIED
- **Objective:** The test that holds every table to the rules names a table that has two constraints of the same name.
- **Description:** Added on 2026-11-19 (PLAN-022), found while DAT-037 was trialled. SQLite takes a table with two checks of one name and keeps both, and when it refuses a row it says the one name, which does not tell which of the two refused it. And `broken_rules` looked for the check of a column by its name: with two checks of that name it went by the one it came to last, and the order in which it comes to them is not fixed, as SQLAlchemy keeps the constraints of a table as a set. One more rule in `broken_rules`, the last it says of each table: a name that more than one constraint or index of the table has is named once, with how many have it, and several such names come by the alphabet. Settled in the planner's trial: every constraint but the key and every index is counted, in one count, which is the list the rule of the names given by hand already goes by; indexes are counted although SQLite itself refuses two of one name, so that the test of the models says it in plain words before anything is made; a name given by hand to two constraints is named for both reasons; the same name in two tables is not a name given twice, as the count is made table by table; and for a column with two checks of the name of its own check, the column has its check if either of the two is that check, whatever their order. One code file changes, `base.py`; tests are added to the two files that test it and no existing test changes. No new module, no table, no migration, no new package. The planner's trial has 16 new tests and detects 372 of 372 planted defects.
- **Acceptance criteria:**
  1. `broken_rules` names a name that more than one constraint or index of a table has, once, in a plain sentence that names the table and the name and says how many have it: for two checks, three checks, a column that is unique and said so twice, an index said twice and a foreign key said twice.
  2. Several such names of one table are listed by the alphabet, after everything else the rule says of the table, whatever the order of the table's constraints; a name given by hand to two constraints is named for both reasons.
  3. One name in two tables is not named as given twice.
  4. For a column with two checks of the name of its own check, `broken_rules` says the same in both orders of the two: the column has its check if one of them is that check, and is named as without it if neither is.
  5. A real SQLite file takes a table with two checks of one name, keeps both, and refuses a row by either with the same words; it refuses a second index of one name; and `broken_rules` names both models.
  6. A schema that keeps the rules gives an empty list as before: no existing test changed, and all of them pass. The type check passes with no `ignore` and the lint with no `noqa`.
  7. `python scripts/check.py` reports 19 of 19 gates and 1325 tests (backend tests 695); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 11 new unit tests in four functions, with tables made by hand, whose constraints are given in an order the test decides; 5 new integration tests in three functions, with two models that break the rule, against a real SQLite file; every existing test, unchanged. Twelve planted defects by the builder and the planner's own, all of DAT-034's, DAT-035's and DAT-037's among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #101 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1325 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 695: 679 before, 16 new); 29 planted defects in the new rule and in `_without_their_check`, 29 of 29 detected, the plan's twelve prove-it steps among them with the results the plan gives; and the 343 planted defects of DAT-034, DAT-035 and DAT-037 again, 343 of 343 detected, every one with the result of the planner's trial. On GitHub, read by the planner from the runs and job logs: run 44595561773 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1325 passed, 0 failed, 0 skipped.", with 695 backend tests on both machines, the three jobs after the gates skipped; run 44599851033 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1325 / 0 tests (repository 41, script tests 206, backend 695, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 372 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 7 files are identical to the planner's trial. No existing test changed, and no package was added. The 5 integration tests make the tables of two models that break the rule in a real SQLite file, on Linux and on Windows: SQLite takes a table with two checks of one name and refuses a row by either with the same words, it refuses a second index of one name, and `broken_rules` names both models.
- **Commit:** `e8e165c`
- **Plan:** `docs/plans/DAT-038.md`

### DAT-039 – The lists a source is described by
- **Status:** PASSED – VERIFIED
- **Objective:** The code knows the twelve kinds of source and the ten ways of collecting from one, each with the text that is stored.
- **Description:** Added on 2026-11-19 (PLAN-023), cut out of DAT-006. One new package for the models of the store, `motosphere.db.models`, which has no model yet, and in it one new module, `motosphere.db.models.source`, with two lists, each a `StrEnum` as a column of a list takes one (DAT-036): `SourceCategory`, the twelve kinds of source of DESIGN §7.1, and `CollectionMethod`, the ten ways of collecting of DESIGN §7.2, both in the design's order. Settled in the planner's trial: the texts, which are words in small letters with one space between two, short and in the singular (`governing body`, `results database`, `html extraction`, `human submission`); and that the conditions of the design ("permitted", "where authorised") are not in the texts, because a text in a row cannot say that somebody checked: the condition is checked when a source is registered and written down with it, as `DATABASE.md` and `DATA_SOURCES.md` now say. Whether a source has one kind and one way is not settled here: the table decides (DAT-006). No table, no model, no migration, no existing test changed. The planner's trial has 29 new tests and detects 18 of 18 planted defects.
- **Acceptance criteria:**
  1. `SourceCategory` has exactly its twelve texts and `CollectionMethod` its ten, each in the order of the design, and no text has two names.
  2. Every text is words in small letters with one space between two.
  3. A column can be of either list: `OneOf` takes it, and the check it gives names the texts of the list in their order.
  4. `DATABASE.md` says what each text means and which words of the design it stands for, and `DATA_SOURCES.md` says which ways of collecting are permitted only on a condition.
  5. No existing test changed, and all of them pass. The type check passes with no `ignore` and the lint with no `noqa`.
  6. `python scripts/check.py` reports 19 of 19 gates and 1354 tests (backend tests 724); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 29 new unit tests in five functions, with the texts of both lists written out a second time; every existing test, unchanged. Ten planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #103 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1354 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 724: 695 before, 29 new); 18 planted defects in the two lists, 18 of 18 detected, the plan's ten prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 44604869576 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1354 passed, 0 failed, 0 skipped.", with 724 backend tests on both machines, the three jobs after the gates skipped; run 44606475596 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1354 / 0 tests (repository 41, script tests 206, backend 724, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 18 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-19. All 8 files are identical to the planner's trial. No existing test changed, and no package was added. The task has no table: the lists are plain code, and what SQLite does with a column of a list is proven for every list by the tests of DAT-036 and comes for these two with the table (DAT-006).
- **Commit:** `5f9a303`
- **Plan:** `docs/plans/DAT-039.md`

### DAT-006 – Information sources table
- **Status:** PASSED – VERIFIED
- **Objective:** The store knows every source of information: who it is, how it is collected from and how it may be used (DESIGN §7.3).
- **Description:** Narrowed on 2026-11-19 (PLAN-023). The table `source`, its model `Source` in `motosphere.db.models.source`, and the first migration, `make_the_sources`. Settled in the planner's trial. The columns: `name` (not empty, unique), `website` (a web address), `category` and `collection_method` (the lists of DAT-039), `scan_every_hours` (whole hours above nought, or no value for a source that is not scanned by the clock, as a file loaded once by a command is not), `terms_address`, `licence`, `usage_restrictions`, `terms_read_at` and `switched_on`. A new source is switched off, and one check, `ck_source_switched_on_terms_read`, refuses a source that is switched on and does not say when its terms were read (CLAUDE.md §10). Two sources may share a website, which PLAN-023 had left open: a site collected from in two ways is two sources of two names, each with runs of its own; only the name is unique, and names are told apart letter for letter. The migrations are written in one new module, `motosphere.db.history`, as plain SQL that names nothing of the store's code, which a test holds the module to; `motosphere.db.migrations` takes `MIGRATIONS` from there. `motosphere.db.models` names every model and gives the whole schema a name, `SCHEMA`; the two tests that hold the whole schema take it from there, and a new test asks a new Python three times and proves that no model anywhere in the code is missing from it. One new fixture, `newest`: the test's own store, brought to the newest schema by `migrate`. Not in this task: the source's country (DAT-011), the kinds of information it offers (DAT-040), and how it is doing (DAT-007, DAT-041). The planner's trial has 74 new tests and detects 51 of 51 planted defects, and 184 of 184 of the earlier ones whose files or tests this task changes.
- **Acceptance criteria:**
  1. A source is stored and read back with everything said of it, and in the table it is plain text and whole numbers.
  2. A source cannot be without its name, its website, its kind or its way of collecting; two sources cannot have one name, and can have one website.
  3. The table refuses a kind or a way of collecting that is not on its list, a website or an address of the terms that is not a web address, empty text for the name, the licence and the restrictions, and a scanning interval that is not a whole number of hours above nought.
  4. A new source is switched off. A source whose terms were not read is refused switched on, when it is stored and later; one that is switched on cannot lose the time its terms were read.
  5. The first migration makes the table in a new store and brings it to version 1, and the test of the models and the migrations finds the two the same.
  6. `SCHEMA` is whole: a model the package does not name, and a model outside the package, each fail a test.
  7. The history names nothing of MotoSphere's own code, and a test names its migrations in their order.
  8. No existing test changed but two, in one line each, and all pass. The type check passes with no `ignore`.
  9. `python scripts/check.py` reports 19 of 19 gates and 1428 tests (backend tests 798); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 74 new integration tests against real SQLite files, in three files: 66 of the table in a store the migrations built, 6 of the history and 2 of the whole schema, asked of a new Python; every existing test. Fourteen planted defects by the builder and the planner's own; the earlier planted defects of the runner, of the fixture of the store, of the comparison and of the two lists again; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #105 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1428 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 798: 724 before, 74 new); 51 planted defects in the model, the migration, the history, the package of the models and the runner, 51 of 51 detected, the plan's fourteen prove-it steps among them with the results the plan gives; the earlier planted defects of the runner (74), of the fixture of the store (15), of the comparison (77) and of the two lists (18) again, 184 of 184 detected; the real commands `migrate` and `schema` on a new store, which is then at version 1 and holds the table `source`. On GitHub, read by the planner from the runs and job logs: run 45278804214 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1428 passed, 0 failed, 0 skipped.", with 798 backend tests on both machines, the three jobs after the gates skipped; run 45281309608 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1428 / 0 tests (repository 41, script tests 206, backend 798, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 235 / 0 planted defects detected (51 new, 184 earlier); the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-23. All 16 files are identical to the planner's trial. Every new test runs against a real SQLite file that the migrations built; nothing is a mock. Two existing tests changed in one line each (they take the whole schema from `SCHEMA`); no package was added.
- **Commit:** `2d3a620`
- **Plan:** `docs/plans/DAT-006.md`

### DAT-040 – The kinds of information a source offers
- **Status:** PASSED – VERIFIED
- **Objective:** The store knows which kinds of information each source offers (DESIGN §7.3, "Available information types").
- **Description:** Added on 2026-11-19 (PLAN-023), cut out of DAT-006. One list, `InformationType`, in `motosphere.db.models.source`, and one table, `source_offer`, with its model `SourceOffer` and the second migration, `make_the_source_offers`: one row for one kind of information that one source offers, with the columns `source_id` and `information_type`. Settled in the planner's trial. The kinds, which the design does not list: nine, from what the design says MotoSphere is a place to explore (DESIGN §1), as words in small letters in the plural: `tracks`, `events`, `championships`, `results`, `standings`, `riders`, `teams`, `news` and `reference data`; the ninth is there because the first source the plan registers, the reference file of the countries (DAT-012), offers none of the other eight. A source offers a kind once (a unique constraint over the two columns, the source first), and two sources can offer the same kind. An offer belongs to a source that exists (a foreign key). A source that has offers cannot be deleted: the foreign key does nothing by itself, so SQLite refuses the delete, and whoever deletes a source takes its offers away first; taking them away in silence with the source was not taken. A source may be without offers. The model of an offer has the key of its source and no `relationship`. The tests of the list go into the file of the two other lists. The planner's trial has 40 new tests and detects 34 of 34 planted defects, and 69 of 69 of the earlier ones whose files or tests this task changes.
- **Acceptance criteria:**
  1. `InformationType` has exactly its nine texts in their order, no text has two names, and every text is words in small letters with one space between two.
  2. A source can offer several kinds of information, and each of the nine; it does not offer one kind twice; two sources can offer the same kind.
  3. The table refuses a kind that is not on the list, an offer without a source or without a kind, and an offer for a source that does not exist, when it is stored and when it is moved.
  4. A source that has offers cannot be deleted; once its offers were taken away it can, and the offers of another source stay.
  5. The second migration makes the table in a store at version 1 and leaves its sources as they were, and the test of the models and the migrations finds the two the same.
  6. The first migration is unchanged, and the history names its two migrations in their order.
  7. No existing test changed but the test of the history's names and the tests of the lists, which take the third list in; all pass. The type check passes with no `ignore`.
  8. `python scripts/check.py` reports 19 of 19 gates and 1468 tests (backend tests 838); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 40 new tests: 25 integration tests of the table in a store the migrations built, 2 of the history (the second migration given to a store at version 1 that has a source), and 13 unit tests of the list; every existing test. Thirteen planted defects by the builder and the planner's own; the earlier planted defects of the table of the sources and of the two lists again; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #107 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1468 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 838: 798 before, 40 new); 34 planted defects in the list, the model and the migration, 34 of 34 detected, the plan's thirteen prove-it steps among them with the results the plan gives; the earlier planted defects of the table of the sources (51) and of the two lists (18) again, 69 of 69 detected; the real commands `migrate` and `schema` on a new store, which is then at version 2 and holds the tables `source` and `source_offer`. On GitHub, read by the planner from the runs and job logs: run 45285106731 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1468 passed, 0 failed, 0 skipped.", with 838 backend tests on both machines, the three jobs after the gates skipped; run 45287559418 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1468 / 0 tests (repository 41, script tests 206, backend 838, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 103 / 0 planted defects detected (34 new, 69 earlier); the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-23. All 12 files are identical to the planner's trial. The 27 new integration tests run against real SQLite files that the migrations built; nothing is a mock. The first migration is unchanged. No package was added.
- **Commit:** `04571b0`
- **Plan:** `docs/plans/DAT-040.md`

### DAT-007 – Data collection runs table
- **Status:** PASSED – VERIFIED
- **Objective:** Every collection run is recorded: which source, when, how it ended and what it changed.
- **Description:** One list, `RunOutcome` (`running`, `succeeded`, `failed`, `interrupted`), and one table, `collection_run`, with its model `CollectionRun` in a new module, `motosphere.db.models.collection_run`, and the third migration, `make_the_collection_runs`: the source (`source_id`), `started_at`, `ended_at`, `outcome`, the counts `records_seen`, `records_added`, `records_changed` and `records_unchanged`, and `error`, the error in plain words when the run failed. One function, `mark_interrupted(work)` in the new module `motosphere.db.runs`, marks every run that a job that died left `running` as interrupted, so that recovery after an interrupted job (CLAUDE.md §13) has a record to work from. Settled in the planner's trial. A run is stored when it starts: a new run is running and has counted nothing, and whoever starts it says when. An interrupted run has no end, because nobody knows when its job died and the store holds no time that somebody made up; `updated_at` says when it was marked. The end goes with the outcome (a run that succeeded or failed says when it ended, and no other run does) and so does the error (a run that failed says what went wrong, and no other run has an error), each by one check. A run cannot end before it started; it can end at that moment. Each count has a check of its own; the table does not ask that added, changed and unchanged add up to seen, because a record that was refused was seen and is none of the three. A source that has runs cannot be deleted, as with its offers: the foreign key does nothing by itself. There is no index beside the key's and no rule against two running runs of one source: DAT-041 and the first task that starts runs have the questions those must answer. `mark_interrupted` is one statement in the caller's unit of work, gives the keys of the runs it marked, smallest first, and changes only their outcome and `updated_at`; nothing calls it yet. The planner's trial has 65 new tests and detects 76 of 76 planted defects, and 85 of 85 of the earlier ones whose files this task changes.
- **Acceptance criteria:**
  1. `RunOutcome` has exactly its four texts in their order, and no text has two names.
  2. A new run is running, has counted nothing and has neither end nor error; a run that ends says when, how and what it changed.
  3. A run belongs to exactly one source that exists, when it is stored and when it is moved; a source that has runs cannot be deleted, and once its runs were taken away it can.
  4. A run cannot end before it started. A run that succeeded or failed says when it ended, and no other run does. A run that failed says what went wrong, in text that is not empty, and no other run has an error.
  5. No count can be below 0, be without a value or be a number that is not whole. The table refuses an outcome that is not on the list.
  6. `mark_interrupted` marks every run that is still running as interrupted and gives their keys in order; of those runs only the outcome and `updated_at` change; no other run and no other table is touched; the marking is kept or taken back with its unit of work.
  7. The third migration makes the table in a store at version 2 and leaves its sources and offers as they were, and the test of the models and the migrations finds the two the same. The first two migrations are unchanged, and the history names its three migrations in their order.
  8. No existing test changed but the test of the history's names; all pass. The type check passes with no `ignore`.
  9. `python scripts/check.py` reports 19 of 19 gates and 1533 tests (backend tests 903); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 65 new tests: 47 integration tests of the table and 9 of `mark_interrupted`, in a store the migrations built, 2 of the history (the third migration given to a store at version 2 that has a source and an offer), and 7 unit tests of the list; every existing test. Sixteen planted defects by the builder and the planner's own; the earlier planted defects of the tables of the sources and of the offers again; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #109 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1533 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 903: 838 before, 65 new); 76 planted defects in the list, the model, the migration and the function, 76 of 76 detected, the plan's sixteen prove-it steps among them with the results the plan gives; the earlier planted defects of the table of the sources (51) and of the table of the offers (34) again, 85 of 85 detected; the real commands `migrate` and `schema` on a new store, which is then at version 3 and holds the tables `collection_run`, `source` and `source_offer`. On GitHub, read by the planner from the runs and job logs: run 45294634124 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1533 passed, 0 failed, 0 skipped.", with 903 backend tests on both machines, the three jobs after the gates skipped; run 45298847089 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1533 / 0 tests (repository 41, script tests 206, backend 903, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 161 / 0 planted defects detected (76 new, 85 earlier); the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-24. All 13 files are identical to the planner's trial. The 58 new integration tests run against real SQLite files, 56 of them in a store that the migrations built; nothing is a mock. The first two migrations are unchanged. No package was added.
- **Commit:** `dc53ad1`
- **Plan:** `docs/plans/DAT-007.md`

### DAT-041 – How a source is doing, told by its runs
- **Status:** PASSED – VERIFIED
- **Objective:** The store says how each source is doing: its last attempted and last successful scan, its last error and its health (DESIGN §7.3).
- **Description:** Added on 2026-11-19 (PLAN-023), cut out of DAT-006. What a source's runs already say (DAT-007) is not stored a second time with the source, where the two could come to disagree: one function, `standing_of(work, source_id)` in the new module `motosphere.db.source_health`, reads it from the table `collection_run` and writes nothing. It gives a `SourceStanding`, a frozen dataclass with `last_attempt`, `last_success`, `last_error` and `health`. Settled in the planner's trial. The health is one of four texts, the list `SourceHealth`, told by the newest of the source's runs that is over (a run that is still running is passed over): `not yet scanned` when no run is over yet, `healthy` after one that succeeded, `failing` after one that failed, `interrupted` after one whose job died. Interrupted is not failing: a run that failed says what went wrong at the source, a run that was interrupted says that the job died. No rule has a number in it. A scan is said by when it started, the one time every run has, so both times are starts. The newest run is the one that started last, and of two that started together the one stored last. The last error is that of the newest run that failed, is no longer said once a later run succeeded, and is still said while a later run is running or was interrupted. A key that no source has is refused with a `LookupError`. The list is not stored, so there is no table, no column and no migration, and the schema stays at version 3. The reliability score of the design is not here: how often a source could be collected from says whether it answers, not whether what it says is right, so it comes with COL-009 from records that were checked, and no number is invented until then. The index the function wants on the table of the runs, over (`source_id`, `started_at`), was read from SQLite's account of its plan in the trial and is cut out as DAT-042 (PLAN-024). `ARCHITECTURE.md` §7, which said that the table of the sources records health, is brought in line. The planner's trial has 38 new tests and detects 45 of 45 planted defects.
- **Acceptance criteria:**
  1. `SourceHealth` has exactly its four texts in their order, and no text has two names.
  2. Of a source that has no run, nothing is said of a last scan or a last error, and its health is `not yet scanned`; the same health holds while its only run is still running, and that run is its last attempt.
  3. The last attempt is the start of the source's newest run, whatever became of it; the last success is the start of its newest run that succeeded.
  4. The health is told by the newest run that is over: `healthy` after one that succeeded, `failing` after one that failed, `interrupted` after one that was interrupted.
  5. The last error is that of the newest run that failed; it is no longer said once a later run succeeded, and is still said while a later run is running or was interrupted.
  6. The newest run is the one that started last, and of two that started together the one stored last. A source is told by its own runs only.
  7. A key that no source has is refused with a `LookupError` in one plain sentence.
  8. Nothing is written to the store when it is asked, and what is said cannot be changed afterwards.
  9. No existing test changed, and all pass. The type check passes with no `ignore` and the lint with no `noqa`.
  10. `python scripts/check.py` reports 19 of 19 gates and 1571 tests (backend tests 941); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 38 new tests: 32 integration tests in a store the migrations built, with runs of every outcome, and 6 unit tests of the list; every existing test. Fourteen planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #111 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1571 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 941: 903 before, 38 new); 45 planted defects in the new module, 45 of 45 detected, the plan's fourteen prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 45309716301 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1571 passed, 0 failed, 0 skipped.", with 941 backend tests on both machines, the three jobs after the gates skipped; run 45311067843 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1571 / 0 tests (repository 41, script tests 206, backend 941, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 45 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-24. All 8 files are identical to the planner's trial. The 32 new integration tests run against real SQLite files in a store that the migrations built, with runs of every outcome; nothing is a mock. No existing code file or test changed, and the schema is still at version 3. No package was added.
- **Commit:** `02da36e`
- **Plan:** `docs/plans/DAT-041.md`

### DAT-042 – An index for the runs of one source
- **Status:** PASSED – VERIFIED
- **Objective:** The store finds the runs of one source, newest first, without reading the whole table of the runs.
- **Description:** Added on 2026-11-24 (PLAN-024), cut out of DAT-041. `standing_of` (DAT-041) asks the table of the runs four times for the newest run of one source that has one of some outcomes. One index, `ix_collection_run_source_id_started_at`, over `source_id` and `started_at` in that order: the model says it, the naming rule names it, and the fourth migration, `index_the_runs_of_a_source`, makes it. Settled in the planner's trial, which asked SQLite for its plan for the four statements with no index and with six. With none, the whole table is read and what was found is sorted. Over the source and the start, the runs of the source are searched for by the index and nothing is sorted. Over the source alone, they are found and then sorted. The key as a third column changes nothing, because SQLite ends every entry of an index with the key by itself, which is why two runs that started together need no sorting either. The outcome as a third column, or the start in falling order, makes SQLite sort the last part of the order again, and the outcome before the start makes it sort whenever more than one outcome is asked for. The index is not unique: two runs of one source can start at the same moment. A test catches the statements `standing_of` really sends and reads SQLite's plan for each (`EXPLAIN QUERY PLAN`), so a statement changed later in a way the index does not serve fails it. Deleting a source: in the trial SQLite's program for that statement opened the table of the runs without the index and the index with it; no test holds it to that, because it is how SQLite works inside. The planner's trial has 7 new tests and detects 28 of 28 planted defects, and 161 of 161 of the earlier ones whose files this task changes.
- **Acceptance criteria:**
  1. The model and the migration say the same index, and the test of the models and the migrations finds the two the same.
  2. The newest schema has the index `ix_collection_run_source_id_started_at` over `source_id` and `started_at`, in that order; it is not unique and is over all rows.
  3. The fourth migration makes the index in a store at version 3 that has runs, and keeps them; where an index of its name is there already it fails, and the store is as it was. The first three migrations are unchanged, and the history names its four migrations in their order.
  4. SQLite's account of its plan for each of the four statements of `standing_of` that read the runs is the one step that searches the index for the source, and nothing is sorted.
  5. No answer of `standing_of` changes: its tests pass as they are, and it says the same with the index and without it.
  6. No existing test changed but the test of the history's names; all pass. The type check passes with no `ignore` and the lint with no `noqa`.
  7. `python scripts/check.py` reports 19 of 19 gates and 1578 tests (backend tests 948); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 7 new tests: 4 integration tests of the index in a store the migrations built, which read SQLite's plan for the real statements, and 3 of the history (the fourth migration given to a store at version 3 that has runs, and to one that has an index of its name already); every existing test. Thirteen planted defects by the builder and the planner's own; the earlier planted defects of the tables of the sources, of the offers and of the runs again; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #113 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1578 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 948: 941 before, 7 new); 28 planted defects in the model and the migration, 28 of 28 detected, the plan's thirteen prove-it steps among them with the results the plan gives; the earlier planted defects of the table of the sources (51), of the table of the offers (34) and of the table of the runs (76) again, 161 of 161 detected; the real commands `migrate` and `schema` on a new store, which is then at version 4 and holds the index `ix_collection_run_source_id_started_at`. On GitHub, read by the planner from the runs and job logs: run 45387972476 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1578 passed, 0 failed, 0 skipped.", with 948 backend tests on both machines, the three jobs after the gates skipped; run 45393820115 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1578 / 0 tests (repository 41, script tests 206, backend 948, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 189 / 0 planted defects detected (28 new, 161 earlier); the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-24. All 8 files are identical to the planner's trial. The 7 new integration tests run against real SQLite files, and three of them read SQLite's own account of its plan for the statements `standing_of` really sends; nothing is a mock. The first three migrations are unchanged. No package was added.
- **Commit:** `0ae92df`
- **Plan:** `docs/plans/DAT-042.md`

### DAT-043 – The lists that say how far a record can be trusted
- **Status:** PASSED – VERIFIED
- **Objective:** The code knows the three levels of confidence and the four verification statuses of a collected record, each with the text that is stored.
- **Description:** Added on 2026-11-24 (PLAN-025), cut out of DAT-008. One new module, `motosphere.db.models.provenance`, with two lists, each a `StrEnum` as a column of a list takes one (DAT-036). They answer two questions, and neither answers the other. `Confidence` is about the reading, how sure it is that a record says what its source says: `high` (the source gives the value in a place made for it, and it was taken as it stands), `medium` (read out of a page or a document made for people, by a rule written for that source) and `low` (worked out from what stands around it, or the source is unclear or says two things). `VerificationStatus` is about the publishing, what standing the source's word has: the four kinds of record DESIGN §6 tells apart, in its order, `official`, `independent`, `reconstructed` and `unverified`, which also tells official information from independently published information (CLAUDE.md §11). Settled in the planner's trial: the texts and what each means; three levels and no number, because nothing measures how sure a reading is; that both lists go from what can be trusted most to what can be trusted least; that the status is said of the record and not of its source, so the kind of a source does not give it; that every value has the name its text spells; and that no text is on both lists. Left to the columns (DAT-008): whether a record may be without one of the two, and how a record says the way it was got. No table, no model, no migration, no existing code file or test changed. The planner's trial has 22 new tests and detects 23 of 23 planted defects.
- **Acceptance criteria:**
  1. `Confidence` has exactly its three texts and `VerificationStatus` its four, each from what can be trusted most to what can be trusted least, and no text has two names.
  2. Every text is words in small letters with one space between two, and every value has the name its text spells.
  3. No text is on both lists.
  4. A column can be of either list: `OneOf` takes it, and the check it gives names the texts of the list in their order.
  5. `DATABASE.md` says what each text means, which words of the design each status stands for, and that the status is said of the record and not of its source.
  6. No existing test changed, and all of them pass. The type check passes with no `ignore` and the lint with no `noqa`.
  7. `python scripts/check.py` reports 19 of 19 gates and 1600 tests (backend tests 970); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 22 new unit tests in seven functions, with the texts of both lists written out a second time; every existing test, unchanged. Twelve planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #115 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1600 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 970: 948 before, 22 new); 23 planted defects in the two lists, 23 of 23 detected, the plan's twelve prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 45400249455 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1600 passed, 0 failed, 0 skipped.", with 970 backend tests on both machines, the three jobs after the gates skipped; run 45401832086 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1600 / 0 tests (repository 41, script tests 206, backend 970, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 23 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-24. All 6 files are identical to the planner's trial. No existing test changed, and no package was added. The task has no table: the lists are plain code, and what SQLite does with a column of a list is proven for every list by the tests of DAT-036 and comes for these two with the columns (DAT-008).
- **Commit:** `f4846bb`
- **Plan:** `docs/plans/DAT-043.md`

### DAT-044 – A column that is a calendar day
- **Status:** PASSED – VERIFIED
- **Objective:** A model can say that a column is a calendar day, and the store refuses anything else in it.
- **Description:** Added on 2026-11-24 (PLAN-026), in front of DAT-008, whose columns are the first to need it: the day a source published a record is a day, with no time of day, and none is made up for it (CLAUDE.md §11). `DATABASE.md` has said since DAT-028 that a day without a time needs a type of its own. One new module, `motosphere.db.days`, with the column type `CalendarDay`, the fifth type that brings its check (DAT-034): TEXT in the table, in the one form `2026-11-24`, with a check named `ck_<table>_<column>_calendar_day`. A model says the column's Python type, `Mapped[date]`, and `Base` gets one entry in the list by which a Python type becomes a column type; the rule by which `Base` gives checks, and `broken_rules`, do not change. Settled in the planner's trial: the form, which is the one SQLite's own date functions and Python's `date.isoformat()` write, so that the order of the texts is the order of the days; the check, which asks three things of the text: that it has the form, that SQLite's calendar reads it and says the same text back (so the 30th of February is refused), and that it is not before the first of January of the year 1 (SQLite knows a year 0 and Python does not); that the form is asked first, because SQLite will not ask its calendar about the word `now` inside a check and fails with words of its own, which the trial found; that the calendar is asked with `IS` and not with `=`, because a check lets what is not known pass; that a time is refused with a sentence of its own, with an offset or without, although Python counts a `datetime` as a `date`, because the time of day would be dropped in silence and the day a moment falls on depends on its offset; that only text in the one form is read as a day; and that the years go from 1 to 9999. A day of which only the year or the month is known is not a day, and this type does not hold it: the table that first has such a thing settles how it is kept. No model, no table, no migration, no new package, no existing test changed. The planner's trial has 94 new tests and detects 63 of 63 new planted defects and 372 of 372 of the earlier tasks'.
- **Acceptance criteria:**
  1. A model that says `Mapped[date]` of a column gets a text column with the check, named by the naming rule: the real SQLite file has the checks by name and letter for letter, for each such column and for no other. A model's `datetime` is still a time.
  2. A day is stored as text in the one form and comes back as the day, from the first day there is to the last; a column that may be without a value holds none or a day; a value of the model's own is stored in the form; a change is stored.
  3. What is not a `date` is refused before anything is written, with a sentence that says what it was given, and a time with a sentence of its own, with an offset or without, in a row and in a question.
  4. Text that is not a day of the calendar in the form is refused by SQLite with the name of the check, word for word, in twenty kinds, in every such column, in a row written with plain SQL and in a change; a number is refused by the check and bytes by the strict table.
  5. Only text in the one form is read as a day: fifteen things that are not are refused when read, also what Python could read as a day.
  6. Rows are found by a day, by the days before and after it, and in the order of the days; SQLite's own date functions read a stored day.
  7. `broken_rules` names such a column whose table is without the check, in the type's words, until the table has it; the rule by which `Base` gives checks, and `broken_rules`, are unchanged.
  8. No existing test changed, and all of them pass. The type check passes with no `ignore` and the lint with no `noqa`.
  9. `python scripts/check.py` reports 19 of 19 gates and 1694 tests (backend tests 1064); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 45 new unit tests in fifteen functions, of saying and reading a day, of the check as SQLite is given it, of its name, of the type and of the entry in the list of `Base`; 49 new integration tests in seventeen functions, with a model that has three such columns and a time next to them, against a real SQLite file that is read with plain SQL, past the model; every existing test, unchanged. Thirteen planted defects by the builder and the planner's own, all of DAT-034's, DAT-035's, DAT-037's and DAT-038's among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #117 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1694 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 1064: 970 before, 94 new); 63 planted defects in the new module and in the new line of `base.py`, 63 of 63 detected, the plan's thirteen prove-it steps among them with the results the plan gives; the 372 planted defects of DAT-034, DAT-035, DAT-037 and DAT-038 planted again, because `base.py` changes, 372 of 372 detected. On GitHub, read by the planner from the runs and job logs: run 45410961772 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1694 passed, 0 failed, 0 skipped.", with 1064 backend tests on both machines, the three jobs after the gates skipped; run 45415020306 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1694 / 0 tests (repository 41, script tests 206, backend 1064, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 435 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-24. All 8 files are identical to the planner's trial. No existing test changed, and no package was added. The check was asked of the real SQLite of three machines: the planner's (3.53.1) and the two of GitHub, Linux and Windows.
- **Commit:** `b1a5eb8`
- **Plan:** `docs/plans/DAT-044.md`

### DAT-008 – Provenance on every collected record
- **Status:** PASSED – VERIFIED
- **Objective:** Every collected record says where it came from, when, how, and how far it can be trusted (DESIGN §8): one set of columns, said once, that a model of collected records takes whole.
- **Description:** One new class, `Collected`, in `motosphere.db.models.provenance`, next to the two lists of DAT-043, which was cut out of this task on 2026-11-24 (PLAN-025). It is a subclass of `Base` that is no table itself, and a model whose records are collected is a subclass of it and not of `Base`. Its table then has eight columns after the columns the model names and before the two times: `source_id`, which refers to `source.id`; `source_address`, a web address (DAT-037); `collected_at`, a time; `published_on`, a calendar day, of the type of DAT-044, which was put in front of this task on 2026-11-24 (PLAN-026); `last_verified_at`, a time; `extraction_method`, one of the ways of collecting (`CollectionMethod`); `confidence` and `verification_status`, of the lists of DAT-043. Settled in the planner's trial: a class to be a subclass of and not a mixin beside `Base`, so that there is one parent and no order of parents to get wrong; that only the day of publishing may be without a value, and that no column gives itself a value, because a default would be a value nobody read anywhere (CLAUDE.md §11), `low` and `unverified` being the words for knowing little; that the extraction method is of the list of the ways of collecting, and is kept with the record although the source says its way too, because that can change; that `last_verified_at` is when the source was last seen to say what the row says, which for a new record is the moment it was collected, so it is never unknown; one check across two columns, `ck_<table>_last_verified_at_not_before_collected_at`, which `Collected` gives to each table itself in `__init_subclass__`, so that a model which says `__table_args__` keeps it; that the two times are compared as text, which is the order of the moments; that nothing holds the day of publishing to the moment of collecting, because a page dated the 26th in New Zealand is read on the 25th by the clock of UTC; and that SQLite refuses to delete a source that records came from, with nothing deleted along with it. Tables made for the tests prove the set, in a store the migrations built, so the source they refer to is the real table; the real tables use the set from DAT-011 on. Cut out on 2026-11-25 (PLAN-027): the index over `source_id` (DAT-045) and the rule that names a table of collected records without the set (DAT-046). No table, no migration, no new package, no existing test changed. The planner's trial has 117 new tests and detects 68 of 68 new planted defects and 23 of 23 of DAT-043's.
- **Acceptance criteria:**
  1. The table of a model that is a subclass of `Collected` has the key, the columns the model names, the eight columns of the set in their order and the two times, in the model and in the real SQLite file. `Collected` itself is no table, and the real schema is as it was.
  2. Each of the eight is of its type and of its list; only `published_on` may be without a value; no column of the set gives itself a value, and none is a key, unique or indexed.
  3. A record is stored with all eight and read back as it was given, and in the file it is text in the store's forms. Every value of each of the three lists is stored as its text and read back.
  4. A record without one of the seven that must be said is refused by SQLite, through the model and past it. The day of publishing may be unknown.
  5. A record of a source that is not there is refused. A source that records came from cannot be deleted and its key cannot be changed, in either of two tables of collected records; one whose records are gone can be deleted.
  6. An address that is not a web address, text that is not on the list of its column, and a day of publishing that is not a day are refused by SQLite with the name of the check; a value of another list and a time given for the day are refused before anything is written.
  7. A record last seen at its source before it was collected is refused with the name of the check, through the model and past it, also when the two times were given in different offsets; the same moment and every later one are taken. A record that is seen again says when and keeps when it was collected.
  8. A change that breaks the set is refused, in seven kinds, and the row stays as it was.
  9. A model that says more of its table keeps what it said and has every check of the set; every table has a check of its own; the tables break none of the rules every table keeps.
  10. No existing test changed, and all of them pass. The type check passes with no `ignore` and the lint with no `noqa`.
  11. `python scripts/check.py` reports 19 of 19 gates and 1811 tests (backend tests 1181); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 42 new unit tests in fourteen functions, of the columns, their order, their types, the reference and the checks, with two models of the tests' own; 75 new integration tests in 24 functions, in a store the migrations built, with the tables of those models made beside the real ones, read with plain SQL, past the model; every existing test, unchanged. Thirteen planted defects by the builder and the planner's own, all of DAT-043's among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #119 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1811 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 1181: 1064 before, 117 new); 68 planted defects in `Collected`, 68 of 68 detected, the plan's thirteen prove-it steps among them with the results the plan gives; the 23 planted defects of DAT-043 planted again, because `provenance.py` changes, 23 of 23 detected. On GitHub, read by the planner from the runs and job logs: run 45698596000 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1811 passed, 0 failed, 0 skipped.", with 1181 backend tests on both machines, the three jobs after the gates skipped; run 45701102574 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1811 / 0 tests (repository 41, script tests 206, backend 1181, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 91 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-25. All 7 files are identical to the planner's trial. No existing test changed, and no package was added. What SQLite refuses was asked of the real SQLite of three machines: the planner's (3.53.1) and the two of GitHub, Linux and Windows.
- **Commit:** `b88fb1b`
- **Plan:** `docs/plans/DAT-008.md`

### DAT-045 – An index for the records of one source
- **Status:** PASSED – VERIFIED
- **Objective:** SQLite finds the records that came from one source without reading a whole table, in every table of collected records.
- **Description:** Added on 2026-11-25 (PLAN-027), cut out of DAT-008, as the index of the runs was cut out of their table (PLAN-024, DAT-042). One word in `Collected`: the column `source_id` says `index=True`, so every table of a model of collected records has an index over that column, which the naming rule names `ix_<table>_source_id`. Without it SQLite reads the whole of every such table to find the records of one source: whenever the store asks what it holds of a source, and by itself every time a source is to be deleted. Settled in the planner's trial: the index is over the source alone and does not go on with the moment a record was last seen. Five things asked about the records of one source (which came from it, how many, whether any, which were not seen since a moment, and the taking away of its records) are each answered by this index in one step, and no code asks for more yet; an index over two columns would be paid for in every table of collected records at every writing, so the task whose code first asks such a question reads SQLite's plan with real numbers of rows and widens the index if it is worth it. The index is said on the column and not in `__table_args__`, so that a model which says `__table_args__` itself keeps it. It is not unique and is over all rows. SQLite's own account of the deleting of a source (`EXPLAIN QUERY PLAN`) names the look into each table that refers to a source, so the tests read from SQLite itself that this look goes by the index, on every machine the gates run on. Two tests of DAT-008 held that such a table has no index, one of the model and one of the file; both now hold this one, and no other existing test changes. No real table has the set yet, so there is no migration. The planner's trial has 25 new tests and detects 16 of 16 new planted defects and 90 of 90 of DAT-008's and DAT-043's.
- **Acceptance criteria:**
  1. Every table of a model that is a subclass of `Collected` has one index over `source_id` alone, named `ix_<table>_source_id` by the naming rule, not unique and over all rows, in the model and in the real SQLite file; no other column of the set has an index.
  2. A model that gives its table an index of its own keeps it and has the index of the set; every table has an index of its own; the tables break none of the rules every table keeps.
  3. SQLite's own account of five things asked about the records of one source is one step each, by the index.
  4. SQLite's own account of the deleting of a source names the look into each table of collected records by that table's index, and no step of it reads a whole table.
  5. Without the index each of the five, and the deleting of a source, reads the whole table; with it and without it the store gives the same answers and refuses the same deleting.
  6. Two existing tests change, the two of DAT-008 that held such a table to have no index, and no other; all tests pass. The type check passes with no `ignore` and the lint with no `noqa`.
  7. `python scripts/check.py` reports 19 of 19 gates and 1836 tests (backend tests 1206); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 11 new unit tests in four functions, of the index in the model; 14 new integration tests in six functions, in a store the migrations built, with the tables of two models of the tests' own made beside the real ones, which read SQLite's plans for statements the code really sends and for the deleting of a source; the two changed tests; every other existing test, unchanged. Nine planted defects by the builder and the planner's own, those of DAT-008 and DAT-043 among them; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #121 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1836 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 1206: 1181 before, 25 new); 16 planted defects in the index, 16 of 16 detected, the plan's nine prove-it steps among them with the results the plan gives; 67 of the planted defects of DAT-008 and the 23 of DAT-043 planted again, because `provenance.py` changes, 90 of 90 detected. On GitHub, read by the planner from the runs and job logs: run 45705440930 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1836 passed, 0 failed, 0 skipped.", with 1206 backend tests on both machines, the three jobs after the gates skipped; run 45707939048 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1836 / 0 tests (repository 41, script tests 206, backend 1206, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 106 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-25. All 8 files are identical to the planner's trial. Two existing tests changed, the two that held such a table to have no index, and no package was added. What SQLite's plans say was read from the real SQLite of three machines: the planner's (3.53.1) and the two of GitHub, Linux and Windows.
- **Commit:** `50ac0f1`
- **Plan:** `docs/plans/DAT-045.md`

### DAT-046 – A table of collected records without its provenance is named
- **Status:** PASSED – VERIFIED
- **Objective:** A table of collected records that was made without the set of DAT-008, or with a part of it changed, is named in plain words, and a test holds the real schema to it.
- **Description:** Added on 2026-11-25 (PLAN-027), cut out of DAT-008, as the rule of the two times was cut out of them (PLAN-019, DAT-032). Nothing in DAT-008 stops a model from being a subclass of `Base` where it should be one of `Collected`, or from saying a column of the set again in its own way. One new module, `motosphere.db.models.provenance_rule`, with one function, `broken_provenance(schema, not_collected)`, which says in one plain sentence for each break which tables of a schema do not say where their records came from, and one list, `NOT_COLLECTED`, which has the three tables of the real schema that hold no collected records, each with its reason. Settled in the planner's trial: every table holds collected records unless the list names it, so a new table that nobody thought about is named; the list is given to the function, so that the tests give their own; the rule stands beside `broken_rules` and in a module of its own, so neither `base.py` nor `provenance.py` changes; the rule says the set a second time and does not take it from `Collected`, so a change to the set is made in two places and a test fails until they agree; a column is as the set has it by its type and list, by whether a row can be without it, by being given no value, and by what it refers to, and the order of the columns is not held; the index is one over `source_id` alone, over all rows and not unique, whatever it is called; the check is looked for by its name and letter for letter; all missing columns of a table are one sentence, and the index and the check are not asked for where a column they need is missing; the list is held to the schema too, so a name on it that is no table is named, and so is a table on it that has all eight columns. All three real tables are on the list, so a second test takes each off in turn and holds the rule to what it then says. No table, no migration, no new package, no existing test changed. The planner's trial has 74 new tests and detects 86 of 86 planted defects.
- **Acceptance criteria:**
  1. `broken_provenance` gives an empty list for the real schema with `NOT_COLLECTED`, and for the tables of models that are subclasses of `Collected`, also one that has rules, a check and indexes of its own.
  2. A table that is not on the list and is without columns of the set is named in one sentence, which names the missing columns in the order of the set and says both ways out.
  3. A column of the set that is of another type or list, that may be without a value where the set says otherwise, that is given a value nobody said, or that does not refer as the set says, is named.
  4. A table without an index over `source_id` alone, over all rows and not unique, is named; so is a table without the check of its two times, by its name and letter for letter. Neither is asked for where a column it needs is missing.
  5. A table on the list is not looked at. A name on the list that is no table is named, and so is a table on the list that has all eight columns.
  6. Each break is one plain sentence, and the breaks come in one order: the list, then table by table, and rule by rule.
  7. Each table of the real schema is named as soon as it is off the list; every table on `NOT_COLLECTED` has a reason of its own.
  8. No existing test changed, and all tests pass. The type check passes with no `ignore` and the lint with no `noqa`.
  9. `python scripts/check.py` reports 19 of 19 gates and 1910 tests (backend tests 1280); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 74 new unit tests in 21 functions, with tables made by hand in schemas of their own, two models of the tests' own that are subclasses of `Collected`, and the real schema; every existing test, unchanged. Fourteen planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #123 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1910 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 1280: 1206 before, 74 new); 86 planted defects in the rule and its list, 86 of 86 detected, the plan's fourteen prove-it steps among them with the results the plan gives. On GitHub, read by the planner from the runs and job logs: run 45712685284 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1910 passed, 0 failed, 0 skipped.", with 1280 backend tests on both machines, the three jobs after the gates skipped; run 45713961295 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1910 / 0 tests (repository 41, script tests 206, backend 1280, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 86 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-25. All 6 files are identical to the planner's trial. No existing test changed, and no package was added.
- **Commit:** `71df1fc`
- **Plan:** `docs/plans/DAT-046.md`

### DAT-009 – Record change history
- **Status:** PASSED – VERIFIED
- **Objective:** The store has a table that keeps, for one field of one record, what it held before it was changed and what it holds now, when it was changed, and which collection run or which person caused the change.
- **Description:** Cut down in the planner's trial on 2026-11-25 (PLAN-028) to the table of the changes: the function that writes a change with its history is DAT-047, that a row of the history can be neither edited nor deleted is DAT-048, and its indexes are DAT-049. One new table, `record_change`, with its model `RecordChange` in `motosphere.db.models.record_change` and the fifth migration, `make_the_record_changes`; the schema is at version 5. One row is one field of one record that was changed: `record_table`, `record_id`, `field`, `old_value`, `new_value`, `collection_run_id`, `decided_by`, and the two times every table has. Settled in the trial: one table for the changes of every table, so the record is named by the name of its table and its key there, which SQLite cannot hold to a row that exists (the function of DAT-047 will); one row for a field and not for a change to several; values as text in the form the store keeps them, in TEXT columns of a strict table and not of SQLite's kind `ANY`, so that `'7'` and `7` are not two values; no value is a value, so either side may be without, and a check, `old_value IS NOT new_value`, refuses a change that changed nothing, also where both are missing, which `!=` would let through; when it was changed is `created_at`, with no second column to say it again; a run caused the change, by reference, or a person did, by name, and a check holds that it is exactly one of the two; the reference to the run says nothing of what happens when the run is deleted, so a run that caused a change cannot be deleted; the key of the record is above 0; nothing forbids two changes that are alike, and their order is the order of their keys; no index yet. The table holds no collected records, so it is on the list `NOT_COLLECTED` with its reason (DAT-046). Nothing writes a change yet. Two existing tests get an addition each (the names of the migrations, and the case of the new table in the test that takes each real table off the list); no other existing test changed; no new package. The planner's trial has 48 new tests and detects 64 of 64 new planted defects.
- **Acceptance criteria:**
  1. The fifth migration makes the table `record_change` in a store at version 4 and leaves the sources, the offers, the runs and the index of the runs as they were; it fails, with the store left at version 4, where a table of its name is there already. A new store is at schema version 5.
  2. The model `RecordChange` and the migration say the same table; in the file it is strict, has the columns in the order of the model, one reference (to `collection_run.id`), no index and six checks.
  3. A change a run caused and a change a person decided are stored and read back with every column; values are kept as the text they were, and no value on either side is kept as no value.
  4. The table refuses: a change whose new value is its old value, also where both are missing; a change that nothing caused and one that a run and a person both caused; a run that does not exist; a row without the table, the key or the field of its record; an empty name of a table, of a field or of a person; a key of a record that is not above 0; and a value of the wrong kind for a column.
  5. A run that caused a change can neither be deleted nor have its key changed, and a run that caused none can be deleted.
  6. `record_change` is on `NOT_COLLECTED` with a reason of its own, and the real schema breaks neither the rules every table keeps nor the rule of DAT-046.
  7. Two existing tests get an addition each and no other changes; all tests pass. The type check passes with no `ignore` and the lint with no `noqa`.
  8. `python scripts/check.py` reports 19 of 19 gates and 1958 tests (backend tests 1328); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 43 new integration tests in 16 functions, in a store the migrations built, on a real SQLite file, through the model and with plain SQL past it; 4 new tests of the history, of the fifth migration given to a store at the version before it and of the names the module gives; one new case of the rule of DAT-046; every other existing test, unchanged. Sixteen planted defects by the builder and the planner's own, with those of the earlier tasks whose files change; the real commands `migrate` and `schema` on a new store; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** In a clean checkout of pull request #125 (Linux, Python 3.13.18 with SQLite 3.53.1, SQLAlchemy 2.1.9, pytest 9.2.0, Node 22.23.4, npm 10.9.9, uv 0.11.32), with nothing installed beforehand: the full run, 19 of 19 gates passed, "Tests: 1958 passed, 0 failed, 0 skipped.", exit code 0 (backend tests 1328: 1280 before, 48 new); 64 planted defects in the migration, the model, the package and the list, 64 of 64 detected, the plan's sixteen prove-it steps among them with the results the plan gives; the 275 planted defects of DAT-006, DAT-040, DAT-007, DAT-042 and DAT-046 planted again, because `history.py` and `provenance_rule.py` change, 275 of 275 detected; the real commands on a new store, which `migrate` makes at schema version 5 and `schema` says is up to date. On GitHub, read by the planner from the runs and job logs: run 45721787587 on the pull request's commit, both gates jobs green, each log ending "19 of 19 gates passed." and "Tests: 1958 passed, 0 failed, 0 skipped.", with 1328 backend tests on both machines, the three jobs after the gates skipped; run 45726021738 for `main` after the merge, all five jobs green at the first attempt, both gates jobs with the same two closing lines, the site republished, and the check of the published site ending "https://bigdaddy284.github.io/MotoSphere/ is the site that was built: 7 of 7 files."
- **Passed / Failed:** 1958 / 0 tests (repository 41, script tests 206, backend 1328, frontend unit 212, browser 171); all 19 gates passed, locally and on both machines on GitHub; 339 / 0 planted defects detected; the published site: 7 / 7 files identical to the build
- **Verification status:** Verified by the planner on 2026-11-26. All 12 files are identical to the planner's trial. Two existing tests got an addition each, as the plan says, and no other existing test changed; no package was added. The table and its checks were asked of the real SQLite of three machines: the planner's (3.53.1) and the two of GitHub, Linux and Windows.
- **Commit:** `8491245`
- **Plan:** `docs/plans/DAT-009.md`

### DAT-047 – A change is written with its history
- **Status:** IN PROGRESS
- **Objective:** A field of a record is changed and the change is written to its history in the same unit of work, so that neither exists without the other.
- **Description:** Added on 2026-11-25 (PLAN-028), cut out of DAT-009. One new module, `motosphere.db.changes`, with one function, `change(work, record, to, run=…)` or `change(work, record, to, decided_by=…)`. It gives a stored record its new values and adds one row to `record_change` for every field that then holds another value, and gives the rows back in the order the fields were given. Settled in the planner's trial: a value is compared, and written to the history, as the text of what the store keeps for it, which the type of the column says as it says it when a row is written, so the history holds the text SQLite itself gives for the column before and after; a column of text takes text and a column of whole numbers a whole number, and what is merely like one is refused, where SQLite would have made something of it; a number with a fraction and bytes have no text yet and a change to such a column is refused, because no real table has one and the choice matters for coordinates; a field that holds the value already gets no row, and when no field differs the record is not touched and the clock is not read; the clock is read once for one call, and every row of the call and the record's `updated_at` carry that moment; `id`, `created_at` and `updated_at` never go through the function; the columns that say where a collected record came from go through it like any other field, so a collector gives the new value and its new provenance in one call and the history holds the address, the day and the moments of the old value (CLAUDE.md §11); a record that is stored for the first time has no history, and a record that was only added is refused until the unit of work has written it; the function writes at once, so what SQLite refuses is refused at the call, the unit of work then fails as a whole, and one that caught the refusal cannot go on; a row of the history is not a record to change; nothing stops a change past the function, and a test stores one so that this is on record. No real table holds records before DAT-011, so three tables made for the tests prove it, in a store the migrations built, with the real table of the changes. No table, no migration, no new package, no existing file of code or tests changed. The planner's trial has 63 new tests and detects 65 of 65 planted defects.
- **Acceptance criteria:**
  1. `change` gives a stored record its new values and adds one row to `record_change` for every field that then holds another value, with the old and the new value, the cause and the moment; a change to three fields is three rows, in the order given.
  2. A field that holds the value already gets no row; when no field differs nothing is written, the record's `updated_at` does not move and the clock is not read.
  3. The old and the new value in the history are the texts SQLite gives for what it keeps in the column before and after, for text, a web address, a whole number, a day, a time, yes or no and a word of a list, with and without a value.
  4. The rows of one call and the record's `updated_at` carry one moment, from one reading of the clock.
  5. Exactly one cause: a run or a person. Neither and both are refused before anything is changed.
  6. A change the store refuses, and work that fails later in the same unit, leave neither the change nor its history; a unit of work that caught a refusal cannot go on.
  7. Refused before anything is changed, a good field of the same call included: a value of the wrong kind for its column; a column of numbers with a fraction or of bytes; a time without an offset; the store's own three columns; a field the table does not have; a record that is not stored yet, of another unit of work, or deleted; and a row of the history.
  8. No existing test and no existing file of code changed, and all tests pass. The type check passes with no `ignore` and the lint with no `noqa`.
  9. `python scripts/check.py` reports 19 of 19 gates and 2021 tests (backend tests 1391); on the pull request both gates jobs are green (Linux and Windows) and the three jobs after the gates are skipped.
- **Tests required:** 63 new integration tests in 24 functions, in a store the migrations built, on a real SQLite file, with three tables of the tests' own and the real table of the changes, read with plain SQL, past the models; every existing test, unchanged. Sixteen planted defects by the builder and the planner's own; the full run of all 19 gates; the workflow run on the pull request, on both machines; the run for `main` after the merge, with its deployment and the check of the published site.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –
- **Plan:** `docs/plans/DAT-047.md`

### DAT-048 – A row of the history is neither edited nor deleted
- **Status:** NOT STARTED
- **Objective:** What the history said once it says for good: a row of `record_change` is added and never edited or deleted.
- **Description:** Added on 2026-11-25 (PLAN-028), cut out of DAT-009, which asked that "history rows cannot be edited or deleted through the model". After DAT-009 nothing stops either. The planner's trial settles where the refusal stands: in the model, which holds whoever goes through it, or in the store itself, by triggers that a migration makes and that hold past the model too, or both; what that means for `updated_at`, which every table has and which a row that is never edited never moves; and how the comparison of the models and the migrations holds a trigger, which no model says today.
- **Acceptance criteria:** an edit and a delete of a row of the history are each refused, in one plain sentence, and the row is as it was; a new row is still stored; a run that caused a change still cannot be deleted; the refusal is proven on a real SQLite file on every machine the gates run on.
- **Tests required:** integration tests against a real SQLite file; the migration, if there is one, applied to a store at the version before it; planted defects, those of DAT-009 among them where its files change; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-049 – Indexes for the history of a record
- **Status:** NOT STARTED
- **Objective:** SQLite finds the history of one record, and the changes one run caused, without reading the whole table of the changes.
- **Description:** Added on 2026-11-25 (PLAN-028), cut out of DAT-009, as the index of the runs was cut out of their table (PLAN-024, DAT-042) and the index of a record's source out of the provenance (PLAN-027, DAT-045). The table of the changes has no index. It is the table that grows with every change to every record, and two things look into it: whoever asks what a record said before, and SQLite itself, every time a run is to be deleted, to see whether the run caused a change. Which indexes are the right ones is read from the plans SQLite makes for the statements that are really asked, and the function of DAT-047 is what asks them.
- **Acceptance criteria:** the indexes are in the model and in the real SQLite file, by the names the naming rule gives them, made by a migration that is given to a store at the version before it; SQLite's own plan for the history of one record in the order of its changes, for the changes one run caused, and for the deleting of a run reads no whole table, read from SQLite itself on every machine the gates run on; the test of DAT-009 that holds the table to have no index is changed to hold these, and no other existing test changes.
- **Tests required:** integration tests against a real SQLite file that read SQLite's plans; the migration applied to a store at the version before it; planted defects, those of DAT-009 among them; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-010 – Review queue
- **Status:** NOT STARTED
- **Objective:** Conflicting or doubtful information waits for a person's decision and is never merged by itself.
- **Description:** Table, model and migration for review items: what is in doubt (a possible duplicate, two sources that disagree, a value outside its rules), the records and sources involved, the state (open, accepted, rejected), who decided and when, and a note that never leaves the store. One function opens an item, and opening the same doubt twice gives one item.
- **Acceptance criteria:** an item names at least one record and why it is in doubt; the same doubt opened twice is one item; a decided item keeps its decision and cannot be reopened silently; the note is not in any published model.
- **Tests required:** integration tests against a real SQLite file; the migration applied to a store at the version before it; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-011 – Countries table
- **Status:** NOT STARTED
- **Objective:** The store holds countries, so that everything else can say where it is.
- **Description:** Table, model and migration for countries: the ISO 3166-1 two-letter and three-letter codes, the English short name, and provenance. Sources gain their country here (the column DAT-006 left out). No rows yet: they come with DAT-012.
- **Acceptance criteria:** codes are stored in capitals and refused in any other form or length; two countries cannot share a code; a source's country must exist.
- **Tests required:** integration tests against a real SQLite file; the migration applied to a store at the version before it; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-012 – Countries reference data
- **Status:** NOT STARTED
- **Objective:** The countries of ISO 3166-1 are in the store, from a source whose licence allows it, with that source recorded.
- **Description:** The planner's trial finds and records the source and its licence in `DATA_SOURCES.md` before the plan is written; if none allows redistribution the task is `BLOCKED – EXTERNAL DEPENDENCY`. A reference file in the repository with its origin and licence beside it, the source registered in the store, and a command that loads the file: countries are added or updated through the history of DAT-009, never deleted, and a second load changes nothing. Nothing is fetched while the command runs.
- **Acceptance criteria:** after loading, the store holds exactly the countries of the file, each with provenance naming the source; loading twice leaves the same rows and no new history; a changed name in the file becomes one change with history; a malformed file is refused whole and the store is unchanged.
- **Tests required:** unit tests of the file's reader; integration tests against a real SQLite file with the real reference file and with damaged ones; the command run for real; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-013 – Regions table
- **Status:** NOT STARTED
- **Objective:** A country can be divided into regions (a state, a county, a province), so that a track can say where in the country it is.
- **Description:** Table, model and migration for regions: the country, the name, the ISO 3166-2 code where one exists, an optional parent region, and provenance. No reference rows: regions arrive with the records that need them.
- **Acceptance criteria:** a region belongs to exactly one country; two regions of one country cannot share a code or, under the same parent, a name; a region's parent is in the same country; a country with regions cannot be deleted.
- **Tests required:** integration tests against a real SQLite file; the migration applied to a store at the version before it; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-014 – Racing disciplines
- **Status:** NOT STARTED
- **Objective:** The store knows the kinds of racing, and a new kind is a new row, not a new design (DESIGN §2.1).
- **Description:** Table, model and migration for disciplines (a stable key, a name, a short description, an order for display), and the seven of DESIGN §2.1 as reference rows added by the migration: outdoor motocross, supercross, amateur motocross, youth and junior motocross, veteran and masters racing, enduro, hard enduro.
- **Acceptance criteria:** the seven disciplines exist after the migration, each once; a key is lower-case words joined by hyphens and cannot be reused; adding an eighth needs no change to any other table.
- **Tests required:** integration tests against a real SQLite file; the migration applied to a store at the version before it; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-015 – Organisations table
- **Status:** NOT STARTED
- **Objective:** The store holds the bodies behind the sport: governing bodies, clubs, promoters and organisers.
- **Description:** Table, model and migration for organisations: name, kind (a fixed list), country, region where known, website, public contact details as published (an organisation's, never a private person's), and provenance. Identities that may be the same are not merged: they go to the review queue (DAT-010).
- **Acceptance criteria:** an organisation has a name, a kind and a country; a kind outside the list is refused; a website must be an http or https address; two organisations with the same name in the same country are both kept, and a review item can name the pair.
- **Tests required:** integration tests against a real SQLite file; the migration applied to a store at the version before it; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-016 – Tracks table with validated coordinates
- **Status:** NOT STARTED
- **Objective:** The store holds tracks with a position that is checked, and can find the tracks inside a rectangle of the map quickly.
- **Description:** Table, model and migration for tracks: name, country, region where known, latitude and longitude in WGS 84, how exact the position is, disciplines, status (open, closed, unknown), surface and facilities as published, website, the organisation that runs it, and provenance. A position is both numbers or neither. An index serves lookups by bounding box, including boxes that cross the 180th meridian; which kind of index (ordinary or R*Tree) is decided by measurement in the planner's trial.
- **Acceptance criteria:** a latitude outside -90 to 90 or a longitude outside -180 to 180 is refused; one coordinate without the other is refused; a position of exactly 0, 0 is refused (a common sign of a missing value, and open sea); a bounding-box query returns exactly the tracks inside, across the 180th meridian too, and uses the index; no coordinate is ever invented.
- **Tests required:** integration tests against a real SQLite file, with boundary and antimeridian cases and a check of the query plan; a measurement with 100,000 generated positions, used only to choose the index and never stored; the migration applied to a store at the version before it; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-017 – Track aliases
- **Status:** NOT STARTED
- **Objective:** A track can be known under several names, and a search by any of them finds it.
- **Description:** Table, model and migration for other names of a track: the name, what kind it is (former name, local-language name, common short name), the language where known, and provenance. Names are compared without regard to case, accents and surrounding space, by one function that later tasks reuse for duplicate detection.
- **Acceptance criteria:** a track cannot have the same alias twice, compared that way; an alias cannot equal the track's own name; deleting is not offered, and an alias proven wrong is ended through history; a lookup by alias returns the track.
- **Tests required:** unit tests of the comparison (case, accents, scripts other than Latin left as they are); integration tests against a real SQLite file; the migration applied to a store at the version before it; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-018 – Media references
- **Status:** NOT STARTED
- **Objective:** The store can point to photographs and other media at their source, with credit and licence, without copying them (DESIGN §14).
- **Description:** Table, model and migration for media references: what it shows (a track or an organisation, for now), the address of the page it is on and of the file, the kind, credit, licence, and provenance. Only references are stored. A file is never downloaded or republished by this task; whether one may ever be shown is decided by its licence in a later phase.
- **Acceptance criteria:** a reference belongs to exactly one record; addresses must be http or https; a reference without a licence is kept as `unknown` and is not exported as showable; nothing in the task fetches a file.
- **Tests required:** integration tests against a real SQLite file; the migration applied to a store at the version before it; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-019 – Snapshot: the store written as text files
- **Status:** NOT STARTED
- **Objective:** The whole store can be written out as text files that are the same, byte for byte, whenever the store is the same.
- **Description:** A command writes every table to text files in a folder: one record per line, records and fields in a fixed order, UTF-8, Unix line ends, with the schema version and a list of the files and their hashes, and reports the snapshot's size. Large tables are divided into files by a rule that depends only on the data. This is the form in which the store is kept between scheduled runs (DAT-001's decision), so a change to the store shows as a small, readable difference. The snapshot also holds the last key each table gave (SQLite's `sqlite_sequence`, DAT-029): without it a rebuilt store would give the key of a deleted row again.
- **Acceptance criteria:** writing the same store twice gives identical files, on Linux and on Windows alike; one changed record changes one line; no file comes near GitHub's file size limit, by a margin the plan states; the folder is written completely or not at all; internal notes are included (this is the store, not the published data) and the folder says so.
- **Tests required:** unit tests of the ordering and the encoding; integration tests against a real SQLite file with every table filled, comparing bytes across two writes and across the two machines by hash; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### DAT-020 – Snapshot: the store rebuilt from text files
- **Status:** NOT STARTED
- **Objective:** A store rebuilt from its snapshot is the same store, and the round trip is proven.
- **Description:** A command builds a new store from a snapshot folder: the schema is brought to the snapshot's version, the records are loaded, and the schema is then brought to the newest version. Every file is checked against its hash first. A snapshot that is damaged, incomplete or newer than the code is refused whole. Every row is stored with the key it had, and every table goes on counting from the last key it gave before the snapshot was made (DAT-029), so that no key is given twice across a rebuild.
- **Acceptance criteria:** store → snapshot → store → snapshot gives identical snapshot files; every table, key and history row survives; a row deleted before the snapshot does not get its key given again after the rebuild; foreign keys hold in the rebuilt store; a changed, missing or extra file is refused in plain words and no store is left behind; a snapshot of an older schema is rebuilt and migrated.
- **Tests required:** integration tests against real SQLite files with every table filled, including a snapshot made at an earlier schema version; damaged snapshots; the two commands run for real; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### PUB-001 – Published data layout and manifest of files
- **Status:** NOT STARTED
- **Objective:** The published data has a fixed layout, and the manifest lists every file with its hash, so the browser can tell exactly what it should receive.
- **Description:** The layout of the published folder is decided and documented (`ARCHITECTURE.md` §6): which files exist, how they are named so that a changed file has a new address, and the format version. The manifest gains the list of files with size and content hash, and record counts. The export writes through the store for the first time; with an empty store it publishes the manifest and nothing else. The frontend's manifest reader accepts the new format and still refuses one it does not know.
- **Acceptance criteria:** the manifest lists exactly the files in the folder, with correct sizes and hashes; a file not listed or a listed file missing fails the export; the format version changes and the frontend refuses the old one in plain words; the check of the published site (FND-035) still passes after deployment.
- **Tests required:** unit tests of the manifest model; integration tests of the export against a real store; frontend unit tests of the reader; browser tests against freshly exported data; planted defects; the full run of all gates on both machines; the run for `main` with its deployment and the check of the published site.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### PUB-002 – Data contract: one schema for both sides
- **Status:** NOT STARTED
- **Objective:** What the pipeline publishes and what the frontend expects are the same thing by construction.
- **Description:** A JSON Schema is generated from the export's Pydantic models and committed; the frontend's types are generated from that schema and committed. A gate fails when either is out of date, and the frontend checks the manifest it receives against the schema's rules, not against hand-written ones.
- **Acceptance criteria:** changing an export model without regenerating fails a gate, on both machines, with a message that names the command to run; the generated files are identical on Linux and on Windows; the frontend refuses a manifest that breaks the schema.
- **Tests required:** unit tests on both sides; a gate test with a deliberately stale schema; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### PUB-003 – Countries file
- **Status:** NOT STARTED
- **Objective:** The countries in the store are published for the browser.
- **Description:** The export writes one file with the countries that have at least one published record or are needed to name one, in a fixed order, listed in the manifest and checked against the contract. Internal fields stay in the store.
- **Acceptance criteria:** the file holds exactly those countries, each with its codes and name; it is listed in the manifest with the right hash; the same store gives the same bytes; with no countries the file is not written and the manifest says so.
- **Tests required:** integration tests of the export against a real store; contract validation; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### PUB-004 – Track list files
- **Status:** NOT STARTED
- **Objective:** The browser can list tracks country by country without downloading them all.
- **Description:** The export writes track lists in chunks by country, each chunk under a size the plan states, with the fields a list needs (name, place, position, disciplines, status) and a pointer to the detail file. Only tracks whose verification status allows publication are exported.
- **Acceptance criteria:** every publishable track is in exactly one chunk; no chunk exceeds the stated size; a track that is not publishable is in none; chunks and their order are the same for the same store; every chunk passes the contract.
- **Tests required:** integration tests of the export against a real store with generated tracks (used only in tests, never published); contract validation; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### PUB-005 – Track detail files
- **Status:** NOT STARTED
- **Objective:** Everything publishable about one track is in one small file the browser fetches when the track is opened.
- **Description:** The export writes one detail file per track (or per small group, if the trial shows too many files): the track's fields, its other names, its organisation, media references that may be shown, and for every value its source and how far it is verified. Text from sources is exported as text and nothing else.
- **Acceptance criteria:** a detail file holds exactly the publishable fields; every value names its source; internal notes, review items and raw responses appear in no file (a test searches the whole published folder for marker values planted in them); markup in a source's text is exported as inert text.
- **Tests required:** integration tests of the export against a real store; a leak test with planted markers; contract validation; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### PUB-006 – Map tile files
- **Status:** NOT STARTED
- **Objective:** The globe can load only the markers in view: tracks are published per map tile and zoom level.
- **Description:** The export writes tile files in a standard tile scheme chosen and documented in the planner's trial: at close zoom levels the tracks themselves, at wide zoom levels counts per cell, computed at export time. Empty tiles are not written, and the manifest tells the browser which exist.
- **Acceptance criteria:** every publishable track with a position is in exactly one tile at each close zoom level; the counts at each wide level add up to the number of tracks; tracks at the poles and at the 180th meridian land in the right tile; no tile exceeds the stated size; the same store gives the same bytes.
- **Tests required:** unit tests of the tile arithmetic against published reference values; integration tests of the export against a real store with generated positions (tests only); contract validation; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### PUB-007 – Export validation
- **Status:** NOT STARTED
- **Objective:** Nothing is published that breaks the contract or carries something internal.
- **Description:** The export ends with a check of the whole published folder: every file is listed in the manifest and matches its hash, every file passes the contract, sizes are within their limits, and no internal field is present. A failure stops the export before anything replaces the previous published data, and the deployment job runs the same check.
- **Acceptance criteria:** a file that breaks the contract, an unlisted file, a wrong hash, an oversized file and a planted internal value each stop the export with a message naming the file; the previous published folder is untouched after a failed export; the gates and the deployment both run the check.
- **Tests required:** integration tests of each failure against a real store and folder; repository checks that the workflow runs the check; planted defects; the full run of all gates on both machines; the run for `main` with its deployment.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### PUB-008 – Frontend data access layer
- **Status:** NOT STARTED
- **Objective:** The frontend has one way to fetch published files: checked against the manifest, kept while the page is open, and honest about loading and failure.
- **Description:** A data module in the frontend: it asks for a file by the name the manifest gives, checks what arrives against the contract, keeps what it has loaded for the visit, never asks twice for the same file at once, and gives every caller the same three states (loading, loaded, failed) with a friendly message. The countries file is its first user, shown nowhere yet; the first screen that uses it comes with the track directory.
- **Acceptance criteria:** a file is fetched once however many parts of the page ask for it; a file that breaks the contract or is not in the manifest is a failure, not data; a failed request can be tried again; nothing outside the site's own data folder is ever requested.
- **Tests required:** frontend unit tests with a stand-in fetch; browser tests against freshly exported data from a real store, including a missing and a damaged file; planted defects; the full run of all gates on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

---

# Roadmap – Phases 3 to 13

Ordered by dependency. Every item is one task and will get a full entry like
those above before its phase starts.

## Phase 3 – Interactive 3D Earth

- GLB-001 Install CesiumJS and wire its static assets into the build
- GLB-002 Globe component displays the Earth (bundled offline imagery)
- GLB-003 Browser verification of Earth rendering (WebGL pixel checks)
- GLB-004 Globe loading and failure states (including no-WebGL message)
- GLB-005 Camera rotation by drag
- GLB-006 Mouse-wheel zoom with sensible limits
- GLB-007 Panning
- GLB-008 Tilt and perspective
- GLB-009 Keyboard navigation
- GLB-010 On-screen controls: zoom in/out, north-up, home view
- GLB-011 Smooth fly-to camera transitions
- GLB-012 Imagery provider research with verified licence terms (documented)
- GLB-013 Configurable imagery provider registry
- GLB-014 Satellite imagery as default provider
- GLB-015 Imagery attribution display
- GLB-016 Terrain provider research and configurable terrain
- GLB-017 Country and regional boundaries layer
- GLB-018 Geographic labels
- GLB-019 Full-screen exploration mode
- GLB-020 Shareable camera position in the URL
- GLB-021 Worldwide navigation regression suite (globe to circuit-level zoom)

## Phase 4 – Geographic marker system

- MRK-001 Map tile loader (published tiles for the area in view)
- MRK-002 One marker rendered from published data
- MRK-003 Marker position accuracy check against known coordinates
- MRK-004 Marker category icons
- MRK-005 Marker selection
- MRK-006 Details panel opens for the selected marker
- MRK-007 Expandable sections in the details panel
- MRK-008 Viewport-aware tile loading and unloading
- MRK-009 Pre-computed clusters in wide-zoom tiles (export)
- MRK-010 Cluster rendering and zoom-to-expand
- MRK-011 Marker category filters
- MRK-012 Terrain-aware marker placement and large-dataset performance test

## Phase 5 – Track directory

- TRK-001 Track source research and licensing (OpenStreetMap, Wikidata, others)
- TRK-002 Source adapter interface and contract tests
- TRK-003 Polite HTTP client (identifying User-Agent, timeouts, bounded retries)
- TRK-004 robots.txt policy check
- TRK-005 Per-domain rate limiter
- TRK-006 Response cache and conditional requests
- TRK-007 HTML/JSON parsing toolkit decision (includes the Scrapling evaluation)
- TRK-008 First track adapter: parsing from recorded fixtures
- TRK-009 Track validation rules
- TRK-010 Track import pipeline with provenance and collection-run records
- TRK-011 Track duplicate detection (proximity and name similarity) feeding the review queue
- TRK-012 Initial import: United Kingdom, with accuracy sampling
- TRK-013 Initial import: Europe
- TRK-014 Initial import: United States and Canada
- TRK-015 Initial import: rest of world
- TRK-016 Track search index (published files, searched in the browser)
- TRK-017 Track list and search in the left panel
- TRK-018 Track details panel
- TRK-019 Track outline geometry where a reliable source exists
- TRK-020 Geographic accuracy validation report

## Phase 6 – Event collection

- EVT-001 Events table and status model
- EVT-002 Racing classes table
- EVT-003 Event–track and event–organiser links
- EVT-004 Published event files: list, detail, by month
- EVT-005 Event source research and licensing
- EVT-006 First event calendar adapter (fixtures)
- EVT-007 Event validation and duplicate detection
- EVT-008 Event import pipeline
- EVT-009 Event status transitions (upcoming, underway, completed, cancelled, postponed)
- EVT-010 Event markers on the globe
- EVT-011 Event details panel
- EVT-012 Upcoming events list with date filter
- EVT-013 Events shown in the track panel
- EVT-014 Additional event adapters, one task per source

## Phase 7 – Championships

- CHP-001 Championships table
- CHP-002 Championship seasons table
- CHP-003 Championship rounds table linked to events
- CHP-004 Championship classes
- CHP-005 Published standings tables (per season, never overwritten)
- CHP-006 Published championship files
- CHP-007 Championship source research and licensing
- CHP-008 First championship calendar adapter
- CHP-009 First standings adapter
- CHP-010 Championship details panel (calendar, rounds, standings)
- CHP-011 Round locations on the globe
- CHP-012 Previous champions and historical seasons
- CHP-013 Additional championship adapters, one task per source

## Phase 8 – Race results

- RES-001 Riders table (minimal identity) and rider aliases
- RES-002 Teams and manufacturers tables
- RES-003 Races and motos tables
- RES-004 Race entries table
- RES-005 Moto results table (position, time, laps, points, DNF/DNS/DSQ)
- RES-006 Overall event results table, kept separate from moto results
- RES-007 Published results files
- RES-008 Rider identity matching rules and review queue integration
- RES-009 Results source research and licensing
- RES-010 First results adapter (fixtures)
- RES-011 Results validation rules
- RES-012 Results import pipeline
- RES-013 Results views in event, track and championship panels
- RES-014 Historical results archive adapters, one task per source

## Phase 9 – Riders and teams

- RDR-001 Rider profile fields and published files
- RDR-002 Rider career records query
- RDR-003 Rider statistics (wins, podiums, points) from stored results only
- RDR-004 Rider details panel
- RDR-005 Team profile fields and published files
- RDR-006 Team details panel
- RDR-007 Manufacturers and bikes
- RDR-008 Rider–team–season history
- RDR-009 Rider list and browse view
- RDR-010 Team list and browse view
- RDR-011 Duplicate rider merge tool (confirmed merges only)
- RDR-012 Rider and team data validation report

## Phase 10 – Automated collection and administration

- COL-001 Pipeline run command: collect, validate, store and export in one run
- COL-002 Source registry: scheduling fields and due-source query
- COL-003 Scheduled daily run (GitHub Actions) that publishes the updated site
- COL-004 Source availability check
- COL-005 Change detection and incremental update
- COL-006 Failure isolation between adapters
- COL-007 Retry policy and job history
- COL-008 Recovery after interrupted runs
- COL-009 Source health and reliability scoring
- COL-010 Cross-source duplicate detection pass
- COL-011 Source discovery: candidate queue with crawl-scope limits
- COL-012 Source validation and activation workflow
- COL-013 Collection logging and run reports
- COL-014 Running the collection from the owner's Windows PC (for sources that refuse hosted runners)
- ADM-001 Administration model: decisions as reviewed files in the repository
- ADM-002 Data statistics page
- ADM-003 Source health page
- ADM-004 Enable/disable a source (configuration file applied by the next run)
- ADM-005 Start a manual run and retry failed sources (from GitHub Actions)
- ADM-006 Review queue report and recorded decisions
- ADM-007 Correct a record with history
- ADM-008 Merge confirmed duplicates
- ADM-009 Collection log page
- ADM-010 Scan schedule configuration

## Phase 11 – Search and comparison

- SRC-001 Search index strategy (index files built at export, searched in the browser)
- SRC-002 Global search index export across entity types
- SRC-003 Search box with grouped results
- SRC-004 Selecting a result flies the globe to it
- SRC-005 Filter model: country, date range, discipline, championship, class, status
- SRC-006 Filters applied to map tiles
- SRC-007 Filter controls that update the globe
- SRC-008 Rider, team and track filters
- CMP-001 Rider comparison data (from published rider files)
- CMP-002 Rider comparison view with head-to-head
- CMP-003 Team comparison
- CMP-004 Championship and season comparison
- CMP-005 Incomplete-data explanations in comparisons
- CMP-006 Statistics charts

## Phase 12 – News and historical expansion

- NWS-001 News articles table (headline, summary, link; no full text)
- NWS-002 News source research and licensing
- NWS-003 RSS/feed adapter
- NWS-004 Published news files
- NWS-005 News feed view
- NWS-006 News linked to countries, championships and events
- HIS-001 Historical record classification (official, independent, reconstructed, unverified)
- HIS-002 Historical archive source research
- HIS-003 Historical adapters, one task per source
- HIS-004 Additional disciplines: enduro and hard enduro venues and events

## Phase 13 – Performance and deployment

- PRF-001 Pipeline and export performance review
- PRF-002 Published file caching and cache-busting review
- PRF-003 Globe performance budget with large datasets
- PRF-004 Browser memory test over a long session
- PRF-005 Dependency vulnerability checks in the check runner
- PRF-006 Security review
- DEP-001 Published site size, traffic and imagery-licence review against GitHub Pages limits
- DEP-002 Custom domain (optional, owner's decision)
- DEP-003 Data backup and restore procedure
- DEP-004 Operations guide and first public release
