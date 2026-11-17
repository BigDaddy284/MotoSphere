# Testing

This document records the testing strategy, commands and latest results.

## Rule

100% of applicable tests must pass before a task is accepted. A single failing
test means the task is not complete.

## Gates

One command runs every gate, in this order, from a clean checkout:

```
python scripts/check.py
```

It needs Python 3.12 or newer, Git, uv and Node.js, and nothing else: the
script itself uses the Python standard library only. Every gate runs even
when an earlier one failed. At the end it prints one line for each gate, with
`PASSED` or `FAILED` and the time it took, and the exit code is 0 only when
every gate passed. `python scripts/check.py --list` shows the gates without
running them, and `--only` runs the gates you name, for example
`python scripts/check.py --only frontend-lint frontend-tests`.

For the five gates that run tests, the runner reads the number of tests
passed, failed and skipped from the tool's own closing lines and shows them in
the summary, with a total for the run. Such a gate also fails when a test was
skipped, when no test ran, or when the numbers cannot be found: a test that
did not run has proved nothing, so it never passes unnoticed. Tests that are
expected to fail, marked as still to do or left out of a run count as skipped.

| Name | Gate | Command | Runs in |
|---|---|---|---|
| `repo` | Repository checks | `python -m unittest discover -s tests/repo -v` | repository root |
| `scripts` | Script tests | `python -m unittest discover -s tests/scripts -v` | repository root |
| `backend-lock` | Backend lock file | `uv lock --check` | `backend/` |
| `backend-install` | Backend install | `uv sync --locked` | `backend/` |
| `backend-types` | Backend type check | `uv run mypy` | `backend/` |
| `backend-lint` | Backend lint | `uv run ruff check .` | `backend/` |
| `backend-format` | Backend format | `uv run ruff format --check .` | `backend/` |
| `backend-tests` | Backend tests | `uv run pytest` | `backend/` |
| `tools-types` | Tooling type check | `uv run --project backend mypy` | repository root |
| `tools-lint` | Tooling lint | `uv run --project backend ruff check scripts tests` | repository root |
| `tools-format` | Tooling format | `uv run --project backend ruff format --check scripts tests` | repository root |
| `frontend-install` | Frontend install | `npm ci` | `frontend/` |
| `frontend-lint` | Frontend lint | `npm run lint` | `frontend/` |
| `frontend-format` | Frontend format | `npm run format:check` | `frontend/` |
| `frontend-types` | Frontend type check | `npm run typecheck` | `frontend/` |
| `frontend-tests` | Frontend unit tests | `npm test` | `frontend/` |
| `frontend-build` | Frontend build | `npm run build` | `frontend/` |
| `browser-tests` | Browser tests | `npm run e2e` | `frontend/` |
| `frontend-audit` | Frontend dependency audit | `python scripts/audit.py` | repository root |

A test compares this table with the script, so the two cannot drift apart.

The three tooling gates cover the Python files outside the pipeline: the
check runner in `scripts/` and the tests in `tests/`. They use the pipeline's
locked ruff and mypy, so nothing else needs installing, and they follow the
pipeline's rules: `ruff.toml` extends `backend/pyproject.toml`, and `mypy.ini`
is as strict. The one difference is that the rules about pytest style are
off, because these tests are written with `unittest`. A test fails when a
Python file appears outside the pipeline in a folder these gates do not cover.
`uv run --project backend ruff format scripts tests`, from the repository
root, applies the formatting.

The dependency audit (`python scripts/audit.py`) runs `npm audit` in
`frontend/` and fails on every security advisory it reports for an installed
package, whatever its severity and whether the package is part of the site or
only a build or test tool. The one way past it is an exception recorded in
`frontend/audit-exceptions.json`: the advisory's id, the package, the reason
in a sentence, the day it was accepted and a day, at most 31 days later, by
which it must be looked at again. Each exception in use is printed on every
run. The audit also fails when an exception is past its review day, when
nothing reports its advisory any more, when it names another package, and
when the file or npm's report cannot be read, so the list can neither grow
stale nor switch the check off. Record an exception only when no fixed
version can be installed and the reason holds for this project; otherwise
update the package.

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

The build under test is served under `/MotoSphere/`, the path the site has on
GitHub Pages (`frontend/site.ts`), and nothing is served at the root of the
test server. A browser test therefore writes addresses relative to the site
(`page.goto('./')`, `request.get('favicon.svg')`), never from the root. Tests
of their own (`e2e/site.spec.ts`) check that everything the page loads comes
from under that path.

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
They also check the workflows described below.

## Continuous integration

GitHub runs every gate for each pull request and for each change to `main`,
on a Linux machine and on a Windows machine. The workflow is
`.github/workflows/checks.yml`. It does nothing of its own: on each machine
it installs Python, uv, Node.js and the browser for the browser tests, and
then runs `python scripts/check.py`, the same command as on a developer's
machine. A job fails when the command does, and its log ends with the same
summary. Each machine gives its own result, "All gates (Linux)" and "All
gates (Windows)": one failing does not stop the other.

The jobs use Python 3.12, the oldest version the pipeline supports, so that
nothing newer slips into the code unnoticed.

The workflow is given as little as possible, and the repository checks hold
it to that:

- Its token can only read the repository, and it uses no secret. The one
  job that publishes the site (see "Deployment") is given the right to
  publish to GitHub Pages and nothing else.
- Every action is pinned to a full commit, with its release beside it, and
  only actions on a short list may be used. To update one, change the commit
  and the release together.
- It never runs with the repository's rights on code from outside
  (`pull_request_target`), and no text from outside, such as the title of a
  pull request, reaches a command.
- No step may be skipped or allowed to fail, and every step runs one
  command: on Windows, a step with several commands only fails on its last
  one. The only condition in the workflow is the one that keeps the two
  publishing jobs to changes to `main`.

## Deployment

For a change to `main`, and only when every gate passed on both machines,
the same workflow publishes the site on GitHub Pages, at
<https://bigdaddy284.github.io/MotoSphere/>. Two more jobs do it:

- "Build the site" exports the published data (`npm run data`), builds the
  application (`npm run build`) and hands the result, `frontend/dist`, to
  the next job. It can only read the repository.
- "Publish the site" is the only job that may publish. It checks out
  nothing and runs no command of its own: it takes the site the other job
  built and hands it to GitHub Pages, through the `github-pages`
  environment.

A pull request never publishes: both jobs are skipped there, and the
workflow starts for nothing but pull requests and changes to `main`. Runs
for `main` go one at a time, in order, so an older commit never replaces a
newer one on the site; a run that is still waiting gives way to a newer
one. The repository checks hold the workflow to all of this, together with
the rules above.

## Latest results

Results are recorded per task in [PROGRESS.md](PROGRESS.md).
