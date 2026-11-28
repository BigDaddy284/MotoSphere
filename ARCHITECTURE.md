# MotoSphere – Architecture

This document records the technical architecture and the reasons behind each
important decision. Change it in the same commit as any change that
contradicts it.

**Naming.** The product is called **MotoSphere** ("The World of Motocross,
Connected."). That is its only name: documents, code, packages and UI text
all use MotoSphere.

**Hosting decision (owner, 2026-11-17).** MotoSphere is hosted on **GitHub
Pages only, with no server**. Scheduled jobs collect the data and publish it
as files that the globe reads. This replaces the server-based stack proposed
in DESIGN.md §13 (FastAPI service, PostgreSQL with PostGIS, long-running
worker). Where this document and DESIGN.md §13 differ, this document wins.
Everything else in DESIGN.md still applies: the real database, the collection
engine, provenance, accuracy rules and the interactive 3D Earth.

Status of this document: decisions marked **Decided** are binding for builders.
Decisions marked **Open** are settled by a named research task before any code
depends on them.

---

## 1. System overview

```
 Scheduled job (GitHub Actions, daily)        the owner's PC (same commands)
                    │                                   │
                    └───────────────┬───────────────────┘
                                    ▼
        Data pipeline (Python package `motosphere`, run as a command)
        collect ─► validate ─► store ─► export
           │                     │         │
           ▼                     ▼         ▼
   Public motocross     Data store     Published data files
   sources (polite      (SQLite,       (versioned JSON: manifest, map
   HTTP client)         with history   tiles, lists, details, search index)
                        and review                │
                        queue)                    │ deployed with the site
                                                  ▼
                            GitHub Pages (static files only)
                                                  │ HTTPS
                                                  ▼
                        Browser (React + TypeScript + CesiumJS)
```

Three pieces:

1. **Frontend** – a static single-page app. The globe dominates the screen.
   It only ever reads published files; it never talks to a server of ours.
2. **Data pipeline** – a command-line program, not a service. One run
   collects from the sources that are due, validates, updates the data store
   and exports the published files. It runs on a schedule in GitHub Actions
   and can be run by hand on Windows 11 with the same commands.
3. **Published data** – the contract between the two: versioned JSON files
   with a manifest. Nothing is scraped, computed or queried on a server
   during a user's visit, because there is no server.

What the owner accepted with this choice: search and map queries are limited
to what can be prepared in advance and done in the browser. There are no
user accounts and no live queries over the whole database.

## 2. Repository layout (Decided)

One repository, clear top-level separation:

```
MotoSphere/
├── backend/                 Python project (uv), package `motosphere`
│   ├── pyproject.toml
│   ├── src/motosphere/
│   │   ├── core/            settings, logging, shared utilities
│   │   ├── cli/             the `python -m motosphere` commands
│   │   ├── db/              engine, units of work, migrations, models
│   │   ├── reference/       lists that come with the project, and their readers
│   │   ├── geo/             coordinates, map tiles, clustering
│   │   ├── services/        business rules (validation, matching, history)
│   │   ├── collectors/      source adapter framework and adapters
│   │   ├── publish/         export models and writers for published files
│   │   └── admin/           review decisions and corrections
│   └── tests/               unit/ and integration/
├── frontend/                Vite + React + TypeScript project
│   ├── src/                 code, with unit tests next to it
│   └── e2e/                 Playwright browser tests
├── scripts/                 check scripts (Python, standard library only)
├── tests/repo/              repository-wide checks (stdlib only)
├── .github/workflows/       checks, scheduled collection, Pages deployment
├── docs/
│   ├── WORKFLOW.md          how tasks are planned, built, tested, merged
│   └── plans/               one implementation plan per task
└── CLAUDE.md DESIGN.md TASKS.md PROGRESS.md ARCHITECTURE.md
    DATA_SOURCES.md DATABASE.md TESTING.md CHANGELOG.md README.md
```

Directories are created by the task that first needs them, not in advance.
The directory keeps the name `backend/` although nothing in it is a server:
it is everything that runs behind the published site.

## 3. Frontend (Decided)

| Choice | Decision | Why |
|---|---|---|
| Framework | React + TypeScript (strict) | As proposed. Mature, typed, well supported by tooling. |
| Build tool | Vite | Fast, simple, first-class TypeScript, easy static asset handling for Cesium. |
| Globe | The Cesium engine (`@cesium/engine`) used directly behind a thin `Globe` component | Cesium is the right engine for a true 3D Earth with terrain and continuous zoom. The engine by itself and not the full `cesium` package, which adds a ready-made viewer (`@cesium/widgets`) whose controls MotoSphere does not use. The engine keeps its arithmetic (positions, angles, the shape of the Earth) in `@cesium/core` and asks that it be imported from there, so the project names that package too. No Resium wrapper: one less dependency that must track Cesium releases, and imperative camera control is simpler to test. Before anything of the globe is started, the stage asks the browser whether it gives a 3D picture of the kind the engine draws with (WebGL 2), on a drawing surface of its own that it gives back at once; where the browser gives none, the stage says so in the place of the globe (GLB-026, TESTING.md). The `Globe` component (`frontend/src/globe/Globe.tsx`) is one element of the page and one engine that draws in it for as long as the globe is shown. It names nothing of the engine: how the engine is loaded and started is handed to it, so the engine is loaded when a globe is shown and not with the page, and the component's unit tests run with a stand-in (GLB-027, TESTING.md). An engine that is started is handed a listener, and when the engine says that its first complete picture is drawn the component tells whoever shows the globe, once and only while the globe is shown (GLB-029). The real way to start the engine is one module, `frontend/src/globe/earth.ts`, and it is the only module of the application that brings the engine in: one widget of the engine in the component's element, which draws the Earth with the Natural Earth II pictures that come with the engine, from the folder of the site that holds the engine's files, and draws only when something has changed. It says that the Earth is drawn when no piece of it is waiting any more, and stopping it takes the widget away and gives the browser its 3D picture back. The page fetches that module when the stage shows the globe and not with the page, and the stage marks the globe as busy until the Earth is drawn (GLB-002, TESTING.md). |
| Data loading | TanStack Query over `fetch` of published files | Caching, cancellation and loading/error states for viewport-driven loading. Introduced by the first task that needs more than one file. |
| Styling | Plain CSS with design tokens (CSS custom properties) and CSS modules | No heavy UI kit. The owner's Graphite theme (see below) is kept consistent through our own tokens. |
| Unit tests | Vitest + Testing Library | Native to Vite. |
| Browser tests | Playwright (Chromium, software WebGL) | Real globe rendering and interaction can be verified headlessly. The tests of the globe are a project of their own, in a browser told to draw in software and one test at a time (FND-058, TESTING.md); every other browser test runs in a browser that gives a page no 3D picture (FND-059). A test reads what the page shows from outside the page, one pixel at a time, from a picture Playwright takes (FND-060). |
| Lint/format | oxlint + Prettier | oxlint has the React hooks, accessibility, import, Vitest and TypeScript rules built in as one dependency, and is what the current Vite template ships. ESLint was the first choice, but `typescript-eslint` depends on the older JavaScript compiler API and the project uses the native TypeScript 7 compiler. Type errors are covered by the type-check gate. |

**Visual identity (owner, 2026-11-17).** The owner supplied the look, and the
reference files are kept unchanged in `docs/design/`:

- **Graphite theme** (`docs/design/graphite-theme/`): soft charcoal greys
  with a sky-blue accent, and the Segoe UI font stack. Its colours become the
  design tokens in task FND-023. Status colours (success, warning, danger,
  info) are ours, because the theme has none.
- **Sky Classic icon style** (`docs/design/sky-classic-icon/`): a rounded
  dark gradient tile carrying a glowing outline glyph with round joins and
  caps, drawn in the sky-blue gradient. The reference shows another
  product's glyph; MotoSphere gets its own glyph in the same style (task
  FND-024), and interface icons follow the same outline style. The owner's
  approved MotoSphere icon, its small version and the rules for both are in
  `docs/design/icon/`.

