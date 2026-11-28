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

The browser tests are in two projects. The tests of the globe are the
files in `frontend/e2e/globe`: they run in a browser that is told how to
draw 3D pictures, and one at a time. Every other test is in the project
`chromium`, whose browser gives a page no 3D picture (see "The browser
of the globe tests").

A browser test waits for what it checks. A check that does not wait, on
something the test collected while the page ran (the requests it recorded
or held back, the problems the page reported), is right only for what must
have happened before the thing the test waited for last: by the time the
page shows the data, it has asked for it. Where there is no such order, the
test waits for the value itself (`expect.poll`). One test did not
(FND-043): it expected the request for the data to have arrived as soon as
the page said "Loading data…", which the page says before it asks, and so
it could fail by chance.

A browser test that measures the page waits first for whatever changes
what it measures. Once the data has arrived the data status has longer
words than while it loads, so it is wider and what stands beside it lies
elsewhere; until FND-049 the top bar of a narrow screen was also a line
taller then, and everything under it lay a line lower. So the tests of
the narrow screen (`e2e/narrow.spec.ts`) load the
page in two places only: `open`, which waits until the top bar says when
the data was updated, and `again`, which loads the page again and waits
for the same. A test of the file holds that there is no third place. Five
tests did not wait (FND-048). Two measured the top bar first and waited
afterwards, and failed whenever the data came later than the measurement:
with the data a second late, every time. Three measured the top bar and
then what lies under it, and failed when the data came between the two.
Three tests hold the data back for a second and check that `open` and
`again` have waited: the data status is there at once, and the top bar
has the height it has with the data.

The build under test is served under `/MotoSphere/`, the path the site has on
GitHub Pages (`frontend/site.ts`), and nothing is served at the root of the
test server. A browser test therefore writes addresses relative to the site
(`page.goto('./')`, `request.get('favicon.svg')`), never from the root. Tests
of their own (`e2e/site.spec.ts`) check that everything the page loads comes
from under that path.

An address under that path that names no file is answered with "not found"
(404), as GitHub Pages answers it, and not with the page (FND-052). Until
then the server of the build under test answered every such address with
the page and the status 200, so a test that asked for a file the build had
left out got an answer, and the file would have been missing on the
published site only. Thirteen tests of `e2e/site.spec.ts` hold it: nine
ask for an address that names no file (a name without an ending, with the
ending of a picture and with that of a page; in a folder that is not
there, in `data/` and in `assets/`; the two folders themselves; and a path
that goes on past the file of the page), and each is answered 404, at its
own address, with something that is not the page; three hold that the page
is still answered, at the path itself, at `index.html` and at the path
with a question after it; and one opens such an address in the browser,
which is told "not found" and shows no top bar. The server of the build
under test is still not GitHub Pages: it answers a file's address with a
slash after it with the file, for one. The check of the published site
(`scripts/live.py`) is what asks GitHub Pages itself.

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

That nothing moves when the data arrives is held by tests of their own
(`frontend/e2e/arrival.spec.ts`, FND-049), at seven narrow sizes from 320
to 899 pixels wide and at one desktop size. Each holds the data back,
measures the top bar, the globe stage and every piece of the top bar while
the page says "Loading data…", lets the data through and measures again:
the top bar and the stage are where and as large as they were, to the
pixel, and every piece is whole, on one line, inside the bar and clear of
the others both times. From 360 pixels on the height of the bar is also
held to its number: the first line, one line of information from 640
pixels on and two below, and the room under them. The same is measured
when the data cannot be loaded, with each of the two things the page then
says. Two tests stand one pixel on either side of the 640: below it each
piece of information has a line of its own, from it on the two share one,
before and after the data arrives. Three tests make the words too long
for their line, by setting the letters far apart on a day with a long
date: on a shared line the data status stays whole and the date is cut
short; a data status too long for the line by itself ends at its edge;
and where each piece has its own line, each ends at the edge. In all
three the bar is as tall as ever and the pieces are on one line each.
These tests load the page before the data is there on purpose, which the
tests of `narrow.spec.ts` must not do.

The test environment of the unit tests has no screen, so
`frontend/src/test/screen.ts` stands in for the part of the browser that
knows how wide the screen is. Every unit test starts with a wide screen; a
test changes the width with `showScreen(pixels)`.

The test environment gives a page no picture to draw on either, so
`frontend/src/test/drawing.ts` stands in for that part of the browser
(GLB-026). Every unit test starts in a browser that gives both kinds of 3D
picture; a test makes it another browser with `browserGives(kinds)`. What
the stand-in gives can be given back and nothing more: no unit test draws.
It says which kinds the page asked for (`picturesAskedFor()`) and how many
pictures the page holds that it has not given back (`picturesHeld()`).

The real engine of the globe draws, which the test environment cannot, and
takes its time to load. So `frontend/src/test/engine.ts` stands in for it
in the unit tests of what shows a globe (GLB-027; see "The life of the
globe"). `standInEngine()` gives a way to load the engine that a test hands
to a globe. A loading ends when the test says so, well (`arrives()`) or
badly (`fails(why)`), and both come back only when everything that waited
on the loading has run. The stand-in says how often it was asked for
(`loadings()`), in which elements engines were started, whether each was in
the page then and how often each was stopped (`engines()`), and where an
engine is running now (`running()`). A test can make it one that cannot be
started (`breaksAtTheStart(why)`). An engine that was started says that its
first complete picture is drawn when the test says so (`draws()`, for the
engine started first or the one named), at once, stopped or not, and as
often as the test has it say so (GLB-029). Nothing of the real engine is in
it.

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

The step that runs the gates is told where temporary files go: `TEMP` and
`TMP`, the two names Windows has for that folder, are set to the runner's
own folder for temporary files (`runner.temp`). Tests make their files in
the system's folder for temporary files, and the tests of the pipeline make
a real store there for each test that needs one. On GitHub's Windows machine
that folder is on the system disk (`C:`); the checkout and the runner's
folder are on the work disk (`D:`). Measured on that machine on 2026-11-27,
both ways in one job (run 46020195509):

| | System disk | Work disk |
|---|---|---|
| One saved change to a store | 19.40 ms | 1.01 ms |
| A store made and given every migration | 385.8 ms | 33.5 ms |
| The 2420 tests of the pipeline | 635.19 s | 81.99 s |

On the system disk single tests waited 20 to 70 seconds for their store, and
the time differed much from run to run: 2237 tests took 814 s in one run for
`main` and 2277 tests 423 s in a later one. As the tests of the pipeline
grew in number, the Windows job came to its limit of 20 minutes and was cut
off there, four times on that day, with no test failed. The limit is left as
it is.

On Linux, Python and Node.js look at `TMPDIR` first and at these two names
when it is not set, and it makes no difference there which folder it is. A
developer's machine is told nothing: there the tests keep their files where
the system says.

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
- Only the step that runs the gates is told anything through its
  environment, and only where its temporary files go.

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

The check has a rule for every kind of file the site is made of: what a
browser must be told a page, a script, a style sheet, a JSON file, an XML
file, a text, a picture of each of four kinds and a program for the
browser's own machine (`.wasm`) is. A browser compiles such a program while
it arrives only when it is served as `application/wasm`, and a text served
as anything but text is offered for saving and not shown. For the four
kinds that came with the engine of the globe and the list of the licences,
what GitHub Pages says a file is was read from the published site on
2026-11-27 and not assumed: `application/wasm`, `image/jpeg`,
`application/xml` and `text/plain`. `frontend/e2e/siteKinds.json` lists
the kinds, each by the end of a file's name. A browser test
(`e2e/site.spec.ts`) holds that list to the site as it was built for the
run, and a test of the check holds the check's rules to the list: a rule
for every listed kind, and none for another. A site that gains a kind of
file so fails the gates until the kind is listed and has its rule, before
anything is published.

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

Seven tests are for the mark that says a file is a store of MotoSphere's.
The files that are not MotoSphere's are made with SQLite alone, as another
program would make them: one with a table, one with a view, one with a
version and one with the mark of another application. Each must be refused
with its exact sentence, and the file must be byte for byte as it was. The
others read the mark where SQLite keeps it, in four bytes of the file's
header, and check that a first migration that fails, and a store that
lacks no migration, leave a new file exactly as it was.

Ten tests are for `pending`, which says what a store lacks: a new store,
one that has had some of the migrations and one that is up to date; that
asking commits nothing and leaves the file byte for byte as it was; that
`migrate` then applies exactly what was named; and that each store
`migrate` refuses (a table and no mark, the mark of another application,
a newer store, a version below zero) is refused by `pending` in the same
words.

The command `migrate` is tested in three places. `test_command_line.py`
runs it in a process of its own, with the pipeline's own list of
migrations: a store that is not there is made, a second run changes
nothing, and the database of another program and a file that is no
database are each refused with one line on standard error, the exit code 1
and the file byte for byte as it was. The pipeline's list is still empty,
and a process of its own cannot be given another, so
`tests/integration/test_migrate_command.py` calls the command in the
test's process with a list of the test's own in the place of the
pipeline's; the store is a real file there too, and nothing else is
replaced. It checks each of the three sentences, a store newer than the
code, and that an error inside a migration reaches the caller.
`tests/unit/test_cli_migrate.py` checks the sentences by themselves and
the command's help.

The command `schema` is tested in the same three places
(`test_command_line.py`, `tests/integration/test_schema_command.py` and
`tests/unit/test_cli_schema.py`). It must never write, so every test that
gives it a file compares the file byte for byte afterwards, the tests of a
store that is read also look for anything new beside it, and the tests
without a file look for the file and its folder afterwards. Each store
`migrate` refuses is given to both commands, and what `schema` says must
be what `migrate` says, word for word.

The store a command works on (`store_to_work_on`, DAT-063) is tested in
`tests/integration/test_store_to_work_on.py`, 16 tests against a real
SQLite file that the real `migrate` command or SQLite alone made, most
of them with a list of migrations of the test's own in the place of the
pipeline's, so that a store can lack some. A store at the newest schema
is given, opened as every store is opened, and a unit of work on it is
kept; so is one at the newest schema of the pipeline's own list. Where
there is no file, none is given and none is made, nor its folder. A
store that lacks one, two or three migrations is not given and is not
given them. Each store `migrate` refuses is refused in the words
`migrate` then says, a file that is no database and a folder in the
store's place in one line each. A relative path is taken from the
current folder. Every test of a refusal compares the file byte for byte
afterwards. Two tests remove the file after the function was asked,
once refused and once given: Windows removes no file that a connection
still holds. `tests/unit/test_cli_store.py` holds the advice to the
command line's own name.

The command `countries` (DAT-061) is tested in the same three places as
`migrate` and `schema`. `tests/integration/test_countries_command.py`,
17 tests, calls it in the test's process against a real SQLite file
that the real `migrate` command made with the pipeline's own
migrations, and with the reference file that comes with the pipeline;
what the command leaves in the store is read with SQLite alone, and
what it must leave as it is was written the same way. On a new store
the 249 countries of the file are there afterwards, each as the file
has it, with their one source. Run again, the command adds nothing and
the file is byte for byte as it was. Countries that were taken out are
added again; a country whose name or code was changed by hand is named,
left as it is, and waits in the review queue; a country the release
does not have is named and left. Each refusal (no store, a store that
lacks a migration, a file `migrate` would refuse, a damaged countries
file, a source described otherwise) gives one line on standard error,
the exit code 1 and a file that is byte for byte as it was. One test
has the store itself refuse the last country of the file, with a
trigger, and finds none of the 248 before it in the store: the loading
is one unit of work. One test runs the command with the making of a
network socket taken away. `test_command_line.py` runs the command in a
process of its own, twice on a new store and once without one.
`tests/unit/test_cli_countries.py`, 17 tests, holds the sentences by
themselves, with none, one and several countries of each kind, and the
command's help. Three tests of the help of the other commands no longer
count the blanks between a command's name and what it does: a longer
name moves that column.

## The rules every table keeps

`backend/tests/integration/test_base.py` has two models of its own,
subclasses of the real `Base`, and makes their tables in a real SQLite
file. It then asks the file, not the models: that both tables are strict
(the one whose model says something of its table too), that a value of
the wrong type is refused in four ways, which type each column has, and
what every constraint and index is called. The names are written out in
the test, so they are checked on Linux and on Windows. The two models are
kept in a schema of their own, so the real schema never sees them. Two
more models there break the rule of the names (DAT-038), each in a schema
of its own: one gives one name to two of its checks, and one says one
index twice. The real SQLite file takes the first table and keeps both
checks: each refuses a row, with the same words, which name the one name
and not which check. It refuses the second table, as an index of that
name is already there. `broken_rules` names both models.

`backend/tests/unit/test_db_base.py` tests `broken_rules` with tables made
for each test: a schema that keeps the rules, a table that is not strict,
six tables without the key every table has (no key, a key of another name,
of two columns, of text, one that is the key of another table, and one that
may be given twice), nineteen tables without the two times every table has
(none, one of the two missing, and for each of the two: of another type, one
that may be empty, one the table sets itself, one the store's code does not
set, one that is one fixed moment, one that SQLite is asked for; a
`created_at` that is set anew at a change, an `updated_at` that is not, one
that a change sets to one fixed moment, and one that a change asks SQLite
for), five columns whose text must not be empty and that are without their
check (no check, the check under another name, and three checks of the right
name that say something else), three ways of writing the check that count
(as `not_empty` gives it, with the table's column, and as text), that the
columns of a table are named in their order, a unique constraint, a foreign
key and an index named by hand, the order of the sentences, and that a check
without a name is refused when its table is defined. Four functions ask the
rule about a name that more than one constraint or index of a table has
(DAT-038): it is named, and how many have it, for two checks, three checks, a
column that is unique and said so twice, an index said twice and a foreign
key said twice; names given twice are listed once each, by the alphabet and
after everything else, also one given by hand, with the constraints of the
table put in the opposite order first; one name in two tables is not named;
and a column with two checks of the name of its own check is judged the same
whichever of the two comes first, in four cases (one of the two is its check
or neither is, each in both orders). Four more functions ask
the rule about a column type of the tests' own that brings a check
(DAT-034): a column of it is named, in that type's own words, until its
table has the check; the check of one type does not count for a column of
another, in four ways; columns of the two types in one table are named in
their order, each in its own type's words; and a type that says it brings a
check and gives none is an error, for the rule and when a model with a
column of it is defined. A table that must keep the rules gets its key and
its two times from two helpers of the tests, `the_key` and `the_times`. One
test there holds the real schema to the rules: `broken_rules(SCHEMA)` must
be empty, where `SCHEMA` is the whole schema (`motosphere.db.models`). It
is the test that fails when a table is added that breaks a rule.

`backend/tests/integration/test_key.py` has two models that name no key,
one of which says something of its table itself, and makes their tables
in a real SQLite file. It asks the file which column is the key and how
the key is written, and then deletes rows and stores new ones: the key of
a deleted last row is not given again, nor any key after every row is
deleted, nor after the store was closed, nor to a row written with plain
SQL past the model. A row stored with a key of its own keeps it, and
later keys come after it.

`backend/tests/integration/test_row_times.py` has a model that names no
time and makes its table in a real SQLite file. With the clock set (see
"The clock of a test" below) it stores and changes rows and reads the two
times the file holds with plain SQL, past the model: a new row has the one
moment the clock said in both columns; a changed row has a new
`updated_at` and its old `created_at`; a row stored again as it was keeps
both, and the clock was not asked; rows stored together in three ways each
get one moment of their own; rows changed by one statement all say when; a
row stored with times of its own keeps them. It also shows where this
ends: a row written with plain SQL without its times is refused, and a
change written with plain SQL, or by a statement that stores a row or
changes the one that is there, leaves `updated_at` as it was. One test
runs without a set clock and expects the moment it is.

## Times in the store

`backend/tests/unit/test_db_times.py` tests the form itself, without a
store: what a UTC time and a time with another offset are written as, that
every text has the same length and that the order of the texts is the
order of the times, each kind of value that is refused (a time without an
offset, a zone that gives none, a time UTC cannot say, a date, text, a
number) with its whole sentence, and twelve texts that are nearly in the
store's form and are refused when read. Two tests are of the store's
clock: that `now()` says the moment it is, in UTC, and that a clock a
test set says what the fixture promises.

`backend/tests/integration/test_times.py` has a model of its own with two
columns of a time, one of which may be empty, and makes its table in a
real SQLite file. It reads the text the file holds with plain SQL, past
the model, and compares it letter for letter; it stores the same moment in
five offsets; it sorts and finds rows by a time in the database; it asks
SQLite's own date functions what moment the text is; and it puts text of
another form into the file with plain SQL and expects the refusal when the
model reads it. A naive time (one without an offset) is made in a test
with `.replace(tzinfo=None)`, since the lint refuses to write one out.

## Calendar days in the store

`backend/tests/unit/test_db_days.py` tests the form itself and the type,
without a store: what seven days from the first there is to the last are
written as, and that each is read back as a day and not as a time at its
midnight; that every text has the same length and that the order of the
texts is the order of the days; each kind of value that is refused on
the way in (text, a number, no value) with its whole sentence, and a
time in three kinds (a time, midnight in UTC, midnight without an
offset) with the sentence a time gets; fifteen things that are not in
the store's form and are refused when read, two of them text Python
could read as a day; that no value stays no value; that the type is TEXT
in a table; the text of the check as SQLite is given it, also for a
column named with a word of SQL, and its name before and after the
naming rule; that the type brings exactly that check, with its two words
for `broken_rules`; the sentence of `broken_rules` for a table made by
hand, until the table has the check; and that to `Base` a `date` is a
day and a `datetime` is still a time.

`backend/tests/integration/test_days.py` has a model of its own with
three such columns, one that may be without a value and one with a value
of its own, and a column of a time beside them. It makes the table in a
real SQLite file and asks the file which columns there are and reads the
three checks as the file says them, letter for letter. Then it stores
rows and reads with plain SQL, past the model, what the file holds and
of which kind it is: a day is text in the one form and comes back as the
day, seven of them from the first day there is to the last; no value is
stored as none; a change is stored; what is not a day is refused in four
kinds, two of them times, and the row stored with it in the same unit of
work is not there either; twenty texts that are not a day, written with
plain SQL, are each refused with the name of the check, word for word,
the 30th of February, the year 0 and the word `now` among them; every
such column refuses what is not a day; a number is refused by the check
and bytes because the table is strict; a change to what is not a day is
refused and the row stays as it was; rows are found by a day, by the
days before and after it and in the order of the days; a question with
a time is refused; what is read through the type and is no day is
refused; SQLite's own date functions read a stored day; and a time
beside a day is stored as a time. One more model names SQLAlchemy's own
type for a day, and SQLite refuses to make its table. A naive time (one
without an offset) is made with `.replace(tzinfo=None)`, since the lint
refuses to write one out. The models are kept in schemas of their own.

## Text that must not be empty

`backend/tests/unit/test_db_texts.py` tests the check without a store:
that the list of white space is exactly what Python calls white space
(every character there is is asked) and what `str.strip` takes off, the
text of the check as SQLite is given it, also for a column named with a
word of SQL, its name before and after the naming rule, that the type
brings exactly that check, with its two words for `broken_rules`, and
that the type is TEXT in a table.

`backend/tests/integration/test_texts.py` has two models of its own, one
of which says something of its table itself, and makes their tables in a
real SQLite file. It asks the file which columns there are and reads the
checks as the file says them, by name and letter for letter. Then it
stores rows: text that is not empty comes back as it was given, in six
kinds; empty text is refused with the name of the check, in nine kinds,
and the row stored with it in the same unit of work is not there either;
each of the 29 white space characters alone is refused, and each is kept
around text; a row written with plain SQL and a change in three ways are
refused; a column that may be without a value takes none and refuses
empty text; every such column has a check of its own; and text that may
be empty is stored empty, as before. The odd characters are written in
the tests as their numbers, not as themselves, so that an editor cannot
change them.

Two more models there, in a schema of their own, share one table: the
second is a subclass of the first and adds a column whose text must not
be empty. `broken_rules` names that column; the test then gives the
table the check, `broken_rules` names nothing, and the real SQLite file
has the check and refuses empty text in the column (DAT-033).

## Yes or no

`backend/tests/unit/test_db_yes_no.py` tests the type without a store:
that yes is said as the whole number 1 and no as 0, and read back from
them; each kind of value that is refused on the way in (the numbers 1 and
0, the word "no", empty text, a number with a fraction) with its whole
sentence, and on the way out (two, less than nothing, 1.0, text, Python's
`True`); that no value stays no value; that the type is INTEGER in a
table; the text of the check as SQLite is given it, also for a column
named with a word of SQL, and its name before and after the naming rule;
that the type brings exactly that check, with its two words for
`broken_rules`; and the sentence of `broken_rules` for a table made by
hand, until the table has the check.

`backend/tests/integration/test_yes_no.py` has a model of its own with
three such columns, one that may be without a value and one with a value
of its own, and a whole number that is not yes or no. It makes the table
in a real SQLite file and asks the file which columns there are and reads
the three checks as the file says them, letter for letter. Then it stores
rows and reads with plain SQL, past the model, what the file holds and of
which kind it is: yes and no are the whole numbers 1 and 0 and come back
as `True` and `False`; no value is stored as none; a change is stored;
what is neither `True` nor `False` is refused in five kinds, and the row
stored with it in the same unit of work is not there either; another
number written with plain SQL is refused with the name of the check, in
five ways, and so is a change to one; what SQLite takes for one of the
two numbers is stored as that number, in four ways; rows are found by
yes, by no and by no value; a question with a number is refused; and a
sum over such a column is read as yes or no, or refused. A word and a
number with a fraction, written with plain SQL, are refused because the
table is strict. The model is kept in a schema of its own.

## One of a list

`backend/tests/unit/test_db_lists.py` tests the type without a store,
with lists of its own: that a value is stored as its plain text and read
back as the value itself; each kind of thing that is refused on the way
in (text that is spelled like a value, text that is not on the list, a
value of another list with the same text, a number) with its whole
sentence, and on the way out (six kinds); that no value stays no value;
that the type is TEXT in a table; the text of the check as SQLite is
given it, in the order of the list, for a column named with a word of
SQL, for texts with the characters SQL has a use for and in large
letters, and for a list with two names for one value; its name before
and after the naming rule; that the type brings exactly that check for
its own list, with its two words for `broken_rules`; what is refused as
a list (five kinds of thing that are not one, a list with nothing on it,
a list with an empty value in four kinds); and the sentence of
`broken_rules` for a table made by hand, until the table has the check,
which the check for another list does not end.

`backend/tests/integration/test_lists.py` has three lists of its own and
a model with a column for each, two of which may be without a value, and
a text column of no list. It makes the table in a real SQLite file and
asks the file which columns there are and reads the three checks as the
file says them, letter for letter. Then it stores rows and reads with
plain SQL, past the model, what the file holds: every value of a list is
stored as its text and comes back as the value; so is a text with a
quote, two quotes, a percent sign, a colon, a question mark, a
backslash, large letters and a letter beyond ASCII; no value is stored
as none; two columns that hold the same text each read it as the value
of their own list, and each refuses what is on the other's list only; a
change is stored; what is not a value of the list is refused in four
kinds, and the row stored with it in the same unit of work is not there
either; text that is not on the list, written with plain SQL, is refused
with the name of the check, in seven kinds, and so is a change to one;
rows are found by a value, by several and by no value; a question with
text is refused; and rows sorted by such a column come by the alphabet.
Three more tests are
of what could go wrong unseen: two statements that differ in the list
only each keep their own list (SQLAlchemy keeps statements it has seen);
a second model of the same table whose list has a value less refuses the
row that still has it when it is read; and a model that names its list
and not the type gets a table SQLite refuses to make. The letter beyond
ASCII is written in the tests as its number, not as itself, so that an
editor cannot change it.

## A web address

`backend/tests/unit/test_db_web.py` tests the type without a store: the
text of the check as SQLite is given it, letter for letter, and for a
column named with a word of SQL; that the white space the check names is
the store's own list; its name before and after the naming rule; that
the type brings exactly that check, with its two words for
`broken_rules`; that the type is TEXT in a table; that `Base` has the
type in its list, so that a model says it by the column's Python type;
and the sentence of `broken_rules` for a table made by hand with two
such columns, until each has its check.

`backend/tests/integration/test_web.py` has a model with three such
columns, one that must have a value, one that may be without, and one of
which the model says more, and a text column of any kind. It makes the
table in a real SQLite file and asks the file which columns there are
and reads the three checks as the file says them, letter for letter.
Then it stores rows and reads with plain SQL, past the model, what the
file holds: thirteen addresses are stored as they were given, with
`https` and with `http`, in small and in large letters, with a port, a
path, a question and a place on the page, with a space written as its
number, with a letter beyond ASCII, with a number for a site in both
kinds, with one character after the scheme, and with the characters
`GLOB` and SQL have a use for. 35 texts that are not a web address are
each refused with the name of the check, and the row stored with them in
the same unit of work is not there either: no characters and a space
alone, a name without a scheme in three kinds, five other schemes, a
scheme and nothing after it, each of the three characters that must not
begin the name, after `https` and after `http`, a slash or two too few
and a letter too many, words or a letter before the scheme, white space
before, after and in it in nine kinds, two addresses in one text, and a
character with the number 0, also with a space behind it. One test
puts each of the 29 white space characters in three places of an address
and finds every one refused. Four addresses that lead nowhere are
stored, because the check does not know: a site there is not, a full
stop for a name, a space without width and a control character. The rest
is as for the other types: text written with plain SQL is refused, and
so is the number 1, which a strict table stores as text; a change to
text that is not an address is refused in three ways and the row stays
as it was; a change to another address is stored; the column that may be
without a value holds none or an address and has a check of its own; the
column of which the model says more has both its check and what the
model said; two spellings of one address are two addresses; and a text
column of any kind is as before. The letter beyond ASCII and the
characters that cannot be seen are written in the tests as their
numbers, not as themselves, so that an editor cannot change them.

## Column types that bring a check

`backend/tests/integration/test_checks.py` has a column type of its own
that brings a check (text in large letters only) and one model with
three columns: two of that type, one of which may be without a value,
and between them one whose text must not be empty. It makes the table in
a real SQLite file and asks the file: the table has the three checks, by
name and in the order of the columns, and the two of the tests' type
read as that type writes them. Then it stores rows: what the check
allows is stored, also no value where the column may be without one; and
what it refuses is refused with the name of the check, in both columns,
and the row stored with it in the same unit of work is not there either.
The model is kept in a schema of its own.

## The models and the migrations agree

`backend/tests/integration/test_compare.py` begins with the test that
holds the real models to the real migrations: it brings the store of the
fixture to the newest schema with `migrate`, makes the tables of the
whole schema (`SCHEMA` in `motosphere.db.models`) in a second real file,
and `differences` must find nothing. It is the test that fails when a
model is added or changed without its migration, or a migration without
its model.
When it fails, its message is what `differences` found, one sentence to a
line.

The other tests prove that the comparison can fail. They have two models
of their own, in a schema of their own, with the parts the tables of the
store are made of (the key and the two times from `Base`, text that must not
be empty, a column that may be without a value, a name that is a word of
SQL, a unique constraint, two checks, a foreign key and two indexes), and
migrations written by hand as plain SQL. Both stores are real SQLite
files in every test.

- A migration written by hand builds what the models say, and so do the
  statements SQLAlchemy writes for the models, run as text.
- How a statement is written makes no difference, in eight ways: on one
  line, with tabs and the line ends of Windows, in small letters, with
  names in quotes of each of the three kinds, with a name in other
  letters, with a comment to the end of a line, and with two comments
  between words, one of them over two lines. A table that was given its
  name later, which SQLite then keeps in quotes, is the same table.
- A quote written twice inside quotes does not end them, in three ways:
  in text, and in a name in quotes of two kinds. The same letters as two
  texts or two names side by side are not the same statement.
- What only one of the two has is named, in nine ways: a table, an index, a
  view and a trigger, all the models have where the migrations build nothing
  (the table in which SQLite keeps the keys given so far is then in one
  store only, and is not named), a view where the models have a table, and a
  table whose name only begins like those SQLite keeps for itself.
- A table or an index that differs is named with the place, in twenty ways,
  each one change to the migration: a column that only one has, of another
  type, that may be without a value in one only, with a value of its own; a
  key that may be given twice; two columns the other way round; a constraint
  that only one has, over the same columns the other way round, of another
  name; a check that says something else; text in single quotes in other
  letters and with another space; a foreign key that does more, and one that
  only the models have; a table that is not strict; and an index that lets
  no two rows be alike, over the same columns the other way round, and over
  some rows only. The sentence is written out in each test. In some, more
  words follow those shown in one statement only, and in one a statement has
  exactly as many words as are shown, and so promises no more.
- A column added to a table in place does not stand where the models
  have it, and is named.
- The sentences come kind by kind and name by name; the tables SQLite
  keeps for itself are not compared; and comparing leaves both files byte
  for byte as they were.

## The store's own history

`backend/tests/integration/test_history.py` tests the real migrations
(`motosphere.db.history`, DAT-006), each on a real SQLite file. The
migrations are named in their order, so one that is moved, taken out or
given another name fails; the list the store is migrated with is that
list itself; the module gives every migration, and their list, by name
(DAT-009); each migration is given to a store at the version before it,
a test for each, and brings it to its own version; the first makes the
table `source` and nothing else, in a file that then carries MotoSphere's
mark; the second makes the table `source_offer` in a store that has a
source, and the source is as it was (DAT-040); the third makes the table
`collection_run` in a store that has a source and an offer, and both are
as they were (DAT-007); the fourth makes the index of the runs of one
source in a store that has runs and had no index, and the runs are as
they were, and it fails, with the store left at its version, where an
index of its name is there already (DAT-042); the fifth makes the table
`record_change` in a store that has a source and a run, and both are as
they were, with the index of the runs, and it fails, with the store
left at its version, where a table of its name is there already
(DAT-009); the sixth makes the four triggers of `record_change` in a
store that has a row of history, the row is as it was and is then held
like any other, and it fails where a trigger of its name is there
already, with the store left at its version and the triggers it had
made before that one taken back (DAT-048); the seventh makes the two
indexes of `record_change` in a store that has two rows of history,
the rows are as they were and are found through each index, the index
of the runs and the four triggers are as they were, and it fails where
an index of its name is there already, with the store left at its
version and the index it had made before that one taken back
(DAT-049); the eighth makes the table `review_item` and its index in a
store that has a source and a row of history, both are as they were,
with the three indexes and the four triggers, and it fails, with the
store left at its version, where a table of its name is there already,
and where an index of its name is, with the table it had made before
that taken back (DAT-010); the ninth makes the two indexes of one
doubt in a store that has an item of each shape, the items are as they
were and each is found through its own index, and it fails, with the
store left at its version and neither of its indexes kept, where a
doubt is there twice, of either shape, and where an index of either of
its names is there already (DAT-050); the tenth makes the two triggers
of a kept decision in a store that has an open and a decided item,
the items are as they were, the open one can then be changed and the
decided one cannot, with the three indexes of the table and the four
triggers of the history as they were, and it fails, with the store
left at its version and neither of its triggers kept, where a trigger
of either of its names is there already (DAT-054); the eleventh makes
the two triggers of the keys in a store that has an item with a key
below 1 and one above, the items are as they were, no item is given a
key below 1 from then on, and the item that had one is still given a
note and a key of 1 or more, and it fails, with the store left at its
version and neither of its triggers kept, where a trigger of either of
its names is there already (DAT-056); the twelfth makes the two
triggers against replacing in a store that was at version 10 and has
an open item and two decided ones, one of them with the key -1, the
items are as they were, neither decided item is replaced from then
on, by its key or as its doubt, a new item that names no key is
stored as ever, and it fails, with the store left at its version and
neither of its triggers kept, where a trigger of either of its names
is there already (DAT-055); the thirteenth makes the table `country`
and the index over the source of its rows in a store that has a source
and a review item, both are as they were, with the six indexes and
the ten triggers, a country of the source that was there is then
stored, and it fails, with the store left at its version, where a
table of its name is there already, and where an index of its name is,
with the table it had made before that taken back (DAT-011); the
fourteenth builds the table of the sources anew in a store that has two
sources, two more that were deleted, so that the keys have a gap and
the highest key given is above every key that is there, and a row in
each of the four tables that point to a source: every source has what
it had, its key too, and is of no country, every row of the four tables
is as it was, the highest key each table has given is as it was, no
pointer is broken, the two copies are gone, and the seven indexes and
ten triggers are there with the new index beside them; the key of a
deleted source is not given again afterwards, in a
table without sources too, whether it ever had one or not; the rows are
held to their sources again, and a source to a country that is there;
and it fails, with the store left at its version, the table without the
column and every row and the highest key as before, where a table of
the name of either copy is there already, and where an index of its
name is, which is its last statement, after the table was dropped, made
anew and filled (DAT-057); the fifteenth builds the table of the sources
anew once more, in the same store with one source of a country: before
it a source of the kind `reference list` is refused; after it every
source has all it had, its key and its country too, every row of the
four tables and the highest key of each table is as it was, no pointer
is broken, and of all the tables and indexes, as SQLite holds them,
only `source` is written otherwise, in the one text more; a source can
be of each of the thirteen kinds, and eight texts that are not of the
list are refused, those nearly the new one among them; the key of a
deleted source is not given again, in a table without sources too; the
rows are held to their sources again, a source to a country that is
there, and a country that a source is of cannot be deleted; and it
fails, with the store as it was, where a table of the name of either
copy is there already, and at its last statement, where a table of the
index's name stands in the index's place (DAT-058); the sixteenth makes
the table `region` and the index over the source of its rows in the
same store, where every table and index that was there is written as
it was and holds what it held, with the ten triggers, a region of the
country and of the source that were there is then stored, and it
fails, with the store left at its version, where a table of its name
is there already, and where an index of its name is, with the table it
had made before that taken back (DAT-013); a store
with the newest schema lacks no migration; and the module
names nothing of MotoSphere's own code, which the test reads from the
module as it is written, imports inside a function included.

## The whole schema

`backend/tests/integration/test_models.py` proves that `SCHEMA` in
`motosphere.db.models` is whole (DAT-006). In the Python that runs the
tests, other tests have loaded models already, so each question is asked
of a new Python that has loaded nothing but what it is told to. One loads
every module MotoSphere has and says which tables the models then say;
one takes `SCHEMA` and says its tables; one loads a single model by its
own module. All three must say the same tables, `source` among them. A
model that the package does not name, and a model that stands outside the
package, each fail these tests.

## The information sources

`backend/tests/integration/test_source.py` tests the table of the
sources (DAT-006) in a store that the migrations built, as every real
store is built. What is stored through the model is also read as SQLite
holds it, and what the table must refuse is also written past the model.
Where SQLite refuses a row, the test names what SQLite said, word for
word, and so which constraint refused it.

- A source is stored and read back with everything said of it: its kind
  and its way of collecting as values of their lists, the time its terms
  were read as the same moment in UTC though it was given in another
  zone, and its two times from the store's clock. In the table it is
  plain text and whole numbers, row written out in the test.
- A new source is switched off, and nothing more is said of it than it
  cannot be without. Without its name, its website, its kind or its way
  of collecting it is refused, each in a test; so is a row written past
  the model that does not say whether it is switched on.
- Two sources cannot have one name, names are told apart letter for
  letter, and two sources can have one website.
- The table refuses what is not on a list, in six ways, and a source can
  be of each of the thirteen kinds and collected from in each of the ten
  ways; it refuses what is not a web address, in four ways for each of its
  two addresses; and empty text, in two ways for each of three columns.
- A source is scanned every so many whole hours: nought, less and part of
  an hour are refused.
- A source whose terms were not read is not stored switched on and cannot
  be switched on later; it is switched on once they were read; a source
  that is switched on cannot lose the time; and it can be switched off
  again and keeps it. A source that is changed says when.

`backend/tests/integration/test_source_country.py` tests the country a
source is of (DAT-057), in a store that the migrations built and that
has one source and the two countries that came from it. A source says
its country and is read back with it, through the model and as SQLite
holds it; a source of which none is said has none; a row written past
the model is read with its country. The country must be there, when a
source is stored and when it is moved, and a key that is not a whole
number is refused in four ways, with what SQLite said, while a whole
number written as text or with a point is stored as the key it is. A
source is given a country later, another, and none; two sources can be
of one country. A country that a source is of cannot be deleted,
through the model or past it; one that no source is of can; and it can
once its source was moved to no country, to another, or deleted. A
source can be of a country that came from it; the two then keep each
other, and are taken away in one order, which the test walks. The
table has the column before its two times, as a whole number that may
be without a value, with a foreign key that does nothing for the
source when the country goes. The sources of one country are found by
the index, which also answers what SQLite asks before a country is
deleted, and are asked for through the model.

`backend/tests/unit/test_db_models_source_country.py` reads the same
from the model, without a store: where the column stands, that it may
be without a value and is given none, the name and the target of its
foreign key, the one index and that it is not a unique one; that the
sources and the countries are the only two tables of the schema that
point to each other, and that nothing else goes round; and that the
schema with the column keeps every rule.

`backend/tests/integration/test_source_offer.py` tests the table of what
the sources offer (DAT-040), in a store that the migrations built. An
offer is stored and read back, its kind as a value of the list; a source
can offer several kinds, and each of the nine; it does not offer one
kind twice, and offers stored together are kept together or not at all;
two sources can offer the same kind; the table refuses a kind that is
not on the list, in five ways, written past the model; an offer belongs
to a source that exists, when it is stored and when it is moved; it
names its source and its kind; a source that has offers cannot be
deleted, and is deleted once they were taken away, while another
source's offers stay.

`backend/tests/unit/test_db_models_source.py` tests the three lists of the
sources, without a store: the two a source is described by (DAT-039) and
the kinds of information one can offer (DAT-040). The texts of the lists
are written out in the test, so a text changed by mistake fails there:
each list has exactly its texts in their order, thirteen kinds of
source, of which the last is this project's own and stands after the
twelve of the design (DAT-058), ten ways of collecting and nine kinds
of information; no text has two names; each of the 32 texts is words
in small letters with one space
between two; and a column can be of each list, with a check that names
its texts in their order, as SQLite is given it. That SQLite refuses a
text that is not on a list is proven for every list by the tests of "One
of a list".

## The collection runs

`backend/tests/integration/test_collection_run.py` tests the table of the
collection runs (DAT-007), in a store that the migrations built. What the
table must refuse is written past the model, as plain SQL, and each test
names what SQLite says, word for word, and so which constraint refused
it.

- **What a run is.** A new run is running, has counted nothing and has
  neither end nor error. A run that ends says when, how and what it
  changed, and says when it was changed; one that fails says what went
  wrong. A run can have each of the four outcomes, and the table refuses
  an outcome that is not on the list, in five ways.
- **Its source.** A source can have several runs, two that started
  together among them. A run belongs to a source that exists, when it is
  stored and when it is moved. A source that has runs cannot be deleted,
  and is deleted once they were taken away, while another source's run
  stays.
- **What a run must say.** Its source, its start, its outcome and each
  of its four counts: a test for each.
- **Its end.** A run cannot end before it started, when it is stored and
  when it is given its end later; it can end at the moment it started.
  Only a run that succeeded or failed says when it ended, and it must:
  four ways are refused. Only a run that failed has an error, and it
  must: four ways are refused. The error is not empty, in three ways.
- **Its counts.** None of the four can be below 0, and each is a whole
  number. They need not add up.

`backend/tests/integration/test_runs.py` tests `mark_interrupted`
(`motosphere.db.runs`), in a store that the migrations built and with the
clock set. Where no run is running, and in a store without runs, nothing
is marked and every row is as it was. A run left running is marked
interrupted, and the whole row is compared: only its outcome and when it
was last changed are different, it has no end and keeps its counts. Every
run left running is marked, whichever source it is of, and the keys come
back in order. No other run is touched, in any column, and neither are
the tables of the sources and of their offers. A run that was marked is
not marked again. The marking is taken back with the unit of work it is
part of; a run that the unit of work had read already says it was
interrupted; and a new run of the same source can start in the same unit
of work.

`backend/tests/unit/test_db_models_collection_run.py` tests the list of
the four outcomes, without a store: its texts are written out in the
test, in their order; no outcome has two names; each is one word in small
letters; and a column can be of the list, with a check that names the
four as SQLite is given them.

## The index of the runs of one source

`backend/tests/integration/test_collection_run_index.py` tests that the
index is there and is used (DAT-042), in a store that the migrations
built. It asks SQLite itself: `EXPLAIN QUERY PLAN` gives SQLite's own
account of how it will answer a statement, and the statements are the
ones `standing_of` really sends, caught as they go to SQLite, with what
they were given.

- The newest schema has the index over `source_id` and `started_at`, in
  that order; it lets two rows be alike, and is over all rows.
- Each of the four statements about the runs of a source is answered in
  one step, by a search of the index for the source, and nothing is
  sorted.
- What the index is for: the same four statements, in the same store
  without the index, read the whole table and sort what they found.
- The index changes no answer: three sources with a run of every outcome
  are said to be doing the same with it and without it.

That the model and the migration say the same index is proven by the
test of the models and the migrations, and that the index forbids
nothing by the tests of the table, where two runs of a source start at
the same moment.

## How a source is doing

`backend/tests/integration/test_source_health.py` tests `standing_of`
(`motosphere.db.source_health`, DAT-041), in a store that the migrations
built, with runs of every outcome. Each answer is compared whole where
the whole of it matters.

- **One run or none.** Of a source without a run nothing is said but
  that it is not yet scanned. A source whose first run is still running
  was attempted and is not yet scanned. One whose only run succeeded is
  healthy; one whose only run failed is failing and says why; one whose
  only run was interrupted says so and has no error.
- **Several runs.** The last attempt is the newest run, whatever became
  of it, a test for each outcome. The last success is the newest run
  that succeeded, whatever came after. The health is told by the newest
  run that is over, with a running run after it. The last error is that
  of the newest run that failed; it is no longer said once a later run
  succeeded, and is still said while a later run is running or was
  interrupted.
- **Which run is the newest.** The one that started last, not the one
  stored last; of two that started together, the one stored last, both
  ways round.
- **Whose runs.** Three sources, one of them without runs: each is told
  by its own.
- **What comes back.** The times are times in UTC. A key that no source
  has is refused in one sentence, in three ways. What was said cannot be
  changed afterwards, a test for each of its four parts.
- **Nothing is written.** After the asking the store's file is byte for
  byte what it was, the unit of work holds nothing new, changed or
  deleted, and the store's clock was not asked.

`backend/tests/unit/test_db_source_health.py` tests the list
`SourceHealth`, without a store: its four texts are written out in the
test, in their order; no text has two names; and each is words in small
letters with one space between two.

## Where a collected record came from

The columns every collected record has (`Collected`, DAT-008) are in no
real table yet, so both files of tests make models of collected records
of their own, in a schema apart from the real one: one model that says
nothing else, and one that says more of its table.

`backend/tests/unit/test_db_models_collected.py`, without a store: the
table of a model that says nothing else is the key, the eight columns in
their order and the two times, and the columns a model names come before
the set; each of the eight is of its type and of its list; only the day
of publishing may be without a value; no column gives itself a value,
and none is a key or unique; the table has one index, over the source of
its records alone, and no other column of the set has one; a model that
gives its table an index of its own keeps it and the index of the set;
every table has an index of its own, named by the naming rule (DAT-045);
the record refers to `source.id` by a reference the naming rule names,
and says nothing of what happens when its source is deleted; the table
has the check of its two times and
the check of every column whose type brings one, with the texts of the
three lists in their order; a model that gives its table a check and a
rule of its own keeps both and the checks of the set; every table has a
check of its own; the tables break none of the rules every table keeps;
and `Collected` itself is no table.

`backend/tests/integration/test_collected.py`, in a store that the
migrations built, so that the source a record refers to is the real
table of the sources. What must be refused is also written past the
model, with plain SQL.

- **Stored and read back.** A record is in the file as text in the
  store's forms, and comes back as it was given. The file has the eleven
  columns as the model says them, the reference to `source`, the one
  index over the source, and the six checks by name, four of them letter
  for letter.
- **What may be unknown.** The day of publishing may be without a value,
  through the model and past it. A record without one of the other seven
  is refused, each in three ways.
- **The source.** A record of a source that is not there is refused. A
  source that records came from cannot be deleted, through the model or
  past it, and its key cannot be changed; one that nothing came from
  can, and so can one whose records are gone. A second table of
  collected records holds its source in the same way. A record can be
  given to another source that exists, and to no other.
- **The address, the lists and the day.** An address that is not a web
  address is refused, in four kinds. Text that is not on the list of its
  column is refused, in 17 kinds, among them a text of one of the other
  two lists; a value of another list is refused before anything is
  written; every value of each list is stored as its text and read
  back. A day of publishing that is not a day is refused, in six kinds,
  and a time is not taken for it. A record published the day after it
  was collected, by the clock of UTC, is stored.
- **The two times.** A record last seen a millionth of a second before
  it was collected is refused; at the same moment, a moment after and a
  week later it is stored. The two are compared as moments whatever
  offset they were given in: 10:29 in Paris is before 09:30 in UTC. A
  record that is seen again says when, keeps when it was collected, and
  its row says that it was changed.
- **Changes.** A change that breaks the set is refused, in seven kinds,
  and the row stays as it was.
- **A model that says more.** Its table refuses what the set refuses and
  what the model said, and stores a row with nothing wrong.

`backend/tests/integration/test_collected_index.py` tests the index over
the source of a record (DAT-045), in a store that the migrations built,
with two tables of the tests' own and records of three sources. An index
is there to be used, so the tests take the statements as the store's
code sends them and ask SQLite itself how it will answer each (`EXPLAIN
QUERY PLAN`).

- **In the file.** Each table has the index by its name, over
  `source_id` alone, as a statement made it; a model's own index is
  there beside it.
- **What is asked about the records of one source**, five questions:
  which records came from it, how many, whether any did, which of them
  were not seen since a moment, and the taking away of its records.
  Each is one statement and SQLite answers it in one step, by the
  index. Where the index alone has the answer SQLite says so (`USING
  COVERING INDEX`).
- **Deleting a source.** SQLite refuses to delete a source that records
  came from. Its account of the deleting names the look into each table
  of collected records, by that table's index, and reads no whole table
  of any kind.
- **Without the index.** The same statements in the same store, with the
  indexes dropped: each of the five reads the whole table, and so does
  the deleting of a source, in both tables.
- **The index changes no answer.** What the store answers about the
  records of each of three sources and of one that is not there, and
  the refusal to delete a source, are the same with the index and
  without it.

`backend/tests/unit/test_db_models_provenance_rule.py` tests the rule
that names a table which does not say where its records came from
(`broken_provenance`, DAT-046), without a store. Its tables are made by
hand, each in a schema of its own, and two models of the tests' own,
subclasses of the real `Collected`, hold the rule to what a model of
collected records really gets.

- **The real schema** breaks no rule. Each of the five tables on the
  list is named as soon as it is taken off it, in the sentences the
  rule has
  for it, so the rule does look at the real tables. Every table on the
  list has a reason, and no two have the same.
- **What keeps the rule.** The tables of the two models, one of which
  has a rule, a check and a second index of its own that begins with
  the source; and a table made by hand as the set says, which keeps
  the rules every table keeps as well.
- **Missing columns.** A table with none of the eight, and tables
  without one, two and four of them, are named once each, with the
  missing columns in the order of the set.
- **A column that is not as the set has it** is named: of another type
  or of another list, in 14 kinds, among them a list of the tests' own
  that has the very texts of the right one; one that may be without a
  value where the set says otherwise, each of the eight; one that is
  given a value nobody said, by the code or by the table, when a row
  is stored or changed, in eight kinds; and one that does not refer as
  the set says, in nine kinds.
- **The index and the check.** A table without the index over the
  source alone is named, in seven kinds; an index of another name
  counts, among others. A table without the check of its two times is
  named, in eight kinds, among them a name that only ends as it
  should; the check of another table does not count. Neither is asked
  for where a column it needs is missing.
- **The list.** A table on it is not looked at; a name on it that is no
  table is named, once; a table on it that has the whole set is named.
- **The order.** The names of the list that are no table come first,
  then table by table by the alphabet, and for each table its missing
  columns, its columns in the order of the set, its index and its
  check.

## The changes to records

`backend/tests/integration/test_record_change.py` tests the table
`record_change` (DAT-009) in a store that the migrations built, on a
real SQLite file. Every refusal is tested twice where the model could
stand in the way: through the model, and with a row given to SQLite
past it.

- **The table in the file** is as the model says it: its columns in
  their order, with their kinds and which may be without a value; its
  one reference, to the runs; its two indexes, which let two rows be
  alike (DAT-049); a strict table; and its six checks by name.
- **What is stored is read back.** A change a run caused and a change
  a person decided, each with every column. Eight pairs of values are
  kept as they were given: no value on either side, empty text, a
  capital letter, a space at the end, "1" and "1.0".
- **A change that changed nothing is refused**, also where the field
  had no value and has none.
- **The cause.** A change that nothing caused is refused, and one that
  a run and a person both caused. The run must exist. A run that
  caused a change cannot be deleted, nor its key changed, and the
  change is as it was; a run that caused none can be deleted.
- **What a change cannot be without**: the table, the key and the
  field of its record. The names of the table, of the field and of
  the person are not empty, and nothing but white space is empty too.
  The key of a record is above 0.
- **The table is strict**: a word for a key, a key with a fraction and
  bytes for a text are refused by SQLite, and a number given for a
  value is kept as its text.
- **The order of the changes** to a field is the order of their keys,
  with two changes that are alike among them.
- **What the table does not hold**: a change to a record of a table
  that is not there is stored. The test is there so that this is not
  taken for something the table does.

That the model and the fifth migration say the same table is proven by
the test of the models and the migrations.

## The history is only added to

`backend/tests/integration/test_record_change_kept.py` tests that a row
of `record_change` is neither edited, deleted nor replaced (DAT-048),
in a store that the migrations built, on a real SQLite file, with two
rows of history in it. After every refusal the table is read back with
every column and must be as it was. The sentences are written out in
the tests.

- **The triggers of the table**: the four of the history, by name and
  table, and no other on it.
- **An edit is refused**, in seven ways, with plain SQL: a value of one
  row, of every row, a value set to what it holds already, only
  `updated_at`, the key, the key set to that of another row to take its
  place, and an edit told to pass over what is refused.
- **A delete is refused**: of the first row, of the newest, of every
  row.
- **A new row in the place of a row is refused**, in six ways, each for
  the first row and for the newest: `INSERT OR REPLACE`, `REPLACE`, a
  plain `INSERT`, `INSERT OR IGNORE`, and an `INSERT` that would edit
  the row, or do nothing, when its key is taken.
- **A key below 1 is refused** (0, -1 and -7), and the history goes on
  afterwards: the next row gets the key 3.
- **Through the model**, in seven ways: a row that was read is given
  another value, every row is in one statement, a row is merged onto
  one that is there, a row that was read is deleted, every row is in
  one statement, and a row is added with a key that is taken and with
  one below 1.
- **A new row is still stored**: through the model and with plain SQL,
  with the next key; a key that is free may be named, also by a
  statement that would replace; and the row after it follows that key.
- **What is not refused**: an edit and a delete that name a key no row
  has, and both in a history without rows. Nothing is changed.
- **A refusal takes back the whole unit of work**, a new row written
  before it included, through the model and on a plain connection.
- **On a connection the store's code did not open**, made with Python's
  own `sqlite3` and with foreign keys off, an edit, a delete, a
  replacement and a key below 1 are refused in the same sentences.
- **A store made from the models** has the same four triggers and
  refuses the same.

That the model and the sixth migration say the same triggers, to the
letter of each sentence, is proven by the test of the models and the
migrations. That `change` still writes a change with its history into
the table that has the triggers is proven by its own tests, which run
in a store with the newest schema.

## The indexes of the history

`backend/tests/integration/test_record_change_index.py` tests that the
two indexes of `record_change` are there and are used (DAT-049), in a
store that the migrations built, with a source, three runs and six
changes: to two tracks and to an event that has the key of one of the
tracks, caused by two runs and decided by a person. It asks SQLite
itself: `EXPLAIN QUERY PLAN` gives SQLite's own account of how it will
answer a statement. The statements are written with the model, as the
store's code will ask them, and caught as they go to SQLite, with what
they were given.

- **The indexes in the file**: the two by name, each over its columns
  in their order, as the statement that made it; each lets two rows be
  alike and is over all rows.
- **Eight questions are answered by an index**, each in one step, a
  search of the index, with nothing sorted afterwards: what a record
  said before in the order of its changes, the same with all a change
  says, the newest first, only the last change, the changes to one
  field, how many times a record was changed, what a run changed in
  the order of the changes, and how many changes a run caused. Where
  the index alone answers, the plan says so.
- **What the indexes are for**: the same eight statements, in the same
  store without the indexes, each read the whole history.
- **SQLite looks for the changes of a run by the index** when a run is
  deleted and when a run is given another key. Both are refused, as
  before; the plan of each searches the history by the index of a run
  and reads no table whole. Without the indexes the whole history is
  read for each.
- **The indexes change no answer**: the eight questions are answered
  the same with the indexes and without them, each answer written out
  in the test, and a run that caused changes is refused its delete in
  both.

That the model and the seventh migration say the same indexes is proven
by the test of the models and the migrations. That the indexes forbid
nothing is proven by the history of these tests itself, in which one
record is changed four times and one run causes four changes. That a
row is still neither edited nor deleted is proven by the tests of the
triggers, which run in a store with the newest schema.

## Changing a record with its history

`backend/tests/integration/test_changes.py` tests `change`
(`motosphere.db.changes`, DAT-047) in a store that the migrations
built, on a real SQLite file. The history is written to the real table
of the changes. The records are of three tables made for the tests,
because no real table has a column of every kind: one with a column
of every kind the store keeps, one whose keys are the keys of the
first, and one of collected records. What the store holds afterwards
is read with plain SQL, past the models.

- **A change** is in the record and its old value in the history,
  with the cause and the moment; a change to three fields is three
  rows of one moment, in the order given, after one reading of the
  clock.
- **The text of a value**: for a column of every kind, with and
  without a value, SQLite is asked for the text of what it keeps
  before and after the change, and the history holds those two.
- **Nothing to change**: a field that holds the value already gets no
  row, also a time said with another offset; when no field differs the
  row in the file is the same to the last column and the clock was
  not asked.
- **The cause**: a run, a person; neither and both are refused before
  anything is changed.
- **Neither without the other**: a value the record's table refuses,
  a run that does not exist and a person without a name each leave the
  record as it was and no history; so does work that fails later in
  the same unit; and a unit of work does not go on after a refusal
  that was caught.
- **Refused before anything is changed**: a value of the wrong kind
  for its column, a column of numbers with a fraction or of bytes, a
  time without an offset, the store's own three columns, a field the
  table does not have, a record that is not stored yet, one of
  another unit of work, a deleted one, and a row of the history.
  Each time a good field given in the same call is not changed.
- **More than one change**: two tables with the same keys are told
  apart in the history; changes in one unit of work follow each
  other, there and back again.
- **A collected record**: what says where it came from is changed in
  the same call as its value, and the history holds the old address,
  day and moments.
- **What the function does not do**: a field set by hand is written
  without a row.

## The review queue

`backend/tests/integration/test_review_item.py` tests the table
`review_item` (DAT-010) in a store that the migrations built, on a
real SQLite file. Every refusal is written past the model, as a row
given to SQLite, and those the model could stand in the way of are
tested through the model as well. After every refusal the table holds
no row.

- **The table in the file** is as the model says it: its columns in
  their order, with their kinds and which may be without a value; its
  one reference, to the sources; its three indexes, the one over the
  source and the two of one doubt; a
  strict table; and its seventeen checks by name, eleven of them
  letter for letter.
- **What is stored is read back.** A possible duplicate, and an item
  of each of the two other kinds, each with every column; a new item
  is open by itself. An accepted and a rejected item say by whom and
  when, and keep a note. An open item can have a note, and is decided
  afterwards through the model.
- **The two lists.** A kind and a state that are not on their lists
  are refused, in four spellings each.
- **What an item cannot be without**: its kind, the table and the key
  of its record, why, and its state; through the model the first four,
  because the model gives a new item its state. Five texts are not
  empty, and nothing but white space is empty too. The key of a record
  is above 0.
- **What goes with the kind.** A possible duplicate without the other
  record is refused; so is one whose other record is the record itself
  or has a smaller key; and one that names a field, a source, an
  address or what a source says, a case for each. An item of each of
  the two other kinds is refused without any one of those four, and
  with another record.
- **The source.** It must exist. A source that an item names cannot be
  deleted, nor its key changed; one that no item names can. SQLite's
  own plan for deleting a source searches the items by the index and
  reads no table whole. Where the source says it is a web address.
- **The decision.** An open item that says who decided, or when, is
  refused, and so is an accepted and a rejected item without either:
  six cases past the model and one through it.
- **The table is strict**: a word for a key, a key with a fraction and
  bytes for a text are refused by SQLite, and a number given for what
  a source says is kept as its text.
- **What a source says is kept as the text it was**: empty text,
  spaces around it, markup and a statement of SQL among them, each
  read back letter for letter, with the table still there.
- **One doubt is one item**: the same possible duplicate a second
  time is refused, and the first is as it was (DAT-050; its own tests
  are below).
- **What the table does not hold**: an item about records of a table
  that is not there is stored. The test is there so that it is not
  taken for something the table does.
- **A decision is kept**: a decided item cannot be put back to open
  nor deleted, each refused with its sentence, and both items are as
  they were (DAT-054; its own tests are below). Until DAT-054 this
  test put on record that the table did not refuse it.

`backend/tests/unit/test_db_models_review_item.py` tests the two lists
without a store: their texts are written out in the test, in their
order; no text has two names; each is words in small letters with one
space between two; open is the first state; and a column can be of
each list, with a check that names its texts as SQLite is given them.

That the model and the eighth migration say the same table and index
is proven by the test of the models and the migrations, and that the
table is on the list of those that hold no collected records, with
what the rule says of it once it is taken off, by the tests of that
rule.

### One doubt is one item

`backend/tests/integration/test_review_item_one_doubt.py` tests the
two indexes by which the store refuses the same doubt a second time
(DAT-050), in a store that the migrations built, on a real SQLite
file. What is refused is written past the model, as a row given to
SQLite, and through the model as well.

- **The indexes in the file**: their names, that each lets no two rows
  be alike and is over some of the rows only, their columns in their
  order, and the statement SQLite keeps for each, letter for letter,
  with the rows it is over. The index of the source is as it was.
- **The same doubt is refused**, with what SQLite says, and the first
  item is as it was: a possible duplicate, whether the first is open,
  accepted or rejected, and with another reason and a note the second
  time; a doubt about a field, in the same three states, whichever of
  the two kinds the first is and whichever the second, at another
  address and for another reason. Where the first is open SQLite
  names the index; where it was decided, the store says that a
  decided item is never replaced (changed by DAT-055: the trigger of
  that rule asks before the index is looked into).
- **Through the model** the same doubt is refused too, of either
  shape, and another doubt stored in the same unit of work before it
  goes with it.
- **Another doubt is stored**: a pair of another table, of another
  record, with another record, and the other record of a pair with a
  third; a doubt about a field of another table, another record,
  another field, from another source, and with another thing said,
  which is compared letter for letter: another value, empty text, a
  space after the value and the number written otherwise are four
  doubts more. A possible duplicate and a doubt about a field of the
  same record stand in each other's way in neither index.
- **SQLite's own plan** for the question "is this doubt there
  already?", written with the model for each shape as the store's
  code will ask it, without naming a kind: one step, a search of the
  index of that shape. Without the two indexes the same statement
  reads the whole table for a pair, and every item of the source for
  a doubt about a field. The indexes change no answer.

That the model and the ninth migration say the same two indexes, with
the rows each is over, is proven by the test of the models and the
migrations.

### Opening a possible duplicate

`backend/tests/integration/test_review_possible_duplicate.py` tests
`open_possible_duplicate` (`motosphere.db.review`, DAT-051) in a store
that the migrations built, on a real SQLite file, so an item is
written to the real table of the review queue. The records are of
tables of the tests' own, kept in a schema apart, because the real
schema had no table of records when they were written. What the store
holds afterwards
is read with plain SQL, past the models.

- **One open item**: it names the table and the two keys of its
  records, the kind and the reason, and nothing else; it was stored at
  one reading of the clock; and the item given back says the same.
- **Either order**: six ways of giving two of three records, and the
  smaller key is always the record.
- **The same doubt again** gives the item that is there and stores
  none, as before and turned round, in a later unit of work and in
  the same one. Not one column of the item is another afterwards, its
  times among them, and the clock is not asked. The reason given the
  second time is not read, an empty one neither.
- **A doubt that was decided** is given back as it was decided,
  accepted or rejected, with who decided, when, and the note, and no
  new item is stored.
- **Another doubt**: a pair that has one record of the first, each
  way, and the same two keys in another table, are four items.
- **The unit of work**: the item has its key and is in the table
  before the function returns, and another connection does not see it
  until the unit ends; a unit that fails afterwards leaves no item.
- **The records are not touched**, and the history gets no row. A
  record stored earlier in the same unit of work can be given, and so
  can collected records.
- **What is refused**, each with its sentence, letter for letter, and
  with nothing written: a record that is new, one that was given to
  the unit of work and is not written yet, one the unit has deleted,
  one of a unit that has ended and one of another unit that is open,
  each as the record and as the other; a new record of another table;
  two records of two tables that have the same key, each way; one
  record twice; and two rows, and one row twice, of each of the five
  tables that hold no collected records. A table that is put on that
  list fails the test until it gets its two rows there.
- **An empty reason** is refused by the store at the call, in three
  spellings, and the unit of work fails as a whole: a record stored
  in it before is not kept.
- **What the function sends**: one look, given the table and the two
  keys with the smaller first, and a write only where the doubt is
  new. SQLite's own plan for the look is one step, a search of the
  index of the pairs.
- **Between the look and the write** another connection tries to
  store the same doubt, and SQLite says "database is locked" to it:
  the function's item is the only one.

### Opening a doubt about a field

`backend/tests/integration/test_review_field_doubt.py` tests
`open_field_doubt` (`motosphere.db.review`, DAT-053) in the same way:
in a store that the migrations built, on a real SQLite file, with
records of tables of the tests' own, and with what the store holds
read back with plain SQL.

- **One open item**, of each of the two kinds: it names the table and
  the key of its record, the field, the source, the address, what the
  source says and the reason, and nothing else; it was stored at one
  reading of the clock; and the item given back says the same.
- **The same doubt again** gives the item that is there and stores
  none, in a later unit of work and in the same one, and the clock is
  not asked. What else is given the second time is not read: the
  other kind, another address, another reason, and an address and a
  reason the store would refuse in a new item.
- **A doubt that was decided** is given back as it was decided,
  accepted or rejected, and no new item is stored.
- **Another doubt**: another field, another source, and what is said
  written otherwise, with a space after it, with a space in it and
  empty; and the same thing said of another record and of the same
  key in another table.
- **What a source says is kept as the text it was and found again by
  it**: empty text, white space around it, markup, a statement of SQL
  and a character beyond ASCII, each kept letter for letter as text,
  with the table still there.
- **The unit of work**: the item has its key and is in the table
  before the function returns, and another connection does not see it
  until the unit ends; a unit that fails afterwards leaves no item.
- **The record is not touched**, and the history gets no row. The
  function does not look at what the record holds: a doubt is stored
  where the text given is the text of what the record holds, for both
  kinds. A record stored earlier in the same unit of work can be
  given. A possible duplicate and a doubt about a field of one record
  are two items.
- **What is refused**, each with its sentence, letter for letter, and
  with nothing written: a record that is new, one that was given to
  the unit of work and is not written yet, one the unit has deleted,
  one of a unit that has ended and one of another unit that is open;
  a row of each of the five tables that hold no collected records,
  which is refused for its table before its field is looked at; the
  kind of a possible duplicate; each of the store's three own
  columns; a field the table does not have, in five spellings; and
  something said that is not text, in six kinds.
- **What the store refuses is refused at the call**, and the unit of
  work fails as a whole: a source that is not there, an address that
  is no web address or empty, and a reason that is empty or blank.
- **What the function sends**: one look, given the table, the key,
  the field, the source and what it says, and a write only where the
  doubt is new. SQLite's own plan for the look is one step, a search
  of the index of what a source says.
- **Between the look and the write** another connection tries to
  store the same doubt, and SQLite says "database is locked" to it.
- **The module** gives its functions by name: the list is held
  whole, so the test changes with every function the module gets.

The tests of `open_possible_duplicate` are unchanged and pass: the
rules for which records and which tables are taken are now asked by
both functions in one place.

### Deciding an item

`backend/tests/integration/test_review_decide.py` tests `decide`
(`motosphere.db.review`, DAT-052), in a store that the migrations
built, on a real SQLite file. The table of the review queue holds
neither the table nor the key of a record to a row that exists, so
these tests need no table of records: their store has one source and
two open items, a possible duplicate and a doubt about a field that
has a note already. What the store holds is read back with plain SQL,
every column of every item.

- **Deciding an open item**, each of the two items with each of the
  two decisions: exactly four columns of the item are another
  afterwards, its state, who decided, when, and when it was last
  changed; the two times are one reading of the clock; the other item
  is as it was; and the item given says what was stored.
- **The note**: without one, an item without a note has none and an
  item with a note keeps it; a note given is stored, also in the
  place of one, and with the white space it was given with; the note
  the item has, given again, changes nothing.
- **The name** is kept as it was given: with white space around it,
  in small letters, and with a character beyond ASCII.
- **Decided once**: an item that was accepted or rejected is refused
  with its sentence when it is given the same decision, the other
  one, or open; not one column is another, and the clock is not
  asked. A second decision in the same unit of work is refused too,
  and the first is the one that is kept.
- **What is no decision** is refused with its sentence: open, text
  that is spelled like each of the two decisions, nothing, a value of
  another list, and yes.
- **What is refused for the item**: one that is new, one that was
  given to the unit of work and is not written yet, one the unit has
  deleted, one of a unit that has ended, and one of another unit that
  is open, which that unit does not write either. An item stored
  earlier in the same unit of work is decided.
- **What the store refuses is refused at the call**, and the unit of
  work fails as a whole: an empty name, a blank one, nobody, and an
  empty and a blank note.
- **The unit of work**: the decision is in the table before the
  function returns, and another connection finds the item open until
  the unit ends; a unit that fails afterwards leaves the item open.
- **Only the item is touched**: the source is as it was, and the
  history gets no row.
- **What the function sends**: one statement, which sets the four
  columns, and the note where one is given, by the key of the item.
- **Before the decision is written** another connection finds the
  item open, changes it, and is told "database is locked" when it
  tries to keep that: the function's decision is the one that is
  kept.

### A decision is kept

`backend/tests/integration/test_review_item_decision_kept.py` tests
that a decided row of `review_item` is neither edited nor deleted
(DAT-054), in a store that the migrations built, on a real SQLite
file. Most tests begin with four items, written past the model: an
open possible duplicate, an accepted one, a rejected doubt about a
field and an open one. After every refusal the table is read back
with every column and must be as it was. The two sentences are
written out in the tests.

- **The triggers of a decided item on the table**: the four, by name
  and table: the two of this rule and the two against replacing
  (DAT-055).
- **No column of a decided item is given another value**: each of the
  sixteen columns of the table, on the accepted item and on the
  rejected one. A test holds that every column the table has is one
  of them, so that a column a later task adds must get its case.
- **A decided item is not edited** in five more ways: put back to
  open, its note taken away, its state set to what it holds already,
  its key set to that of an open item to take its place, and an edit
  told to pass over what is refused.
- **A statement over many items** that would edit a decided one
  changes none: SQLite takes back what it had done to the open items
  before.
- **A decided item is not deleted**: the accepted one, the rejected
  one, every decided one, and every item in one statement.
- **Decided, and kept from then on**: an open item of each shape,
  decided with plain SQL in each of the two ways, and one decided
  through `decide`, can afterwards be neither put back nor deleted.
- **What is as before**: an open item gets a note and another reason
  and is deleted; a new item is stored open or decided, with plain
  SQL and through the model; a statement that meets no decided item
  is not refused; and neither is one in an empty table.
- **Through the model**: a decided item that was read is put back to
  open, given a note or deleted, every item is given a note or
  deleted in one statement, and an item with another reason is
  merged onto a decided one; each is refused in the same sentences.
- **A refusal takes back the whole unit of work**, the decision of
  another item made earlier in it included.
- **On a connection the store's code did not open**, made with
  Python's own `sqlite3` and with foreign keys off, five statements
  are refused in the same sentences, and what the refused statement
  had done before is taken back. There too a refusal stops the
  statement and not the work: what was written before it, and what
  is written after it, is kept.
- **A store made from the models** has the same four triggers and
  refuses the same.
- **A decided item is not replaced**: four statements that say
  `REPLACE` and would take the accepted item out, by its key and as
  its doubt, are each refused, and every item is as it was. Until
  DAT-055 this test put on record that the four took the item out;
  that task turned it round. Its own tests are under "A decided item
  is never replaced".

That the model and the tenth migration say the same triggers, to the
letter of each sentence, is proven by the test of the models and the
migrations, which is unchanged. The tests of `decide` are unchanged
and pass: the function refuses a decided item before the table is
asked.

### A key is 1 or more

`backend/tests/integration/test_review_item_key.py` tests the two
triggers by which a key of the review queue is 1 or more (DAT-056), in
a store that the migrations built, on a real SQLite file, with two
open items and a decided one written past the model. After every
refusal every column of every item is read back with plain SQL.

- **The table has these triggers and no other**: the two of a kept
  decision, the two against replacing and the two of the keys. This
  is the one test that names every trigger of the table; a task that
  gives it another names it there. (The tests of a kept decision and
  those against replacing ask for their own.)
- **A new item with a key below 1 is refused**: with the keys 0, -1,
  -7 and the least whole number SQLite holds, each as an open item, a
  decided one, a doubt about a field, and in a statement that says
  `OR REPLACE` or `OR IGNORE`; also in a queue without items.
- **A key of 1 or more that is named is taken** (4, 30, the greatest
  whole number SQLite holds, and 1 in a queue without items), and **a
  new item that names no key gets the next one**, with plain SQL, with
  the key written as NULL, and through the model.
- **An open item is not given a key below 1**, alone, with another
  column, and with `OR REPLACE` or `OR IGNORE`; a statement that would
  give one item of several such a key changes none of them, whether it
  meets that item first or second, and neither does a unit of work
  whose second statement is refused.
- **An open item is given another key of 1 or more as before**, also
  the key it has, and one counted from its own.
- **Of a decided item the store says first that it is never edited.**
- **A statement that gives no item a key below 1 is not refused**: an
  edit that names no key, a key below 1 for an item that is not there,
  and a delete.
- **Through the model** a new item with the key 0 or -1 is refused,
  and so is the key 0 for an open item, with what the unit of work
  wrote before taken back.
- **On a connection the store's code did not open**, with foreign
  keys off, the same is refused in the same sentence; and there a
  refusal stops the statement and not the work: what was written
  before it, and what is written after it, is kept.
- **A store made from the models** has the same six triggers and
  refuses the same.

### A decided item is never replaced

`backend/tests/integration/test_review_item_never_replaced.py` tests
the two triggers by which no row takes the place of a decided item
(DAT-055), in a store that the migrations built, on a real SQLite
file. Most tests begin with two sources and four items written past
the model: an open possible duplicate, an accepted one, a rejected
doubt about a field and an open one. After every refusal every column
of every item is read back with plain SQL.

- **The two triggers**, by name and table, and **the ways a row can
  clash**: the table has the two indexes of one doubt as its only
  indexes that hold a row to be the only one of its kind, and one key.
  An index that is added fails this test, so that the triggers are
  given its question too.
- **A new item in the place of a decided one is refused**, in eleven
  ways (with the key of the accepted item or of the rejected one, as
  a possible duplicate, a doubt about a field or a decided item; as
  the two records of the accepted item, open, decided, with a free
  key and with the key of an open item; as what the rejected item
  says of a field, also of the other kind at another address, and
  with a key), each with `INSERT`, `INSERT OR REPLACE`, `REPLACE` and
  `INSERT OR IGNORE`; and with `ON CONFLICT DO NOTHING` and `ON
  CONFLICT … DO UPDATE`.
- **A value written another way** is the value the table would hold:
  the key as text and as a number with a point, the records and the
  source as text, what is said as a number.
- **An open item is not put in the place of a decided one**, in six
  ways (its key, its two records, also decided in the same statement,
  what it says of a field, also of the other kind), each with
  `UPDATE`, `UPDATE OR REPLACE` and `UPDATE OR IGNORE`.
- **A statement over several rows** that would replace a decided item
  on its way changes none: two new items of which the second clashes;
  a new decided item and then the same doubt again; a copy of an open
  item with the key of a decided one; the open items each given the
  next key; and the open items decided and made one doubt, where the
  first becomes the decided item the second would replace. A unit of
  work whose second statement is refused keeps nothing.
- **Another doubt by one column is stored**: for a new item, each of
  the three columns of the first index and the five of the second
  alone, a pair that shares its first record with the accepted item
  or with the rejected one, and a doubt about another field of a
  record of the accepted item, each with `INSERT` and with `REPLACE`;
  and an open item is made each of the first eight with `UPDATE OR
  REPLACE`. Both decided items are as they were.
- **An open item is replaced, and changed, as before**: by a new item
  with its key, by the same doubt again of either shape, by another
  open item given its key or made its doubt; and it is decided, given
  another key and a note, and deleted.
- **A new item that names no key is stored**, open or decided, with
  plain SQL and with the key written as NULL.
- **A decided item with the key 1** is not replaced, by a new item or
  by an open one: 1 is the least key the first trigger asks about.
- **Of a decided item the store says that it is never edited**, also
  where the edit would put it in the place of the other decided item.
- **In a queue without items** nothing is refused.
- **Through the model**: a new item with the key of a decided one, a
  new item that is its doubt, an insert told to take its place, an
  open item that was read and given its two records, and an update
  told to take its key; each is refused in the same sentence, and
  what the unit of work wrote before is taken back.
- **On a connection the store's code did not open**, with foreign
  keys off, six statements are refused in the same sentence, each
  with SQLite's recursive triggers off and on; and there a refusal
  stops the statement and not the work, for a new item and for an
  open one. There too, where nothing takes the work back, each of the
  five statements over several rows leaves nothing of itself behind
  when the refusal is caught: what it had stored or changed before it
  came to the decided item is taken back by SQLite.
- **A store made from the models** has the same two triggers and
  refuses the same, and replaces an open item as before.

That the model and the twelfth migration say the same triggers, to the
letter of each sentence, is proven by the test of the models and the
migrations, which is unchanged. The tests of `open_possible_duplicate`,
`open_field_doubt` and `decide` are unchanged and pass: the functions
look for the doubt before they write.

## How far a collected record can be trusted

`backend/tests/unit/test_db_models_provenance.py` tests the two lists of
`motosphere.db.models.provenance` (DAT-043), without a store. The texts
of the lists are written out in the test, so a text changed by mistake
fails there: each list has exactly its texts in their order, three
levels of confidence and four statuses; no text has two names; each of
the 7 texts is words in small letters with one space between two; each
value has the name its text spells, so that `Confidence.HIGH` is `high`
in the store and no other text of its list; no text is on both lists;
and a column can be of each list, with a check that names its texts in
their order, as SQLite is given it. That SQLite refuses a text that is
not on a list is proven for every list by the tests of "One of a list".

## The countries

`backend/tests/integration/test_country.py` tests the table of the
countries (DAT-011) in a store that the migrations built, with one
source in it, on a real SQLite file. What is stored through the model
is also read as SQLite holds it, and what the table must refuse is
also written past the model, as plain SQL. Where SQLite refuses a row,
the test names what SQLite said, word for word, and so which
constraint refused it; nothing is stored then.

- **What is stored.** A country is read back with everything said of
  it, its times in UTC and its lists as their values; the row is plain
  text and whole numbers; a country whose source gives no day has
  none; a row written past the model is read as a country.
- **What a country cannot be without**: each of the ten columns but
  the day it was published, written past the model and through it. The
  model gives none of them a value.
- **The form of a code**: 18 texts that are not two capital letters and
  18 that are not three, each refused by the check of its column:
  small letters in every place, too few and too many, nothing, a
  figure, a hyphen, a space or a new line before or after, a letter
  with a tilde, Greek capitals and wide capitals that look like the
  letters, and three with a character of the number 0. The model does
  not put a code into capitals; a number is not a code; bytes are not
  text. Six pairs of codes are taken, among them the first and the
  last letter in every place and a code the standard leaves to its
  users.
- **One code, one country**: a second country with a code of two
  letters that is taken is refused, and so is one with a code of three
  that is taken, through the model and past it; a country cannot be
  given the code of another afterwards. Two countries with codes of
  their own are both stored, also where they hold one name.
- **The name**: empty text of four kinds is refused; six names are
  stored as they were given, with letters beyond the 26, an
  apostrophe, brackets, white space around them and small letters.
- **Where it came from**: a country of a source that is not there is
  refused; a source that countries came from cannot be deleted; a
  country can be deleted, its source stays and can then be deleted;
  the key of a deleted country is not given again. Ten texts that
  break a rule of the eight columns are refused, each by its check;
  a country is not last seen before it was collected, to the
  microsecond; a country can be got in each of the ten ways, be of
  each of the three levels of confidence and of each of the four
  statuses. The countries of one source are found through the index,
  which SQLite says it uses, also when a source is to be deleted.
- **Its history**: `change` gives a country a new name and a new moment
  it was last seen, writes one row of history for each of the two and
  none for a code that stays, and both carry the moment of the change;
  a change the table refuses leaves the country as it was and no
  history.

`backend/tests/unit/test_db_models_country.py` reads the model, without
a store: the table is in the whole schema and the model is named by
the package; a country is a collected record and its table is not on
the list of those that hold none; the fourteen columns in their order;
only the day it was published may be without a value; no column but
the two times gives itself a value; the two checks of the codes, as
SQLite is given them; the names of the nine checks, the two rules of
one code and the reference, and the one index; and the whole schema
with the countries breaks neither the rules every table keeps nor the
rule of where records came from.

## The regions

`backend/tests/integration/test_region.py` tests the table of the
regions (DAT-013) the way the table of the countries is tested: in a
store that the migrations built, on a real SQLite file, here with one
source and two countries in it; through the model and past it, as
plain SQL; and with what SQLite said, word for word, where it refuses
a row.

- **What is stored.** A region is read back with everything said of
  it; the row is plain text and whole numbers; a region whose source
  gives no day has none; a row written past the model is read as a
  region.
- **What a region cannot be without**: each of the nine columns but
  the day it was published, written past the model and through it. The
  model gives none of them a value. Bytes are not a name, and text is
  not a key.
- **Its country**: a region of a country that is not there is refused,
  and a region cannot be moved to one; a country that has regions
  cannot be deleted, and the country and its region are then as they
  were; a country without regions can be deleted beside one that has
  them; a region can be deleted, its country stays and can then be
  deleted.
- **One name, one region of a country**: a second region of the name
  in the country is refused, through the model and past it; a region
  cannot be given the name of another of its country, nor be moved to
  a country that has a region of its name. Two countries can each have
  a region of one name, and one country regions of several names. Six
  names that differ from a name that is there in their capitals, in a
  space before or after, in a word more or in one letter with an
  accent are each stored beside it: two names are one only if they are
  the same text.
- **The name**: empty text of four kinds is refused; seven names are
  stored as they were given, with letters beyond the 26, an
  apostrophe, hyphens, letters of another script, white space around
  them and small letters.
- **Where it came from**: a region of a source that is not there is
  refused; a source that regions came from cannot be deleted, and can
  be once they are taken away; the key of a deleted region is not
  given again. Ten texts that break a rule of the eight columns are
  refused, each by its check; a region is not last seen before it was
  collected, to the microsecond; a region can be got in each of the
  ten ways, be of each of the three levels of confidence and of each
  of the four statuses.
- **What finds it**: the regions of one source are found through the
  index over the source, which SQLite says it uses, also when a source
  is to be deleted. The regions of one country are found through the
  index SQLite keeps for the rule of the names, which is over the
  country and then the name: SQLite says it uses it for the regions of
  a country, for one region by its name, and when a country is to be
  deleted.
- **Its history**: `change` gives a region a new name and a new moment
  it was last seen, writes one row of history for each of the two and
  none for the country that stays, and both carry the moment of the
  change; a change the table refuses leaves the region as it was and
  no history.

`backend/tests/unit/test_db_models_region.py` reads the model, without
a store: the table is in the whole schema and the model is named by
the package; a region is a collected record and its table is not on
the list of those that hold none; the thirteen columns in their order;
only the day it was published may be without a value; no column but
the two times gives itself a value; the two references, to the country
and to the source, neither of which says what is to happen when what
it points to is deleted; the rule of the names, with the country
first; the names of the seven checks, the rule and the two references,
and the one index; and the whole schema with the regions breaks
neither the rules every table keeps nor the rule of where records came
from.

## The countries file

`backend/tests/unit/test_reference_countries.py` tests the list of the
countries that comes with the project and its reader
(`motosphere.reference.countries`, DAT-012). No store is opened and
nothing is fetched.

- **The files.** The countries file and the licence beside it are those
  of release 4.20.1 of iso-codes, byte for byte: each is held to its
  SHA-256, which the test names. Neither has a line ending a checkout
  could change. The note beside them names both files with those
  values, the release, the notice of copyright and the licence as the
  release states them, and says that the files are unchanged. The folder
  holds those three files and no other.
- **The countries of the file.** There are 249, read from the file of
  the project, in the order of the file. Eight are named as the file
  writes them, among them names with letters that are not of the 26,
  with a comma and with an apostrophe. No two have one code; every code
  is capitals of the 26 letters, two or three; no name has white space
  around it.
- **What is read.** A file made up for the test gives its countries in
  its order. What more an entry holds is left unread, whatever it is. A
  name is given as it is written, also in another script, and the same
  when the file writes its letters as numbers. Two countries can have
  one name. A country cannot be changed once it is read.
- **What is refused**, each with its sentence, word for word: content
  that is not UTF-8; content that cannot be read as JSON, cut off, with
  a mark of byte order, with something after its end, with a number too
  long to be read; the three words Python reads as numbers and JSON does
  not have; content nested too deeply; a name twice in one place, also
  in what is left unread; content that is not the one list under its
  name and nothing else; something else than a list there; a list
  without countries; an entry that is not names and values; an entry
  without one of its two codes or its name, or with something there that
  is not text; a code in any form but capitals of the 26 letters in the
  right number (small letters, a figure, a space or a line break around
  it, a letter with a ring, Greek and wide letters that look the same, a
  nought character); a name that is empty, that has white space around
  it, that has white space inside other than a plain space, or that has
  a control character; and one code in two entries, of two letters or of
  three. A wrong entry at any place in a file refuses the whole file,
  and so does the project's own file with one entry damaged.

## The source of the countries

Two files test how the source of the countries is described and put in
the store (`motosphere.reference.countries_source`, DAT-060).

`backend/tests/unit/test_reference_countries_source.py`, 12 tests
without a store: the name, which is also the name of the folder that
holds what was taken from the source; the kind, the way of collecting
and the one kind of information it offers; the website, the licence and
the restrictions, each written out a second time; that the description
names columns of a source in the order of the table, and that every
column of a source is described, or is one of the four that are for
people to say, or is the store's own; that the note beside the file
names the same website and licence, and that the text of the licence is
beside the file under the licence's name.

`backend/tests/integration/test_countries_source.py`, 26 tests against a
real SQLite file that the migrations built:

- **Stored as described.** In an empty store the function stores one
  row, read back as SQLite holds it, column for column, and one offer.
  The row is switched off, says that nobody has read its terms, and has
  no country and no hours.
- **Once.** Asked for four times, in two units of work, it is one row,
  and nothing was written after the first time: the row says it was
  last changed when it was stored. Beside another source it takes the
  next key and leaves the other alone. A source whose name differs by a
  capital, a figure or a space is another source.
- **Given as it is.** A source of the name that is there as described
  is given back and nothing is written. What a person said of it stays:
  when its terms were read, that it is switched on, its hours and its
  country. It may offer more than the pipeline says.
- **Refused**, each with its sentence, word for word, and the store as
  it was: another website, also one that differs by a stroke at its
  end; another kind; another way of collecting; an address of terms;
  another licence or none; other restrictions or none; no offer of
  `reference data`, with no offer at all and with another one. What
  another source offers does not count for this one. A refusal names
  everything that differs, in the order of the table, with two things
  and with four.
- **Part of its unit of work.** The source and its offer are written
  when the function returns. When the unit of work fails afterwards,
  neither is kept; when the function refuses, what the unit of work
  did before goes with it.

## The loading of the countries

Two files test how the countries of the reference file are brought into
the store (`motosphere.reference.countries_load`, DAT-059).

`backend/tests/unit/test_reference_countries_load.py`, 8 tests without a
store: the release, its day and its address, each written out a second
time; that the address is the file of the release in the folder it was
fetched from; that the note beside the file names the same release, day,
file and folder; and that what a loading gives back is four lists in one
order and cannot be changed afterwards.

`backend/tests/integration/test_countries_load.py`, 48 tests against a
real SQLite file that the migrations built. Every row is read back as
SQLite holds it:

- **What is stored.** The 249 countries of the project's file in an
  empty store, in the order of the file, with their names as the file
  writes them; every column of a new row, with the clock set; one
  moment for all rows of a loading; the source with its offer, switched
  off, and a source of the countries that is there already; no
  collection run and no history.
- **Loaded again.** A second loading sends SQLite no statement that
  writes, which the test hears by listening to the statements, and
  another test holds that the listening hears a loading that does
  write. A later loading adds only what the store does not have. A
  country that is there from another source stays as it is.
- **What the store says otherwise of.** Another name, also one that
  differs by a capital, by a letter written as two or by a space;
  another code of three; a code of three under another code of two.
  Each is left as it is and named, and the other countries are added.
  A country the file does not have is left and named, in the order of
  the codes. What was found is named in the order of the file. With
  all of it at once, no statement changes or deletes a country.
- **What waits in the review queue** (DAT-062). For each of the six ways
  in which the store says otherwise, the items that are opened: the
  record, the field and what the file says. Every column of an item,
  with the clock set. A code of three under another code of two, which
  waits as what the file says of that country, and a country that
  differs both ways. The order of the file. No item where the store is
  as the file has it or has a country the file does not have. Loaded
  again, no statement that writes is sent; an item a person has decided
  stays as it was decided and is not opened again; a file that says yet
  another thing opens an item beside it. The items go with a unit of
  work that fails.
- **What is handed over.** A list that is given one country at a time;
  no countries; a list that has one code twice, of two letters, of
  three, or a whole country, which the store refuses.
- **The unit of work.** A source that is described otherwise refuses
  the loading and nothing is stored. The rows are written when the
  function returns. Nothing is kept when the unit of work fails
  afterwards, and what it did before goes with a refused loading.

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

A test that needs the tables asks for the fixture `newest` instead: the
same store, brought to the newest schema by `migrate`, as every real
store is, and without rows (DAT-006).

`tests/integration/test_store_fixture.py` tests the fixture `store`. For
what happens after a test has ended, it lets pytest run a small file of
tests in a process of its own (pytest's `pytester`), four of which leave
connections open, and reads the outcome.

## The clock of a test

The store sets two times in every row from its one clock, `now()` in
`motosphere.db.times`. A test that needs to know those times asks for the
fixture `clock` (`backend/tests/conftest.py`). The clock is then set for
that test: it says 19 November 2026, 08:00 UTC, when it is first asked and
one second more every time after that. The fixture is the list of the
moments it said, in order, so a test can say `clock[0]` for the moment the
first row was stored and `len(clock)` for how often the store asked.
Because no two askings get the same moment, a test can tell one reading of
the clock from two.

A test that does not ask for the fixture runs with the real clock. Only
the clock is replaced, never the store.

## A unit test that starts the page

Two unit tests start the whole page by bringing in `src/main.tsx`: one in
`frontend/src/main.test.tsx` and one in
`frontend/src/globe/engineAddress.test.ts`. React does not show a page at
once. It puts the work in a queue and does it a moment later, and what
follows from showing the page a moment after that. A test that ends
before the queue is empty leaves that work waiting. If the test's file
ends too, the test's document is taken away, and the work runs
afterwards without one: the run then ends with "ReferenceError: window is
not defined" and counts as failed, although every test passed. Whether
that happens is a matter of a few moments either way, so it happens
rarely: once so far, on GitHub's Linux machine (run 46006701452).

So both tests start the page inside React's `act`:

```ts
await act(async () => {
  await import('./main.tsx')
})
```

`act` comes back only when React has nothing left to do: the page is
shown in full, with all that follows from showing it. Each of the two
tests then looks at the page at once, without waiting for it
(`getByRole` where it was `findByRole`, and a root element that is not
empty). A start outside `act` therefore fails its test every time, and
not one run in many.

A new unit test that brings in `main.tsx`, or that shows something with
React by any other way than `render` of Testing Library, does the same.
`render` of Testing Library uses `act` by itself.

The document of a test has work of its own waiting when these two files
end, one piece for each style sheet `main.tsx` brings in. That is not
React's: the document drops what it has waiting when it is taken away
(`_queueATask` of jsdom says so), and it is left as it is.

## What a unit test leaves waiting

The two tests that start the whole page end only when React has nothing
left to do (the section above). That does not hold a test that is
written later, and it does not have to be a test that forgets `act`: a
test that waits for the page as Testing Library advises (`findBy…`) can
end a moment before React has done the last of its work. Counted over
five whole runs of the unit tests, one test of the 387 ended so once.
If such a test is the last of its file, the work runs after the test's
document is gone, and the run fails with "window is not defined"
although every test passed.

So the set-up of the unit tests (`frontend/src/test/setup.ts`) lets no
test end with work of React's waiting. It does so with
`frontend/src/test/reactsWork.ts`:

- **A watch.** React asks the system to call it back when it has work
  to do, with `setImmediate`; the function it hands over is named
  `performWorkUntilDeadline`. Before React is loaded, the set-up puts a
  watch around the system's `setImmediate`. The watch counts each piece
  of React's work from the moment React asks for it until it runs, and
  hands on everything else untouched. That is why the watch is the
  first thing `setup.ts` brings in: React keeps the `setImmediate` it
  finds when it is loaded.
- **After each test** the set-up unmounts what the test showed and
  clears the session, as before, and then lets React's waiting work
  run until none is waiting. Work can ask for more work, so it looks
  again after each turn, up to 100 times. After that it fails the test
  with "React still has work waiting after it was let run 100 times:
  something asks it for more work without end."
- **When the file is over** it gives the system its own `setImmediate`
  back, and fails the file if anything of React's is still waiting:
  "The test file ends with 1 of React's work still waiting: it would
  run after the test's document is gone." After the step above nothing
  is; this is what is left to say so if that step is ever lost.

**Why the test is not failed instead.** The task was first to fail
every test file that ends with work waiting. The trial showed that a
test which does nothing wrong ends that way now and then, by a few
moments. A guard that fails such a test fails a run now and then,
which is the fault it was to remove. Letting the work run, while the
test's document is still there, removes the fault itself.

**What it does not see.** Only what React asks the system for is
counted. A page that waits for something else when its test ends, a
file it loads later or an answer from the network, is not seen: the
watch cannot know that React will be asked for more. A test of such a
page waits for what it expects to see, as before. Nor is the work the
test's document has of its own counted (the section above).

**The tests** are in `frontend/src/test/reactsWork.test.tsx`, 19 of
them. Two hold the system the tests run on: it is the system itself,
and something that gives out no `setImmediate` is refused with a
sentence. Ten hold the watch over a stand-in for the system: what is
counted and what is not, what is handed on and back, a piece that
fails when it runs, work that asks for more work, the 100 turns and the
sentence after them, and the end of a file with and without work
waiting. The stand-in has the system itself run each piece, and no
timer: on Windows a timer waits for the next tick of the clock, and the
tests that let work run a hundred times took most of a second each.
Four hold what the set-up does after each test and at the end
of a file, with a stand-in for the test runner. Three are with React
itself: a page started outside `act` is seen by the watch as one piece
of work and is shown when the watch has let it run, and a test that
ends with such a page not yet shown is followed by a test that finds it
shown. **The first of these is the test that fails after an upgrade of
React that asks the system for its work in another way:** the watch
then has to follow.

## The browser of the browser tests

The browser tests start their browser with one feature of the browser
turned off, `TcpPortRandomizationWin` (`frontend/e2e/browser.ts`, set in
`frontend/playwright.config.ts`). The feature exists on Windows only.

**Why.** Three times a run on GitHub's Windows machine failed in one
browser test that could not open the page: "page.goto:
net::ERR_NO_BUFFER_SPACE at http://127.0.0.1:4173/MotoSphere/" (runs
44429659797, 45984920265 and 45996124551). Each time it was another
test, every other test passed, and the job passed when it was run once
more. The message is Windows's for "no room for one more connection".

**What was measured, on GitHub's Windows machine (2026-11-27).**

- The machine has room. It gives out 16,384 ports for connections
  (49152 to 65535). In a whole run of all gates the most connections
  held at one moment were 774, of which 716 were closed ones that
  Windows keeps for two minutes; about 430 were the browser's to the
  test server.
- The browser picks its ports at random there. The source of the
  browser the tests use (Chromium 153.0.8010.12, `net/base/features.cc`
  and `net/socket/tcp_socket_win.cc`) has the feature
  `TcpPortRandomizationWin` on by default for Windows 11 22H2 and later:
  before every connection it asks Windows for a port picked at random
  (`SO_RANDOMIZE_PORT`). Windows Server 2025, GitHub's machine, is such
  a Windows. Measured: with the feature on, of 2,999 connections one
  after another, 0 to 2 had the port next to the one before; with it
  off, 2,994 to 2,997.
- With the feature on, a connection fails now and then. Two trials, each
  in turns of a minute with the feature on and off, in one job:
  30,000 requests each way, every one on a connection of its own; and
  6,000 browser contexts each way, opened and closed as the tests do
  it, with a page of five files (about 24,000 connections each way).
  With the feature on, 8 of 53,978 connections failed: 2 with
  `net::ERR_NO_BUFFER_SPACE` and 6 with `net::ERR_ADDRESS_IN_USE`, and
  one page could not be opened. With it off, none of 53,993 failed. The
  machine held about 5,000 connections throughout, the same either way.

So the fault is in how the browser asks Windows for a port, not in the
application, the test server or the number of connections. Why Windows
refuses a port it was asked to pick at random was not looked into: that
is between the browser and Windows.

**How it is turned off.** A browser takes one list of features to turn
off, and Playwright already gives it one. What a browser does with a
second list beside the first was not relied on: Playwright's own list is
taken out (`ignoreDefaultArgs`) and given again with the one feature
added, so the browser is given one list. The
list is written out in `frontend/e2e/browser.ts` as Playwright 1.63.0
has it. Five browser tests (`frontend/e2e/browser.spec.ts`) hold it:

- a browser started as the tests start theirs has exactly one such
  list, and it is the list of `browser.ts`;
- that list is Playwright's own and, after it, the one feature;
- a browser started with none of the project's options has exactly the
  list `browser.ts` calls Playwright's own. **This is the test that
  fails after an upgrade of Playwright that changes its list:** the
  list in `browser.ts` then has to follow;
- the project of these tests is given these options, and the project
  of the globe tests the options of its own browser (see the next
  section);
- the browser is seen to take its ports in order. The test starts a
  server of its own, which closes every connection after one answer,
  has the page open 40 connections to it one after another, and reads
  the port the browser came from each time. On Windows at least half of
  them must come from a port that is one to four after the one before.
  Measured on GitHub's Windows machine in the two trials above, more
  than 99 in 100 do with the feature off, and fewer than 1 in 200 with
  it on. **This is the test that fails, on a Windows machine, when a
  later browser knows the feature under another name or not at all:**
  the words the browser is started with would then be as before and
  turn nothing off. On other systems there is no such feature and the
  system gives out ports its own way: there the test has the 40
  connections arrive and holds nothing about their order.

The browser tests are still not given a second try (`retries: 0`), and
no test is skipped: a failure of `page.goto` is seen as before.

## The browser of the globe tests

The tests of the globe are a project of their own in
`frontend/playwright.config.ts`, `globe`, with the files in
`frontend/e2e/globe` (FND-058). Two things set it apart from the project
of the other tests, `chromium`: its browser is started with one word
more, `--use-angle=swiftshader` (`GLOBE_BROWSER` in
`frontend/e2e/browser.ts`), and its tests run one at a time
(`workers: 1`), whatever the number of workers of the run. Both are
there for what was measured. To run the tests of the globe alone:
`npx playwright test --project globe`.

**What was measured (2026-11-27)**, with the engine drawing the Earth
from the pictures that come with it, in a page of the built site, on a
developer's Linux machine and on GitHub's Linux and Windows machines.
None of the three has a graphics card for the browser, and on all three
the browser draws in software, with the renderer that comes with it
(SwiftShader), with the word and without it.

- **Four warnings for every page with a 3D picture.** Started as the
  other tests start it, the browser logs four warnings of its own on
  the console of every page that shows a 3D picture, whether the engine
  draws it or four lines of the test's own: "GL Driver Message (OpenGL,
  Performance, GL_CLOSE_PATH_NV, High): GPU stall due to ReadPixels".
  They come from how the browser brings the picture to the page, not
  from the page. Every browser test fails on a warning on the console,
  so every test that shows the globe would fail. With the word, on all
  three machines: none, with the engine, with a plain picture, and with
  twenty globes made and taken away one after another. Nine other words
  a browser can be started with were tried, and none of them helps on
  all three machines.
- **On GitHub's Linux machine the Earth appears four to five times
  sooner.** One globe alone there, until the Earth was drawn complete:
  4.8 to 5.4 seconds without the word, 0.9 seconds with it (once 2.2).
  Two at once: 7.9 to 8.7 seconds without, 1.9 to 2.1 with.
- **Two globes at once starve each other on GitHub's Windows machine.**
  One globe alone was drawn complete there in 2.1 to 4.8 seconds with
  the word (2.9 to 6.2 without). Of eight globes that were started two
  at a time, four with the word and four without, one was complete,
  after 36 seconds, and seven were not within 40 seconds. All the while
  the browsers went on drawing, up to 40 pictures a second, and files
  of the site, which the test server on the same machine hands out,
  took 20 to 37 seconds to arrive. No request failed and nothing was
  reported. It looks as if the drawing in software takes the
  processors and everything else waits; why Windows shares them so much
  less evenly than Linux was not looked into.
- **One globe at a time is drawn.** In a run of all browser tests with
  the tests of the globe held to one at a time: on GitHub's Windows
  machine 16 of 16 globes were complete in 1.5 to 7.6 seconds (the
  first took the longest), on its Linux machine 16 of 16 in 0.6 to 0.8
  seconds. Playwright starts the tests of the first project first, so
  the globes were drawn at the end of the run: on both machines two of
  the 261 other tests ended later than the first test of the project
  `globe`. A globe drawn while other browser tests run beside it was
  not measured.

**One at a time is held by the tests themselves.** Every globe test
uses the `test` of `frontend/e2e/globe/fixtures.ts`, which is the `test`
of all browser tests and also takes a turn for as long as the test
runs: a file in the folder of the run's results that only one can make.
A globe test that starts while another has the turn fails at once, with
"Two globe tests ran at once. They must run one at a time: see the
project "globe" in playwright.config.ts." So a project that is given
more than one worker, by a change to the settings or by an upgrade of
Playwright that reads them otherwise, fails its tests and does not
starve them.

Ten browser tests (`frontend/e2e/globe/browser.spec.ts`) hold this:

- the browser of the project is started with the list of features to
  turn off that every test's browser has, and with the word;
- it is not told the word that takes 3D pictures away from the other
  tests (see below);
- a page shows thirty 3D pictures one after another, drawn in software,
  and the browser says nothing on the console. **This is the test that
  fails when a later browser no longer knows the word:** the four
  warnings are back;
- the tests are in the project `globe`, the second of two, with these
  options;
- a globe test holds the turn while it runs, and another that asks for
  it is refused with the sentence above;
- the turn is taken where nobody has it, in a folder that is made for
  it, refused to a second, who is told what the system said of the
  file too, and handed back;
- four tests that do nothing but take a third of a second each. They
  pass when they run one after another. **These are the tests that
  fail when the project is given more than one worker:** two of them
  then run at once, and the one that comes second is refused the turn.

**The other tests run in a browser that gives no 3D picture
(FND-059).** One globe at a time holds only as long as no test outside
the project of the globe draws a 3D picture, and once the globe is in
the page, every test that opens the page would. So the browser of the
project `chromium` is started with one word more, `--disable-3d-apis`
(`NO_3D_SWITCH` in `frontend/e2e/browser.ts`). A page that asks such a
browser for a 3D picture is given none, as in a browser that cannot
draw one; a flat picture it gets as before, and the browser says
nothing on the console about either. The browser of the globe tests
names every word it is started with itself, and this is not one of
them.

Two browser tests (`frontend/e2e/browser.spec.ts`) hold it:

- the browser of the project is started with the word, once;
- a page of the site asks for a 3D picture of each of the two kinds a
  browser has (`webgl2` and `webgl`) and gets neither, draws a flat
  picture and reads its colour back, and nothing is on the console.
  **This is the test that fails when a later browser no longer knows
  the word:** a page would be given a 3D picture again.

What a page of the site shows a person whose browser gives no 3D
picture is under "The stage without a globe".

## Reading what the page shows

A test that must know what a person sees looks at the picture itself:
that the Earth is drawn is proven from its pixels (GLB-003).
`colourAt(page, x, y)` in `frontend/e2e/pixel.ts` gives the colour of
one point of the page as the browser shows it: red, green and blue,
each from 0 to 255 (FND-060). The point is counted in the page's own
pixels, across from its left edge and down from its top. On a screen
that is sharper than the page, one pixel of the page is still one
answer.

**The picture is read from outside the page.** In the planner's trial
a page that read its own 3D picture back (`gl.readPixels`) made the
browser log a warning, and every browser test fails on a warning. So
Playwright takes a picture of the one pixel of the page, a PNG, and
`colourOfOnePixel` reads the colour from that with what Node.js brings
(`node:zlib`). No package was added. On the planner's Linux machine a
point took about 35 thousandths of a second, so a test asks for the
points it needs and not for the whole page.

**What is on top is what is read.** The answer is the colour the
browser shows at the point, whatever of the page lies there. A test
that reads the globe makes sure that nothing lies over the point.

**What cannot be read is refused with a sentence, and nothing is
guessed.**

| What is asked | What is said |
|---|---|
| A point that is not a point of the page: left of it, above it, at or beyond its width or height, between two pixels, or no number | "(1280, 0) is not a point of the page, which is 1280 by 720 pixels." |
| What is no PNG | "This is not a PNG picture." |
| A PNG that is cut short, has a chunk whose checksum is wrong, does not begin with its header or end with its end, has data that cannot be unpacked, or a line that is not as long as one pixel or is filtered in a way there is none of | "The PNG picture is damaged." (for data that cannot be unpacked, what Node.js said of it goes with the error as its cause) |
| A PNG of more or fewer pixels than one | "The PNG picture is 2 by 1 pixels, not one pixel." |
| A PNG of another kind than a browser makes: sixteen bits, greys, a palette, interlaced | "The PNG picture is of a kind that is not read here (bit depth 16, colour type 2, interlace 0). Read are bit depth 8, colour type 2 or 6, interlace 0." |
| A pixel that is not opaque | "The pixel of the PNG picture is not opaque (128 of 255), so its colour is not what is seen." |

Eighteen browser tests hold this. Thirteen
(`frontend/e2e/pixel.spec.ts`) give `colourOfOnePixel` pictures the
test makes itself, chunk by chunk, and one picture as the browser of
the tests made it, kept in the test: red, green and blue, with and
without the fourth byte; each of the five ways a line can be filtered;
data in several pieces with another chunk between; every refusal of
the table; the picture cut short after each of its bytes; and the
picture with each of its bytes in turn changed, none of which is read
as a colour. Four more in the same file ask a page of the built site:
a flat picture of four quarters, with a colour of its own for the one
pixel in each corner, is read at eighteen points, the corners, their
neighbours, the middle of each edge and where the quarters meet; the
answer changes when what the page shows changes; nine points that are
not points of the page are refused; and a page of 200 by 100 pixels on
a screen that is larger and twice as sharp is read pixel for pixel of
the page. One test in the project of the globe
(`frontend/e2e/globe/pixel.spec.ts`) has the page show a 3D picture,
its upper half in one colour and its lower half in another, and reads
both colours exactly at ten points, the four corners among them, with
nothing on the console.

## The stage without a globe

The engine of the globe draws the Earth as a 3D picture. Started in a
browser that gives a page none, it puts up a panel of its own and logs
an error. So before anything of the globe is started, the stage asks
the browser for such a picture (`browserDraws3D` in
`frontend/src/globe/drawing.ts`) and gives it back at once. Where the
browser gives none, the stage says in the place of the globe "The 3D
globe cannot be shown in this browser." and under it, in a second
sentence, why, and what a person can do (GLB-026). Where the browser
gives one, the stage is empty until the globe is in the page (GLB-002).
The sentences name no technology and speak of no error.

**Only the newer kind of 3D picture counts.** A browser has two kinds
(`webgl2` and the older `webgl`). The engine as it is installed
(`@cesium/engine` 26.5.0, `Source/Renderer/Context.js`) asks a browser
that knows the newer kind for that kind and for no other; it takes the
older kind only in a browser that does not know the newer at all, or
when it is told to, which nothing of MotoSphere does. No browser of the
tests is such a browser, so the globe has not been seen drawn with the
older kind, and the stage does not try it: it asks for the newer kind,
and a browser with only the older is told that the globe cannot be
shown.

**The picture is given back.** A browser keeps only so many 3D pictures
for a page and warns on the console when it takes the oldest away. In
the planner's trial, in the browser of the globe tests, a question that
kept its picture, asked forty times in a row, made the browser log
"WARNING: Too many active WebGL contexts. Oldest context will be lost."
25 times. Asked forty times with a pause after each, the same question
logged nothing: the browser had cleared the pictures away by itself in
between. The question as it is, asked forty times in a row, logs
nothing.

28 unit tests and 13 browser tests hold this.

The unit tests, over the stand-in for the drawing surface:

- `frontend/src/test/drawing.test.ts` (9) tests the stand-in itself:
  the browser a test starts in, the kinds it gives and does not give,
  what it says it was asked for, when a picture counts as held, and
  that it is as new once it is put in place again;
- `frontend/src/globe/drawing.test.ts` (7) tests the question: yes with
  the newer kind, no without any and no with the older kind alone; one
  picture asked for each time, of the newer kind; nothing held
  afterwards; and yes without an error in a browser that takes no
  picture back;
- `frontend/src/globe/GlobeStage.test.tsx` (8) tests the stage: empty
  where the browser draws; the two sentences in their order where it
  does not; the browser asked when the stage is first shown and not
  again, and its first answer kept; no picture held; and the same where
  React shows the stage twice, as it does in development;
- one test of the shell (`AppShell.test.tsx`) and three of the
  application (`App.test.tsx`): what the stage shows is in the globe
  stage and nowhere else, and the sections and both panels work as
  before where the globe cannot be shown.

The browser tests, with the built site:

- `frontend/e2e/stage.spec.ts` (10), in the project `chromium`, whose
  browser gives a page no 3D picture: the question itself, handed to
  the page as it stands, says no; the stage has the two sentences and
  nothing else; no file of the engine is asked for; the words are in
  the middle of the stage, in the colours and sizes of the theme, in
  lines no longer than 32 times the size of the text, and stay there
  when the panels are closed; on four narrow screens both sentences are
  whole inside the stage, 24 pixels from its edge, and the page does
  not scroll; and in a stage too low for the words they start at its
  top and the stage scrolls to their end;
- `frontend/e2e/globe/stage.spec.ts` (3), in the project `globe`: the
  stage is empty; the question, handed to the page, says yes forty
  times in a row with nothing on the console; and the top bar and both
  panels work around the empty stage.

Every other browser test of the project `chromium` now runs with the
two sentences in the stage, and none of them was changed for it.

## The life of the globe

The `Globe` component (`frontend/src/globe/Globe.tsx`, GLB-027) is one
element of the page and one engine that draws in it. It is handed how
the engine is loaded (`load`, which gives the way to start an engine in
an element, which in turn gives the way to stop it) and whom to tell
when that fails (`onFailed`). An engine that is started is handed a
listener, to which it says that its first complete picture is drawn
(`drawn`), and the component can be handed whom to tell of that
(`onDrawn`, GLB-029). It is not in the page yet: the real
engine is GLB-002, and what a person is told when it fails is GLB-004.
So these tasks have unit tests and no browser tests, and they run with
the stand-in engine (`frontend/src/test/engine.ts`).

`frontend/src/globe/Globe.test.tsx` (44):

- **The element**: one empty `div` and nothing else, which stays the
  same element when the globe is drawn again.
- **Loading**: the engine is asked for once when the globe is shown,
  and nothing is started while it loads. A globe that React draws but
  does not show, because something beside it is not ready, asks for
  nothing. The way of loading that was handed in when the globe was
  shown is the one used: a later one is not asked, and neither it nor
  another listener makes the globe load or start anything anew.
- **Starting**: when the engine has arrived one engine is started, in
  the globe's own element, which is in the page then; nobody is told
  anything.
- **Going**: the engine is stopped once when the globe goes and not
  before. An engine that arrives after the globe has gone is never
  started. A globe that is shown again after it has gone loads and
  starts anew, in its new element. Of two globes side by side each has
  its own engine, and only its own is stopped with it.
- **Failing**: whoever shows the globe is told once, with the very
  thing that went wrong, when the engine cannot be loaded, when the way
  of loading breaks before it gives anything, and when the engine has
  arrived and cannot be started; nothing is running then, and going
  says nothing more. The listener the globe has now is the one told.
  Nobody is told of an engine that cannot be loaded for a globe that
  has gone.
- **In development** React shows a component, takes it away and shows
  it again (`StrictMode`). Then the engine is asked for twice; once
  both loadings have ended, in either order, exactly one engine is
  running, in the globe's element; nothing is started for the loading
  of the globe that was taken away; that one engine is stopped once
  when the globe goes; a failure is told once though both loadings
  fail; and nothing is started when the globe goes while both loadings
  are under way.
- **The first complete picture** (GLB-029, 17 tests): nobody is told
  while the engine loads, nor when it has only been started. When the
  engine says that its picture is drawn, whoever shows the globe is
  told once, with nothing else, and the engine goes on running; told
  once though the engine says it again and again. Nobody is told what
  an engine says after its globe has gone. The listener the globe has
  now is the one told, also one that was handed in only after the
  engine was started; another listener makes the globe load or start
  nothing anew. A globe can be shown by someone who does not ask.
  Each of two globes is told of its own engine and of no other, and a
  globe that is shown again after it has gone is told of its new
  engine only. A globe that React put aside and shows again later
  (`Activity`) is stopped for that time, tells nobody what its old
  engine says, starts a new engine in the same element when it is
  shown again, and is then told a second time. Nobody is told that a picture is drawn when the engine
  cannot be loaded or cannot be started. A listener that fails is not
  taken for a failure of the engine: what it fails with goes back to
  the engine that said it, the engine goes on running, and the listener
  is not told a second time. Under `StrictMode` it is told once, of the
  one engine that runs, in whichever order the two loadings ended, and
  nobody is told once the globe has gone.
- **The engine itself**: the component as it is written brings in
  `react` and nothing else, and names nothing of the engine.

`frontend/src/test/engine.test.ts` (27) tests the stand-in: it has done
nothing at first; it counts every asking and does not arrive by itself;
it arrives and fails when the test says so, for the loading asked for
first or the one named, with what the test says went wrong; both come
back only when a chain of twenty things that waited on the loading has
run; a loading that was not asked for is named in a sentence; it
remembers where each engine was started and whether that was in the
page, counts the stops of each, and runs only what was never stopped;
every loading gives the same way to start; once broken it cannot be
started and remembers nothing more; what it hands out is a copy; and
two stand-ins share nothing. Since GLB-029 (11 tests): it says nothing
by itself to whom an engine was handed; an engine says that its picture
is drawn when the test says so, the one started first or the one named,
at once, as often as the test says so and stopped or not; what the
listener fails with comes back to the test; an engine that was not
started is named in a sentence, and an engine that could not be started
has no number; and two stand-ins do not share whom their engines say
it to. Where the tests that were there start an engine, they now hand
it a listener that does nothing.

No test of the two files ends with work of React's waiting: the set-up
of the unit tests holds every test to that (FND-056). The component
itself asks React for nothing after it is shown.

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

The least Node.js is held to what the packages need (FND-046). A package
in `frontend/package-lock.json` may say which Node.js it runs on, and npm
installs it on an older one with a warning only. So
`tests/repo/test_node_version.py`, part of the repository checks, reads
the range every locked package gives and holds that the least version in
`frontend/package.json` is the oldest Node.js that all of them allow: a
package that needs a newer one fails the check, and so does a least
version above what is needed. The lock file's own entry for the project,
and every place where the README tells a person which Node.js to have,
must say the same number, written the same way. The checks read the forms
of range the lock file uses (`>=22.12.0`, `^20.19.0`, `20`, and several
with `||` between) and fail on any other form rather than guess at it.
How they read a range, a lock file and a text is tested on ranges, lock
files and texts made up for the purpose, so that the checks of the real
files cannot pass by reading wrongly.

## The packages the site ships

The packages a visitor's browser gets are named under `dependencies` in
`frontend/package.json`: React with `react-dom`, and since GLB-001 the
engine of the globe, `@cesium/engine`, with `@cesium/core`, where the
engine keeps its arithmetic. `tests/repo/test_frontend_packages.py`, part
of the repository checks, holds that list. A package added to it, taken
from it, or named both there and among the packages that only build and
test the site, fails the check until the list in the test says the same,
so that whose code every visitor runs is decided and not come by. The
lock file must name the same packages for the project, must not mark a
shipped one as only for the work, and must install one copy of each, at
the top and nowhere beneath another package. The checks also hold that
the engine is the engine by itself: neither the full `cesium` package,
nor its ready-made viewer `@cesium/widgets`, nor the wrapper `resium` is
named or installed, at any depth of the lock file. How the checks read a
lock file is tested on lock files made up for the purpose.

The engine is tested as it is installed
(`frontend/src/globe/engine.test.ts`, unit tests): nothing stands in its
place. The tests ask it where six places on the Earth are that the
reference ellipsoid WGS84 gives exactly (four on the equator and the two
poles), and hold that longitude comes first, that a height is counted in
metres, and that it gives back the degrees and the height a place was
made from. One test makes the engine's globe and holds that its
ellipsoid is the very object the application gets from `@cesium/core`,
which two copies of that package would not give. The engine writes a
warning the first time a name is used that it wants imported from
elsewhere; in these tests a warning is an error, so a name taken from
the wrong package fails the test that uses it. Nothing of the
application uses the engine yet, so the built site is what it was.

## The licences that go with the site

The build writes the licences of the packages the site is built with
into one file of the site, `licences.txt` (ARCHITECTURE.md §3). The step
that does it (`frontend/sitebuild/licences.ts`) is tested in three ways.

On made-up lock files and made-up package folders
(`frontend/sitebuild/licences.test.ts`, unit tests, each folder made for
the test and taken away after it): which packages of a lock file count,
one for every place a package is put, and what the step refuses in a
lock file (no list of packages, a package with no version or with no
licence named); which files of a package hold a licence, by their names,
in its top folder and in every folder beneath it (FND-051), each given by
its path, the files of a folder before those of the folders in it; that
the packages put beneath a package, in a folder `node_modules` at any
depth, are not read as part of it, and that a link to a folder is not
followed, so that a folder which leads back to itself ends;
and that a text is kept letter for letter but for its line ends and the
empty lines around it; that a file that is not text, or is empty, is
refused; that a package which must be there and is not installed stops
the build, and one that may be left out does not; and every way the list
of packages without a text of their own can be wrong: a package that
brings no text and is not on the list, one on the list that brings a
text, one on the list that is not shipped, and one whose licence is said
to come with a package that brings none.

A computer gives the entries of a folder in an order of its own: Linux
by their names, Windows without regard to capital letters. In these unit
tests every folder gives them with the first entry last (a stand-in for
the one call of Node.js that lists a folder, which changes nothing but
the order), so that the order of the texts in the file is the work of
the step on every computer.

On this project as it is installed (the same file): every package the
project names as shipped is in the file with a text of its own, no
package that is only for the work is in it, React comes with the words
of its licence, and the packages without a text of their own are the
five a person has read, each given with a package that is there. Every
licence file of every such package is among the texts, at any depth of
its folder: the test finds the files another way than the step does,
from the list of all the files of a package as Node.js gives it. One
package brings a second licence beneath its top folder today,
`protobufjs` with `google/LICENSE`, and a test holds that both are
there.

On the built site (`frontend/e2e/licences.spec.ts`, browser tests): the
file is served as plain text under the path of the site and not at the
root of the server, it is letter for letter what the step writes for the
packages installed, it names React with the words of its licence, and
the source of the page names it. When these tests were written the
server of the build under test answered a path under the site that it
does not know with the page itself, so they go by the text and the kind
of the file and not by the status of the answer alone; since FND-052
that server answers such a path with "not found".

## The licences the project has accepted

`tests/repo/test_frontend_licences.py`, part of the repository checks,
holds the licence of every package the site is built with to a list: the
packages the lock file does not mark as only for the work, which are the
ones whose licences go with the site. The list names each accepted
licence as the lock file writes it, with what it asks of whoever passes
the code on and how the project meets that. There are seven today: MIT,
ISC, 0BSD, BSD-3-Clause, Apache-2.0, `(MPL-2.0 OR Apache-2.0)` and
`(MIT AND Zlib)`.

The checks fail for a package under a licence that is not on the list,
and name the package and the licence; for a package the lock file gives
no licence for, or something that is not a text; and for a licence on
the list that no package is under any more, so that the list says what
the site passes on today and nothing else. A package put in two places
is held in each. A licence is taken as it is written: `mit`,
`(Zlib AND MIT)` and `MIT OR GPL-3.0` are not on a list that has `MIT`
and `(MIT AND Zlib)`, and two licences on the list do not make their
combination one. What a combination asks is for a person to read, not
for a check to work out. A lock file the checks cannot read fails them;
it does not pass for want of anything found, and one check holds that
the reading finds the four packages the project itself names as shipped,
with their licences.

When a check fails: read the licence of the package it names, in the
text the package brings, and put it on the list with what it asks and
how the project meets it, in the same pull request, or do not take the
package. Do not put a licence on the list unread.

The list was first written by the planner of this project, who read each
of the seven in the texts the packages bring. It is the project's own
record of what it relies on, not a lawyer's opinion. How the checks read
a lock file and hold packages to a list is tested on lock files and
lists made up for the purpose.

## The engine's own files in the site

The engine of the globe fetches files of its own while it runs, and the
build puts them into the site under `cesium/` (ARCHITECTURE.md §3). The
step that does it (`frontend/sitebuild/engineFiles.ts`) is tested in two
ways.

On folders made up for the test (`frontend/sitebuild/engineFiles.test.ts`,
unit tests, each folder made for one test and taken away after it): the
step finds every file beneath the folder the engine fetches from, at any
depth, each by its path with `/` on every computer; the files of a folder
come before those of the folders in it, each by name, and the one call
that lists a folder has a stand-in that gives the entries with the first
one last, so that the order is the step's own work on every computer; no
file is left out for what it is called (one that begins with a dot, one
without an ending, a folder named `node_modules`); the rest of the
package and other packages are not read; a file listed as left out is
left out, and no other of the same name; and the step refuses, each in a
plain sentence, a listed file that is not there, a listed folder, an
engine that is not installed, a folder without files, and a link among
the files, which it names. On the engine as it is installed: the step
gives every file the package brings but those left out, found another
way than the step finds them; among them one of each thing the engine
asks for by name (a background script and a piece of one, a program, a
table, the picture of the Earth with the file that describes it, the
stars, a marker, the engine's own logo, a style sheet); the files are of
eight kinds, so that a kind the engine did not bring before is noticed;
exactly the two logos are left out, each with its reason; and the step
is for the build and not for the development server.

On the built site (`frontend/e2e/engine.spec.ts`, browser tests): the
folder `cesium/` of the build holds the files the step gives and no
other, each byte for byte the file of the installed engine, and no
picture, program or folder of the engine is anywhere else in the site.
Through the server of the build, one file of each of the eight kinds is
answered at its address under the site's path with the type a browser
needs and the bytes of the engine, and then every one of the 275 files
with its bytes. The engine's licence is in the site's file of licences.
The two logos are named in the tests themselves, not read from the list
of the step: each is in the installed engine and is answered "not found"
by the site. So are a file the engine does not bring, the rest of its
package, its own code, a file of the engine outside its folder, the
folder the engine keeps the files in and the folder of the installed
packages; and nothing of it is at the root of the server. These tests
can tell a file that is not there since FND-052.

In development (`frontend/sitebuild/engineFilesInDevelopment.test.ts`,
unit tests, GLB-024): the tests start the development server itself, with
the project's own settings, on this computer only and on a port that is
free, ask it over the network and stop it again; what the server keeps
for itself goes to a folder made for the run. It answers every one of the
275 files at the address the built site has for it, with the bytes of
the installed engine, the type a browser needs and its length; one file
of each of the eight kinds is asked by name. A file asked with a question
after its name is answered, and a question about a file (HEAD) is
answered without the file. Answered "not found": the two logos, which
the engine brings; a file and a kind of file the engine does not bring;
the folder itself and a folder in it; the engine's own code; a name that
leaves the folder, written with "%", and one with a stroke the other
way; a name that cannot be read; a file named in other capitals than it
has; and a request that would change something. Outside the folder, an
address that names no file is answered "not found" and not with the
page, which FND-052 had asked the development server by hand; the
engine's files are not at the root of the server; and the page, the
application's code and an icon are answered as before. On projects made
up for the test, each with a server of its own and no settings of this
project: the files are answered under the path of that site, a name the
address writes with "%" is read, a file is answered as it is now and not
as it was when the server started, and nothing else in that folder is
answered, whatever the project has there, while a folder of the same
name elsewhere is left to the server. The server does not start, and
says why in the step's own sentence, when the engine is not installed,
when a file listed as left out is not there, and when the engine brings
a file of a kind the step has no type for. The step has a type for
exactly the eight kinds the installed engine brings, and is for the
development server and not for the build.

The address the engine is told (`frontend/src/globe/engineAddress.test.ts`,
unit tests, GLB-025): the address is the folder of the engine's files
beneath the site's path, written out, and it names no other computer: it
is a path from the top of a site, and read from a page it stays on the
computer of that page. Telling puts the address under the name the engine
reads, also over another address. The engine as installed, once it is
told, builds the address of a background script, of a program, of a
table, of a picture of the Earth and of the description of those pictures
beneath the folder, on the computer of the page. The rest is read from
the text of the application's code, of the page and of the settings of
the build: the engine's own word for the address is in one module only;
the address is built in one module only and written out nowhere; the
folder's name is taken from where the build and the development server
take it; and the application tells the engine in one place, where it
starts, before it shows anything, with nothing before it but what it
brings in. Started for the test, the application has told the engine,
also when it cannot start. On the built site
(`frontend/e2e/engine.spec.ts`, two browser tests): the page as it was
built has told the address; and the browser, asked from the page for a
file of each of the eight kinds beneath the address it was told, gets
each with the status 200, at the address the site has for it, with the
length of the engine's file.

After a deployment the check of the published site fetches each of these
files with the rest and compares it byte for byte with the built one. It
also holds what GitHub Pages says each kind of file is, the engine's
among them (FND-053; see "Deployment").

## Latest results

Results are recorded per task in [PROGRESS.md](PROGRESS.md).
