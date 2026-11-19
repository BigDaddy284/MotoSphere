# Database

This document records the data store: the decisions it rests on and, as
tables are added, its schema and entity relationships.

## Current state

No schema exists yet. The store is an SQLite file used by the data pipeline
([ARCHITECTURE.md](ARCHITECTURE.md) §5). Its first decisions are recorded
below (task DAT-001).

## Where the store's file is

The store is one SQLite file. Its path is the setting
`MOTOSPHERE_STORE_PATH`, by default `store/motosphere.sqlite3` in the
`backend` folder (README.md, "Configuration"). An empty path is refused when
the settings are read. Reading the settings creates no file and no folder.

Git ignores `backend/store/` and every `*.sqlite3` file with the files
SQLite keeps beside one, wherever they are: the file itself is never
committed. What is kept between runs is the text written out from it (see
"Where the store is kept between runs").

## Opening the store

One function opens the store: `open_store(path)` in `motosphere.db.store`.
It returns the SQLAlchemy engine for the file, and nothing else in the
pipeline connects to it. What it promises:

- **An SQLite that lacks something is refused first.** The function asks
  `missing()` (see "What the store relies on in SQLite") before it touches
  the disk. If the answer is not empty, the store is not opened and nothing
  is written.
- **Every connection enforces foreign keys.** SQLite leaves them off unless
  each new connection switches them on, so the engine does that for every
  connection it makes.
- **Transactions are SQLite's own.** A connection is always inside a
  transaction, and work that fails is taken back as a whole, a new table or
  another change to the schema included. (Python's older way of handling
  SQLite transactions keeps a change to the schema even when the work
  around it is taken back. The engine uses the way Python 3.12 brought,
  `autocommit=False`, which SQLAlchemy documents for SQLite.)
- **No connection is kept open.** A connection is closed when its work is
  done, so a store that is not in use is a closed file, which Windows needs
  before the file can be moved or removed.
- **The path is made whole when the store is opened.** A relative path is
  taken from the current folder at that moment and the engine keeps to that
  file. A file that is not there yet is created, empty, with its folder.

When the store cannot be opened the function raises `StoreError` with one
plain sentence that begins "The data store cannot be opened:" and names the
reason: what the SQLite lacks, a path that is a folder, a folder that
cannot be made, or a file that is not an SQLite database (the file is left
as it was).

## Units of work

Everything the pipeline writes to the store, it writes in a unit of work:
`unit_of_work(store)` in `motosphere.db.work`, used in a `with` statement
on the engine that `open_store` returned. It gives an SQLAlchemy session
for one piece of work. What it promises:

- **Kept as a whole.** When the block ends, everything the work did is
  committed together, rows that were only added to the session included.
- **Or not at all.** When the block raises, everything the work did is
  taken back, a new table included. That holds for a row that breaks a
  foreign key, whether the statement was sent at once or the row is written
  when the unit ends, and for work that is stopped from outside (Ctrl+C).
- **The error is the caller's.** The error that ended the work reaches the
  caller as it was raised, not wrapped in another.
- **One connection, closed either way.** A unit of work does all its work
  on one connection and closes it when it ends or fails.
- **No commit part-way.** A unit of work that calls `commit()` itself is
  refused with "A unit of work is kept as a whole when it ends; it cannot
  be committed part-way.", and what it did is taken back. Work that took
  itself back with `rollback()` cannot go on in the same unit.
- **Over means over.** The session cannot be used after its unit has ended.
  What the work read or wrote can still be read afterwards, as it was when
  the unit ended.

SQLite lets one connection write at a time, and the pipeline does one unit
of work at a time: a unit is not started inside another.

## How the schema changes

The store's schema is built and changed only by migrations. A migration is
a Python function that is given a connection and changes the schema, and
the records with it where the change needs that. The migrations stand in
one list, `MIGRATIONS` in `motosphere.db.migrations`, oldest first, and the
place of a migration in that list is its number. The list is empty until
the first table is added. What the module promises:

- **A store knows its version.** The number of the last migration a store
  has had is kept in the file itself, in the field SQLite gives
  applications for this (`user_version`). A new store is at version 0.
  `schema_version(store)` reads it.
- **`pending(store)` says which migrations a store lacks**: their
  numbers, in order. It writes nothing. A new store lacks all of them and
  a store that is up to date lacks none. It refuses a store exactly as
  `migrate` does, in the same words, because `migrate` asks it.
