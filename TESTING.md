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
its names is there already (DAT-050); a store with the newest
schema lacks no migration; and the module
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
  be of each of the twelve kinds and collected from in each of the ten
  ways; it refuses what is not a web address, in four ways for each of its
  two addresses; and empty text, in two ways for each of three columns.
- A source is scanned every so many whole hours: nought, less and part of
  an hour are refused.
- A source whose terms were not read is not stored switched on and cannot
  be switched on later; it is switched on once they were read; a source
  that is switched on cannot lose the time; and it can be switched off
  again and keeps it. A source that is changed says when.

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
each list has exactly its texts in their order, twelve kinds of source,
ten ways of collecting and nine kinds of information; no text has two
names; each of the 31 texts is words in small letters with one space
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

- **The real schema** breaks no rule. Each of its five tables is named
  as soon as it is taken off the list, in the sentences the rule has
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

- **The triggers in the file**: the four of the history, by name and
  table, and no other.
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
because the real schema has no table of records yet: one with a column
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
  that is not there is stored; and a decided item can be put back to
  open, or deleted. The tests are there so that neither is taken for
  something the table does, and the last is changed by the task that
  closes it (DAT-054).

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
  address and for another reason.
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
schema has no table of records yet. What the store holds afterwards
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

The test of DAT-010 that puts a decided item back to open past the
function is unchanged and passes: that the table refuses it is
DAT-054.

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

## Latest results

Results are recorded per task in [PROGRESS.md](PROGRESS.md).
