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
│   │   ├── db/              engine, session, models, migrations glue
│   │   ├── geo/             coordinates, map tiles, clustering
│   │   ├── services/        business rules (validation, matching, history)
│   │   ├── collectors/      source adapter framework and adapters
│   │   ├── publish/         export models and writers for published files
│   │   └── admin/           review decisions and corrections
│   ├── migrations/          schema migrations
│   └── tests/               unit/ and integration/
├── frontend/                Vite + React + TypeScript project
│   ├── src/                 code, with unit tests next to it
│   └── e2e/                 Playwright browser tests
├── scripts/                 setup, check and local-run scripts
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
| Globe | CesiumJS used directly behind a thin `Globe` component | Cesium is the right engine for a true 3D Earth with terrain and continuous zoom. No Resium wrapper: one less dependency that must track Cesium releases, and imperative camera control is simpler to test. |
| Data loading | TanStack Query over `fetch` of published files | Caching, cancellation and loading/error states for viewport-driven loading. Introduced by the first task that needs more than one file. |
| Styling | Plain CSS with design tokens (CSS custom properties) and CSS modules | No heavy UI kit. The owner's Graphite theme (see below) is kept consistent through our own tokens. |
| Unit tests | Vitest + Testing Library | Native to Vite. |
| Browser tests | Playwright (Chromium, software WebGL) | Real globe rendering and interaction can be verified headlessly. |
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
- Anything shipped to the browser is public. No secret may be placed in the
  frontend or in a published file.
- A screen under 900 pixels wide is a narrow one (a phone, or a tablet held
  upright). There the globe stage keeps the whole width and an open side
  panel lies over it; from 900 pixels on, the panels stand beside the stage.
  The width is written once, in the layout's style sheet
  (`frontend/src/layout/AppShell.module.css`).

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

## 5. Data store (Decided in outline; details by research task DAT-001)

- **SQLite**, through Python's standard library driver. It is a real
  relational database with foreign keys, constraints, indexes and
  transactions, needs no installation on Windows 11 or in GitHub Actions, and
  suits a single-writer batch pipeline. The earlier choice of PostgreSQL with
  PostGIS assumed a hosted database server, which the hosting decision
  removed.
- **Geography without PostGIS.** Coordinates are stored as validated latitude
  and longitude (WGS 84). Bounding-box lookups use ordinary or R*Tree indexes;
  distances use the haversine formula in Python; map tiles and clusters are
  computed at export time. DAT-001 confirms which SQLite features (R*Tree,
  FTS5, JSON) are present in the Python builds we use on both platforms
  before anything depends on them.
- **Name matching** for duplicate detection is done in Python, with the
  library chosen in the task that first needs it.
- **Keeping the data between runs (Open – DAT-001).** A GitHub Actions run
  starts from nothing, so the store must be saved somewhere durable. Leading
  candidate: after each run the store is written out as deterministic,
  sorted text files in a dedicated `data` branch of this repository, and the
  next run rebuilds the SQLite database from them. That gives a full,
  reviewable history of every change for free. The alternative (keeping the
  database file itself as a release asset) is compared in DAT-001, together
  with repository and Pages size limits.
- Database tests run against a real SQLite database file. It is never
  replaced by mocks.
- Every imported record carries provenance (source, source URL, collected-at,
  published-at, last-verified-at, extraction method, confidence, verification
  status). Changes are recorded in a history table rather than overwritten.
  Ambiguous or conflicting records go to a review queue; uncertain identities
  are never merged automatically.

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
- A source registry table drives scheduling and records health (DESIGN §7.3).
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

Development and first use are on Windows 11. Everything works locally without
GitHub: the checks, a pipeline run, and viewing the site with locally exported
data. Scripts that the user runs are PowerShell (`scripts/*.ps1`); logic
shared with Linux and CI lives in Python scripts so it is written once. The
commands are documented in README.md and verified on a real Windows machine
before the task that adds them is accepted.

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
