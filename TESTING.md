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
| Browser tests (`frontend/e2e`) | `cd frontend && npm run e2e` |

The backend suite includes integration tests that run the real command line
(`python -m motosphere`) as a separate process.

Frontend tests sit next to the code they test and query the page by role and
text, the way a user perceives it.

The browser tests run with Playwright in headless Chromium against the
production build, served locally. Every browser test also fails if the page
logs an error or warning, throws an uncaught error, or has a failed request or
an HTTP error response. A test about a failure names the problems it expects
with `expectProblem`; it then fails if one of them does not happen, and still
fails on any other. The rule has tests of its own (`e2e/fixtures.spec.ts`).

Before it builds, the browser tests' server exports the published data with
the real export command, so the tests check the served manifest with the
frontend's own reader and check that it was exported for this run. The browser
tests therefore need uv as well as Node.js.

The data status in the top bar is tested in the browser against that data, and
with replaced answers for a slow, damaged or newer manifest, a manifest the
server does not have, a failed request and other time zones.

The theme's colours are the owner's Graphite theme
(`docs/design/graphite-theme/`), defined once in
`frontend/src/styles/tokens.css`. A unit test checks each Graphite token
against the owner's exact value. Contrast is tested per colour on the surfaces
it is used on (7:1 for main text, 4.5:1 for secondary text, links and status
colours, 3:1 for disabled text and for the sky blue on the pressed and
selection colours). White on the accent blue measures 3.89:1, which meets 3:1
but not 4.5:1, so that pair is limited to bold button labels. The tests also
reject raw colours or unknown tokens in any style sheet under `frontend/src`.
Browser tests check the applied theme colours and font stack, the keyboard
focus ring and reduced motion. The browser tests also check the icon files as
served: the page's links, the content types, the sizes of the images, the
colours of chosen pixels, and that the designs hold nothing that runs or loads.

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
