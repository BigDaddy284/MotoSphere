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
| 1 | Foundation (FND) | 42 | 40 |
| 2 | Data store and published data (DAT, PUB) | 28 | 0 |
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

**Current task:** FND-042 – Phones: the layout follows the visible height.

**Hosting decision (owner, 2026-11-17):** GitHub Pages only, with no server.
Scheduled jobs collect the data and publish it as files that the globe reads
(`ARCHITECTURE.md`). Tasks FND-001 to FND-013 were planned before that
decision; everything after FND-013 follows it. Three foundation tasks were
added for it (FND-020 to FND-022).

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
browser.

Added tasks are listed where they fall in dependency order, so task numbers
in Phase 1 are not strictly ascending.

Phase 1 is specified in full below. Phases 2–13 are listed as an ordered
roadmap of named tasks; each phase is expanded into full task entries (with
acceptance criteria and required tests) before its first task starts, and any
task that turns out too large to test thoroughly is split further at that
point. Task counts above therefore grow rather than shrink.

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
- **Status:** NOT STARTED
- **Objective:** On a phone the layout is as tall as the part of the screen the browser really shows, so its lower edge is never under the browser's own bars.
- **Description:** A phone's browser shows and hides its own bars, and the height the layout uses today is the tallest of the two. The layout asks for the height that follows the bars, and keeps today's as the fallback for a browser that does not know it. Added by PLAN-008 as part of FND-040; a task of its own since PLAN-009, because the test browser has no bars that come and go: there the two heights are equal, so the tests can show that nothing changed and that the style sheet asks for the right height, and only a real phone can show the rest.
- **Acceptance criteria:** the layout's style sheet asks for the height that follows the browser's bars, after the plain height as its fallback, and the page's own minimum height does the same; in the test browser the layout is exactly as tall as the screen at every tested size and the page itself does not scroll; every existing test passes unchanged. The effect on a real phone is confirmed by the owner on the published site and recorded as such, not as a test result.
- **Tests required:** unit tests that read the style sheets; browser tests at phone and desktop sizes that measure the layout's height; planted defects; the full run on both machines.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### FND-019 – Windows scripts for local use
- **Status:** NOT STARTED
- **Objective:** Use MotoSphere on Windows 11 without GitHub, with one command per job.
- **Description:** PowerShell scripts to set up the tools, run all checks, and export the data and open the application locally (and stop it again); README documents prerequisites, first-time setup and each command.
- **Acceptance criteria:** on a real Windows 11 machine, a clean checkout reaches a working application in the browser by following the README only; stopping leaves no process behind.
- **Tests required:** script checks runnable anywhere (PowerShell syntax parse, documented commands exist); end-to-end verification on Windows 11. If no Windows machine is reachable the task is `BLOCKED – EXTERNAL DEPENDENCY`, not passed.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

---

# Roadmap – Phases 2 to 13

Ordered by dependency. Every item is one task and will get a full entry like
those above before its phase starts.

## Phase 2 – Data store and published data

Data store
- DAT-001 Data store research and decision record (SQLite features on Windows and Linux, keeping data between scheduled runs, size limits)
- DAT-002 Store settings and engine/session module (SQLite, foreign keys enforced)
- DAT-003 Isolated test-database fixture (real SQLite file per test)
- DAT-004 Schema migration infrastructure (upgrade and downgrade tested)
- DAT-005 Model conventions: keys, timestamps, constraint naming
- DAT-006 Information sources table (source registry core)
- DAT-007 Data collection runs table
- DAT-008 Provenance columns and confidence/verification enumerations
- DAT-009 Record change-history table
- DAT-010 Review queue table
- DAT-011 Countries table
- DAT-012 Countries reference data import (ISO 3166, licence verified)
- DAT-013 Regions table
- DAT-014 Racing disciplines table and reference data
- DAT-015 Organisations table (governing bodies, clubs, promoters)
- DAT-016 Tracks table with validated coordinates and bounding-box index
- DAT-017 Track aliases table
- DAT-018 Media references table
- DAT-019 Snapshot: write the store to deterministic text files
- DAT-020 Snapshot: rebuild the store from text files (round trip proven)

Published data
- PUB-001 Published data layout, versioning and manifest file list with content hashes
- PUB-002 Data contract: JSON Schema from the export models and generated frontend types
- PUB-003 Countries file
- PUB-004 Track list files (in chunks, by country)
- PUB-005 Track detail files
- PUB-006 Map tile files (tracks by tile and zoom level)
- PUB-007 Export validation (every published file checked against the contract; nothing internal exported)
- PUB-008 Frontend data access layer (loading, caching, error states)

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
