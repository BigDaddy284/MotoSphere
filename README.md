# MotoSphere

The World of Motocross, Connected.

MotoSphere is a global motocross information platform centred on an
interactive 3D Earth. It is intended to discover, collect, organise and present
freely accessible information about motocross tracks, events, championships,
race results, riders and teams worldwide, so that people can explore the sport
directly from the globe.

## Status

Early development. The backend API can now be started and answers a health
check. There is also a frontend skeleton that shows the application name; it
does not talk to the backend yet and has no globe. The repository holds the
project documentation, the repository checks, the backend Python package with
its tests and the frontend project.

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

## Running the API

Prerequisites: Python 3.12 or newer and
[uv](https://docs.astral.sh/uv/getting-started/installation/).

From the repository root:

```
cd backend
uv sync --locked
uv run python -m motosphere
```

While it is running, the health check is at
<http://127.0.0.1:8000/api/health> and the interactive API documentation at
<http://127.0.0.1:8000/api/docs>. Press Ctrl+C to stop the server. To use a
different host or port, change the settings described in
[Configuration](#configuration).

## Running the frontend

Prerequisites: [Node.js](https://nodejs.org/) 22.12 or newer, which includes
npm.

From the repository root:

```
cd frontend
npm ci
npm run dev
```

Open the address Vite prints, normally <http://localhost:5173>. The page shows
the application name; it does not use the API yet. Press Ctrl+C to stop the
development server.

## Running the checks

Prerequisites: Python 3.12 or newer, Git and
[uv](https://docs.astral.sh/uv/getting-started/installation/). The frontend
checks also need Node.js 22.12 or newer.

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

Frontend type check (TypeScript, strict mode) and production build, from
`frontend/` (run `npm ci` first to install the locked dependencies):

```
npm run typecheck
npm run build
```

## Configuration

The backend reads its settings from environment variables whose names start
with `MOTOSPHERE_`, or from a `backend/.env` file. To use a file, copy
[backend/.env.example](backend/.env.example) to `backend/.env` and change the
values you need. The example file lists every setting with its default value.

- An environment variable always wins over the same setting in `backend/.env`.
- Every name in `backend/.env` must be a known setting. An unknown or misspelt
  name, such as `MOTOSPHERE_API_PROT`, stops the backend with an error naming
  it, instead of being silently ignored.
- Never commit `.env`. Git already ignores it.

| Variable | Default | Meaning |
|---|---|---|
| `MOTOSPHERE_ENVIRONMENT` | `development` | Where MotoSphere is running: development, test or production. |
| `MOTOSPHERE_API_HOST` | `127.0.0.1` | The network address the API listens on. The default only accepts connections from this computer. |
| `MOTOSPHERE_API_PORT` | `8000` | The port number the API listens on, from 1 to 65535. |
| `MOTOSPHERE_LOG_LEVEL` | `INFO` | How much detail is written to the log: DEBUG, INFO, WARNING, ERROR or CRITICAL. |

Values for `MOTOSPHERE_ENVIRONMENT` and `MOTOSPHERE_LOG_LEVEL` are not
case-sensitive.
