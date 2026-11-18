# MotoSphere

The World of Motocross, Connected.

MotoSphere is a global motocross information platform centred on an
interactive 3D Earth. It is intended to discover, collect, organise and present
freely accessible information about motocross tracks, events, championships,
race results, riders and teams worldwide, so that people can explore the sport
directly from the globe.

## Status

Early development. The data pipeline has a command line with two commands so
far: one prints the installed version, the other writes the published data
manifest, which holds no data yet. The frontend shows the application's
layout, with no globe and no data yet. The repository holds the
project documentation, the repository checks, the backend Python package with
its tests and the frontend project.

The current state of `main` is published at
<https://bigdaddy284.github.io/MotoSphere/>. Every change to `main` that
passes all checks is published there automatically, and the published
site is then compared with what was built ([TESTING.md](TESTING.md),
"Deployment").

- [TASKS.md](TASKS.md) lists every development task and its status.
- [PROGRESS.md](PROGRESS.md) holds the test report for each completed task.

## Documentation

- [DESIGN.md](DESIGN.md) – the complete product specification.
- [CLAUDE.md](CLAUDE.md) – the development rules.
- [TASKS.md](TASKS.md) – the task-by-task development checklist.
- [PROGRESS.md](PROGRESS.md) – completed work, current task, test reports and next steps.
- [ARCHITECTURE.md](ARCHITECTURE.md) – technical architecture and important design decisions.
- [DATA_SOURCES.md](DATA_SOURCES.md) – information sources, access methods, licences, restrictions and collection status.
- [DATABASE.md](DATABASE.md) – database schema and entity relationships.
- [TESTING.md](TESTING.md) – testing strategy, commands and latest results.
- [CHANGELOG.md](CHANGELOG.md) – significant changes and releases.
- [docs/WORKFLOW.md](docs/WORKFLOW.md) – how tasks are planned, built, tested and merged.

## Running the data pipeline

Prerequisites: Python 3.12 or newer and
[uv](https://docs.astral.sh/uv/getting-started/installation/).

From the repository root:

```
cd backend
uv sync --locked
uv run python -m motosphere version
```

This prints the installed MotoSphere version. The pipeline will gain commands
to collect, check and publish data; `uv run python -m motosphere --help` lists
the commands. Nothing listens on a network port.

To write the published data files:

```
uv run python -m motosphere export --out <directory>
```

This writes `manifest.json` into the directory, creating the directory if it
is missing. The manifest records the version of the data format, when the data
was generated and the MotoSphere version that generated it. There is no data to
export yet, so it holds no record counts.

## Running the frontend

Prerequisites: [Node.js](https://nodejs.org/) 22.12 or newer, which includes
npm, and [uv](https://docs.astral.sh/uv/getting-started/installation/).

From the repository root:

```
cd frontend
npm ci
npm run data
npm run dev
```

`npm run data` runs the pipeline's export and writes the published data into
`frontend/public/data/`, which Git ignores. Run it again whenever you want
fresh data. The top bar shows when the data was updated, or "Data
unavailable" when `npm run data` has not been run.

Open the address Vite prints, normally <http://localhost:5173/MotoSphere/>.
The application lives under `/MotoSphere/` everywhere, on your machine as on
the published site, because GitHub Pages serves a project's site under the
name of its repository (the path is set once, in `frontend/site.ts`). The page
shows the application's layout: a top bar, a sections panel, the globe area and a
details panel. The top bar shows when the data was updated and, next to it,
today's date, both in the language and time zone of your browser; the date
changes at midnight. The sections panel lists the
application's sections, and one can be chosen with the mouse or the keyboard;
there is no globe or data yet. The Sections and Details buttons in the top bar
close and open the side panels. On a narrow screen (under 900 pixels wide: a
phone, or a tablet held upright) an open side panel lies over the globe area
instead of standing beside it, and the top bar takes the lines it needs: the
name between the two buttons, then the data status and the date, without the
tagline. There the page opens with both side panels closed, so that the globe
area is in view, and only one panel is open at a time. Press Ctrl+C to stop the
development server.

The icon files in `frontend/public/` (`favicon.svg`, `favicon.ico` and
`apple-touch-icon.png`) are generated from the designs in `docs/design/icon/`
with `npm run icons`, and committed. Run it only when a design changes.

## Running the checks

Prerequisites: Python 3.12 or newer, Git and
[uv](https://docs.astral.sh/uv/getting-started/installation/). The frontend
checks also need Node.js 22.12 or newer.

Every check with one command, from any folder of the repository:

```
python scripts/check.py
```

It installs the locked dependencies, runs every gate in order and ends with a
summary; the exit code is 0 only when every gate passed.
`python scripts/check.py --list` shows the gates, and `--only` runs the ones
you name, for example `python scripts/check.py --only backend-tests`. The
gates are listed in [TESTING.md](TESTING.md). The last gate checks the
frontend's dependencies against published security advisories; an advisory
that is accepted for now is recorded, with its reason and a review date, in
`frontend/audit-exceptions.json`. GitHub runs the same command for every pull
request and every change to `main` (`.github/workflows/checks.yml`). The rest
of this section runs the same checks one at a time.

Repository checks, from the repository root:

```
python -m unittest discover -s tests/repo -v
```

Backend unit tests, from the repository root (the first command installs the
locked environment):

```
cd backend
uv sync --locked
uv run pytest
```

Backend lint and format checks, from `backend/`:

```
uv run ruff check .
uv run ruff format --check .
```

`uv run ruff format .` applies the formatting.

Backend type check (mypy, strict mode), from `backend/`:

```
uv run mypy
```

The same three checks for the Python files outside the pipeline (`scripts/`
and `tests/`), from the repository root. They use the tools installed for the
backend:

```
uv run --project backend mypy
uv run --project backend ruff check scripts tests
uv run --project backend ruff format --check scripts tests
```

`uv run --project backend ruff format scripts tests` applies the formatting.

Frontend lint (oxlint), format check (Prettier), unit tests, type check
(TypeScript, strict mode) and production build, from `frontend/` (run `npm ci`
first to install the locked dependencies):

```
npm run lint
npm run format:check
npm test
npm run typecheck
npm run build
```

`npm run format` applies the frontend formatting.

`npm run test:watch` re-runs the frontend tests whenever a file changes while
you develop.

Frontend browser tests, from `frontend/`:

```
npm run e2e
```

This first exports the published data, then builds the application, opens it
in a headless Chromium browser and checks the page a user would see, so it
needs uv as well. It needs port 4173 to be free. On a machine where
Playwright's Chromium has never been installed, run
`npx playwright install chromium` once first.

## Configuration

The backend reads its settings from environment variables whose names start
with `MOTOSPHERE_`, or from a `backend/.env` file. To use a file, copy
[backend/.env.example](backend/.env.example) to `backend/.env` and change the
values you need. The example file lists every setting with its default value.

- An environment variable always wins over the same setting in `backend/.env`.
- Every name in `backend/.env` must be a known setting. An unknown or misspelt
  name, such as `MOTOSPHERE_LOG_LEVLE`, stops the backend with an error naming
  it, instead of being silently ignored.
- Never commit `.env`. Git already ignores it.

| Variable | Default | Meaning |
|---|---|---|
| `MOTOSPHERE_ENVIRONMENT` | `development` | Where MotoSphere is running: development, test or production. |
| `MOTOSPHERE_LOG_LEVEL` | `INFO` | How much detail is written to the log: DEBUG, INFO, WARNING, ERROR or CRITICAL. |

Values for `MOTOSPHERE_ENVIRONMENT` and `MOTOSPHERE_LOG_LEVEL` are not
case-sensitive.
