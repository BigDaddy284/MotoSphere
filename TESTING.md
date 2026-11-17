# Testing

This document records the testing strategy, commands and latest results.

## Rule

100% of applicable tests must pass before a task is accepted. A single failing
test means the task is not complete.

## Gates

| Gate | Command |
|---|---|
| Repository checks (`tests/repo`) | `python -m unittest discover -s tests/repo -v` |
| Backend unit tests (`backend/tests`) | `cd backend && uv run pytest` |
| Backend lint | `cd backend && uv run ruff check .` |
| Backend format | `cd backend && uv run ruff format --check .` |
| Backend type check | `cd backend && uv run mypy` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend format | `cd frontend && npm run format:check` |
| Frontend unit tests (`frontend/src/**/*.test.tsx`) | `cd frontend && npm test` |
| Frontend type check | `cd frontend && npm run typecheck` |
| Frontend build | `cd frontend && npm run build` |

The backend suite includes integration tests that start the real API server on
a free local port and call it over HTTP.

Frontend tests sit next to the code they test and query the page by role and
text, the way a user perceives it.

Before the backend unit tests, `uv sync --locked` (run in `backend/`) installs
the locked environment, including the `motosphere` package itself.

Before the frontend gates, `npm ci` (run in `frontend/`) installs the locked
dependencies from `package-lock.json`.

The repository checks use the Python standard library only and need nothing
but Python 3.12 or newer and Git. They verify the required documents, ignore
rules, line-ending attributes, that no secret or environment file is tracked,
the `.editorconfig` baseline, README links and the changelog layout. Tests that
inspect tracked files read the Git index, so stage changes before running them.

## Latest results

Results are recorded per task in [PROGRESS.md](PROGRESS.md).