Rules:

- No track or marker data hardcoded in the frontend. Everything shown on the
  globe comes from the published data files, which come from the data store.
- Map rendering code and business logic stay in separate modules.
- The site is served from a sub-path (`/MotoSphere/`) on GitHub Pages, so
  every URL the app builds is relative to the configured base path, never to
  the domain root.
- GitHub Pages cannot rewrite URLs, so view state that should be shareable
  (camera position, selected item) lives in the query string or fragment, not
  in the path.
- The site is files and nothing else: an address that names no file is
  answered with "not found" (404), and the application has no page but the
  one at the site's path. Vite's servers are told the same
  (`appType: 'mpa'` in `frontend/vite.config.ts`). Left to themselves they
  answer every address that names no file with the page, which is meant for
  an application that reads the address itself; a file missing from the
  build would then be missing on the published site only (FND-052).
- Anything shipped to the browser is public. No secret may be placed in the
  frontend or in a published file.
- A screen under 900 pixels wide is a narrow one (a phone, or a tablet held
  upright). There the globe stage keeps the whole width and an open side
  panel lies over it; from 900 pixels on, the panels stand beside the stage.
  The width is written in the layout's style sheet
  (`frontend/src/layout/AppShell.module.css`) and, for the script, in
  `frontend/src/layout/narrowScreen.ts`; a unit test fails when the two
  differ.
