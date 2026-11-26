# Changelog

All notable changes to this project are documented in this file. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Hosting model: GitHub Pages only, with no server. The architecture and task
  list were re-planned around a scheduled data pipeline and published data
  files (owner decision, 2026-11-17).
- Visual identity: the owner's Graphite theme and Sky Classic icon style are
  the design references (`docs/design/`).
- The application is served under `/MotoSphere/`, the path it has on GitHub
  Pages, in development and in the browser tests too; the development
  address is now <http://localhost:5173/MotoSphere/> (FND-022).

### Added

- Repository baseline: `.gitignore`, `.gitattributes`, `.editorconfig`,
  README, document stubs (DATA_SOURCES.md, DATABASE.md, TESTING.md,
  CHANGELOG.md) and the repository check suite in `tests/repo` (FND-001).
- Backend Python project skeleton (`backend/`): uv project with a committed
  lock file, `motosphere` package and pytest suite (FND-002).
- Backend linting and formatting with ruff, including security rules (FND-003).
- Backend static type checking with mypy in strict mode (FND-004).
- Backend settings module with environment variable and `.env` configuration
  (FND-005).
- Backend logging configuration: single line format with UTC timestamps and
  escaped line breaks (FND-006).
- API application factory and health endpoint `GET /api/health` (FND-007).
- `python -m motosphere` starts the API server (FND-008).
- Frontend project skeleton (`frontend/`): Vite, React and TypeScript in strict
  mode (FND-009).
- Frontend unit testing with Vitest and Testing Library (FND-010).
- Frontend linting with oxlint (React, accessibility and security rules) and
  formatting with Prettier (FND-011).
- Browser tests with Playwright against the built application, with an
  automatic page health check (FND-012).
- Dark theme design tokens and base styles, with automatic contrast checks
  (FND-013).
- The owner's Graphite theme: charcoal surfaces, sky-blue accent and Segoe UI
  font stack (FND-023).
- Application shell layout: top bar, sections panel, globe stage and details
  panel (FND-014).
- Section navigation: the nine sections listed in the sections panel,
  selectable by mouse or keyboard (FND-025).
- Collapsible side panels: buttons in the top bar close and open the sections
  and details panels, remembered for the session (FND-015).
- Current date in the top bar, in the language and time zone of the user's
  browser, changing at midnight (FND-026).
- Pipeline command line: `python -m motosphere <command>`, with a `version`
  command (FND-020).
- `export` command: writes the published data manifest, `manifest.json`,
  atomically and deterministically (FND-021).
- Application icon: the owner's approved design as the page icon, with a
  small version for browser tabs, an ICO fallback and a touch icon (FND-024).
- Frontend manifest reader: fetches and checks the published data manifest,
  with a plain result for every failure (FND-016).
- `npm run data`: exports the published data for local development; the
  browser tests run against freshly exported data (FND-027).
- Data status in the top bar: when the published data was updated, or that it
  is unavailable (FND-028).
- Browser tests can name the page problems they expect; the data status is
  tested with a missing manifest and a failed request (FND-029).
- `python scripts/check.py`: one command that runs every gate in order and
  reports which passed (FND-017).
- The check runner reports how many tests each gate ran and fails a gate when
  a test was skipped (FND-030).
- Lint, format and type gates for the Python files outside the pipeline
  (`scripts/`, `tests/`), run with the pipeline's locked tools (FND-031).
- Continuous integration: GitHub runs every gate on Linux for each pull
  request and each change to `main` (FND-018).
- Continuous integration also runs every gate on Windows (FND-032).
- `python scripts/audit.py`: the dependency audit, with exceptions that are
  recorded with a reason and a review date (FND-033).
- Deployment: every change to `main` that passes all gates on both machines
  is published on GitHub Pages, at
  <https://bigdaddy284.github.io/MotoSphere/> (FND-034).
- `python scripts/live.py <site.tar> <address>`: compares a published site
  with the site that was built, file by file, and names what differs
  (FND-035).
- After each deployment a job runs that comparison against the published
  site, so a deployment that leaves the site broken or stale fails the run
  (FND-037).
- Narrow screens (under 900 pixels wide: a phone, or a tablet held upright):
  the globe stage keeps the whole width, and an open side panel lies over
  it (FND-038).