- **`migrate(store)` gives a store the migrations it lacks**, in order, and
  returns their numbers: exactly those `pending` names. A store that lacks
  none is not written to.
- **A migration and its version are one transaction.** A migration is kept
  as a whole, with the store's new version, or not at all. When one fails,
  the store stays at the version before it, the migrations before it stay
  applied, and the error reaches the caller as it was raised. The store
  goes on from there once the migration is mended.
- **Only a store of MotoSphere's is migrated.** A store's file carries a
  mark: the number 1299141488 (the letters "MoSp", `APPLICATION_ID`), in
  the field SQLite gives applications to say whose a database is
  (`application_id`). A new file, with nothing in it, gets the mark in the
  transaction of its first migration, so a file has the mark and its first
  version together or neither. A file that carries the mark is migrated.
  Every other file is refused before anything is written, with one plain
  sentence that begins "The data store cannot be brought up to date:",
  names the file and says why (`SchemaError`), and is left byte for byte as
  it was: a file with the mark of another application, and a file with no
  mark that has a table, a view or a version. So `migrate` never changes
  another program's database, whatever file `MOTOSPHERE_STORE_PATH` names.
- **A version the code does not know is refused.** A store that is newer
  than the code, or whose version no migration gave, is refused with one
  plain sentence that begins "The data store cannot be brought up to
  date:" (`SchemaError`), and is left as it is. The mark is looked at
  first, so the file of another program is never taken for a newer store.
- **The history only grows.** A migration that has been merged is not
  changed, moved or taken out, because stores and snapshots at its version
  exist. A mistake in one is put right by a new one.
- **There is no way back.** No migration can be undone by another function.
  An earlier state of the store is an earlier snapshot in the `data` branch
  (see "Where the store is kept between runs"), rebuilt at the version it
  was written at.
- **A migration does not commit.** `migrate` does. A migration that commits
  by itself fails, and what it had done by then is kept without its
  version. The test that brings an empty store to the newest schema with
  the real list fails for such a migration, so it cannot be merged.

**The command.** `python -m motosphere migrate` brings the store to the
newest schema (DAT-024). It opens the store at `MOTOSPHERE_STORE_PATH`
with `open_store`, which makes the file if it is not there, calls
`migrate`, and writes one sentence to standard output, with the file's
whole path and the store's version: "A new data store was made: …", "The
data store was brought up to date: … went from schema version 2 to 5." or
"The data store is up to date: …". A store that cannot be opened, or that
is refused, gives its one sentence on standard error, with nothing before
or after it, and the exit code 1, and is left as it is. An error inside a
migration is not caught: it is a fault in the code, its traceback is what
whoever mends it needs, and the store stays at the version before that
migration.

**The command that only looks.** `python -m motosphere schema` says which
schema the store has, and never writes (DAT-025). Where
`MOTOSPHERE_STORE_PATH` names no file it says "There is no data store: …
does not exist." and makes none: it does not call `open_store`, which
would. Otherwise it opens the store, asks `pending`, and writes one
sentence to standard output, with the file's whole path: "The data store
is up to date: … is at schema version 5." or "The data store lacks 2
migrations: … is at schema version 3, and the newest is version 5." In
all three cases the exit code is 0. A store that cannot be opened, or that
`migrate` would refuse, gives the same sentence as there on standard
error, and the same exit code 1: the two commands ask the same function,
so they cannot come to disagree about a store. The file is byte for byte
the same afterwards, and nothing is made beside it.

SQLite can add, rename and drop a column and rename a table in place. For
any other change the table is built anew. A migration can do that inside
its transaction while other tables point to the table and foreign keys
stay on: it asks SQLite to check them only when the transaction ends
(`PRAGMA defer_foreign_keys = ON`, which lasts for that transaction),
copies the table aside, drops it, makes it anew under its own name, fills
it again and drops the copy. If a row that is pointed to was lost on the
way, the commit is refused and the store is as it was before. The tests
do exactly this on every machine the gates run on.

The mark was chosen on 2026-11-19 (DAT-023). SQLite's own list of the
marks it knows (`magic.txt` in its source, read that day) names Fossil,
GeoPackage, MBTiles and a few others, and 1299141488 is not among them.
The mark never changes: a store with another one would be refused.

**Decision (DAT-004):** a small runner of the project's own, not Alembic.