- On a narrow screen the information of the top bar (the data status and
  the date) stands under its first line, and how many lines it has depends
  on the width of the screen and on nothing else: below 640 pixels each
  piece has a line of its own, and from 640 pixels on the two share one.
  The words do not decide it, so the bar is as tall while the data loads
  as when it has arrived or could not be loaded, and nothing under it
  moves (FND-049). A piece too long for its line is not wrapped: it ends
  in "…", and on a shared line the data status stays whole and the date
  gives way. At 640 pixels both pieces have room on one line in each of
  the 61 languages the planner's test browser writes dates in, on every
  day of a year: the widest pair needs 572 pixels with the edges of the
  bar, with the fonts of that machine. The 640 is written in the style
  sheet and in the browser tests, and the unit test of the widths names
  every question about width the style sheet asks.
- On a narrow screen an open side panel covers the globe stage, so both
  panels start closed, at most one is open, and nothing about them is
  remembered: loading the page again shows the globe. On a wide screen each
  panel starts open and the user's choice is remembered for the session
  (`frontend/src/layout/useSidePanels.ts`).
- Where the main way of pointing is a finger (`@media (pointer: coarse)`),
  every control is at least 44 pixels tall (the token
  `--size-touch-target`), and the browser tests check that none is
  narrower than that. A new control gets that rule in its own style sheet.
  The buttons in the top bar stand in the middle of its first line there,
  not on its line of text: where a button stands on a line of text depends
  on the font, and one of 44 pixels in a line of 48 has no room for that.
  With a mouse everything stays as designed.
- Heights that follow the screen are written in `dvh`, the part of the
  screen the browser really shows, never in `vh`: on a phone `vh` counts
  the part under the browser's own bars. There is no `vh` line as a
  fallback, because every browser the build is made for (Vite's default
  list: Chrome and Edge 111, Firefox 114, Safari 16.4) knows `dvh`, and
  the build removes such a line anyway. A unit test rejects `vh` in any
  style sheet under `frontend/src`.
- The packages the site ships to the browser are the ones under
  `dependencies` in `frontend/package.json`: React with `react-dom`, and
  the engine of the globe with `@cesium/core`. A repository check holds
  the list (`tests/repo/test_frontend_packages.py`), because adding a
  package there is a decision about whose code every visitor runs. The
  lock file must hold one copy of each: with two copies of `@cesium/core`,
  a position the application makes would not be one the engine knows as
  its own.
- The licences of the packages the site is built with go with the site.
  Most of them ask that their text go with every copy, and the build
  takes such notices out of the code it makes. So a step of the build
  (`frontend/sitebuild/licences.ts`) writes one file, `licences.txt`,
  beside the page: the name, the version and the licence of every
  package the lock file installs that is not only for the work, each
  with the licence files the installed package brings, letter for
  letter. A package may bring code of others in a folder of its own with
  their licence beside it, so the step looks into every folder of the
  package, but not into `node_modules` beneath it, where other packages
  are put. The build fails when a package brings no such file, unless the
  step names the package whose file gives its licence; a person who has
  read both puts that there. The source of the page says in a comment
  where the file is.
- The licence of every such package is one the project has accepted. The
  list is in `tests/repo/test_frontend_licences.py`, part of the
  repository checks: each licence as the lock file writes it, with what
  it asks of whoever passes the code on and how the project meets that.
  A package under any other licence, or with none named, fails the
  checks until its licence has been read and put on the list, in the
  pull request that brings the package. The packages that only build and
  test the site are not held to the list: nothing of them is passed on.
- The engine fetches files of its own while it runs: background scripts,
  programs for the browser's own machine, tables and pictures. They come
  with the package, in its folder `Build`, and are not code the build
  takes in. A step of the build (`frontend/sitebuild/engineFiles.ts`)
  puts them into the site as they are, under the folder `cesium/` of the
  site's path: 275 files, 8.3 MB, with `@cesium/engine` 26.5.0. None is
  picked by hand, so that another version of the engine brings what it
  needs: the step takes every file beneath that folder, at any depth,
  and stops the build for a link among them. Two files are left out,
  each named in the step with its reason: the logos of Bing Maps and of
  Google Earth, which the engine shows only with imagery of those
  companies. The globe uses neither, and a provider of imagery is taken
  on with its terms read, its pictures with it (§8). The files are
  passed on unchanged, as the package brings them under the engine's
  licence, whose text is in `licences.txt`. Nothing of the application
  asks for a file of it yet, so a visitor's browser fetches none.
- In development nothing is built, and the development server answers
  from the folder of the project, where the engine's files are not. A
  second step in the same file answers the folder `cesium/` of the
  site's path from the installed engine while the development server
  runs (GLB-024): each file the built site has, read anew for every
  request, with the type a browser needs, and "not found" for every
  other address in that folder, the two logos among them. It goes by
  the same list as the build, so the globe is developed against what
  the site will hold. The server does not start when the engine is not
  installed, or when the engine brings a file of a kind the step has no
  type for: a person then says what a browser must be told it is.
