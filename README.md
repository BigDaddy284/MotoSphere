# MotoSphere

The World of Motocross, Connected.

MotoSphere is a global motocross information platform centred on an
interactive 3D Earth. It is intended to discover, collect, organise and present
freely accessible information about motocross tracks, events, championships,
race results, riders and teams worldwide, so that people can explore the sport
directly from the globe.

## Status

Early development. There is no application to run yet; the repository
currently holds the project documentation, the repository checks and a backend
Python package skeleton with its unit tests.

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

## Running the checks

Prerequisites: Python 3.12 or newer, Git and
[uv](https://docs.astral.sh/uv/getting-started/installation/).

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
