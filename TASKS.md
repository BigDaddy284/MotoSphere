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
| 1 | Foundation (FND) | 19 | 9 |
| 2 | Database and API (DB, API) | 28 | 0 |
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

**Current task:** FND-010 – Frontend unit testing.

Phase 1 is specified in full below. Phases 2–13 are listed as an ordered
roadmap of named tasks; each phase is expanded into full task entries (with
acceptance criteria and required tests) before its first task starts, and any
task that turns out too large to test thoroughly is split further at that
point. Task counts above therefore grow rather than shrink.

---

# Phase 1 – Foundation (FND)

Goal: an empty-but-real application. A backend that starts and answers a
health check, a frontend shell with the final layout regions, every quality
gate wired up, one command that runs all gates, and documented start/stop on
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
- **Status:** IN PROGRESS
- **Objective:** Component tests run with one command.
- **Description:** Add Vitest, jsdom and Testing Library; `npm test` runs the suite once and exits. First tests cover `App` and the entry point.
- **Acceptance criteria:**
  1. `npm test` runs once, passes the five planned tests and exits 0; it exits non-zero when an assertion fails.
  2. Tests query the page the way a user perceives it (roles and text).
  3. Test files are type-checked by `npm run typecheck` and are not part of the production bundle.
  4. README, TESTING.md and CHANGELOG.md describe the new gate; all earlier gates still pass.
- **Tests required:** frontend unit tests (5); frontend type check; frontend build; repository checks (9); backend gates unchanged (55 tests).
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –
- **Plan:** `docs/plans/FND-010.md`

### FND-011 – Frontend linting and formatting
- **Status:** NOT STARTED
- **Objective:** Enforce one code style for TypeScript automatically.
- **Description:** ESLint (typescript-eslint, React hooks rules) and Prettier with `npm run lint` and `npm run format:check`.
- **Acceptance criteria:** both commands pass; a deliberate violation is reported, then removed.
- **Tests required:** lint, format check, plus all earlier frontend gates.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### FND-012 – Browser test infrastructure
- **Status:** NOT STARTED
- **Objective:** Verify the real built application in a real browser.
- **Description:** Add Playwright (Chromium) under `frontend/e2e/`; the test run builds the app, serves the build and opens it.
- **Acceptance criteria:** `npm run e2e` passes headlessly; the smoke test confirms the page title, the visible application name and zero console errors.
- **Tests required:** Playwright smoke test; all earlier gates.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### FND-013 – Dark theme design tokens
- **Status:** NOT STARTED
- **Objective:** One source of truth for colours, type and spacing.
- **Description:** CSS custom properties for the dark motorsport theme (surfaces, text, one restrained accent, status colours, spacing, radii, type scale) and base styles (reset, fonts, focus rings).
- **Acceptance criteria:** tokens defined once and used by `App`; text/background contrast meets WCAG AA (≥ 4.5:1) for body text; visible keyboard focus.
- **Tests required:** unit test computing contrast ratios from the token values; browser test asserting computed background/text colours.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### FND-014 – Application shell layout
- **Status:** NOT STARTED
- **Objective:** The final screen regions, with the globe area dominant.
- **Description:** Top bar (name, placeholder search slot, date, data-status slot), left navigation (Explore, Events, Tracks, Championships, Riders, Teams, Results, News, Statistics), centre stage reserved for the globe, right details panel. Semantic landmarks. No functionality behind the links yet.
- **Acceptance criteria:** all four regions render with accessible landmarks and names; the centre stage takes the largest share of the viewport at 1366×768 and 1920×1080; no page scrollbars at those sizes.
- **Tests required:** component tests for regions and nav items; browser test measuring region sizes at both viewports.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### FND-015 – Collapsible side panels
- **Status:** NOT STARTED
- **Objective:** Let the user give the globe the whole screen.
- **Description:** Collapse/expand controls for the left and right panels, keyboard accessible, state remembered for the session.
- **Acceptance criteria:** each panel collapses and expands by mouse and keyboard; `aria-expanded` reflects state; the centre stage grows when a panel collapses.
- **Tests required:** component tests for state and ARIA; browser test measuring centre-stage width before and after.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### FND-016 – Frontend API client and backend status
- **Status:** NOT STARTED
- **Objective:** Prove the frontend and backend talk to each other.
- **Description:** A small typed API client, a Vite dev proxy for `/api`, and a status indicator in the top bar driven by `GET /api/health` with loading, connected and unavailable states in plain language.
- **Acceptance criteria:** indicator shows each of the three states correctly; a failed request shows a friendly message and never an unhandled error.
- **Tests required:** unit tests with a mocked fetch for all three states; a browser test against the real backend process (connected) and with the backend stopped (unavailable).
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### FND-017 – Unified check runner
- **Status:** NOT STARTED
- **Objective:** One command that runs every gate and reports counts.
- **Description:** `python scripts/check.py` (stdlib only) runs repo checks, lint and format checks for root-level Python (`tests/repo`, `scripts/`), backend ruff/mypy/pytest, frontend lint/typecheck/unit/build and browser tests, in order, and prints a per-gate and overall pass/fail summary. Non-zero exit if any gate fails. Options to run a single gate.
- **Acceptance criteria:** all gates run from a clean checkout on Linux and Windows; a failing gate makes the exit code non-zero and is named in the summary; TESTING.md documents the command.
- **Tests required:** unit tests for the runner's result handling using stub commands; one full real run.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### FND-018 – Continuous integration
- **Status:** NOT STARTED
- **Objective:** Every pull request is checked automatically.
- **Description:** A GitHub Actions workflow that installs Python, uv and Node, then runs `python scripts/check.py` on Linux and Windows runners for pull requests and pushes to `main`.
- **Acceptance criteria:** the workflow runs on the task's own pull request and passes on both operating systems.
- **Tests required:** the workflow run itself (both jobs green); local check runner still passes.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