- The engine asks for its files beneath one address. Left to itself it
  works that address out from where its own code was loaded, which in
  the built site is a file of the build with a name of its own, and the
  engine's files are not beside it. So the application tells it
  (GLB-025). One module, `src/globe/engineAddress.ts`, builds the
  address from the site's path and the name of the folder, and puts it
  under the name the engine reads, `CESIUM_BASE_URL`. Both parts are in
  `frontend/site.ts`, and the build and the development server take the
  folder's name from there too, so the files cannot be put in one place
  and looked for in another. The application tells the engine where it
  starts, before it shows anything, and nowhere else: the engine reads
  the address the first time it needs a file, and keeps it. The address
  is a path and names no computer, so the engine asks the site the page
  came from and nobody else. The engine also has a function for this,
  `buildModuleUrl.setBaseUrl`. It is not used: calling it needs the
  engine loaded, and the engine is loaded only when the globe is shown
  (GLB-002).
- A name the engine has moved to `@cesium/core` (`Cartesian3`,
  `Ellipsoid`, `Math` and about 150 in all) is imported from there. The
  engine still hands those names out, with a warning, and says it will
  stop doing so.

## 4. Data pipeline (Decided)

| Choice | Decision | Why |
|---|---|---|
| Language | Python ≥ 3.12 | As proposed. |
| Form | Command-line program, `python -m motosphere <command>` | There is no server to run. The same commands work in GitHub Actions and on Windows 11. |
| Models and validation | Pydantic v2 | Typed validation of collected records and of every published file. |
| Data access | SQLAlchemy 2 (synchronous) over SQLite | Typed models and portable SQL. If a server is ever wanted, the models move to PostgreSQL without a rewrite. |
| Packaging | uv with a committed lock file | One tool for Python version, virtualenv and locked installs on Windows and Linux. |
| Lint/format | ruff | One fast tool. |
| Types | mypy, strict | Type checking is a mandatory gate. |
| Tests | pytest | Unit tests plus integration tests against a real SQLite database and the real commands. |
| Settings | pydantic-settings, env prefix `MOTOSPHERE_`, optional `.env` | Environment-based configuration. `.env` is never committed; `.env.example` is. |

The FastAPI application, health endpoint and server start command built in
FND-007 and FND-008 are no longer part of the product. Task FND-020 removes
them and their dependencies and turns `python -m motosphere` into the
pipeline's command line. The settings and logging modules stay.

## 5. Data store (Decided)

- **SQLite**, through Python's standard library driver. It is a real
  relational database with foreign keys, constraints, indexes and
  transactions, needs no installation on Windows 11 or in GitHub Actions, and
  suits a single-writer batch pipeline. The earlier choice of PostgreSQL with
  PostGIS assumed a hosted database server, which the hosting decision
  removed.
- **Geography without PostGIS.** Coordinates are stored as validated latitude
  and longitude (WGS 84). Bounding-box lookups use ordinary or R*Tree indexes;
  distances use the haversine formula in Python; map tiles and clusters are
  computed at export time.
- **Where the file is** is one setting, `MOTOSPHERE_STORE_PATH`, by default
  `backend/store/motosphere.sqlite3`. Git ignores that folder and every
  `*.sqlite3` file (DAT-002).
- **One function opens the store**, `open_store` in `motosphere.db.store`
  (DAT-021). It returns the SQLAlchemy engine. Every connection enforces
  foreign keys and uses SQLite's own transactions, so failed work is taken
  back as a whole, a change to the schema included; no connection is kept
  open after use; and an SQLite that lacks what the store relies on is
  refused before anything is written (DATABASE.md).
- **Everything is written in units of work**, `unit_of_work` in
  `motosphere.db.work` (DAT-022): a session on the opened store whose work
  is committed as a whole when it ends and taken back as a whole when it
  fails, with the error passed on as it was raised and the connection
  closed either way. A unit cannot commit part-way (DATABASE.md).
- **The schema changes only by migrations**, run by a small runner of the
  project's own, `migrate` in `motosphere.db.migrations` (DAT-004). The
  migrations are functions in one list, a store keeps the number of the
  last one it has had, and each is one transaction with that number: kept
  as a whole or not at all. There is no way back; an earlier state is an
  earlier snapshot. Alembic was weighed and not taken. Only a store of
  MotoSphere's is migrated: the first migration marks the file, and a file
  that has anything in it and not that mark is refused and left as it is
  (DAT-023). The command `python -m motosphere migrate` runs it on the
  store the settings name, and is the first command that uses the store
  (DAT-024). The command `python -m motosphere schema` says which schema
  that store has and writes nothing (DAT-025, DATABASE.md). Every other
  command that works on the store gets it from one function,
  `store_to_work_on` in `motosphere.cli.store` (DAT-063), which gives the
  store only when it is there and at the newest schema, and makes and
  migrates nothing: that stays with `migrate`. The first of them is
  `python -m motosphere countries`, which loads the countries of the
  reference file into the store in one unit of work and says what it
  found (DAT-061, DATABASE.md). The
  migrations themselves are written in one module, `motosphere.db.history`,
  as plain SQL that names nothing of the store's code, so that a migration
  builds tomorrow what it builds today (DAT-006).
