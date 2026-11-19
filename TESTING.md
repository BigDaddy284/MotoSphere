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
kept in a schema of their own, so the real schema never sees them.

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
without a name is refused when its table is defined. Four more functions ask
the rule about a column type of the tests' own that brings a check
(DAT-034): a column of it is named, in that type's own words, until its
table has the check; the check of one type does not count for a column of
another, in four ways; columns of the two types in one table are named in
their order, each in its own type's words; and a type that says it brings a
check and gives none is an error, for the rule and when a model with a
column of it is defined. A table that must keep the rules gets its key and
its two times from two helpers of the tests, `the_key` and `the_times`. One
test there holds the real schema to the rules: `broken_rules(Base.metadata)`
must be empty. It passes today because there is no table yet, and it is the
test that fails when a table is added that breaks a rule.

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
fixture to the newest schema with `migrate`, makes the tables of
`Base.metadata` in a second real file, and `differences` must find
nothing. It passes today because there is neither a model nor a migration
yet, and it is the test that fails when one is added without the other.
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

## Latest results

Results are recorded per task in [PROGRESS.md](PROGRESS.md).