- On a narrow screen the top bar takes the lines it needs, so that nothing
  in it is cut off: the name between the two buttons, then the data status
  and the date; the tagline is not shown there (FND-039).
- On a narrow screen the page opens with both side panels closed and the
  globe stage in view, only one panel is open at a time, and loading the
  page again closes them (FND-040).
- On a touch screen the buttons in the top bar and the sections are 44
  pixels tall, so that a finger can hit them; with a mouse nothing changes
  (FND-041).
- The layout is as tall as the part of the screen the browser really
  shows, so that on a phone its lower edge is not under the browser's own
  bars (FND-042).
- `python scripts/tools.py` says whether a computer has the tools MotoSphere
  needs: the version of each it found, and where to get one that is missing,
  too old or broken (FND-019).
- The data store's first decisions (`DATABASE.md`): what it relies on in
  SQLite, held by `motosphere.db.sqlite` and its tests on every machine the
  gates run on, and where the store is kept between scheduled runs
  (DAT-001).
- A setting for where the data store's file is, `MOTOSPHERE_STORE_PATH`
  (default `store/motosphere.sqlite3` in the `backend` folder). Git ignores
  that folder and every `*.sqlite3` file (DAT-002).
- The function that opens the data store, `open_store`, and SQLAlchemy 2 as
  the pipeline's way to its database: foreign keys enforced on every
  connection, failed work taken back as a whole, no connection left open,
  and a plain sentence when the store cannot be opened (DAT-021).
- Units of work, `unit_of_work`: what the pipeline writes to the data store
  is kept as a whole when the work ends and taken back as a whole when it
  fails, and a unit cannot commit part-way (DAT-022).
- For the backend's tests, a fixture that gives every test a real data
  store of its own and reports a test that leaves a connection to it open
  (DAT-003).
- The migration runner, `migrate`: the data store's schema is built and
  changed only by numbered migrations, each kept as a whole with the
  store's new version or not at all, and a store the code does not know is
  refused in plain words. No new package (DAT-004).
- The mark of a MotoSphere data store: the first migration marks the
  store's file as MotoSphere's, and a file that has anything in it and not
  that mark is never migrated. It is refused in plain words and left byte
  for byte as it was (DAT-023).
- The command `python -m motosphere migrate`: it brings the data store the
  settings name to the newest schema, makes the store if it is not there,
  and says in one sentence what it did. It is the first command that uses
  the store (DAT-024).
- `pending`: it says which migrations a data store lacks and writes
  nothing. `migrate` applies exactly those, and both refuse the same
  stores in the same words (DAT-027).
- The command `python -m motosphere schema`: it says in one sentence
  whether the data store is up to date, how many migrations it lacks, or
  that there is no store, and changes nothing. A store `migrate` would
  refuse is refused in the same words (DAT-025).
- The base of all models, `Base`: every table is strict, its columns have
  the types a strict table takes, and its constraints and indexes are
  named by one rule. `broken_rules` says which tables break a rule
  (DAT-005).
- Times in the data store, `motosphere.db.times`: a time is stored as
  text in one form, in UTC with its offset written out and the whole
  fraction of its second (`2026-11-19T08:26:04.123456+00:00`), so the
  order of the texts is the order of the times. A time without an offset
  is refused, and what comes back is an aware UTC time. A model's
  `datetime` column gets this type from `Base` (DAT-028).
- The key of every table: one whole-number column, `id`, which a model
  gets from `Base` without naming it, and whose values SQLite never gives
  twice, also not after a row is deleted. `broken_rules` names a table
  without it (DAT-029).
- When a row was first stored and when it was last changed: the columns
  `created_at` and `updated_at`, which a model gets from `Base` without
  naming them. The store's code sets them from the store's clock, `now()`
  in `motosphere.db.times`: both to the same moment for a new row, and
  `updated_at` anew for a row that is changed (DAT-031).
- `broken_rules` names a table without the two times every table has:
  one whose `created_at` or `updated_at` is missing, or is not as `Base`
  gives it (DAT-032).
- Text that must not be empty, `motosphere.db.texts`: a model says
  `Mapped[NotEmpty]` of a column, and its table gets a check, named by
  the naming rule, by which SQLite itself refuses text with no characters
  and text with nothing but white space, whoever writes the row. Text
  that is not empty is stored as it was given (DAT-030).
- `broken_rules` names a column whose text must not be empty and whose
  table does not have the check for it: a column of a table made without
  a model, and one that a subclass of a model adds to its parent's table
  (DAT-033).