- **The models and the migrations are held together** by one test
  (DAT-026): it builds one store with the migrations and one from the
  models, and `differences` in `motosphere.db.compare` must find them the
  same, statement for statement as SQLite keeps them. So a model cannot
  change without a migration, nor a migration without its model
  (DATABASE.md).
- **Every table keeps the same rules**, through the base of all models,
  `Base` in `motosphere.db.base` (DAT-005): a table is strict, its columns
  have the types a strict table takes, and its constraints and indexes are
  named by one rule. Its key is one whole-number column, `id`, which the
  base gives and whose values SQLite never gives twice, also not after a
  row is deleted (DAT-029). Its last two columns, `created_at` and
  `updated_at`, say when a row was first stored and when it was last
  changed; the base gives them too, and the store's code sets them from
  the store's one clock (DAT-031). A column whose model says that its
  text must not be empty gets a check from the base, and SQLite refuses
  empty text in it, also text of nothing but white space (DAT-030). The
  check comes with the column's type: any column type can bring a check
  for its column (`WithItsCheck` in `motosphere.db.checks`), and the base
  gives it to the table (DAT-034). A column that is yes or no is such a
  column too: a model says `bool`, the table holds the whole number 1 or
  0, and SQLite refuses any other (DAT-035). And so is a column whose
  value is one of a list the code knows: the list is a `StrEnum`, the
  table holds its texts, and the check names them (DAT-036). And so is a
  column that is a web address: a model says `WebAddress`, the table
  holds text, and the check refuses text that does not begin with
  `https://` or `http://` and go on with the name of a site, and text
  with white space in it (DAT-037). And so is a column that is a calendar
  day: a model says `date`, the table holds text such as `2026-11-24`,
  and the check refuses text that is not a day of the calendar in that
  form. A time is not taken for a day, and no time of day is made up for
  one (DAT-044).
  `broken_rules` names a table that breaks a rule, a table without the
  key or without the two times among them (DAT-032), and a column whose
  type brings a check and whose table is without it (DAT-033), and a name
  that more than one constraint or index of a table has (DAT-038), and a
  test holds the schema to it (DATABASE.md).
- **A time is stored in one form**, as text: in UTC, with its offset
  written out and the whole fraction of its second, for example
  `2026-11-19T08:26:04.123456+00:00` (`motosphere.db.times`, DAT-028). The
  order of the texts is the order of the times. A time without an offset
  is refused, and what comes back is an aware UTC time. A model's
  `datetime` column gets this type from `Base` (DATABASE.md).
- **The models live in one package**, `motosphere.db.models`, which names
  every model: `SCHEMA` there is the whole schema, and a test proves that
  no model anywhere in the code is missing from it. The first table is
  that of the information sources, `source` (DAT-006), with the two lists
  a source is described by: the twelve kinds of source and the ten ways of
  collecting of DESIGN.md §7 (DAT-039), and a thirteenth kind of this
  project's own, for whoever keeps a reference list such as the
  countries of a standard (DAT-058). A new source is switched off, and
  the table refuses one that is switched on before its terms were read.
  A second table, `source_offer`, says which of nine kinds of information
  each source offers, a row for each (DAT-040, DATABASE.md).
- **Every collection run is recorded** in the table `collection_run`
  (DAT-007): which source, when it started and ended, how it ended and
  what it counted, with the error in plain words when it failed. A run
  whose job died is still running in the table; `mark_interrupted` in
  `motosphere.db.runs` marks such runs interrupted at the next start and
  touches nothing else (DATABASE.md). The table has an index over the
  source and the start of a run (DAT-042), and a test reads from SQLite
  itself that the statements which ask for the newest run of a source
  are answered by it.
- **How a source is doing is read from its runs, not stored**
  (DAT-041): `standing_of` in `motosphere.db.source_health` says when a
  source was last attempted, when that last succeeded, its last error
  and its health, one of four texts. Stored with the source as well,
  they could come to disagree with the runs (DATABASE.md).
- **What the store relies on in SQLite** is named in one module,
  `motosphere.db.sqlite`: SQLite 3.45.0 or newer and six features, R*Tree,
  FTS5 and the JSON functions among them. Its tests run against the real
  SQLite on every machine the gates run on. DAT-001 found all six on
  GitHub's Linux and Windows machines, whose SQLite differs in version and
  in build (DATABASE.md).