### FND-019 – Windows start and stop scripts
- **Status:** NOT STARTED
- **Objective:** Start and stop the whole application on Windows 11 with one command each.
- **Description:** `scripts/start.ps1` and `scripts/stop.ps1` start/stop the API and the frontend dev server; README documents prerequisites, first-time setup, start, stop and how to run the checks.
- **Acceptance criteria:** on a real Windows 11 machine, a clean checkout reaches a working app in the browser by following the README only; stop leaves no process behind.
- **Tests required:** script checks runnable anywhere (PowerShell syntax parse, documented commands exist); end-to-end verification on Windows 11. If no Windows machine is reachable the task is `BLOCKED – EXTERNAL DEPENDENCY`, not passed.
- **Tests executed:** –
- **Passed / Failed:** – / –
- **Verification status:** Not verified
- **Commit:** –

---

# Roadmap – Phases 2 to 13

Ordered by dependency. Every item is one task and will get a full entry like
those above before its phase starts.

## Phase 2 – Database and API

Database foundation
- DB-001 PostgreSQL + PostGIS local setup (Linux/CI script, Windows script and guide)
- DB-002 Database settings and engine/session module
- DB-003 Isolated test-database fixture (real PostgreSQL, rolled back per test)
- DB-004 Alembic migration infrastructure (upgrade/downgrade tested)
- DB-005 Enable PostGIS, pg_trgm and unaccent by migration
- DB-006 Health endpoint reports database status
- DB-007 Model conventions: keys, timestamps, constraint naming
- DB-008 Information sources table (source registry core)
- DB-009 Data collection runs table
- DB-010 Provenance columns and confidence/verification enumerations
- DB-011 Record change-history table
- DB-012 Review queue table
- DB-013 Countries table
- DB-014 Countries reference data import (ISO 3166, licence verified)
- DB-015 Regions table
- DB-016 Racing disciplines table and reference data
- DB-017 Organisations table (governing bodies, clubs, promoters)
- DB-018 Tracks table with geographic point and spatial index
- DB-019 Track aliases table
- DB-020 Media references table

API foundation
- API-001 Versioned router `/api/v1` and uniform error format
- API-002 Pagination conventions
- API-003 Countries list endpoint
- API-004 Tracks list endpoint (paginated, filter by country)
- API-005 Track detail endpoint
- API-006 Tracks within a bounding box (spatial query)
- API-007 OpenAPI contract check and generated frontend types
- API-008 API security baseline (CORS, limits, headers, admin token guard)

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

