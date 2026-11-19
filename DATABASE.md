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