- **Name matching** for duplicate detection is done in Python, with the
  library chosen in the task that first needs it.
- **Keeping the data between runs (Decided – DAT-001).** A GitHub Actions
  run starts from nothing, so the store must be saved somewhere durable.
  After each run the store is written out as deterministic, sorted text
  files in a dedicated `data` branch of this repository, and the next run
  rebuilds the SQLite database from them. That gives a full, reviewable
  history of every change for free. Keeping the database file itself as a
  release asset stays in reserve for the day the text files grow too large;
  a workflow cache or artifact does not last. DATABASE.md has the
  comparison, GitHub's limits and the sizes at which the decision is looked
  at again.
- Database tests run against a real SQLite database file. It is never
  replaced by mocks. The fixture `store` gives every test a file of its
  own, opened as the pipeline opens its store, and reports a test that
  leaves a connection to it open (DAT-003, TESTING.md).
- Every imported record carries provenance (source, source URL, collected-at,
  published-at, last-verified-at, extraction method, confidence, verification
  status). The last two are one of a list each: three levels of confidence,
  and the four statuses the design tells apart, from official to unverified
  (DAT-043, DATABASE.md). The eight are one set of columns, said once:
  a model of collected records is a subclass of `Collected` and not of
  `Base` itself, and its table has them all, with the reference to its
  source and the check that a record was not last seen at its source
  before it was collected. Only the day of publishing may be unknown
  (DAT-008). Every such table has an index over the source of its
  records, so that the records of one source are found, and a source is
  deleted, without reading a whole table (DAT-045). Every table holds
  collected records unless a list in the code says that it does not,
  with the reason; a rule names a table that is off that list and
  without the set, or has a part of it otherwise, and a test holds the
  real schema to it (DAT-046). Changes are recorded
  in a history table rather than overwritten: the table `record_change`
  keeps, for one field of one record, what it held before and holds now,
  when it was changed, and the collection run or the person that caused
  it (DAT-009). The table is only added to: four triggers in the store
  itself refuse to edit, delete or replace a row, whoever writes to the
  file (DAT-048). Two indexes find the changes of one record and the
  changes one run caused without reading the whole table
  (DAT-049). One function, `change`, gives a record its new values
  and writes a row of history for every field that differs, in the same
  unit of work, so neither is kept without the other (DAT-047).
  Ambiguous or conflicting records go to a review queue; uncertain identities
  are never merged automatically. The queue is the table `review_item`:
  one item is one doubt about one record, of one of three kinds (two
  records may be the same thing, a source says otherwise than the
  record, or a source says what the rules of a field refuse), with why,
  and with whether a person accepted or rejected it, who and when
  (DAT-010). One doubt is one item: the store refuses the same doubt a
  second time, also after it was decided, so that a person is not asked
  again what they have answered (DAT-050). One function,
  `open_possible_duplicate`, puts two stored records that may be the
  same thing to the queue, and gives back the item that is there when
  the doubt is one already (DAT-051). Another, `open_field_doubt`, does
  the same for what a source says of a field of a record, which it
  keeps as the text the source gave (DAT-053). A third, `decide`, puts
  down a person's decision on an open item, by whom and when, and
  refuses an item that was decided already (DAT-052). The table keeps
  a decision itself: two triggers in the store refuse to edit or to
  delete an item that was decided, whoever writes to it (DAT-054). Two
  more hold the key of an item to 1 or more (DAT-056), under every
  name SQLite has for the key (DAT-068), and two more refuse a row
  that would take the place of a decided item (DAT-055).
- **The countries are the first table of collected records**, `country`
  (DAT-011): a country is known by its two codes of ISO 3166-1, which
  the table holds to capital letters and to one country each, and has
  its English name. Every row says where it came from, with the eight
  columns every collected record has. The table knows the form of a
  code and not the standard's list: the countries themselves are
  loaded from a source whose licence allows it (DAT-012, DATABASE.md).
  A source can say which country it is of (DAT-057), so the two tables
  point to each other: a source is stored before its countries and is
  said to be of one of them afterwards, and a country that a source is
  of cannot be deleted.
- **The regions are the parts a country is divided into**, `region`
  (DAT-013): a region is a part of exactly one country and has a name,
  which no other region of that country has. It is a collected record,
  and a country that has regions cannot be deleted. The table has no
  reference rows: a region comes with the record that needs it. A
  region can say its code of ISO 3166-2, in the standard's form, and
  no two regions have one code (DAT-064). That the code agrees with
  the country, two regions of a country that share a name, and a
  region inside a region are tasks of their own (DAT-067, DAT-066,
  DAT-065; DATABASE.md).

The schema is documented in DATABASE.md as tables are added.

## 6. Published data (Decided)