- A test that holds the models and the migrations together, and
  `differences` in `motosphere.db.compare`, which says in plain words
  where the schema the models describe and the one the migrations build
  differ: it compares the statements SQLite keeps for each table and
  index, word for word (DAT-026).
- A column type can bring the check for its column, `WithItsCheck` in
  `motosphere.db.checks`: `Base` gives that check to the table of every
  model with such a column, and `broken_rules` names a column whose
  table is without it, in the type's own words. Text that must not be
  empty is the first such type, and the next needs no change to either
  (DAT-034).
- A column that is yes or no, `motosphere.db.yes_no`: a model says
  `Mapped[bool]`, the table holds the whole number 1 for yes and 0 for
  no, and SQLite itself refuses any other number in it, by a check.
  Only `True` and `False` are stored: a number and a word are refused,
  not taken for one of them (DAT-035).
- A column whose value is one of a list, `motosphere.db.lists`: the list
  is a `StrEnum`, a model says `mapped_column(OneOf(TheList))`, the table
  holds the list's texts, and SQLite itself refuses any other text in the
  column, by a check that names them. Only a value of the list is
  stored: text is refused, also text that is spelled like one
  (DAT-036).
- A column that is a web address, `motosphere.db.web`: a model says
  `Mapped[WebAddress]`, the table holds text, and SQLite itself refuses
  text that does not begin with `https://` or `http://` and go on with
  the name of a site, and text with white space in it, by a check. An
  address is stored as it was given (DAT-037).
- `broken_rules` names a name that more than one constraint or index of
  a table has, and how many have it. SQLite takes a table with two
  checks of one name, and a refusal then does not tell which of the two
  refused the row (DAT-038).
- The two lists an information source is described by, in the new
  package of the models, `motosphere.db.models`: the twelve kinds of
  source and the ten ways of collecting of the design, each with the text
  that is stored (DAT-039).
- The first table of the data store, `source`, for the information
  sources, with its model and the first migration. A new source is
  switched off, and the table refuses one that is switched on before its
  terms were read. The migrations are written in `motosphere.db.history`,
  and `SCHEMA` in `motosphere.db.models` is the whole schema: a test
  proves that no model is missing from it (DAT-006).
- The table `source_offer`, which says what kinds of information each
  source offers, with its model, the second migration and the list of
  the nine kinds. A source offers a kind once, an offer belongs to a
  source that exists, and a source that has offers cannot be deleted
  (DAT-040).
- The table `collection_run`, the record of every collection run, with
  its model, the third migration and the list of the four outcomes. A
  run belongs to a source that exists, a source that has runs cannot be
  deleted, a run cannot end before it started, its end and its error go
  with its outcome, and no count is below 0. `mark_interrupted` in
  `motosphere.db.runs` marks the runs a dead job left running as
  interrupted and touches nothing else (DAT-007).
- `standing_of` in `motosphere.db.source_health` says how a source is
  doing, read from its collection runs and stored nowhere else: when it
  was last attempted, when that last succeeded, its last error, and its
  health, which is `not yet scanned`, `healthy`, `failing` or
  `interrupted` (DAT-041).
- The store's first index, over the source and the start of a collection
  run, with the fourth migration. SQLite goes straight to the runs of one
  source in the order they started, where it read the whole table and
  sorted; a test reads that from SQLite itself for the statements of
  `standing_of` (DAT-042).
- The two lists that say how far a collected record can be trusted, in
  `motosphere.db.models.provenance`: its confidence, `high`, `medium` or
  `low`, and its verification status, `official`, `independent`,
  `reconstructed` or `unverified`. No table has a column of them yet
  (DAT-043).
- A column that is a calendar day, `motosphere.db.days`: a model says
  `Mapped[date]`, the table holds text in one form, `2026-11-24`, and
  SQLite itself refuses text that is not a day of the calendar in that
  form, by a check; the 30th of February is refused. Only a `date` is
  stored: a time is refused, not cut down to its day, and no time of day
  is made up for a day (DAT-044).
- The columns by which every collected record says where it came from,
  as one set, `Collected` in `motosphere.db.models.provenance`: its
  source, the address it was found at, when it was collected, the day it
  was published where the source says it, when the source was last seen
  to say it, how it was got, its confidence and its verification status.
  A model of collected records is a subclass of `Collected`. SQLite
  refuses a record of a source that is not there, the deleting of a
  source that records came from, and a record last seen at its source
  before it was collected. No table has the set yet (DAT-008).