| Way | For | Against | Verdict |
|---|---|---|---|
| A runner of the project's own | No new package: about thirty lines on SQLAlchemy, which the pipeline already has. A migration and its version are one transaction, and the tests prove it against a real file. Nothing to configure. | The project keeps it. It has no way back and no branches, and it does not write a migration from the models. | Chosen |
| Alembic | The usual tool beside SQLAlchemy. It can write the first draft of a migration from the models, and it rebuilds a table for the changes SQLite cannot make in place. | Three more packages (alembic 1.20.1, Mako 1.4.3 and MarkupSafe 3.0.4 on 2026-11-19), a configuration file and a folder of scripts of its own. What it adds beyond the runner serves several developers changing the schema at once, ways back, and databases a person administers by hand. The store has one line of history and one writer, and is rebuilt from its snapshot on every run. | Not now |

The decision is looked at again if the store ever moves to a database
server (ARCHITECTURE.md §4).

## The rules every table keeps

A model is a class that describes one table. Every model is a subclass of
`Base` in `motosphere.db.base` (DAT-005), and through it every table keeps
these rules:

- **A table is strict.** In an ordinary table SQLite stores whatever it is
  given: the text "seven" in a column of whole numbers. In a strict table
  it refuses a value that is not of its column's type. `Base` makes the
  table of every model strict, whatever else the model says of its table.
- **A table has the same key as every other**: one whole-number column
  named `id`, its first column. A model does not name it; `Base` gives it.
  SQLite gives a new row the next key, and **never gives a key twice**
  (the key is written `PRIMARY KEY AUTOINCREMENT`). Without that, SQLite
  gives the key of a deleted last row to the next new row, and what
  pointed to the old row by its key, its history or where it came from,
  would point to the new one. A row may be stored with a key of its own,
  and later keys come after it. SQLite keeps the last key each table gave
  in a table of its own, `sqlite_sequence`; a copy of the store that is to
  keep the promise has to keep that table too (the snapshot, DAT-019 and
  DAT-020).
- **A row says when it was first stored and when it was last changed**, in
  the last two columns of every table, `created_at` and `updated_at`
  (DAT-031). A model does not name them; `Base` gives them. They are
  times as the store keeps a time (see "Times" below), and the store's
  code sets them, not the table and not the caller: a new row gets the
  moment the store's clock says, the same moment in both columns, and a
  row that is changed gets a new `updated_at` and keeps its `created_at`.
  A row that is stored again as it was keeps both. See "When a row was
  stored and changed" below.
- **A column has one of the types a strict table takes**: INTEGER, REAL,
  TEXT or BLOB. A model that gives only the Python type of a column gets
  the right one: an `int` is INTEGER, a `str` TEXT, a `float` REAL and
  `bytes` BLOB, and a `datetime` is the store's own type for a time, which
  is TEXT (see "Times" below). SQLite refuses to make a strict table with a
  column of another type ("unknown datatype"); SQLAlchemy's own types for
  text, for numbers with a fraction, for yes and no and for times are four
  such.
- **Constraints and indexes are named by one rule** (`NAMING`), so that a
  migration can name what it changes, and so that the names are the same
  on every machine:

  | What | Its name | For example |
  |---|---|---|
  | A foreign key | `fk_<table>_<columns>_<table it points to>` | `fk_item_owner_id_owner` |
  | A unique constraint | `uq_<table>_<columns>` | `uq_item_owner_id_number` |
  | A check | `ck_<table>_<what the model calls it>` | `ck_item_number_positive` |
  | An index | `ix_<table>_<columns>` | `ix_item_place` |

  A check has no columns to be named after, so its model gives the last
  part of the name. A check without one is refused when its table is
  defined. The key has no name: SQLite writes it with its column, and
  nothing can change a key but building the table anew.

`broken_rules(schema)` says in plain words which tables of a schema break
a rule: a table that is not strict (one made without a model can be), a
table without the key every table has, a table without the two times
every table has, and a constraint or an index that was named by hand. A
test holds the real schema to it with every change.