The published files are the application's "API". They are produced only by
the export step, from the data store.

- A **manifest** (`data/manifest.json`) names the format version, when the
  data was generated, record counts and every file with its content hash. The
  frontend reads the manifest first and shows the data date to the user.
- **Map tiles.** Markers are published as small files per map tile and zoom
  level. Wide zoom levels contain pre-computed clusters, close zoom levels
  contain individual records. The browser loads only the tiles in view, so it
  never downloads every record.
- **Lists** are published in chunks (the equivalent of pagination).
  **Details** are one small file per item or per small group of items.
- **Search** uses index files built at export time and searched in the
  browser, loaded in parts as needed (strategy decided in SRC-001).
- The export models are Pydantic models. A JSON Schema is generated from
  them, frontend types are generated from the schema, and every exported file
  is validated against it. That schema is the contract.
- File names carry a version or hash so browsers never show stale data after
  an update.
- Only public information is exported. Internal fields (review notes, raw
  responses, logs with addresses) never leave the data store.

## 7. Data collection (Decided in outline, details per research task)

- A source adapter framework inside `motosphere.collectors`: one adapter per
  source, each independently testable, enable-able and disable-able. A failure
  in one adapter never stops another.
- A source registry table drives scheduling (DESIGN §7.3). How a source is
  doing is not a column of it: it is read from the source's collection runs
  (`motosphere.db.source_health`, DAT-041).
- One shared **polite HTTP client**: honest identifying User-Agent,
  robots.txt check, per-domain rate limit, timeouts, bounded retries, on-disk
  cache, conditional requests (ETag / Last-Modified).
- **Scheduling** is a daily GitHub Actions workflow that runs the pipeline
  and then deploys the site. A run can also be started by hand, in GitHub or
  on the owner's PC. Known limits, to be respected rather than worked around:
  a run may take at most a few hours, so large first imports are spread over
  several runs; GitHub pauses scheduled workflows in repositories with no
  activity for 60 days; and some websites refuse requests from hosted
  runners. A source that refuses is collected from the owner's PC or marked
  unavailable. Blocks are never circumvented.
- Adapter tests run against recorded fixtures, never the live site. Live
  collection is verified separately and recorded in DATA_SOURCES.md.
- All collected content is untrusted: it is validated, stored as data and
  escaped on render. Nothing found in scraped content is ever executed.
- **Reference lists come with the project.** What other records are
  described by, such as the countries of the world, is not collected from
  a website while the pipeline runs. It is a file in
  `motosphere.reference`, taken unchanged from a source whose licence
  allows passing it on, with a note beside it that says which release it
  is from, where it was fetched and what its licence asks. A test holds
  the file to that release, byte for byte, so a change to it is a
  decision somebody made. A reader gives the records of the file or
  refuses the file whole, with a sentence that says what is wrong; it
  reads what MotoSphere keeps and leaves the rest unread. The file is
  data from outside like any other: nothing of it is run. The first such
  list is the countries of ISO 3166-1, from the project iso-codes
  (DAT-012; `DATA_SOURCES.md` has the source and its licence). The
  source of a list is described for the store beside its reader
  (`motosphere.reference.countries_source`, DAT-060): the code says
  what the source is, and what is for people to say of it, whether its
  terms were read and whether it is switched on, is left to them.
  The list itself is brought into the store by a function beside both
  (`motosphere.reference.countries_load`, DAT-059), which adds what the
  store does not have and changes no country. It is not a collection
  run: nothing is fetched, because the file is part of the project.
  What the file says otherwise of a country that is there goes to the
  review queue (DAT-062). The command `countries` calls the loading
  (DAT-061).

### Scrapling evaluation (preliminary, confirmed in task TRK-007)

CLAUDE.md §10 asks whether https://github.com/D4Vinci/Scrapling suits this
project. Preliminary verdict from its README: **only partly, and not as the
fetcher.**

- Its headline features are stealth: browser TLS-fingerprint impersonation,
  fingerprint spoofing, and automated bypass of Cloudflare Turnstile
  challenges. DESIGN §14 requires the opposite: identify the application in
  requests and never bypass anti-bot protections or CAPTCHAs. Those fetchers
  must not be used.
- Useful parts: a fast HTML parser with CSS/XPath selection and "smart element
  tracking" that survives small site redesigns; and a spider layer with
  optional robots.txt obedience and per-domain throttling. Licence is
  BSD-3-Clause, Python ≥ 3.10.
- Gaps for us: no documented HTTP conditional requests, and Windows support is
  not stated.

Working position: fetch with our own polite client; consider Scrapling's
parser as an optional parsing library inside adapters if it proves itself
against plain `lxml`/`selectolax` in the research task. Its stealth fetchers
stay out of the dependency set (do not install the `fetchers` extra).

## 8. Globe imagery and terrain (Open – research tasks in Phase 3)

