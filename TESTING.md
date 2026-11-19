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

A browser test waits for what it checks. A check that does not wait, on
something the test collected while the page ran (the requests it recorded
or held back, the problems the page reported), is right only for what must
have happened before the thing the test waited for last: by the time the
page shows the data, it has asked for it. Where there is no such order, the
test waits for the value itself (`expect.poll`). One test did not
(FND-043): it expected the request for the data to have arrived as soon as
the page said "Loading data…", which the page says before it asks, and so
it could fail by chance.

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

The browser tests measure the layout at two desktop sizes and at five narrow
ones, from 320 to 899 pixels wide (`frontend/e2e/narrow.spec.ts`): where each
region is, which one is on top, and that the page itself does not scroll. At
the narrow sizes they also measure everything the top bar shows: each piece
must be whole, on one line, inside the bar and clear of the others. There
they also open and close the side panels with the buttons, as a visitor
does, load the page again, and change the width of the window across the
line between narrow and wide.

The test environment of the unit tests has no screen, so
`frontend/src/test/screen.ts` stands in for the part of the browser that
knows how wide the screen is. Every unit test starts with a wide screen; a
test changes the width with `showScreen(pixels)`.

The browser tests also run with a touch screen
(`frontend/e2e/touch.spec.ts`), at phone and at desktop size: every button
in the top bar and every section must be 44 pixels tall and at least as
wide, each button exactly in the middle of the bar's first line, and the
top bar no taller for it. The same tests with a mouse check that the sizes
stay as they were.

The test browser has no bars that come and go, so no test can show what
the layout does under a phone's address bar. The tests check what can be
checked: that the style sheets, as the browser received them, ask for the
height of the visible screen (`frontend/e2e/height.spec.ts`), that the
layout is exactly as tall as the screen at phone size, turned on its side,
and at desktop size, and, as a unit test, that no style sheet measures by
the height of the whole screen. The effect on a real phone is confirmed by
the owner on the published site.

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
  one. The only condition in the workflow is the one that keeps the three
  jobs that publish the site and check it to changes to `main`.

## Deployment

For a change to `main`, and only when every gate passed on both machines,
the same workflow publishes the site on GitHub Pages, at
<https://bigdaddy284.github.io/MotoSphere/>, and then checks what was
published. Three more jobs do it:

- "Build the site" exports the published data (`npm run data`), builds the
  application (`npm run build`) and hands the result, `frontend/dist`, to
  the next job. It can only read the repository.
- "Publish the site" is the only job that may publish. It checks out
  nothing and runs no command of its own: it takes the site the other job
  built and hands it to GitHub Pages, through the `github-pages`
  environment.
- "Check the published site" takes the site the first job built and
  compares the published address with it (see below). It can only read. A
  deployment that leaves the site broken, incomplete or older than this
  run turns the run red.

A pull request never publishes: all three jobs are skipped there, and the
workflow starts for nothing but pull requests and changes to `main`. Runs
for `main` go one at a time, in order, so an older commit never replaces a
newer one on the site; a run that is still waiting gives way to a newer
one. The repository checks hold the workflow to all of this, together with
the rules above.

That GitHub accepted a deployment does not say what a visitor gets, so the
last job looks at the site itself. One command compares a published site
with the site that was built:

```
python scripts/live.py <site.tar> <address>
```

`site.tar` is the built site as "Build the site" hands it over, and the
address is where it is published, ending with a slash. The script asks the
address for every file of the built site, and for the address itself, which
must answer with the page. Each answer must be there (status 200, with no
redirect), be served as the right kind of content, and match the built
file byte for byte. The data manifest names the moment it was exported, so
an older deployment never matches. A new deployment takes a moment to reach
every server, so the script tries again every 10 seconds for up to 5
minutes before it fails, and then names each file that is wrong. It uses
the Python standard library only and accepts an address without encryption
only on this computer. Its tests (`tests/scripts/test_live.py`) run it
against a small web server on this computer and reach nothing else.

When "Check the published site" fails, its log names each file that is
wrong. The site may then be broken for visitors: the run for the next
change to `main` publishes and checks again, and starting the failed job
again repeats the check alone.

## The data store's SQLite