- MRK-001 Map features endpoint (GeoJSON by bounding box)
- MRK-002 One marker rendered from API data
- MRK-003 Marker position accuracy check against known coordinates
- MRK-004 Marker category icons
- MRK-005 Marker selection
- MRK-006 Details panel opens for the selected marker
- MRK-007 Expandable sections in the details panel
- MRK-008 Viewport-aware marker loading
- MRK-009 Server-side clustering endpoint
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
- TRK-016 Track search endpoint
- TRK-017 Track list and search in the left panel
- TRK-018 Track details panel
- TRK-019 Track outline geometry where a reliable source exists
- TRK-020 Geographic accuracy validation report

## Phase 6 – Event collection

- EVT-001 Events table and status model
- EVT-002 Racing classes table
- EVT-003 Event–track and event–organiser links
- EVT-004 Events API: list, detail, by date range
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
- CHP-006 Championships API
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
- RES-007 Results API
- RES-008 Rider identity matching rules and review queue integration
- RES-009 Results source research and licensing
- RES-010 First results adapter (fixtures)
- RES-011 Results validation rules
- RES-012 Results import pipeline
- RES-013 Results views in event, track and championship panels
- RES-014 Historical results archive adapters, one task per source

## Phase 9 – Riders and teams

- RDR-001 Rider profile fields and API
- RDR-002 Rider career records query
- RDR-003 Rider statistics (wins, podiums, points) from stored results only
- RDR-004 Rider details panel
- RDR-005 Team profile fields and API
- RDR-006 Team details panel
- RDR-007 Manufacturers and bikes
- RDR-008 Rider–team–season history
- RDR-009 Rider list and browse view
- RDR-010 Team list and browse view
- RDR-011 Duplicate rider merge tool (confirmed merges only)
- RDR-012 Rider and team data validation report

## Phase 10 – Automated collection and administration

- COL-001 Worker process entry point
- COL-002 Source registry: scheduling fields and due-source query
- COL-003 Scheduler: daily scan loop
- COL-004 Source availability check
- COL-005 Change detection and incremental update
- COL-006 Failure isolation between adapters
- COL-007 Retry policy and job history
- COL-008 Recovery after interrupted jobs
- COL-009 Source health and reliability scoring
- COL-010 Cross-source duplicate detection pass
- COL-011 Source discovery: candidate queue with crawl-scope limits
- COL-012 Source validation and activation workflow
- COL-013 Collection logging and run reports
- COL-014 Windows scheduled start for the worker
- ADM-001 Admin authentication guard
- ADM-002 Database statistics endpoint and view
- ADM-003 Source health view
- ADM-004 Enable/disable a source
- ADM-005 Trigger a manual scan and retry failed jobs
- ADM-006 Review queue view and decisions
- ADM-007 Correct a record with history
- ADM-008 Merge confirmed duplicates
- ADM-009 Collection log viewer
- ADM-010 Scan schedule configuration

## Phase 11 – Search and comparison

- SRC-001 Search index strategy (PostgreSQL full-text and trigram)
- SRC-002 Global search endpoint across entity types
- SRC-003 Search box with grouped results
- SRC-004 Selecting a result flies the globe to it
- SRC-005 Filter model: country, date range, discipline, championship, class, status
- SRC-006 Filters applied to map endpoints
- SRC-007 Filter controls that update the globe
- SRC-008 Rider, team and track filters
- CMP-001 Rider comparison query
- CMP-002 Rider comparison view with head-to-head
- CMP-003 Team comparison
- CMP-004 Championship and season comparison
- CMP-005 Incomplete-data explanations in comparisons
- CMP-006 Statistics charts

## Phase 12 – News and historical expansion

- NWS-001 News articles table (headline, summary, link; no full text)
- NWS-002 News source research and licensing
- NWS-003 RSS/feed adapter
- NWS-004 News API
- NWS-005 News feed view
- NWS-006 News linked to countries, championships and events
- HIS-001 Historical record classification (official, independent, reconstructed, unverified)
- HIS-002 Historical archive source research
- HIS-003 Historical adapters, one task per source
- HIS-004 Additional disciplines: enduro and hard enduro venues and events

## Phase 13 – Performance and deployment

- PRF-001 Query performance review and indexes
- PRF-002 API response caching
- PRF-003 Globe performance budget with large datasets
- PRF-004 Browser memory test over a long session
- PRF-005 Dependency vulnerability checks in the check runner
- PRF-006 Security review
- DEP-001 Hosting, storage and imagery-licence cost investigation
- DEP-002 Production configuration and build
- DEP-003 Backup and restore procedure
- DEP-004 Deployment guide and first hosted release