A table is without the two times (DAT-032) if `created_at` or `updated_at`
is missing, is not a time as the store keeps one, may be empty, or gets a
value from the table itself; if the store's code does not set it by
calling a function when a row is stored (it sets none, or one fixed
moment, or asks SQLite for the moment, which SQLite does not give in the
store's form); if `updated_at` is not set anew in that way when a row is
changed; or if `created_at` is set anew at all. The rule sees that the
store's code calls a function, not which one: that it is the store's
clock is what a model gets from `Base` by not naming the two columns.

There is no model yet, and so no table. The rules are proven with two
models of the tests' own, which are kept in a schema apart from the real
one. The rule for text that must not be empty (DAT-030) follows.

## Times

A strict table has no type for a time, so the store keeps a time as text,
in one form (DAT-028, `motosphere.db.times`):

```
2026-11-19T08:26:04.123456+00:00
```

- **It is always in UTC.** A time given with another offset is stored as
  the same moment in UTC: 10:26 at +02:00 is stored as 08:26.
- **Its offset is always written out**, as `+00:00`, so the text says of
  itself that it is UTC.
- **It always has the six digits of the fraction of its second**, also
  when they are zeros. So every text has the same length, and the order of
  the texts is the order of the times: sorting and comparing rows by a
  time needs nothing but the text.
- **A time without an offset is refused** before anything is stored, with
  one plain sentence: nothing can tell which moment it means. The unit of
  work it was part of is taken back as a whole. A question that compares a
  column with such a time is refused in the same way.
- **What comes back is an aware UTC time**, whatever offset was given.

A model says `Mapped[datetime]`, and `Base` gives the column the store's
type for a time, `UtcDateTime`. In the table the column is TEXT.

The text can be read without the pipeline's code: by a person, and by
SQLite's own date functions (`unixepoch`, `strftime`), which take it as
the moment it is.

The store holds this one form only. Text in any other form in a column of
a time (a time in another offset, one without its fraction, SQLite's own
`2026-11-19 08:26:04`) can only get there past the models, and is refused
when it is read, with a sentence that shows the text: a wrong time is not
passed on as if it were right. The table itself does not check the form;
whether it should is settled with the checks of DAT-030.

Times UTC cannot say in the years 1 to 9999 are refused. A column for a
date without a time of day needs a type of its own, which comes with the
first table that has such a column.

## When a row was stored and changed

Every table has the columns `created_at` and `updated_at` (DAT-031). Both
must be there in every row, and the table gives neither a value of its
own: the store's code does, when it runs the statement that stores or
changes the row.

- **The store has one clock**, `now()` in `motosphere.db.times`, which
  says the moment it is, in UTC. It is asked once for every row that is
  stored, once for every row that is changed through its model, and once
  for a statement that changes many rows at once.
- **A new row** gets that moment as `created_at` and as `updated_at`: the
  same moment, not two readings of the clock. So a row that was never
  changed is one whose two times are the same.
- **A changed row** gets a new `updated_at`. Its `created_at` stays. A row
  whose values are set to what they already are is not changed: both
  times stay, and the clock is not asked.
- **A row may be stored with times of its own**, and keeps them; with only
  a `created_at` of its own, it was last changed then. The store that is
  built again from its text files (DAT-020) stores its rows that way.
- This holds for rows stored and changed through a model and through
  SQLAlchemy's `insert` and `update` of a model, one row or many.

Two ways of writing go past it, and neither is used by the store's code:

- **Plain SQL.** A row written with plain SQL has to say both times itself,
  or SQLite refuses it ("NOT NULL constraint failed"). A change written
  with plain SQL leaves `updated_at` as it was.
- **A statement that stores a row or changes the one that is there**
  (`INSERT … ON CONFLICT DO UPDATE`). When it changes a row, `updated_at`
  stays as it was: SQLAlchemy does not set it there. The first code that
  uses such a statement has to set `updated_at` in it.

A test sets the clock with the fixture `clock` (`TESTING.md`), so that it
knows every moment the store was told.

## What the store relies on in SQLite

SQLite is not one program. Every Python carries its own, built with its own
choice of features, and the Python on a GitHub machine is not the one on a
developer's computer. So the store needs **SQLite 3.45.0 or newer** and the
six features below, and relies on nothing else that a build of SQLite can
leave out.

| Feature | Why the store needs it |
|---|---|
| foreign keys that are enforced | A record cannot point to a source, a country or a track that is not there. |
| tables with strict column types | A number column holds numbers. Without this, SQLite stores whatever it is given. |
| statements that return the rows they wrote (RETURNING) | The key of a new record is read back in the statement that wrote it. |
| JSON functions | Structured values that are kept as text can be read and checked in the store. |
| R*Tree indexes (for finding places inside a part of the map) | Finding the tracks inside a rectangle of the map. Whether tracks use one is decided by measurement in DAT-016. |
| full-text search (FTS5) | Finding a name in the store, for duplicate detection and for administration. |

`motosphere.db.sqlite` names the least version and the six features, and
its function `missing()` says in plain words what a given SQLite lacks. Its
tests run against the SQLite of the Python that runs them, so the gates
prove it on Linux and on Windows for every change
([TESTING.md](TESTING.md)).

What each machine had on 2026-11-19, read by the planner from a probe that
ran on GitHub's machines (pull request #53, closed without merging, run
44432064695) and on the planner's own:

