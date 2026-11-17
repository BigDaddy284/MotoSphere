# MotoSphere – Architecture

This document records the technical architecture and the reasons behind each
important decision. It is the planner's evaluation of the stack proposed in
DESIGN.md §13. Change it in the same commit as any change that contradicts it.

**Naming.** The product is called **MotoSphere** ("The World of Motocross,
Connected."). DESIGN.md and CLAUDE.md call it "Global Motocross Dashboard";
they describe the same product. Code, packages and UI text use MotoSphere.

Status of this document: decisions marked **Decided** are binding for builders.
Decisions marked **Open** are settled by a named research task before any code
depends on them.

---

## 1. System overview

```
 Browser (React + TypeScript + CesiumJS)
        │  HTTPS / JSON + GeoJSON, /api/v1
        ▼
 Backend API (Python, FastAPI)  ──────────────┐
        │  SQLAlchemy 2 + GeoAlchemy2          │ same Python package,
        ▼                                      │ separate process
 PostgreSQL 16 + PostGIS 3  ◄──── Collection worker (scheduler + source adapters)
                                               │  polite HTTP client
                                               ▼
                                     Public motocross sources
```

Four runtime pieces, each startable and stoppable on its own:

1. **Frontend** – static single-page app. The globe dominates the screen.
2. **API** – read-mostly REST API. Never scrapes during a user request.
3. **Database** – the single source of truth, including provenance.
4. **Collection worker** – a separate process that runs scheduled source
   adapters and writes through the same data layer as the API.

## 2. Repository layout (Decided)

One repository, clear top-level separation:

```
MotoSphere/
├── backend/                 Python project (uv), package `motosphere`
│   ├── pyproject.toml
│   ├── src/motosphere/
│   │   ├── api/             FastAPI routers and request/response schemas
│   │   ├── core/            settings, logging, shared utilities
│   │   ├── db/              engine, session, models, migrations glue
│   │   ├── geo/             spatial queries, clustering
│   │   ├── services/        business logic used by API and worker
│   │   ├── collectors/      source adapter framework and adapters
│   │   ├── jobs/            scheduler and worker entry point
│   │   └── admin/           administrative operations
│   ├── migrations/          Alembic
│   └── tests/               unit/ and integration/
├── frontend/                Vite + React + TypeScript project
│   ├── src/
│   ├── tests/               Vitest unit tests (co-located tests also allowed)
│   └── e2e/                 Playwright browser tests
├── scripts/                 start/stop/setup/check scripts
├── tests/repo/              repository-wide checks (stdlib only)
├── docs/
│   ├── WORKFLOW.md          how tasks are planned, built, tested, merged
│   └── plans/               one implementation plan per task
└── CLAUDE.md DESIGN.md TASKS.md PROGRESS.md ARCHITECTURE.md
    DATA_SOURCES.md DATABASE.md TESTING.md CHANGELOG.md README.md
```

Directories are created by the task that first needs them, not in advance.

## 3. Frontend (Decided)

| Choice | Decision | Why |
|---|---|---|
| Framework | React + TypeScript (strict) | As proposed. Mature, typed, well supported by tooling. |
| Build tool | Vite | Fast, simple, first-class TypeScript, easy static asset handling for Cesium. |
| Globe | CesiumJS used directly behind a thin `Globe` component | Cesium is the right engine for a true 3D Earth with terrain and continuous zoom. No Resium wrapper: one less dependency that must track Cesium releases, and imperative camera control is simpler to test. |
| Server state | TanStack Query | Caching, cancellation and loading/error states for viewport-driven requests. Introduced by the first task that fetches data. |
| Styling | Plain CSS with design tokens (CSS custom properties) and CSS modules | No heavy UI kit. A dark motorsport theme is easier to keep consistent with our own tokens. |
| Unit tests | Vitest + Testing Library | Native to Vite. |
| Browser tests | Playwright (Chromium, software WebGL) | Real globe rendering and interaction can be verified headlessly. |
| Lint/format | oxlint + Prettier | oxlint has the React hooks, accessibility, import, Vitest and TypeScript rules built in as one dependency, and is what the current Vite template ships. ESLint was the first choice, but `typescript-eslint` depends on the older JavaScript compiler API and the project uses the native TypeScript 7 compiler. Type errors are covered by the type-check gate. |

Rules: no track or marker data hardcoded in the frontend. Everything shown on
the globe comes from the API. Map rendering code and business logic stay in
separate modules.

## 4. Backend (Decided)

| Choice | Decision | Why |
|---|---|---|
| Language | Python ≥ 3.12 | As proposed. |
| Framework | FastAPI + Pydantic v2 | As proposed. Typed schemas, generated OpenAPI. |
| Data access | SQLAlchemy 2 (**synchronous**) + psycopg 3 + GeoAlchemy2 | Sync keeps tests and Windows operation simple. Async psycopg needs a non-default event loop on Windows, which is a recurring source of breakage. FastAPI runs sync endpoints in a thread pool, which is ample for this workload. |
| Migrations | Alembic | Every schema change is a reviewed, reversible migration. |
| Packaging | uv with a committed lock file | One tool for Python version, virtualenv and locked installs on Windows and Linux. |
| Lint/format | ruff | One fast tool. |
| Types | mypy, strict | Type checking is a mandatory gate. |
| Tests | pytest | Unit tests plus integration tests against a real PostgreSQL. |
| Settings | pydantic-settings, env prefix `MOTOSPHERE_`, optional `.env` | Environment-based configuration. `.env` is never committed; `.env.example` is. |

## 5. Database (Decided)

- **PostgreSQL 16 + PostGIS 3**, as proposed. Geographic columns use
  `geography(Point, 4326)` with GiST indexes. `pg_trgm` and `unaccent` support
  fuzzy name matching for duplicate detection and search.
- SQLite/SpatiaLite was considered for easier Windows setup and rejected: it
  would have to be replaced for hosted deployment, and its spatial and
  concurrency behaviour differs enough that tests would not prove production
  behaviour.
- **No Docker requirement.** Windows uses the standard PostgreSQL installer
  plus the PostGIS bundle; a setup script and guide are their own task (DB-001).
- Database tests run against a real PostgreSQL test database. PostgreSQL is
  never swapped for an in-memory substitute in tests.
- Every imported record carries provenance (source, source URL, collected-at,
  published-at, last-verified-at, extraction method, confidence, verification
  status). Changes are recorded in a history table rather than overwritten.
  Ambiguous or conflicting records go to a review queue; uncertain identities
  are never merged automatically.

The schema is documented in DATABASE.md as tables are added.

## 6. API (Decided)

- REST, JSON, versioned under `/api/v1`. Health check at `/api/health`.
- List endpoints are paginated. Map endpoints take a bounding box and zoom
  level and return GeoJSON; at wide zoom levels the server returns clusters,
  not individual records.
- One consistent error format. All input validated by Pydantic. Only
  parameterised queries.
- The OpenAPI schema is the contract; frontend types are generated from it.

## 7. Data collection (Decided in outline, details per research task)

- A source adapter framework inside `motosphere.collectors`: one adapter per
  source, each independently testable, enable-able and disable-able. A failure
  in one adapter never stops another.
- A source registry table drives scheduling and records health (DESIGN §7.3).
- One shared **polite HTTP client**: honest identifying User-Agent,
  robots.txt check, per-domain rate limit, timeouts, bounded retries, on-disk
  cache, conditional requests (ETag / Last-Modified).
- The worker is a separate process. A lightweight in-process scheduler
  (APScheduler) is used at first. Redis/Celery are introduced only if workload
  proves the need.
- Adapter tests run against recorded fixtures, never the live site. Live
  collection is verified separately and recorded in DATA_SOURCES.md.
- All collected content is untrusted: it is validated, stored as data and
  escaped on render. Nothing found in scraped content is ever executed.

### Scrapling evaluation (preliminary, confirmed in task COL research)

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
- Providers are defined in a registry and selected by configuration. Keys live
  in environment configuration only.

## 9. Testing gates (Decided)

Every task must pass every gate that exists at that point:

1. Repository checks (`tests/repo`).
2. Backend: ruff, mypy, pytest (unit and integration).
3. Frontend: oxlint, Prettier, TypeScript, Vitest, production build.
4. Browser: Playwright against the built app.

A single command, `python scripts/check.py`, runs all gates and prints a count
summary (task FND-017). Until it exists, each plan lists the exact commands.
Details live in TESTING.md.

## 10. Security baseline (Decided)

Secrets only in environment configuration. Input validation at the API edge.
Parameterised SQL. Scraped text escaped on render and never executed.
Administrative operations require an admin token and are disabled when none is
configured. Dependency vulnerability checks (`pip-audit`, `npm audit`) are part
of the check runner once dependencies exist.

## 11. Windows 11 operation (Decided)

Development and first use are on Windows 11. Scripts that the user runs are
PowerShell (`scripts/*.ps1`); logic shared with Linux/CI lives in Python
scripts so it is written once. Start-up and shut-down commands are documented
in README.md and verified on a real Windows machine before the task that adds
them is accepted.

## 12. Deployment (Open – Phase 13)

The split into static frontend, stateless API, PostgreSQL and a worker maps
directly onto ordinary hosting. Hosting cost, storage, imagery licensing for a
public site and background processing are investigated in Phase 13 before any
recommendation is made.
