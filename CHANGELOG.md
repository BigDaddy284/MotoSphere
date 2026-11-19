# Changelog

All notable changes to this project are documented in this file. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Hosting model: GitHub Pages only, with no server. The architecture and task
  list were re-planned around a scheduled data pipeline and published data
  files (owner decision, 2026-11-17).
- Visual identity: the owner's Graphite theme and Sky Classic icon style are
  the design references (`docs/design/`).
- The application is served under `/MotoSphere/`, the path it has on GitHub
  Pages, in development and in the browser tests too; the development
  address is now <http://localhost:5173/MotoSphere/> (FND-022).

### Added

- Repository baseline: `.gitignore`, `.gitattributes`, `.editorconfig`,
  README, document stubs (DATA_SOURCES.md, DATABASE.md, TESTING.md,
  CHANGELOG.md) and the repository check suite in `tests/repo` (FND-001).
- Backend Python project skeleton (`backend/`): uv project with a committed
  lock file, `motosphere` package and pytest suite (FND-002).
- Backend linting and formatting with ruff, including security rules (FND-003).
- Backend static type checking with mypy in strict mode (FND-004).
- Backend settings module with environment variable and `.env` configuration
  (FND-005).
- Backend logging configuration: single line format with UTC timestamps and
  escaped line breaks (FND-006).
- API application factory and health endpoint `GET /api/health` (FND-007).
- `python -m motosphere` starts the API server (FND-008).
- Frontend project skeleton (`frontend/`): Vite, React and TypeScript in strict
  mode (FND-009).
- Frontend unit testing with Vitest and Testing Library (FND-010).
- Frontend linting with oxlint (React, accessibility and security rules) and
  formatting with Prettier (FND-011).
- Browser tests with Playwright against the built application, with an
  automatic page health check (FND-012).
- Dark theme design tokens and base styles, with automatic contrast checks
  (FND-013).
- The owner's Graphite theme: charcoal surfaces, sky-blue accent and Segoe UI
  font stack (FND-023).
- Application shell layout: top bar, sections panel, globe stage and details
  panel (FND-014).
- Section navigation: the nine sections listed in the sections panel,
  selectable by mouse or keyboard (FND-025).
- Collapsible side panels: buttons in the top bar close and open the sections
  and details panels, remembered for the session (FND-015).
- Current date in the top bar, in the language and time zone of the user's
  browser, changing at midnight (FND-026).
- Pipeline command line: `python -m motosphere <command>`, with a `version`
  command (FND-020).
- `export` command: writes the published data manifest, `manifest.json`,
  atomically and deterministically (FND-021).
- Application icon: the owner's approved design as the page icon, with a
  small version for browser tabs, an ICO fallback and a touch icon (FND-024).
- Frontend manifest reader: fetches and checks the published data manifest,
  with a plain result for every failure (FND-016).
- `npm run data`: exports the published data for local development; the
  browser tests run against freshly exported data (FND-027).
- Data status in the top bar: when the published data was updated, or that it
  is unavailable (FND-028).
- Browser tests can name the page problems they expect; the data status is
  tested with a missing manifest and a failed request (FND-029).
- `python scripts/check.py`: one command that runs every gate in order and
  reports which passed (FND-017).
- The check runner reports how many tests each gate ran and fails a gate when
  a test was skipped (FND-030).
- Lint, format and type gates for the Python files outside the pipeline
  (`scripts/`, `tests/`), run with the pipeline's locked tools (FND-031).
- Continuous integration: GitHub runs every gate on Linux for each pull
  request and each change to `main` (FND-018).
- Continuous integration also runs every gate on Windows (FND-032).
- `python scripts/audit.py`: the dependency audit, with exceptions that are
  recorded with a reason and a review date (FND-033).
- Deployment: every change to `main` that passes all gates on both machines
  is published on GitHub Pages, at
  <https://bigdaddy284.github.io/MotoSphere/> (FND-034).
- `python scripts/live.py <site.tar> <address>`: compares a published site
  with the site that was built, file by file, and names what differs
  (FND-035).
- After each deployment a job runs that comparison against the published
  site, so a deployment that leaves the site broken or stale fails the run
  (FND-037).
- Narrow screens (under 900 pixels wide: a phone, or a tablet held upright):
  the globe stage keeps the whole width, and an open side panel lies over
  it (FND-038).
- On a narrow screen the top bar takes the lines it needs, so that nothing
  in it is cut off: the name between the two buttons, then the data status
  and the date; the tagline is not shown there (FND-039).
- On a narrow screen the page opens with both side panels closed and the
  globe stage in view, only one panel is open at a time, and loading the
  page again closes them (FND-040).
- On a touch screen the buttons in the top bar and the sections are 44
  pixels tall, so that a finger can hit them; with a mouse nothing changes
  (FND-041).
- The layout is as tall as the part of the screen the browser really
  shows, so that on a phone its lower edge is not under the browser's own
  bars (FND-042).
- `python scripts/tools.py` says whether a computer has the tools MotoSphere
  needs: the version of each it found, and where to get one that is missing,
  too old or broken (FND-019).