| Machine | Python | SQLite | The six features | Not in this build |
|---|---|---|---|---|
| GitHub, Linux (`ubuntu-24.04`) | 3.12.16 | 3.45.1 | all | Geopoly |
| GitHub, Windows (`windows-2025`) | 3.12.10 | 3.49.1 | all | Geopoly, the `dbstat` table |
| The planner's Linux (uv's own Python) | 3.13.18 | 3.53.1 | all | – |

3.45 is the oldest series the store has been run with, so it is the least
version: an older SQLite may well have all six features, but nobody has
tried.

Also in all three, and free to use: JSON kept in binary form (JSONB),
generated columns, `INSERT … ON CONFLICT`, window functions, dropping and
renaming a column, indexes on part of a table and on an expression, tables
without a row id, the mathematical functions, and the trigram tokenizer of
FTS5.

Not to be used, because at least one machine lacks them: Geopoly and the
`dbstat` table.

Two limits differ between the builds, and the store's code stays under the
lower of each: one statement carries at most 32,766 bound values (250,000
on GitHub's Linux), and one function call at most 127 arguments (1,000 on
the other two).

## Where the store is kept between runs

A run of the pipeline on GitHub starts on an empty machine, so the store
must be kept somewhere that lasts.

**Decision:** after a run the store is written out as text files that are
the same, byte for byte, whenever the store is the same, and those files
are committed to a branch of this repository named `data`. The next run
rebuilds the SQLite file from them.

| Way | For | Against | Verdict |
|---|---|---|---|
| Text files in a `data` branch | Every change to the data is a readable difference with a date, kept for good. Nothing outside the repository is needed. The rebuild is proven by a round-trip test (DAT-020). | The repository grows with every change, and files and repositories have size limits (below). | Chosen |
| The database file as a release asset | One file of up to 2 GiB, and no limit on the total. | The file is binary: there is no readable history and no way to see what a run changed. Each run replaces it, so an earlier state is gone unless every one is kept. | In reserve, for size |
| A workflow cache | Fast. | GitHub removes an entry that was not read for 7 days, and the oldest entries when the repository's 10 GB are used up. It is not a place to keep anything. | Rejected |
| A workflow artifact | Simple. | It belongs to one run, and goes when that run is deleted or its artifacts expire. | Rejected |

GitHub's limits, as its documentation gave them on 2026-11-19:

| What | Limit | Read from |
|---|---|---|
| One file in a repository | A warning above 50 MiB; refused above 100 MiB | <https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github> |
| A repository | "ideally less than 1 GB, and less than 5 GB is strongly recommended" | the same page |
| A published Pages site | No larger than 1 GB; a soft limit of 100 GB of traffic a month; a deployment is stopped after 10 minutes | <https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits> |
| A release asset | Under 2 GiB each, at most 1,000 in a release, no limit on the total | <https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases> |
| Workflow caches | 10 GB for a repository; an entry not read for 7 days is removed | <https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching> |

How the decision is kept within those limits:

- No file of a snapshot is larger than 25 MiB, half of the size GitHub
  warns about. Large tables are divided into several files by a rule that
  depends only on the data (DAT-019).
- The command that writes a snapshot reports its size (DAT-019). When one
  snapshot passes 250 MB, or the repository with its history 1 GB, the
  decision is looked at again before more is added. The tables that grow
  fastest, the race results, would move to release assets first.
- The published site has a budget of 500 MB, half of the limit, and the
  export's own check holds it (PUB-007).

Who writes the branch: only the job that collects, one run at a time. It is
the only job with the right to write to the repository's contents, and it
runs no code that came from a collected page (CLAUDE.md §14). The job is
planned with the first task that collects real records. Until then the
store exists only in tests.