Every Python carries its own SQLite, and the builds differ. The data store
relies on a least version and six features (`motosphere.db.sqlite`,
[DATABASE.md](DATABASE.md)). Two kinds of test hold that, both part of the
backend tests. `tests/integration/test_sqlite_on_this_machine.py` asks the
machine's own SQLite, unchanged, and fails when it lacks anything: that is
the proof for each machine the gates run on, Linux and Windows.
`tests/unit/test_db_sqlite.py` makes the real SQLite behave like a lesser
one (an older version, a build without a feature, one that does not enforce
what it accepted) and checks that each is reported in plain words. Two of
its tests compare the module with `DATABASE.md`, so the decision record and
the code cannot drift apart.

## Opening the data store

`tests/integration/test_store.py` opens a real SQLite file in the test's own
temporary folder through `open_store`, the function the pipeline uses, and
nothing in it is a mock. It checks what the function promises
([DATABASE.md](DATABASE.md)): a row without its parent is refused on the
first connection, on later ones, on two at once and after the store is
opened again; work that fails is taken back, a new table included; every
connection is closed after use and the file can then be removed (which is
what fails on Windows when one is left open); and each way the store can be
refused gives its one plain sentence and writes nothing.

## Units of work

`tests/integration/test_work.py` does units of work on a real SQLite file
in the test's own temporary folder, opened through `open_store`; nothing in
it is a mock. Its two small tables are the test's own. It checks what
`unit_of_work` promises ([DATABASE.md](DATABASE.md)): work that ends is
there for the next unit and when the store is opened again; work that fails
leaves no row and no new table, whatever ended it; the error reaches the
caller unchanged; a row without its parent ends the whole unit; one
connection is used and closed, and the file can then be removed; a commit
part-way is refused; and a session cannot be used after its unit has ended.

## Migrations

`tests/integration/test_migrations.py` runs the migration runner on the
real SQLite file the fixture `store` gives each test; nothing in it is a
mock. The migrations are the tests' own, small ones that make and rename
tables. It checks what `migrate` promises ([DATABASE.md](DATABASE.md)):
every migration is applied in order, and only those a store lacks;
migrating twice changes nothing; the version is there when the store is
opened again; a migration that fails, or is stopped from outside, leaves
the store at the version before it and its error reaches the caller
unchanged; a migration and its version are one transaction; and a store
whose version the code does not know is refused in plain words and left as
it is. One test brings an empty store to the newest schema with the
pipeline's real list of migrations, and so tests every migration that is
ever added. Three more build a table anew inside a migration while rows
point to it, which is how a migration makes a change SQLite cannot make in
place.

## A data store of its own for every test

A backend test that needs the data store asks for the fixture `store`
(`backend/tests/conftest.py`). It gets the engine of a real SQLite file,
`store.sqlite3` in the test's own temporary folder, opened through
`open_store` as the pipeline opens its store, and empty. No two tests share
a file, so tests can write the same keys and run in any order. The store is
never a mock.

A test must close what it opens (`with store.connect() …`,
`with unit_of_work(store) …`). A connection it leaves open is closed for it
when the test ends, so that the file can be removed on Windows too, and the
test is reported as an error: "Connections to its store that the test left
open: 1. They were closed for it." A connection that was dropped without
being closed counts too. That way a leak in the code under test fails the
test that found it, and not a later one.

`tests/integration/test_store_fixture.py` tests the fixture. For what
happens after a test has ended, it lets pytest run a small file of tests in
a process of its own (pytest's `pytester`), four of which leave
connections open, and reads the outcome.

## The tools a computer needs

`python scripts/tools.py` says whether a computer has the five tools the
gates and the application need (Python, Git, uv, Node.js and npm), which
version of each it found, and whether Python and Node.js are as new as the
project asks. The least versions are read from `backend/pyproject.toml` and
`frontend/package.json`, so each is written once. It is not a gate: a gate
whose tool is missing fails by itself and says so. Its tests
(`tests/scripts/test_tools.py`, part of the script tests) read lines the
real tools printed, ask the real Python for its version, run the script on
the computer that runs the tests, where all five tools must be ready, and
run it once with a search path that holds no tool.

## Latest results

Results are recorded per task in [PROGRESS.md](PROGRESS.md).