- The data store's first decisions (`DATABASE.md`): what it relies on in
  SQLite, held by `motosphere.db.sqlite` and its tests on every machine the
  gates run on, and where the store is kept between scheduled runs
  (DAT-001).
- A setting for where the data store's file is, `MOTOSPHERE_STORE_PATH`
  (default `store/motosphere.sqlite3` in the `backend` folder). Git ignores
  that folder and every `*.sqlite3` file (DAT-002).
- The function that opens the data store, `open_store`, and SQLAlchemy 2 as
  the pipeline's way to its database: foreign keys enforced on every
  connection, failed work taken back as a whole, no connection left open,
  and a plain sentence when the store cannot be opened (DAT-021).
- Units of work, `unit_of_work`: what the pipeline writes to the data store
  is kept as a whole when the work ends and taken back as a whole when it
  fails, and a unit cannot commit part-way (DAT-022).
- For the backend's tests, a fixture that gives every test a real data
  store of its own and reports a test that leaves a connection to it open
  (DAT-003).
- The migration runner, `migrate`: the data store's schema is built and
  changed only by numbered migrations, each kept as a whole with the
  store's new version or not at all, and a store the code does not know is
  refused in plain words. No new package (DAT-004).
- The mark of a MotoSphere data store: the first migration marks the
  store's file as MotoSphere's, and a file that has anything in it and not
  that mark is never migrated. It is refused in plain words and left byte
  for byte as it was (DAT-023).
- The command `python -m motosphere migrate`: it brings the data store the
  settings name to the newest schema, makes the store if it is not there,
  and says in one sentence what it did. It is the first command that uses
  the store (DAT-024).
- `pending`: it says which migrations a data store lacks and writes
  nothing. `migrate` applies exactly those, and both refuse the same
  stores in the same words (DAT-027).
- The command `python -m motosphere schema`: it says in one sentence
  whether the data store is up to date, how many migrations it lacks, or
  that there is no store, and changes nothing. A store `migrate` would
  refuse is refused in the same words (DAT-025).
- The base of all models, `Base`: every table is strict, its columns have
  the types a strict table takes, and its constraints and indexes are
  named by one rule. `broken_rules` says which tables break a rule
  (DAT-005).
- Times in the data store, `motosphere.db.times`: a time is stored as
  text in one form, in UTC with its offset written out and the whole
  fraction of its second (`2026-11-19T08:26:04.123456+00:00`), so the
  order of the texts is the order of the times. A time without an offset
  is refused, and what comes back is an aware UTC time. A model's
  `datetime` column gets this type from `Base` (DAT-028).
- The key of every table: one whole-number column, `id`, which a model
  gets from `Base` without naming it, and whose values SQLite never gives
  twice, also not after a row is deleted. `broken_rules` names a table
  without it (DAT-029).
- When a row was first stored and when it was last changed: the columns
  `created_at` and `updated_at`, which a model gets from `Base` without
  naming them. The store's code sets them from the store's clock, `now()`
  in `motosphere.db.times`: both to the same moment for a new row, and
  `updated_at` anew for a row that is changed (DAT-031).
- `broken_rules` names a table without the two times every table has:
  one whose `created_at` or `updated_at` is missing, or is not as `Base`
  gives it (DAT-032).
- Text that must not be empty, `motosphere.db.texts`: a model says
  `Mapped[NotEmpty]` of a column, and its table gets a check, named by
  the naming rule, by which SQLite itself refuses text with no characters
  and text with nothing but white space, whoever writes the row. Text
  that is not empty is stored as it was given (DAT-030).
- `broken_rules` names a column whose text must not be empty and whose
  table does not have the check for it: a column of a table made without
  a model, and one that a subclass of a model adds to its parent's table
  (DAT-033).
- A test that holds the models and the migrations together, and
  `differences` in `motosphere.db.compare`, which says in plain words
  where the schema the models describe and the one the migrations build
  differ: it compares the statements SQLite keeps for each table and
  index, word for word (DAT-026).
- A column type can bring the check for its column, `WithItsCheck` in
  `motosphere.db.checks`: `Base` gives that check to the table of every
  model with such a column, and `broken_rules` names a column whose
  table is without it, in the type's own words. Text that must not be
  empty is the first such type, and the next needs no change to either
  (DAT-034).

### Removed

- The API server and its health endpoint, the `MOTOSPHERE_API_HOST` and
  `MOTOSPHERE_API_PORT` settings and the `fastapi`, `uvicorn` and `httpx2`
  dependencies, following the GitHub Pages hosting decision (FND-020).
- The dependency audit's one recorded exception, for a slow pattern match
  in picomatch (GHSA-fc5q-39xc-vjpf, recorded on 2026-11-17): a day later
  `npm audit` no longer reported the advisory, and the audit failed until
  the exception was taken out. No exception is recorded now (FND-036).

### Fixed

- A browser test that could fail by chance. The test of "Loading data…"
  expected the request for the data to have arrived as soon as the page
  said so, and the page says so before it asks. The test now waits for the
  request (FND-043).