Requirements: satellite imagery by default, terrain where available, visible
attribution, provider swappable by configuration, no Google assets, and no
claim that a provider is free until its terms have been read and recorded.

- **Baseline (Decided):** the globe starts with the Natural Earth II imagery
  bundled with CesiumJS and no terrain. It needs no key and no network, so the
  app always starts and browser tests are deterministic.
- **Candidates to verify:** NASA GIBS, EOX Sentinel-2 cloudless, Esri World
  Imagery, Cesium ion (token; imagery and World Terrain), MapTiler, Mapbox.
  Each is recorded with its licence, attribution, limits and whether a key is
  required before it is offered in the app.
- **Keys on a static site are public.** Any provider key used by the app is
  visible to every visitor. Only providers that need no key, or whose terms
  allow a public key restricted to our site address, can be used.
- Providers are defined in a registry and selected by configuration.

## 9. Administration (Decided)

There is no server to log in to, so administration works through the
repository:

- **Reports** (data statistics, source health, collection logs, the review
  queue) are generated by the pipeline and published as pages or files.
- **Decisions** (enable or disable a source, accept or reject a queued
  record, correct a record, confirm a merge) are recorded in
  version-controlled files and applied by the next pipeline run, with the
  change kept in the record's history. Who may decide is controlled by who
  may write to the repository.
- A manual run or a retry is started from the GitHub Actions page.

## 10. Testing gates (Decided)

Every task must pass every gate that exists at that point:

1. Repository checks (`tests/repo`).
2. Pipeline: ruff, mypy, pytest (unit and integration). The Python files
   outside the pipeline (`scripts/`, `tests/`) pass the same ruff and mypy
   checks, with the pipeline's locked tools (task FND-031).
3. Frontend: oxlint, Prettier, TypeScript, Vitest, production build.
4. Browser: Playwright against the built app, reading data produced by the
   real export command.

A single command, `python scripts/check.py`, runs all gates, counts the
tests and fails when a test was skipped (tasks FND-017 and FND-030). GitHub
runs the same command on Linux and on Windows for every pull request and
every change to `main`, with a token that can only read (tasks FND-018 and
FND-032). Details live in
TESTING.md.

## 11. Security baseline (Decided)

- The published site is static and holds no secrets, sessions or user input
  that reaches a server.
- Secrets needed by the pipeline (if any source ever requires a key) live in
  GitHub Actions secrets or the local `.env`, never in the repository and
  never in a published file.
- Scraped text is validated on the way in, exported as data and escaped on
  render. It is never executed, and never interpreted as HTML.
- Parameterised SQL only.
- Workflows run with the least permissions they need. Only the deployment
  job may publish the site, and only the collection job may write data.
- Dependency vulnerability checks are part of the check runner. The
  frontend's is `scripts/audit.py`: it fails on every advisory `npm audit`
  reports unless an exception is recorded in `frontend/audit-exceptions.json`
  with a reason and a review date at most 31 days away. The pipeline's
  (`pip-audit`) is task PRF-005.

## 12. Windows 11 operation (Decided)

On Windows 11 MotoSphere is used in a browser: it is the published site
(§13), and nothing is installed or started for it. The owner decided on
2026-11-19 that there is no offline version. So there are no commands that
build, serve and open a private copy on a PC, and no PowerShell scripts;
an earlier wording of this section planned both.

What stays is working on the project, and that is the same on Windows and
on Linux. Every command in README.md (the checks, the pipeline, the
frontend's development server) is one command on both, logic shared with
continuous integration lives in Python scripts so it is written once, and
the gates run on a Windows machine for every pull request (§11).
`scripts/tools.py` says whether a computer has the tools the project
needs. It reads the least versions of Python and Node.js from the files
where those tools read them (`backend/pyproject.toml`,
`frontend/package.json`), and it only looks: it installs nothing. The
least Node.js is not chosen by hand: it is the oldest that every locked
package of the frontend runs on, and a repository check holds it there
(FND-046).

## 13. Deployment (Decided)

- **GitHub Pages**, deployed by the checks workflow after every gate passed
  for a change to `main`: one job exports the data and builds the frontend,
  a second job, the only one with the right to publish, hands both to
  GitHub Pages as one site (task FND-034; TESTING.md, "Deployment"). A
  third job then compares every file the published address serves with the
  site that was built, and fails the run when they differ (tasks FND-035
  and FND-037).
- Needed from the owner: Pages switched on for the repository with "GitHub
  Actions" as the source. GitHub offers Pages free for public repositories;
  for a private repository the account needs a paid plan.
- Limits to design within: a published site of at most 1 GB, a soft limit of
  100 GB of traffic per month, and static files only. Published data size is
  tracked from the first export and reviewed in Phase 13.
- A custom domain is optional and is the owner's decision (Phase 13).