- An index over the source of a collected record, which `Collected`
  gives to every table with the set. SQLite goes straight to the records
  of one source, where it read the whole table, also when a source is to
  be deleted and it looks whether records came from it; the tests read
  that from SQLite itself (DAT-045).
- A rule that names every table which does not say where its records
  came from, `broken_provenance` in
  `motosphere.db.models.provenance_rule`. A table must have the columns
  of `Collected` as it gives them, with the index over its source and
  the check of its two times, unless it is on the list of the tables
  that hold no collected records, `NOT_COLLECTED`, which has each with
  its reason. A test holds the real schema to it (DAT-046).
- The table of the changes to records, `record_change`, with its model
  `RecordChange` and the fifth migration: for one field of one record,
  what it held before and holds now, when it was changed, and the
  collection run or the person that caused it. The table refuses a
  change that changed nothing, one that nothing caused and one that two
  things caused. The data store's schema is at version 5. Nothing
  writes a change yet (DAT-009).
- `change` in `motosphere.db.changes`: one function that gives a stored
  record new values and writes what each changed field held before to
  the table of the changes, in the same unit of work, with the
  collection run or the person that caused it. A field that holds the
  value already gets no row; values are compared as the text of what
  the store keeps; and a change the store refuses leaves neither the
  change nor its history (DAT-047).
- The history of the records is only added to: the sixth migration
  makes four triggers on `record_change`, and SQLite itself then refuses
  to edit a row, to delete one, to put a new row in the place of one
  (`INSERT OR REPLACE`), and to store a row with a key below 1, each in
  one plain sentence, whoever writes to the file. The data store's
  schema is at version 6 (DAT-048).
- Two indexes on the history of the records, made by the seventh
  migration: one finds the changes of one record, in the order they
  were made, and one the changes a collection run caused, which SQLite
  also uses before it lets a run be deleted. Neither question reads the
  whole table any more. The data store's schema is at version 7
  (DAT-049).
- The review queue: the table `review_item`, made by the eighth
  migration. One item is one doubt about one record, of one of three
  kinds: two records may be the same thing, a source says otherwise
  than the record holds, or a source says a value that the rules of
  its field refuse. An item says why, names what goes with its kind
  and nothing else, and says whether a person accepted or rejected it,
  who and when. A note can be kept with it, which is never published.
  The data store's schema is at version 8. Nothing opens an item yet
  (DAT-010).
- One doubt is one review item: the store itself refuses the same
  doubt a second time, by two indexes the ninth migration makes. A
  possible duplicate is the same doubt when it is about the same two
  records, and a doubt about a field when the same source says the
  same thing of the same field of the same record. A doubt that was
  decided counts as well, so that a person is not asked again what
  they have answered. The data store's schema is at version 9
  (DAT-050).
- `open_possible_duplicate` in `motosphere.db.review`: one function
  that puts two stored records of one table that may be the same thing
  to the review queue, in either order, and gives back the item. A
  doubt that is there already stays one item, also after it was
  decided. A record that is not stored, two records of two tables,
  rows of a table that holds no collected records and a record given
  as its own duplicate are each refused in one sentence (DAT-051).

### Removed

- The API server and its health endpoint, the `MOTOSPHERE_API_HOST` and
  `MOTOSPHERE_API_PORT` settings and the `fastapi`, `uvicorn` and `httpx2`
  dependencies, following the GitHub Pages hosting decision (FND-020).
- The dependency audit's one recorded exception, for a slow pattern match
  in picomatch (GHSA-fc5q-39xc-vjpf, recorded on 2026-11-17): a day later
  `npm audit` no longer reported the advisory, and the audit failed until
  the exception was taken out. No exception is recorded now (FND-036).

### Fixed

- A browser test that could fail by chance. The test of "Loading data…"
  expected the request for the data to have arrived as soon as the page
  said so, and the page says so before it asks. The test now waits for the
  request (FND-043).
- What `broken_rules` said of a column whose table has two checks of the
  name of the column's own check. It went by whichever of the two it came
  to last, and the order in which it comes to them is not fixed. The
  column now has its check if either of the two is that check (DAT-038).
