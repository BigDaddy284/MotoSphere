# Database

This document records the data store: the decisions it rests on and, as
tables are added, its schema and entity relationships.

## Current state

The store is an SQLite file used by the data pipeline
([ARCHITECTURE.md](ARCHITECTURE.md) §5). Its schema is at version 19 and
has seven tables: `source`, that of the information sources (DAT-006),
each of which can say which country it is of (DAT-057),
`source_offer`, which says what kinds of information each of them offers
(DAT-040; see "The information sources" for both), `collection_run`,
the record of every time a source was collected from (DAT-007; see "The
collection runs"), which has the store's first index (DAT-042),
`record_change`, which keeps what a field of a record held before it
was changed (DAT-009; see "The changes to records") and is only added
to: the store itself refuses to edit, delete or replace a row of it
(DAT-048; see "The history is only added to"). Two indexes find the
changes of one record and the changes one run caused without reading
the whole table (DAT-049). The fifth is `review_item`, the review
queue: what is in doubt and waits for a person's decision (DAT-010;
see "The review queue"), where the store itself refuses the same doubt
a second time (DAT-050) and keeps a decision: an item that was decided
is neither edited nor deleted (DAT-054; see "A decision is kept"), and
no row takes its place (DAT-055; see "A decided item is never
replaced"). A key of the queue is 1 or more, under every name SQLite
has for the key (DAT-056, DAT-068; see "A key is 1 or more"). The sixth is `country`, the countries by their two codes of
ISO 3166-1, and the first table of collected records (DAT-011; see
"The countries"); a new store has no rows in it, and the command
`countries` loads them (DAT-061; see "The loading of the countries").
The seventh is `region`, the parts a country is divided into, each of
one country and by its name (DAT-013; see "The regions"), which can
say its code of ISO 3166-2 (DAT-064), which begins with the code of
its country (DAT-067); it has no rows, and nothing
writes to it yet. One function
changes a record and writes its history in the same unit of work
(DAT-047; see "Changing a record"), one puts two records that may
be the same thing to the review queue (DAT-051; see "Opening a possible
duplicate"), one puts what a source says of a field of a record
there (DAT-053; see "Opening a doubt about a field"), and one puts
down a person's decision on an item (DAT-052; see "Deciding an
item"); nothing calls them yet. The
columns by which every collected record says where it came from are in
the code, as one set that a model of collected records takes whole
(DAT-008; see "Where a collected record came from"), and so are the two
lists that say how far such a record can be trusted (DAT-043; see "How
far a collected record can be trusted"). The countries are the first
table that has them, and the regions the second. The other five tables
hold no collected records,
and a list in the code says of each why not. A rule names every table
that neither has the set nor is on
that list (DAT-046; see "Every table says where its records came from,
or why not"). The decisions the store rests on are recorded below, from
task DAT-001 on.

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
one list, `MIGRATIONS`, oldest first, and the place of a migration in that
list is its number. The list and the migrations themselves are written in
`motosphere.db.history` (see "The history" below), and
`motosphere.db.migrations` gives a store those it lacks. What that module
promises:

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
data store was brought up to date: … went from schema version 2 to 13." or
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
is up to date: … is at schema version 19." or "The data store lacks 16
migrations: … is at schema version 3, and the newest is version 19." In
all three cases the exit code is 0. A store that cannot be opened, or that
`migrate` would refuse, gives the same sentence as there on standard
error, and the same exit code 1: the two commands ask the same function,
so they cannot come to disagree about a store. The file is byte for byte
the same afterwards, and nothing is made beside it.

**The store a command works on.** `migrate` makes the store and brings it
to the newest schema, and `schema` looks. Every other command that reads
or writes the store works on it as it is, and gets it from one function,
`store_to_work_on` in `motosphere.cli.store` (DAT-063). It gives the store
the settings name, opened with `open_store`, and only when the file is
there and lacks no migration. It puts nothing right: where there is no
file it makes none, and a store that lacks migrations is not given them,
so that a command that was asked for one thing does not do another as
well. What is wrong is said in one sentence (`StoreNotReadyError`), and
where `migrate` puts it right the sentence says so:

| The store | What is said |
|---|---|
| There is no file | "There is no data store: … does not exist. Run `python -m motosphere migrate` first." |
| It lacks migrations | "The data store lacks 6 migrations: … is at schema version 13, and the newest is version 19. Run `python -m motosphere migrate` first." |
| `migrate` would refuse it, or it cannot be opened | What `migrate` says of it, word for word |

The file is byte for byte the same afterwards, nothing is made beside it,
and no connection to it is left open. The first command that uses the
function is the one that loads the countries (DAT-061; see "The command
that loads the countries").

**The history.** `motosphere.db.history` has every migration, and the
list of them, and nothing else (DAT-006):

| Number | Migration | What it does | Task |
|---|---|---|---|
| 1 | `make_the_sources` | Makes the table of the information sources, `source` | DAT-006 |
| 2 | `make_the_source_offers` | Makes the table of what the sources offer, `source_offer` | DAT-040 |
| 3 | `make_the_collection_runs` | Makes the table of the collection runs, `collection_run` | DAT-007 |
| 4 | `index_the_runs_of_a_source` | Makes the index of the runs of one source in the order they started, `ix_collection_run_source_id_started_at` | DAT-042 |
| 5 | `make_the_record_changes` | Makes the table of the changes to records, `record_change` | DAT-009 |
| 6 | `let_the_record_changes_only_be_added_to` | Makes the four triggers by which no row of `record_change` is edited, deleted or replaced | DAT-048 |
| 7 | `index_the_record_changes` | Makes the two indexes of `record_change`: of the changes of one record, `ix_record_change_record_table_record_id`, and of the changes one run caused, `ix_record_change_collection_run_id` | DAT-049 |
| 8 | `make_the_review_items` | Makes the table of the review queue, `review_item`, and the index of the sources its items name, `ix_review_item_source_id` | DAT-010 |
| 9 | `hold_one_doubt_to_one_review_item` | Makes the two indexes by which one doubt is one review item, each of which lets no two rows be alike and is over the items of one shape: `ix_review_item_record_table_record_id_other_record_id` and `ix_review_item_record_table_record_id_field_source_id_source_value` | DAT-050 |
| 10 | `keep_the_decision_of_a_review_item` | Makes the two triggers by which a decided row of `review_item` is neither edited nor deleted | DAT-054 |
| 11 | `hold_the_key_of_a_review_item_to_1_or_more` | Makes the two triggers by which a row of `review_item` has a key of 1 or more | DAT-056 |
| 12 | `keep_a_decided_review_item_from_being_replaced` | Makes the two triggers by which no row takes the place of a decided row of `review_item` | DAT-055 |
| 13 | `make_the_countries` | Makes the table `country` and the index over the source of its rows | DAT-011 |
| 14 | `let_a_source_say_its_country` | Builds the table `source` anew with the column `country_id`, every source with what it had, and makes the index over that column, `ix_source_country_id` | DAT-057 |
| 15 | `let_a_source_be_a_reference_list` | Builds the table `source` anew with a check of `category` that names one more kind of source, `reference list`, every source with what it had, and makes the index `ix_source_country_id` again | DAT-058 |
| 16 | `make_the_regions` | Makes the table `region` and the index over the source of its rows | DAT-013 |
| 17 | `let_a_region_say_its_code` | Builds the table `region` anew with the column `iso_3166_2`, the check of its form and the rule that no two regions have one code, every region with what it had, and makes the index `ix_region_source_id` again | DAT-064 |
| 18 | `hold_the_key_of_a_review_item_under_every_name` | Makes the second trigger of the keys of `review_item` anew, so that it fires after every change of a row and not only after one that names the column `id` | DAT-068 |
| 19 | `hold_the_code_of_a_region_to_its_country` | Makes four triggers, two on `region` and two on `country`, by which the code of a region begins with the code of its country; it changes no table, no index and no row | DAT-067 |

- **A migration is plain SQL, written out in its function.** It names no
  model, no list and no type of the store's code, and the module imports
  nothing of MotoSphere's, which a test holds it to. So a migration builds
  tomorrow what it builds today, whatever becomes of the code. What two
  migrations both need, such as the white space that a check for empty
  text names, each writes out for itself.
- **A test names the migrations in their order.** One that is moved, taken
  out or given another name fails it, and a new one adds its name there,
  last.
- **Each migration is given to a store at the version before it**, in a
  test of its own, and one test holds what all of them build to the
  models (see "The models and the migrations agree").

SQLite can add, rename and drop a column and rename a table in place. For
any other change the table is built anew. A change made in place must leave
the table as its model makes it, which a column added in place does not (see
"The models and the migrations agree"). A migration can build a table anew
inside its transaction while other tables point to the table and foreign
keys stay on: it asks SQLite to check them only when the transaction ends
(`PRAGMA defer_foreign_keys = ON`, which lasts for that transaction), copies
the table aside, drops it, makes it anew under its own name, fills it again
and drops the copy. If a row that is pointed to was lost on the way, the
commit is refused and the store is as it was before. The tests do exactly
this on every machine the gates run on. The fourteenth migration is the
first that does it to a table of the store (DAT-057; see "A source says
which country it is of"). The fifteenth does it a second time, to the
same table (DAT-058; see "A kind of source that is not of the sport").
The seventeenth does it to the table of the regions, which no table
points to yet (DAT-064; see "The regions").

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
  `bytes` BLOB, a `datetime` is the store's own type for a time, which is
  TEXT (see "Times" below), a `date` is the store's own type for a
  calendar day, which is TEXT too (see "Calendar days" below), and a
  `bool` is the store's own type for yes or no, which is INTEGER (see
  "Yes or no" below). SQLite refuses to make a strict table with a column
  of another type ("unknown datatype"); SQLAlchemy's own types for text,
  for numbers with a fraction, for yes and no, for times and for days are
  five such.
- **A column whose type brings a check has that check** (DAT-034). Some
  of what the store promises of a column is narrower than any type of a
  strict table, and is kept by a check in the table. The column's type
  brings the check, and `Base` gives it to the table of every model that
  has such a column. See "Column types that bring a check" below.
- **Text that must not be empty is refused when it is empty**, by the
  table itself (DAT-030). It is the first such type: a model says
  `Mapped[NotEmpty]` of such a column, and `Base` gives its table the
  check the type brings. See "Text that must not be empty" below.
- **A column that is yes or no holds 1 or 0 and no other number**
  (DAT-035). A model says `Mapped[bool]` of such a column, and `Base`
  gives its table the check the type brings. See "Yes or no" below.
- **A column whose value is one of a list holds a text of that list and
  no other** (DAT-036). A model says `mapped_column(OneOf(TheList))` of
  such a column, and `Base` gives its table the check the type brings,
  which names the texts. See "One of a list" below.
- **A column that is a web address holds text that begins as one and has
  no white space in it** (DAT-037). A model says `Mapped[WebAddress]` of
  such a column, and `Base` gives its table the check the type brings.
  See "A web address" below.
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
- **Each constraint and each index of a table has a name of its own**
  (DAT-038). The naming rule gives two constraints one name when they
  are of one kind and on the same columns, and two checks one name when
  a model calls them the same. SQLite takes a table with two checks of
  one name. It keeps both, and says the one name when it refuses a row,
  which does not tell which of the two refused it. Two indexes of one
  name SQLite refuses itself, when the second is made.

`broken_rules(schema)` says in plain words which tables of a schema break
a rule: a table that is not strict (one made without a model can be), a
table without the key every table has, a table without the two times
every table has, a column whose type brings a check and whose table
does not have it, a constraint or an index that was named by hand, and a
name that more than one constraint or index of a table has. A test holds
the real schema to it with every change.

A table is without the two times (DAT-032) if `created_at` or `updated_at`
is missing, is not a time as the store keeps one, may be empty, or gets a
value from the table itself; if the store's code does not set it by
calling a function when a row is stored (it sets none, or one fixed
moment, or asks SQLite for the moment, which SQLite does not give in the
store's form); if `updated_at` is not set anew in that way when a row is
changed; or if `created_at` is set anew at all. The rule sees that the
store's code calls a function, not which one: that it is the store's
clock is what a model gets from `Base` by not naming the two columns.

A column whose type brings a check is without it (DAT-033, DAT-034)
unless its table has the check its type gives for it: one of the name the
naming rule gives, and of the same text, as SQLite is given it when the
table is made. For text that must not be empty that is the check
`not_empty` gives, `ck_<table>_<column>_not_empty`. A check of another
name does not count, and neither does one of that name that says
something else, nor the check another type gives. The columns of a table
are named in their order, each in the words of its own type: what is not
refused, and which function gives the check. Where a table has two checks
of the name of a column's check, the column has its check if one of the
two is that check, whichever SQLAlchemy comes to first (it keeps the
constraints of a table without an order). That there are two is said by
the rule of the names.

A name is given twice (DAT-038) if more than one constraint or index of
one table has it. The key is not counted, as it has no name. The rule
names each such name once, by the alphabet, after everything else it
says of the table, and says how many have the name:
`The table odd_one gives the name ck_odd_one_laps_sane to 2 of its
constraints and indexes: each must have a name of its own.` A name given
by hand to two constraints is named for both reasons. The same name in
two tables is not a name given twice: only a name given by hand can be
that, and it is named as one.

A test holds the real schema to the rules: `broken_rules` must find
nothing in `SCHEMA`, the whole schema (see "The models and the migrations
agree"). That each rule can be broken is proven with models of the tests'
own, which are kept in schemas apart from the real one.

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
passed on as if it were right. The table itself does not check the form,
and that is settled (DAT-030): a check in a table is for what the models
cannot promise, and through the models a time cannot have another form.

Times UTC cannot say in the years 1 to 9999 are refused. A day without a
time of day is not kept as a time: it has a type of its own (see
"Calendar days" below).

## Calendar days

Much of what the store holds is said by the day and not by the moment:
the day a race is held, the day a rider was born, the day a page says it
was published. Such a day has no time of day and no offset, and the
store makes none up for it: a day kept as the moment its midnight struck
somewhere would say more than its source did (CLAUDE.md §11). A strict
table has no type for a day, so the store keeps a day as text, in one
form (DAT-044, `motosphere.db.days`):

```
2026-11-24
```

A model says it with the column's Python type:

```python
held_on: Mapped[date]
born_on: Mapped[date | None]
```

- **It always has the four digits of its year, the two of its month and
  the two of its day.** So every text has the same length, and the order
  of the texts is the order of the days: sorting and comparing rows by a
  day needs nothing but the text.
- **In the table the column is TEXT, with a check**, which `Base` adds
  when the model is defined. The check is named after its column,
  `ck_<table>_<column>_calendar_day`, by the naming rule, and reads:

  ```
  CONSTRAINT ck_event_held_on_calendar_day CHECK ((held_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]') AND date(held_on) IS held_on AND held_on >= '0001-01-01')
  ```

  It asks three things of the text. It has the form of a day. It is a
  day SQLite's own calendar has: SQLite reads it as a day and says the
  same text back. For the 30th of February it says the 2nd of March, and
  for what it cannot read it says nothing, so neither passes. And it is
  not before the first day there is, 1 January of the year 1: SQLite
  knows a year 0, and Python does not.
- **To Python the column is a `date`**, and only a `date` is stored.
  Text and numbers are refused before anything is written, with a
  `TypeError` that says what was given:
  `Only a day (a date) is stored as a day, not str: '2026-11-24'.`
- **A time is refused**, although Python counts a `datetime` as a
  `date`: its time of day would be dropped without a word, and which day
  a moment falls on depends on where one stands. The sentence says so:
  `A time is not stored as a day: datetime.datetime(2026, 11, 24, 8, 0,
  tzinfo=datetime.timezone.utc). Say the day itself: which day a moment
  falls on depends on where one stands.` A question that compares such a
  column with a time is refused in the same way. `Base` does not take
  one for the other either: a model's `datetime` is still a time.
- **SQLite refuses text that is not a day**, on storing and on changing,
  in a row written with plain SQL too, and the refusal names the check:
  `CHECK constraint failed: ck_event_held_on_calendar_day`. A day no
  calendar has, a day with a time, with white space, without its
  hyphens or with one digit where two belong, the year 0, the word `now`
  and empty text are all refused so. A number is refused by the check as
  well, and bytes because the table is strict.
- **The form is asked first.** SQLite will not ask its calendar about
  the word `now` in a check at all, and says so in words of its own.
  With the form before the calendar the word never gets that far, and
  is refused like any other text.
- **A column that may be without a value** (`date | None`) holds no
  value or a day. No value means that the day is not known.
- **The text can be read without the pipeline's code**: by a person, and
  by SQLite's own date functions (`date`, `strftime`, `julianday`), which
  take it as the day it is.

Where this ends:

- A day of which only the year or the month is known is not a day, and
  this type does not hold it. The table that first has such a thing
  settles how it is kept; nothing is made up to fill a day out.
- The check asks SQLite's calendar, which is today's calendar carried
  back to the year 1, and so is Python's. A day that was written in
  another calendar is not converted by the store.
- What is read through the type is read as a day, and text in another
  form is refused when it is read (`The store holds a day that is not in
  the store's form: '2026'.`), also when Python could read it as a day
  (`20261124`). The table never holds such text; but what a function of
  SQLite makes of such a column is read through the type too when
  SQLAlchemy is told so, and is then refused. The earliest and the
  latest day of a column (`func.min`, `func.max`) come back as days.
- As for every type that brings a check, a column that a subclass of a
  model adds to its parent's table, and a table made without a model, get
  no check from `Base` (see "Column types that bring a check" below):

  ```python
  table.append_constraint(calendar_day("held_on"))
  ```

## Text that must not be empty

Much of the store's text is names: of a track, a rider, a source. A name
that is empty means nothing, and a page shows it as a gap. So a column
whose text must not be empty says so, and the table refuses empty text
itself, whoever writes the row (DAT-030, `motosphere.db.texts`).

A model says it with the column's type:

```python
name: Mapped[NotEmpty]
nickname: Mapped[NotEmpty | None]
```

- **In the table the column is TEXT, with a check**, which `Base` adds
  when the model is defined. The check is named after its column,
  `ck_<table>_<column>_not_empty`, by the naming rule, and reads:

  ```
  CONSTRAINT ck_rider_name_not_empty CHECK (trim(name, char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)) != '')
  ```

- **Empty is text with no characters, and text with nothing but white
  space.** White space is the 29 characters Python calls so, the ones
  `str.strip` takes off, each written in the check by its number in
  Unicode: the space, the tab and the ends of a line among them, and the
  space that cannot be broken (160), which web pages are full of. So text
  is empty to the table exactly when `text.strip()` is empty in Python.
  The numbers are written out in the code, `WHITE_SPACE`, so that the
  check is the same text on every machine; a test holds the list to
  Python's.
- **SQLite refuses the row**, on storing and on changing, through a model
  or with plain SQL, and the refusal names the check:
  `CHECK constraint failed: ck_rider_name_not_empty`. The unit of work the
  row was part of is taken back as a whole.
- **Text that is not empty is stored as it was given**, with the white
  space it has around it. The store does not tidy text; whoever collects
  it does, before it is stored.
- **A column that may be without a value** (`NotEmpty | None`) holds no
  value or text that is not empty, and never empty text: "not known" is
  said in one way only.
- **Any other text column is as before**: a model that says `Mapped[str]`
  gets TEXT without a check, and empty text is stored.

Where this ends:

- A character that Python does not call white space is content to the
  check, also one that cannot be seen: the space without width (U+200B)
  is one, and a test says so.
- `Base` adds the check to the table of a model when the model is
  defined. A column that a subclass of a model adds to its parent's table
  gets none, and neither does a table made without a model.
  `broken_rules` names such a column (DAT-033), so the test that holds
  the real schema to the rules fails until the table is given the check:

  ```python
  table.append_constraint(not_empty("maker"))
  ```

## Yes or no

Whether a source is switched on, whether a result is official: much of
what the store holds is yes or no. A strict table has no type for it, so
the store keeps it as a whole number, 1 for yes and 0 for no, and the
table refuses every other number itself, whoever writes the row (DAT-035,
`motosphere.db.yes_no`).

A model says it with the column's Python type:

```python
active: Mapped[bool]
official: Mapped[bool | None]
```

- **In the table the column is INTEGER, with a check**, which `Base` adds
  when the model is defined. The check is named after its column,
  `ck_<table>_<column>_yes_or_no`, by the naming rule, and reads:

  ```
  CONSTRAINT ck_source_active_yes_or_no CHECK (active IN (0, 1))
  ```

- **To Python the column is `True` or `False`**, and only these two are
  stored. A number, a word and every other value is refused before
  anything is written, with a `TypeError` that says what it was given:
  `Only yes or no (True or False) is stored as yes or no, not str: 'no'.`
  Python takes much for true or false that is neither, the word "no"
  among it, so nothing is taken for them. A question is held to the same:
  rows are asked for with `True` and `False`
  (`Source.active.is_(True)`), not with 1 and 0.
- **SQLite refuses another number**, on storing and on changing, in a row
  written with plain SQL too, and the refusal names the check:
  `CHECK constraint failed: ck_source_active_yes_or_no`. The unit of work
  the row was part of is taken back as a whole.
- **What the file holds is always the whole number 1 or 0.** A strict
  table stores what can be a whole number without loss as that number:
  the text `'1'` and the number `1.0`, written with plain SQL, are stored
  as 1. What cannot, the word `'yes'` among it, the table refuses because
  the column is INTEGER.
- **A column that may be without a value** (`bool | None`) holds no
  value, yes or no. No value means "not known", which is not no.
- **A value of the model's own** (`mapped_column(default=False)`) is
  stored as its number too.
- **Any other whole-number column is as before**: a model that says
  `Mapped[int]` gets INTEGER without a check.

Where this ends:

- What is read through the type is read as yes or no, and a number that
  is neither is refused when it is read
  (`The store holds what is neither yes (1) nor no (0): 2.`), not taken
  for yes. The table never holds one. But SQLAlchemy reads a sum over
  such a column (`func.sum`) through the column's type too, so a sum is
  refused, or comes back as yes or no. To count the rows that are yes,
  ask for them: `select(func.count()).where(Source.active.is_(True))`.
- As for every type that brings a check, a column that a subclass of a
  model adds to its parent's table, and a table made without a model, get
  no check from `Base` (see "Column types that bring a check" below):

  ```python
  table.append_constraint(yes_or_no("active"))
  ```

## One of a list

What kind of source this is, how a run ended, how sure a record is: much
of what the store holds is one of a few values that the code knows. Such
a list is said once, in the code, and the table refuses every text that
is not on it, whoever writes the row (DAT-036, `motosphere.db.lists`).

A list is a `StrEnum`. Its values are the texts that are stored:

```python
class Surface(StrEnum):
    SAND = "sand"
    HARD_PACK = "hard pack"
```

A model says the list with the column's type:

```python
surface: Mapped[Surface] = mapped_column(OneOf(Surface))
shade: Mapped[Shade | None] = mapped_column(OneOf(Shade))
```

- **In the table the column is TEXT, with a check that names the texts**
  in the order of the list, which `Base` adds when the model is defined.
  The check is named after its column, `ck_<table>_<column>_one_of`, by
  the naming rule, and reads:

  ```
  CONSTRAINT ck_track_surface_one_of CHECK (surface IN ('sand', 'hard pack'))
  ```

- **To Python the column is a value of the list**, and only such a value
  is stored. Text is refused before anything is written, also text that
  is spelled like a value, and so is a value of another list, with a
  `TypeError` that says what it was given:
  `Only a value of the list Surface is stored in this column, not str: 'sand'.`
  A question is held to the same: rows are asked for with
  `Track.surface == Surface.SAND`, not with the text.
- **SQLite refuses any other text**, on storing and on changing, in a row
  written with plain SQL too, and the refusal names the check:
  `CHECK constraint failed: ck_track_surface_one_of`. The texts are
  compared letter for letter: `'Sand'` and `'sand '` are not on the list.
  The unit of work the row was part of is taken back as a whole.
- **Each column keeps its own list.** Two lists may have a text in
  common; each column reads it as the value of its own.
- **A text may have any characters**: a quote, a percent sign, a letter
  beyond ASCII. It is written into the check as text.
- **A column that may be without a value** (`Surface | None`) holds no
  value or a value of the list. That is how "not known" is said, so a
  list with an empty value is refused when the type is made, and so is
  one with nothing on it, and anything that is not a `StrEnum`.
- **Any other text column is as before**: `Mapped[str]` is TEXT without a
  check.

A model has to name the type. One that says only
`surface: Mapped[Surface]` gets SQLAlchemy's own type for a list, which
is none of the four a strict table takes, and SQLite refuses to make the
table (`unknown datatype`). So the slip cannot go unnoticed: the test
that holds the models and the migrations together makes every table.

What a change to a list means:

- **A value more, a value less or a value spelled another way is a change
  to the schema.** The check names the texts, so the table the models
  describe is another table, and the test that holds the models and the
  migrations together fails until a migration builds the table anew with
  the new check (see "The models and the migrations agree"). A migration
  that takes a value off a list first says what becomes of the rows that
  have it.
- **The order of the list is part of the check** too, so a list is not
  put in another order without need. A new value goes at the end.
- **The name of a value is not stored**, only its text: a value can be
  given another name in the code without a migration.

Where this ends:

- Rows sorted by such a column come in the order of the texts, by the
  alphabet, not in the order of the list.
- A text that is read through the type and is not on its list is refused
  (`The store holds what is not on the list Surface: 'mud'.`), not read
  as something else. A table that has its check never holds one.
- As for every type that brings a check, a column that a subclass of a
  model adds to its parent's table, and a table made without a model, get
  no check from `Base` (see "Column types that bring a check" below):

  ```python
  table.append_constraint(one_of("surface", Surface))
  ```

## A web address

A source has a website, and every record says at which address it was
found. A page makes a link of such an address, so text that is not one
must not get that far. A column that holds a web address says so, and
the table refuses other text itself, whoever writes the row (DAT-037,
`motosphere.db.web`).

A model says it with the column's type:

```python
website: Mapped[WebAddress]
feed: Mapped[WebAddress | None]
```

- **In the table the column is TEXT, with a check**, which `Base` adds
  when the model is defined. The check is named after its column,
  `ck_<table>_<column>_web_address`, by the naming rule, and reads:

  ```
  CONSTRAINT ck_source_website_web_address CHECK (((website GLOB '[Hh][Tt][Tt][Pp][Ss]://[^/?#]*') OR (website GLOB '[Hh][Tt][Tt][Pp]://[^/?#]*')) AND NOT (website GLOB '*[' || char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288) || ']*') AND instr(website, char(0)) = 0)
  ```

- **A web address begins with `https://` or `http://`**, in small or in
  large letters, and goes on with the name of a site: with at least one
  character, which is not `/`, `?` or `#`, the three that end such a
  name. So `example.org`, `//example.org`, `https://` and
  `https:///tracks` are refused, and so is every other scheme: `ftp:`,
  `mailto:`, `file:`, and `javascript:`, of which a page must never make
  a link.
- **It has no white space anywhere**, by the store's own list of white
  space (see "Text that must not be empty"): no space before or after
  it, no line end, no space in it, and so not two addresses in one text
  either. Where an address has a space, whoever collects it writes the
  space as its number, `%20`, before it is stored.
- **It has no character with the number 0.** SQLite's `GLOB` reads text
  up to such a character and no further, so white space behind one would
  go unseen.
- **SQLite refuses the row**, on storing and on changing, through a model
  or with plain SQL, and the refusal names the check:
  `CHECK constraint failed: ck_source_website_web_address`. The unit of
  work the row was part of is taken back as a whole.
- **An address is stored as it was given.** Nothing is put in small
  letters and nothing is taken off. The store does not tidy an address;
  whoever collects it does, before it is stored.
- **A column that may be without a value** (`WebAddress | None`) holds no
  value or a web address, and never empty text.
- **Any other text column is as before**: `Mapped[str]` is TEXT without a
  check.

The check is written with `GLOB` and not with `LIKE`, because `GLOB`
tells small letters from large ones on every machine, and what `LIKE`
does about them can be changed for a connection. A check must refuse the
same text wherever the file is opened.

Where this ends:

- **The check does not know whether an address leads anywhere.** It holds
  the beginning of an address to the rules and not the rest, and it does
  not ask the network: `https://no-such-site.invalid/` and `https://.`
  pass. Whether a site answers is found out by whoever collects from it.
- **Two spellings of one address are two addresses to the store.**
  `https://example.org/a`, `HTTPS://EXAMPLE.ORG/a` and
  `https://example.org/a/` are three texts, and a question for one does
  not find the others. Code that must find an address again brings it to
  one spelling before it stores it.
- A character that Python does not call white space is content to the
  check, also one that cannot be seen: the space without width (U+200B)
  and a control character that is not white space pass, and tests say
  so.
- As for every type that brings a check, a column that a subclass of a
  model adds to its parent's table, and a table made without a model, get
  no check from `Base` (see "Column types that bring a check" below):

  ```python
  table.append_constraint(web_address("website"))
  ```

## Column types that bring a check

A column of the store has one of four types (see "The rules every table
keeps"), and much of what the store must promise of a column is narrower
than any of them: text that is not empty is narrower than TEXT. Such a
promise is kept by a check in the table, so that SQLite itself refuses the
row, whoever writes it. The check comes with the column's type (DAT-034,
`motosphere.db.checks`).

A column type that brings a check is a subclass of `WithItsCheck`, beside
its SQLAlchemy type, and says three things:

```python
class NotEmptyText(WithItsCheck, Text):
    refuses = "empty text"
    given_by = "not_empty"

    def check_for(self, name: str) -> CheckConstraint:
        return not_empty(name)
```

- `check_for(name)` gives the check for the column of that name. The
  check has the last part of its name (`name_not_empty`), which the
  naming rule completes once the check is given to a table, and belongs
  to no table until then.
- `refuses` and `given_by` are the words `broken_rules` uses of a column
  that is without the check: what is not refused, and the name of the
  function that gives the check, for whoever has to give it by hand.

Everything else follows by itself, for every such type:

- **`Base` gives the check to the table** of every model that has a
  column of the type, when the model is defined.
- **`broken_rules` names a column of the type whose table is without the
  check**: `The table X does not refuse empty text in its column Y: it
  must have the check that not_empty gives for the column, named by the
  naming rule.`, with the two words of the column's own type.
- **A type that says it brings a check and gives none is an error**
  (`NotImplementedError`), when a model with a column of it is defined
  and when `broken_rules` is asked about a table with one.

A model can only say a type by the column's Python type
(`Mapped[NotEmpty]`) once the type is in the list `Base` keeps for that
(`type_annotation_map`); until then it names the type itself
(`mapped_column(TheType)`).

The types that bring a check so far: `NotEmptyText`, text that must not
be empty, `YesOrNo`, yes or no, `OneOf`, a value of a list,
`WebAddressText`, a web address, and `CalendarDay`, a calendar day (all
above).

Where this ends is the same for every such type: `Base` gives the check
when a model is defined, so a column that a subclass of a model adds to
its parent's table gets none, and neither does a table made without a
model. `broken_rules` names such a column, and its table is given the
check by hand, as "Text that must not be empty" shows. And a migration
writes the check itself, as it writes the rest of the table (see "The
models and the migrations agree").

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

## The models and the migrations agree

The models say what the store's tables are, to the code that reads and
writes rows. The migrations build the tables, in every store there is.
One test holds the two together (DAT-026): it brings an empty store to
the newest schema with `migrate`, makes the tables of the models in a
second store, and asks `differences` in `motosphere.db.compare` where the
two differ. It runs with every change, so a model cannot change without a
migration, nor a migration without its model.

- **What is compared** are the statements by which SQLite itself says
  each table, index and trigger is made, which it keeps in the file
  (`sqlite_master`), and that of a view, should there ever be one. What
  SQLite keeps for itself is left out: everything whose name begins with
  `sqlite_`, which no other name may.
- **Two statements are the same when they are the same words in the same
  order.** How the words are spaced and where the lines end, large and
  small letters, quotes around a name and comments make no difference.
  Text in single quotes is compared letter for letter. So a migration is
  plain SQL written by hand, and it does no harm that SQLite puts the name
  of a table in quotes once the table has been renamed.
- **Everything a statement says counts**: the columns and their order;
  the type of each, whether it may be without a value, and a value of its
  own; the key, and that it is never given twice; every constraint with
  its name, its columns and its text; that the table is strict; and of an
  index its name, its table, its columns in their order, whether it lets
  no two rows be alike, and whether it is over some rows only.
- **`differences` gives one sentence** for each table or index that
  differs, kind by kind and name by name: `Only the models have the table
  rider.`, `Only the migrations have the index ix_rider_name.`, or, for
  one that both have, the words of both from where they first differ:

  ```
  The table rider is not the same in both. Where they first differ, the models say `number integer not null , name text ...` and the migrations say `number text not null , name text ...`.
  ```

  The words begin where the column or constraint begins that differs, and
  are shown in the form in which they are compared.

What follows for a migration:

- **It writes a table as its model makes it**: the key first, the model's
  columns in their order, the two times last, then the constraints as
  SQLAlchemy writes them. The quickest way to the statement is to let
  SQLAlchemy write it from the model once and to copy it into the
  migration as text, so that the migration does not depend on the model
  afterwards:

  ```python
  print(CreateTable(Rider.__table__).compile(dialect=sqlite.dialect()))
  ```

  (`CreateIndex` does the same for an index.)
- **A column is added by building the table anew.** SQLite can add a
  column in place, but it then stands after the columns the table had,
  and the last two columns of every model are the two times. See "How the
  schema changes" for how a table is built anew while rows point to it.
- **A constraint or an index gets a new name by building it anew.** A
  column renamed in place keeps the old names of its constraints, and the
  models name them after the new one.
- **A trigger is said twice, as the statement that makes it** (DAT-048).
  No model has a word for a trigger, so the module of the model has the
  statement as text, and makes the trigger with the connection that has
  just made the table, wherever the table is made from the model. The
  migration writes the same statement out for itself. The two are
  compared like every other statement, the text of the refusal letter
  for letter.

Where this ends:

- The test compares the newest schema only. That a store which stopped at
  an earlier version reaches it is what the tests of `migrate` prove.
- The test takes the models from `SCHEMA` in `motosphere.db.models`, which
  is the whole schema: the package names every model, so loading it, or
  any one model, loads them all. A test proves that it is whole (DAT-006).
  In a new Python, which has loaded nothing else, it loads every module
  MotoSphere has and asks which tables the models then say; `SCHEMA`,
  asked in another new Python, must say the same. So a model that the
  package does not name, or one that stands outside it, fails a test and
  is not passed over in silence.
- What a model cannot say is not compared yet: a search index and an
  index of places, which SQLite builds as tables of its own kind with
  further tables beneath them. The task that adds the first decides how
  the two are held together there.

Today the two have seven tables, nine indexes and ten triggers to
agree on: `source`, `source_offer`, `collection_run`, `record_change`,
`review_item`, `country`, `region`, the index of the runs of one
source, the two indexes and the four triggers of `record_change`, the
three indexes and the six triggers of `review_item`, the index of the
countries of one source, the index of the sources of one country, and
the index of the regions of one source. For
`source` the two agree on the table as the fifteenth migration built
it anew, not as the first made it or as the fourteenth built it, and for
`region` on the table as the seventeenth built it anew, not as the
sixteenth made it. For an
index that is over some
rows only, which rows is part of the statement, and so of what must
agree.
That the comparison can fail is proven with two models and migrations of
the tests' own (`TESTING.md`).

## The information sources

A source is a website or a dataset that MotoSphere may collect from, and
the store knows every one of them (DESIGN.md §7.3). The table `source`
(DAT-006), its model `Source` and the two lists a source is described by
(DAT-039) are in `motosphere.db.models.source`, and so are the table of
what the sources offer, `source_offer`, its model `SourceOffer` and the
list of the kinds of information (DAT-040). The models of the store
live in the package `motosphere.db.models`, one module for each table or
for a few that belong together. The package names every model, and
`SCHEMA` there is the whole schema.

**The table `source`.** Its key and its two times are those of every
table. The first migration makes it (`make_the_sources`), and the
fourteenth builds it anew with the column `country_id`
(`let_a_source_say_its_country`; see "A source says which country it is
of" below). The fifteenth builds it anew once more, for one more kind
of source (`let_a_source_be_a_reference_list`; see "A kind of source
that is not of the sport" below).

| Column | What it holds | When it is without a value | What the table refuses |
|---|---|---|---|
| `name` | What the source is called | Never | Empty text; a name another source has |
| `website` | The address of the site it is | Never | Text that is not a web address |
| `category` | What kind of source it is | Never | Text that is not on the list `SourceCategory` |
| `collection_method` | How it is collected from | Never | Text that is not on the list `CollectionMethod` |
| `scan_every_hours` | After how many hours it is looked at again | It is not looked at by the clock | Nought and less; part of an hour |
| `terms_address` | Where its terms of use are | None is known | Text that is not a web address |
| `licence` | The licence under which what it publishes may be used, as the source names it | None is known | Empty text |
| `usage_restrictions` | What its terms ask for or forbid, in plain words | None is known | Empty text |
| `terms_read_at` | When a person last read its terms | Nobody has yet | |
| `switched_on` | Whether MotoSphere collects from it | Never | A number that is not 1 or 0; yes, while `terms_read_at` is without a value |
| `country_id` | The country it is of: the key of a row of `country` | It is of no one country, or nobody has said yet | A key that no country has; what is not a whole number |

What the planner's trial settled:

- **A new source is switched off, and a source is switched on only after
  its terms were read** (CLAUDE.md §10: sources are validated before they
  are activated). The model gives a new source "no". The table gives the
  column no value of its own, so a row that is written past the model and
  does not say is refused, not switched on in silence. The check
  `ck_source_switched_on_terms_read` refuses a row that is switched on and
  does not say when its terms were read: when it is first stored, when it
  is switched on later, and when the time is taken away from a source that
  is switched on. A source can be switched off again, and keeps the time.
  The table cannot know that somebody read the terms; it makes sure that
  whoever switches a source on has written down when.
- **Two sources cannot have one name, and they can have one website.** A
  source has one kind and one way of collecting. A site that is collected
  from in two ways, its news by a feed and its calendar from its pages, is
  two sources of two names with the same website, and each has runs of
  its own ("The collection runs"). `website` is the address of the site,
  not of the page or the feed that is read. Names are told apart letter
  for letter: `Example` and `EXAMPLE` are two names, and so are a name
  and the same name with a space after it.
- **How often a source is scanned is said in whole hours**: 24 is daily and
  168 weekly. A source without a number is not looked at by the clock, as
  a file that is loaded once by a command is not.
- **What is not in the table.** The kinds of information it offers
  are in a table of their own, `source_offer` (below). When it was last
  scanned, how it is doing and its last error are what its runs say, and
  one function reads it from them ("How a source is doing"). They are not
  stored a second time here, where the two could come to disagree.

**A source says which country it is of** (DAT-057), so that the sources
of one country can be found: the federation of a country, its clubs,
its tracks. The column `country_id` holds the key of a row of `country`
("The countries").

- **A source may be without a country.** A body for the whole world is
  of no one country, and of a source that was stored before somebody
  looked, nobody has said yet. The table does not tell the two apart:
  no value means only that no country is said. Neither the model nor
  the table gives the column a value.
- **The country must be there.** The foreign key
  `fk_source_country_id_country` refuses a key that no country has,
  when a source is stored and when it is changed. The column is a whole
  number: the table is strict, so text and part of a number are refused,
  and a whole number written as text is read by SQLite as the number it
  is and then held to the same rule.
- **A country that a source is of cannot be deleted.** Nothing is done
  for the source when its country would go: SQLite refuses to delete
  the country. Once no source is of it any more, because each was moved
  to another country, to none, or was itself deleted, the country can
  go. Two sources can be of one country.
- **The sources of one country are found by an index**,
  `ix_source_country_id`, over the column alone. SQLite also uses it
  for the question it asks itself before a country is deleted, whether
  a source is of it, and answers that from the index without reading
  the table.
- **The two tables point to each other.** A country says which source
  it came from, and a source says which country it is of. A body that
  publishes the list of the countries is itself of one of them. So
  such a source is stored first, of no country; its countries follow;
  and then it is said which of them it is of. To take them away, the
  source is first of no country again, then its countries go, then the
  source. While the two point to each other neither can be deleted.
  Nothing else in the schema goes round, and a test holds that:
  SQLAlchemy cannot put two such tables in an order (`sorted_tables`
  warns, and a warning fails a test here), and nothing in the store's
  code asks it to. Making the tables from the models needs no order in
  SQLite, where a table can name one that is not there yet.
- **How the migration adds the column.** SQLite puts a column that is
  added to a table that is there after all the others, and cannot give
  it a foreign key with a name, so the table would not be as its model
  makes it ("The models and the migrations agree"). The fourteenth
  migration builds the table anew ("How the schema changes"): it asks
  SQLite to check the foreign keys only when the transaction ends,
  copies the rows of `source` aside (`source_before`), drops the table,
  makes it again with the column and fills it from the copy, every
  source with what it had and with its key, and of no country. Then it
  drops the copy and makes the index. The four tables whose rows point
  to a source (`source_offer`, `collection_run`, `review_item` and
  `country`) are not touched, and their rows point to the same sources
  afterwards; if one did not, the migration would be refused as a
  whole.
- **The highest key is kept.** SQLite remembers for a table whose keys
  are never given twice the highest key it has given (in its own table
  `sqlite_sequence`), and forgets it when the table is dropped. Filled
  again, the new table would know only the keys of the sources that
  are there, and the key of a source that was deleted would be given
  to the next one. So the migration reads the highest key before it
  drops the table (`source_key_before`) and puts it back after filling
  it. A table that never gave a key has none before and none after.
  The highest keys of the other tables are not touched.
- **The migration is all or nothing**, like every migration. Where a
  table of the name of one of its two copies is there already, or an
  index of the name of its index, it fails and the store is as it was:
  at version 13, the table without the column, every row and the
  highest key as before. A test makes it fail at its very last
  statement, after the table was dropped, made anew and filled.

**A kind of source that is not of the sport** (DAT-058). The twelve
kinds of source of the design are each a kind of website of the sport.
The countries of the world come from none of them: from a project that
keeps the lists of a standard (`DATA_SOURCES.md`, "The countries:
iso-codes"). So that such a source is registered as what it is, the
list has a thirteenth kind, `reference list`.

- **What it is for.** Whoever keeps a list that other records are
  described by: the countries of a standard today, and what else of
  that sort the store comes to need. It says who publishes, as the
  twelve do. What such a source offers is said by the kind of
  information `reference data`, and how it is collected from by a way
  of collecting, as for every source.
- **It stands last.** The twelve keep the order of the design, and the
  one that is this project's own follows them. A test holds the place.
- **The table has to be built anew for it.** The check of the column
  `category` names the texts it takes, and SQLite cannot change a check
  of a table that is there. The fifteenth migration does what the
  fourteenth did ("How the migration adds the column" and "The highest
  key is kept" above): it copies the rows aside, drops the table, makes
  it again with the check that names the thirteenth text too, fills it
  from the copy, every source with all it had, its key and its country
  too, puts the highest key back and drops the copies. The index of
  the sources of one country went with the table, and the migration
  makes it again. The four tables whose rows point to a source are not
  touched.
- **Nothing else of the table changes.** A test reads how SQLite holds
  every table and index before and after: only `source` is written
  otherwise, and only in the one text more.
- **Every other text is refused as before**, a text that is nearly the
  new one too: with a capital, with white space after it or two spaces
  in it, in the plural, and the kind of information `reference data`,
  which is of another list.
- **The migration is all or nothing.** Where a table of the name of one
  of its two copies is there already, or where its last statement
  fails, the store is as it was: at version 14, the table without the
  new kind, every row and the highest key as before. For the last
  statement to fail, the test puts a table of the index's name where
  the index was.

Each list is said once, in the code, as a `StrEnum` whose values are the
texts that are stored (see "One of a list"). The texts are words in small
letters, with one space between two. Once a table has a column of a list,
a text is changed or taken away only by a migration: the table's check
names the texts, and rows hold them.

**What kind of source it is**, `SourceCategory`: who publishes it. The
twelve of DESIGN.md §7.1, in its order, and after them one that is this
project's own (DAT-058; see "A kind of source that is not of the sport").

| The text that is stored | In the design | What it is |
|---|---|---|
| `governing body` | Official governing bodies | A body that makes the rules of the sport, for the world or for a country |
| `championship` | Official championship websites | The website of one championship or series |
| `organiser` | Championship organisers | Whoever runs a championship from year to year |
| `promoter` | Race promoters | Whoever puts on single races and sells them |
| `track` | Individual motocross tracks | One track, about itself |
| `club` | Local motorcycle clubs | A local motorcycle club |
| `regional organisation` | Regional racing organisations | An organisation for the racing of one region of a country |
| `results database` | Public results databases | A public collection of race results or of timing |
| `news publication` | Motocross news publications | A magazine or a news site about the sport |
| `community website` | Publicly accessible community websites | A website the riders and followers of the sport write themselves |
| `social media page` | Public social media pages where permitted | A public page on a social network, only where that network permits collecting |
| `historical archive` | Publicly accessible historical archives | A public archive of how the sport was |
| `reference list` | – (not in the design) | Whoever keeps a list that other records are described by, such as the countries of a standard; not a website of the sport |

**How it is collected from**, `CollectionMethod`. The ten of DESIGN.md
§7.2, in its order. Three of them are permitted only on a condition, which
the design names and the list does not check: it is checked when a source
is registered, and recorded with the source (`DATA_SOURCES.md`).

| The text that is stored | In the design | What it is |
|---|---|---|
| `official api` | Official APIs | An interface the source itself offers to programs |
| `structured feed` | Public structured feeds | A feed of records in a form made for programs, such as a calendar file |
| `rss feed` | RSS feeds | A feed of what is new, as RSS or Atom |
| `public dataset` | Public datasets | A whole set of records published for reuse, under a licence |
| `html extraction` | Permitted HTML extraction | Pages made for people, only where the site's terms and its robots.txt permit |
| `structured document` | Structured public documents | A public document with a fixed layout, such as a results sheet |
| `json endpoint` | Public JSON endpoints where authorised | The data behind a public page, only where the source authorises its use |
| `sitemap discovery` | Sitemap discovery | The list of its pages that a site publishes for programs |
| `search engine discovery` | Search-engine discovery where permitted | What a search engine finds, only where the engine permits it |
| `human submission` | Human-submitted source references | A reference a person has sent in |

**The table `source_offer`** says which kinds of information each source
offers (DESIGN.md §7.3, "Available information types"; DAT-040). A source
can offer several, so they are rows of a table of their own and not a
column of the source: one row for one kind that one source offers. Its
key and its two times are those of every table. The second migration
makes it (`make_the_source_offers`).

| Column | What it holds | When it is without a value | What the table refuses |
|---|---|---|---|
| `source_id` | The source that offers it: the key of a row of `source` | Never | A key that no source has |
| `information_type` | The kind of information | Never | Text that is not on the list `InformationType`; a kind the same source offers already |

- **A source offers a kind once.** No two rows have the same source and
  the same kind (`uq_source_offer_source_id_information_type`). Two
  sources can offer the same kind.
- **An offer belongs to a source that exists**, when it is stored and
  when it is changed (`fk_source_offer_source_id_source`).
- **A source that has offers cannot be deleted.** Whoever deletes a
  source takes its offers away first, in the same unit of work; nothing
  is taken away in silence with the source.
- **A source may be without offers.** The table of the sources does not
  ask for one.

**The kinds of information**, `InformationType`. The design names no
list of them, so the planner's trial settled one from what the design
says MotoSphere is a place to explore (DESIGN.md §1): nine texts, words
in small letters in the plural.

| The text that is stored | What it is |
|---|---|
| `tracks` | Where tracks are and what they are like |
| `events` | Races and other events with their dates: calendars and the rounds of a championship |
| `championships` | Championships and series: their seasons, their classes and who won them |
| `results` | How races ended, single motos included |
| `standings` | The standings of a championship, with their points |
| `riders` | Riders: who they are and what they have ridden |
| `teams` | Teams: who they are and who rides for them |
| `news` | News and announcements |
| `reference data` | What other records are described by, such as the countries of the world |

## The collection runs

A run is one attempt to collect from one source, and the store records
every one of them (DESIGN.md §5.1, "Data collection runs"; DAT-007). The
table `collection_run`, its model `CollectionRun` and the list of how a
run stands or ended, `RunOutcome`, are in
`motosphere.db.models.collection_run`. The third migration makes the
table (`make_the_collection_runs`). Its key and its two times are those
of every table.

| Column | What it holds | When it is without a value | What the table refuses |
|---|---|---|---|
| `source_id` | The source that was collected from: the key of a row of `source` | Never | A key that no source has |
| `started_at` | When the run started | Never | |
| `ended_at` | When the run ended | While it is running, and when it was interrupted | A time before `started_at`; a time for a run that is running or was interrupted; no time for a run that succeeded or failed |
| `outcome` | How the run stands or ended | Never; a new run is `running` | Text that is not on the list `RunOutcome` |
| `records_seen` | How many records the source gave the run | Never; a new run has 0 | A number below 0 |
| `records_added` | How many of them were new to the store | Never; a new run has 0 | A number below 0 |
| `records_changed` | How many were different from what the store had | Never; a new run has 0 | A number below 0 |
| `records_unchanged` | How many were what the store had already | Never; a new run has 0 | A number below 0 |
| `error` | What went wrong, in plain words | Unless the run failed | Empty text; an error for a run that did not fail; no error for a run that failed |

**How a run stands or ended**, `RunOutcome`:

| The text that is stored | What it is | Its end | Its error |
|---|---|---|---|
| `running` | It has started and has not said how it ended | None | None |
| `succeeded` | It ended, and collected what it set out to collect | Said | None |
| `failed` | It ended, and says what went wrong | Said | Said |
| `interrupted` | It never said how it ended, because its job died | None | None |

- **A run is stored when it starts**, and it is then running. When it
  ends it says so itself, in the same row: when it ended, how, and what
  it counted.
- **A run belongs to a source that exists**, when it is stored and when
  it is changed (`fk_collection_run_source_id_source`), **and a source
  that has runs cannot be deleted.** Whoever deletes a source takes its
  runs away first, in the same unit of work; no record of a run is lost
  in silence with its source. A source can have any number of runs, two
  that started at the same moment among them.
- **A run cannot end before it started**
  (`ck_collection_run_ended_at_not_before_started_at`). It can end at the
  moment it started. Times are text of one form whose order is the order
  of the times ("Times"), so the table compares them as they are.
- **The end and the error go with the outcome.** A run that succeeded or
  failed says when it ended, and no other run does
  (`ck_collection_run_ended_at_when_succeeded_or_failed`). A run that
  failed says what went wrong, and no other run has an error
  (`ck_collection_run_error_when_failed`).
- **An interrupted run has no end.** Nobody knows when its job died, and
  the store does not hold a time that somebody made up. `updated_at`
  says when the run was marked, which is another thing.
- **A count is a whole number that is not below 0**, each by a check of
  its own (`ck_collection_run_records_seen_not_negative` and three more).
  The table does not ask that added, changed and unchanged add up to
  seen: a record that was refused was seen and is none of the three.
- **What is not in the table.** Two runs of one source can be running at
  once as far as the table goes.

**The index of the runs of one source**,
`ix_collection_run_source_id_started_at`, is over `source_id` and
`started_at`, in that order (DAT-042). The model says it, the naming rule
names it, and the fourth migration makes it (`index_the_runs_of_a_source`).
It forbids nothing: two runs of one source can start at the same moment.

- **What it is for.** `standing_of` asks for the newest run of one source
  that has one of some outcomes ("How a source is doing"). SQLite says of
  each of those statements how it will answer it, and a test reads that:
  with the index, one step, `SEARCH collection_run USING INDEX
  ix_collection_run_source_id_started_at (source_id=?)`, and nothing is
  sorted; without it, `SCAN collection_run` and `USE TEMP B-TREE FOR
  ORDER BY`, so the whole table is read and what was found is sorted.
- **Why these two columns and no more.** The planner's trial asked SQLite
  for its plan with six indexes. Over the source alone, the runs are
  found and then sorted. With the key as a third column the plan is the
  same as without it: SQLite ends every entry of an index with the key
  by itself, which is also why two runs that started together stand in
  the order they were stored. With the outcome as a third column, or
  with the start in falling order, the last part of the order must be
  sorted again. With the outcome before the start, a question about more
  than one outcome is sorted.
- **Deleting a source.** SQLite must look for the runs of a source before
  it lets the source go. In the trial its program for that statement
  opened the table of the runs without the index, and the index with it.
  No test holds it to that: it is how SQLite works inside, and what it
  must do, refuse the delete, is tested (DAT-007).

**Runs that were left running.** A job that dies cannot say how its run
ended, and the run would be running in the table for ever.
`motosphere.db.runs.mark_interrupted(work)` marks every run that is
still running as interrupted and gives the keys of the runs it marked,
smallest first. It is for the moment nothing can be running: the start
of collecting, before the first new run is stored, so that whoever takes
up the work has a record of what was cut off (CLAUDE.md §13). It changes
the outcome of those runs and, with it, when they were last changed, and
nothing else: they get no end and keep what they had counted, and no
other run and no other table is touched. It is part of the unit of work
it is given, and is kept or taken back with it. Nothing calls it yet:
the first task that collects does.

## How a source is doing

The registry of the design says of each source when it was last scanned,
when that last worked, what last went wrong and how it is doing (DESIGN.md
§7.3: "Last attempted scan", "Last successful scan", "Error information",
"Current health"). The store has no columns for these. They are what the
source's runs say already, and a second copy with the source could come
to disagree with the runs. `standing_of(work, source_id)` in
`motosphere.db.source_health` reads them from the table `collection_run`
whenever it is asked, and writes nothing (DAT-041). It gives a
`SourceStanding`, which cannot be changed afterwards:

| What it says | What it is | When it is without a value |
|---|---|---|
| `last_attempt` | When the source's newest run started, whatever became of it | The source has no run |
| `last_success` | When its newest run that succeeded started | None has succeeded |
| `last_error` | What went wrong in its newest run that failed, in plain words | None has failed, or one has succeeded since |
| `health` | How it is doing, from the list `SourceHealth` | Never |

**How a source can be doing**, `SourceHealth`. It is told by the newest
of the source's runs that is over. A run that is still running says
nothing yet, so it is passed over.

| The text | When |
|---|---|
| `not yet scanned` | No run of the source is over yet: it has none, or only one that is running |
| `healthy` | Its newest run that is over succeeded |
| `failing` | Its newest run that is over failed |
| `interrupted` | Its newest run that is over was cut off, because its job died |

- **A scan is said by when it started.** That is the one time every run
  has: a run that was interrupted has no end. So both times are starts,
  and the last success is the last attempt exactly when the newest run
  succeeded.
- **The newest run is the one that started last**, not the one that was
  stored last; of two that started at the same moment, the one stored
  last is the newer.
- **The last error is no longer said once a later run succeeded.** A run
  that is running, or was interrupted, after the one that failed does not
  take the error away: nothing has shown yet that it is over.
- **Interrupted is not failing.** A run that failed says what went wrong
  at the source. A run that was interrupted says that the job died,
  which is a thing to look at in the job and not in the source; so the
  two are told apart, and an interrupted source has no error of its own.
- **A key that no source has is refused** with a `LookupError` that says
  so in one sentence. Of a source that does not exist nothing is true,
  also not that it was never scanned.
- **The list is not stored.** `SourceHealth` is no column of any table:
  it is worked out when it is asked for, and so a text of it can be
  changed without a migration.
- **No reliability score.** The design's registry has one (DESIGN.md
  §7.3). How often a source could be collected from says whether it
  answers, not whether what it says is right, and a score from the runs
  alone would be a number with nothing behind it. It comes with the task
  that scores the sources from records that were checked (COL-009); no
  number is invented until then. The same task can make the health finer
  than the outcome of one run.
- **Four small questions, and the index that answers them.** The
  function asks the table four times for the newest run of one source
  with one of some outcomes. The index over the source and the start
  takes SQLite straight to the source's runs in the order asked for, and
  a test reads from SQLite itself that all four are answered so ("The
  collection runs", DAT-042).

## Where a collected record came from

Every record MotoSphere collects keeps with it where it came from and
how far it can be trusted (DESIGN.md §8, CLAUDE.md §11). The design
names eight things a record keeps. They are eight columns, the same in
every table of collected records, and they are said once: in
`Collected`, in `motosphere.db.models.provenance` (DAT-008). A model
whose records are collected is a subclass of `Collected`, and not of
`Base` itself:

```python
class Track(Collected):
    __tablename__ = "track"

    name: Mapped[NotEmpty]
```

Its table then has the key, the columns the model names, the eight
columns of the set, and the two times every table ends with, and an
index over the source of its records (DAT-045). The first table that
has the set is `country` (DAT-011; see "The countries"). The migration
that makes a table of collected records writes the eight columns, their
checks and the index out with the table, as it writes everything.

| Column | In the design | What it holds | May be without a value |
|---|---|---|---|
| `source_id` | Source identity | The source the record was collected from: the key of a row of `source` | No |
| `source_address` | Original source URL | The address at which it was found: the page, the feed or the file that says it, not the front page of the site. A web address (see "A web address") | No |
| `collected_at` | Collection timestamp | When what the row says was taken from its source | No |
| `published_on` | Original publication date where known | The day its source says it was published. A calendar day (see "Calendar days") | Yes: the source does not say |
| `last_verified_at` | Last verification timestamp | When the source was last seen to say what the row says | No |
| `extraction_method` | Extraction method | How this record was got: one of the ways of collecting, `CollectionMethod` (see "The information sources") | No |
| `confidence` | Confidence level | How sure it is that the record says what its source says: `Confidence` (see "How far a collected record can be trusted") | No |
| `verification_status` | Verification status | What standing the source's word has: `VerificationStatus` (the same section) | No |

- **Only the day a record was published may be unknown**, because not
  every source says it, and no day is made up for one that does not
  (CLAUDE.md §11). The other seven are known of every record when it is
  collected, and whoever stores the record says them: no column of the
  set gives itself a value. A value the table gave by itself would be a
  value nobody read anywhere. Where little is known of how far a record
  can be trusted, the lists have the words for it, `low` and
  `unverified`, and the collector says them.
- **A record belongs to a source that exists.** `source_id` refers to
  `source`, by a reference the naming rule names
  (`fk_<table>_source_id_source`), and SQLite refuses a record of a
  source that is not there. It also refuses to delete a source that
  records came from, or to change its key (`FOREIGN KEY constraint
  failed`): the records are taken away first, or given to another
  source. Nothing is deleted along with a source.
- **An index over the source** (DAT-045), `ix_<table>_source_id`, which
  `Collected` gives to every table with the column. With it SQLite goes
  straight to the records of one source, where it read the whole table:
  when it is asked which records came from a source, how many, or
  whether any did, when the records of a source are taken away, and
  when a source is to be deleted and SQLite itself looks whether
  records came from it. That last look is made in every table that
  refers to a source, at every deleting of one. The tests read all of
  this from SQLite's own account of how it answers (`EXPLAIN QUERY
  PLAN`), with the index and without it.
- **The index is over the source alone.** Every question the store asks
  about the records of a source today begins with the source and is
  answered by this index. One that goes on with the moment a record
  was last seen ("what of this source was not seen since Monday") is
  answered by it too: SQLite finds the records of the source by the
  index and looks at each. An index over both columns would save that
  look, and would be paid for in every table of collected records at
  every writing. Nothing asks that question yet; the task whose code
  first asks it reads SQLite's plan with real numbers of rows and
  widens the index if that is worth it.
- **The two times.** `collected_at` is when what the row says was taken
  from its source. `last_verified_at` is when the source was last seen
  to say so. For a new record they are the same moment. When the source
  is looked at again and says what it said, only `last_verified_at`
  moves; when it says something else, the row is changed and both move.
  A check, `ck_<table>_last_verified_at_not_before_collected_at`,
  refuses a record that was last seen at its source before it was
  collected. The two are compared as text, which is the order of the
  moments, because the store keeps every time in one form (see
  "Times"). `Collected` gives the check to each table itself, as `Base`
  gives the checks of the column types, so a model that says more of
  its table (`__table_args__`) keeps it.
- **Neither time is the store's clock.** `created_at` says when the row
  was stored, and the store sets it. A record that was collected
  yesterday and is stored today says yesterday in `collected_at`.
- **Seen again is not the same as right.** `last_verified_at` says that
  a program found the source still saying it. Whether what the source
  says can be trusted is the verification status, and whether two
  sources agree is for the review queue (DAT-010).
- **No check holds the day a record was published to the moment it was
  collected.** A page dated the 26th in New Zealand is read on the 25th
  by the clock of UTC, and a test stores such a record.
- **Why a record says how it was got, when its source says so too.** A
  source is collected from in one way at a time
  (`source.collection_method`), and that way can change: a site that
  was read page by page may offer a feed next year. The record keeps
  the way it was got. Nothing in the store holds the two to each other,
  because a check cannot look into another table; the code that
  collects says the way it used.
- **The address is stored as it was given** (see "A web address"), so
  two spellings of one address are two addresses here too.
- **Not in the set.** A record does not say which run collected it.
  What a record was before it was changed, and which run changed it,
  is said by the changes to it (see "The changes to records").

## Every table says where its records came from, or why not

Nothing in `Collected` stops a model from being a subclass of `Base`
where it should be one of `Collected`, or from saying a column of the
set again in its own way. `broken_provenance`, in
`motosphere.db.models.provenance_rule` (DAT-046), says in plain words
which tables of a schema do so, one sentence for each break, and a test
holds the real schema to it.

- **A table holds collected records unless a list says that it does
  not.** So a new table that nobody thought about is named. The list
  of the real schema is `NOT_COLLECTED`, in the same module, and has
  each table with its reason:

  | Table | Why it holds no collected records |
  |---|---|
  | `collection_run` | A run is the store's own record of its work: it is what collects, and not what is collected |
  | `record_change` | A change is the store's own record of what it did to a record. Where the new value came from is said by the record, and by the run that caused the change |
  | `review_item` | A review item is the store's own record of a doubt. What a source said is in it, with the source that said it, and it is kept there to be decided, not to be shown |
  | `source` | A source is where records come from. A person describes it and reads its terms: it is not collected from a source itself |
  | `source_offer` | What a source offers is part of the description of the source, which a person gives |

  Whoever adds a table that holds nothing collected puts it on the
  list, with the reason, and the reason is read with the change.
- **What a table of collected records must have.** The eight columns,
  each as the set has it: of its type, and of its list where it is of
  one; a row cannot be without it, unless it is the day the record was
  published; neither the table nor the store's code gives it a value;
  `source_id` refers to `source.id` and says nothing of what happens
  when the source is deleted or its key changed, and no other column
  of the set refers to anything. An index over `source_id` alone, over
  all rows, in which two rows can be alike. And the check of its two
  times, by the name the naming rule gives it and letter for letter.
- **What it need not have.** The rule does not hold the order of the
  columns, and says nothing of what else a table has: a model can have
  rules, checks and indexes of its own, also an index that begins with
  the source and goes on. That a name was given by hand is for the
  rules every table keeps to say, not for this one.
- **One sentence for the missing columns of a table**, which names
  them in the order of the set and says what to do: "The table track
  is without 8 of the eight columns every table of collected records
  has (source_id, …): its model must be a subclass of Collected, or
  the table must be on the list of the tables that hold no collected
  records, with the reason." A column that is there and not as the set
  has it, a missing index and a missing check have a sentence each.
  The index is not asked for where there is no `source_id`, nor the
  check where one of its two times is missing: the missing column
  says it all.
- **The list is held to the schema as well.** A name on it that is no
  table is named: a list that names what is not there is a list
  nobody reads. And a table on it that has all eight columns is named,
  because it holds collected records after all and must come off the
  list. A table on the list is not looked at otherwise: the runs and
  the offers have a `source_id` of their own, which is not the set,
  and a review item has a `source_id` and a `source_address` that can
  both be without a value.
- **The set is said twice, and that is meant.** The rule does not take
  the columns from `Collected`: it says them again, in its own words.
  A change to the set is therefore made in two places, and a test,
  which gives the tables of models of `Collected` to the rule, fails
  as long as the two do not agree.
- **Beside `broken_rules`, not a part of it** (see "The rules every
  table keeps"). `Base` knows nothing of sources, and most of the
  schemas that function is asked about hold nothing that was
  collected. The real schema is held to both, by a test each.
- **What the rule cannot see.** Whether the rows of a table were
  collected is a person's judgement, and the list is where it is
  written down. The rule cannot tell a good reason from a bad one; it
  makes sure that there is one to read.

## How far a collected record can be trusted

Two of the columns every collected record has are one of a list each:
its confidence and its verification status (see "Where a collected
record came from"). The two lists are in
`motosphere.db.models.provenance` (DAT-043). The first table with a
column of each is `country` (DAT-011).

They are two questions, and neither answers the other:

- **Confidence** is about the reading: how sure it is that the record
  says what its source says.
- **Verification status** is about the publishing: what standing the
  source's word has.

A result read without doubt from a fan's website is of high confidence
and independent. A date worked out from an official notice is official
and of low confidence.

**How sure it is**, `Confidence`. The design asks for a confidence level
and names no levels (DESIGN.md §8), so the planner's trial settled
three, from the surest to the least sure.

| The text that is stored | When |
|---|---|
| `high` | The source gives the value in a place made for it, such as a field of a feed or a cell under its heading, and it was taken as it stands |
| `medium` | The value was read out of a page or a document made for people, by a rule written for that source. It is wrong where the page is not as the rule expects it |
| `low` | The value was worked out from what stands around it, or the source is unclear about it or says two things |

**What standing the source's word has**, `VerificationStatus`. The four
kinds of record the design tells apart (DESIGN.md §6), in its order.

| The text that is stored | In the design | What it is |
|---|---|---|
| `official` | Officially published records | Published by whoever is answerable for what the record says: the body that ran the race or the championship, or the track about itself |
| `independent` | Independently published records | Published by somebody else, such as a news publication, a results database or a community website |
| `reconstructed` | Reconstructed historical records | Put together afterwards from what is left, where nothing published at the time is at hand. It is never shown as an official record |
| `unverified` | Unverified historical references | A mention that has not been checked against anything |

- **Three levels and no number.** A number between 0 and 1 would look
  more exact than anything behind it, because nothing measures how sure
  a reading is. Each of three levels can be said in a sentence, and a
  collector can be held to the sentence.
- **The status is said of the record, not of its source.** A governing
  body is official about its own championship and independent about a
  race somebody else ran. So the kind of a source (`SourceCategory`)
  does not give the status of what is collected from it.
- **Official does not mean right, and independent does not mean
  wrong.** The status says who published a thing. Whether two sources
  agree is another matter, and where they do not the review queue is
  for it (CLAUDE.md §11, DAT-010).
- **Both lists go from what can be trusted most to what can be trusted
  least.** That order is the list's, in the code. SQLite does not know
  it: in a table the texts are plain text, and a column sorted by them
  is sorted by their letters.
- **No text is on both lists**, so a text read from a row says by
  itself which of the two questions it answers.
- **A record cannot be without either** (DAT-008). Neither column has
  a value of its own, and neither may be empty: where little is known,
  `low` and `unverified` say so. How a record says the way it was got,
  the design's extraction method, is a column of the list of the ways
  of collecting (`CollectionMethod`).

## The changes to records

Nothing MotoSphere has collected is written over without a trace: "Preserve
original records and update history wherever practical." (CLAUDE.md
§11). When a field of a record is changed, what it held before is kept.
The table `record_change` keeps it, and its model `RecordChange` is in
`motosphere.db.models.record_change`. The fifth migration makes the
table (`make_the_record_changes`, DAT-009).

This section is the table and its rules. The function that changes a
record and writes its history in the same unit of work is the next
section, "Changing a record" (DAT-047). That a row of the history is
neither edited nor deleted is the section after this one, "The history
is only added to" (DAT-048). Its two indexes are at the end of this
section (DAT-049).

| Column | Holds | Rule |
|---|---|---|
| `id` | The key of the change | Given by the store, and never given twice (see "The rules every table keeps") |
| `record_table` | The table of the record that was changed, by its name | Never without it; not empty |
| `record_id` | The key of that record in its table | Never without it; above 0 |
| `field` | The field that was changed, by the name of its column | Never without it; not empty |
| `old_value` | What the field held before, as text | Can be without: the field had no value |
| `new_value` | What the field holds now, as text | Can be without: the field has no value now. Never the same as `old_value` |
| `collection_run_id` | The collection run that caused the change | A run that exists (`collection_run.id`), or none |
| `decided_by` | The person who decided the change, by name | Not empty, or none |
| `created_at`, `updated_at` | When the row was stored and changed | See "When a row was stored and changed". A row is never edited, so `updated_at` stays what it was when the row was stored |

- **One row is one field of one record that was changed.** A change to
  three fields of a record is three rows. So the history of one field
  is read without taking a row apart, and a field that did not change
  has no row.
- **One table for the changes of every table.** A table of history
  beside every table of records would say the same columns again for
  each of them, each with a migration and tests of its own. The price:
  SQLite cannot hold `record_table` and `record_id` to a row that
  exists, because a reference is to one table. A test stores a change
  to a track in a store that has no table of tracks, so the price is
  on record. What holds the two to a record is the function that
  writes a change with its history: it takes them from the record it
  changes (see "Changing a record").
- **Values are kept as text, in the form the store keeps them in.** A
  moment, a day and a word of a list are text in the store already
  (see "Times", "Calendar days" and "One of a list"). A whole number
  is kept as its text, and so is a yes or no, which the store keeps
  as 1 or 0 (see "Yes or no"); the function that writes a change says
  which text a value has (see "Changing a record"). The two columns are TEXT in
  a strict table, and not of SQLite's kind `ANY`, which keeps a value
  as it is given: then "7" and 7 would be two values in one column,
  and whether a field changed would depend on how its value was
  handed over.
- **No value is a value.** A field that had no value and has one now
  has changed, and so has one that lost its value: `old_value` or
  `new_value` is then without. Empty text and no value are not the
  same, and a change from one to the other is a change.
- **A change that changed nothing is refused** by a check,
  `old_value IS NOT new_value`. It says `IS NOT` and not `!=`: in SQL
  nothing is equal to no value, not even no value, so `!=` would let
  a row through whose field had none and has none. The table
  compares the texts letter for letter, so "Example Park" and
  "example park" are a change, and so are "1" and "1.0".
- **When it was changed is `created_at`.** A change and its history
  are written together, so the moment the row was stored is the moment
  of the change, and a second column would say the same.
- **What caused it: a run or a person, one of the two.** A change the
  collecting made names its run, and through the run its source and
  when it ran. A change a person made names the person. A check
  refuses a row that names neither, and a row that names both. The
  review queue (DAT-010) can later be named beside the person; the
  task that adds it decides how.
- **A run that caused a change cannot be deleted**, nor its key
  changed: the reference says nothing of what happens then, and SQLite
  refuses. A history that loses its cause when a run is tidied away
  would not be one.
- **Nothing forbids two changes that are alike.** A field can go from
  one value to another, back, and there again. The order of the
  changes to a field is the order of their keys, which the store
  gives in the order the rows were stored and never gives twice.
- **Not collected records.** The table is on the list of the tables
  that hold no collected records (see "Every table says where its
  records came from, or why not").

**The two indexes of the history** (DAT-049). The table of the changes
of every table grows with every change to every record, and two
things are asked of it again and again. The model says an index for
each, the naming rule names them, and the seventh migration makes them
(`index_the_record_changes`):

| Index | Over | What it finds |
|---|---|---|
| `ix_record_change_record_table_record_id` | `record_table`, `record_id`, in that order | The changes of one record |
| `ix_record_change_collection_run_id` | `collection_run_id` | The changes one run caused |

Neither forbids anything: a record is changed as often as it is, and a
run causes as many changes as it does.

- **What they are for.** SQLite says of a statement how it will answer
  it, and a test reads that for eight questions about the history,
  written as the store's code will ask them. With the indexes each is
  one step, a search of the index (`SEARCH record_change USING INDEX
  ix_record_change_record_table_record_id (record_table=? AND
  record_id=?)`, or the same with the index of a run), and nothing is
  sorted. Without them each is `SCAN record_change`: the whole history
  is read to find the changes of one record.
- **The order of the changes costs nothing.** SQLite ends every entry
  of an index with the key of its row. So within one record the
  entries stand in the order of the keys, which is the order the
  changes were made in (see above): the history of a record is read
  oldest first, or newest first, or only its last change, straight from
  the index, and so are the changes of one run.
- **Why the field is not in the index.** A third column, `field`, would
  put the changes of a record in the order of the names of their
  fields and only then of their keys. The planner's trial asked SQLite:
  the history of a record in the order it happened is then sorted
  after it is found (`USE TEMP B-TREE FOR ORDER BY`). The changes to
  one field of a record are found by the index of the record and the
  field is then looked at row by row, of which a record has few.
- **Why the table comes before the key.** With the key first the index
  would do the same for these questions. The table first also finds
  every change to the records of one table, should that be asked.
- **Deleting a run.** SQLite must look for the changes a run caused
  before it lets the run go or lets its key change, because the
  reference refuses both. It indexes nothing by itself for a reference,
  so without the index of a run it reads the whole history for every
  run that is deleted. With it, the test reads from SQLite's plan for
  the two statements that the history is searched by the index and
  that no table is read whole. It looks all the same for a run that
  caused nothing, which can be deleted.
- **What has no index.** Nothing asks for the changes one person
  decided, and no index is made for a question nobody asks: every
  index is paid for whenever a row is added. Ordering by `created_at`
  instead of the key is sorted; the key says the same order and is
  the one to ask for.
- **The history is still only added to.** An index is not a row. The
  seventh migration adds no row and edits none, and the triggers of
  the table are as they were.

## The history is only added to

What a row of `record_change` said once it says for good. A history
that can be put right afterwards proves nothing, so the store itself
refuses to edit a row, to delete one, and to put a new row in the place
of one (DAT-048). A row is added, and that is all that happens to it.

**Decision:** the refusal stands in the file, as four triggers on the
table, which the sixth migration makes
(`let_the_record_changes_only_be_added_to`). SQLite stops the statement
that fires one and gives its sentence as the error:

| Trigger | Fires | The sentence |
|---|---|---|
| `tr_record_change_never_edited` | before a row is edited | `A row of the history (record_change) is never edited.` |
| `tr_record_change_never_deleted` | before a row is deleted | `A row of the history (record_change) is never deleted.` |
| `tr_record_change_never_replaced` | before a new row whose key a row already has | `A row of the history (record_change) is never replaced.` |
| `tr_record_change_key_positive` | after a new row whose key is below 1 | `A key of the history (record_change) is 1 or more.` |

- **Why in the file and not in the model.** A refusal in the model
  holds whoever goes through the model, and nobody else: not a
  statement that edits many rows at once, not plain SQL, not another
  program that opens the file. A trigger is part of the file. It holds
  the models, the store's own code, a migration, and a connection that
  the store's code did not open, on which not even foreign keys are
  switched on. One place says it, so there are no two sentences to
  keep alike.
- **An edit is any change to a row**: a value, the key, the moment in
  `updated_at`, and also an edit that gives a column the value it
  holds already. The store does not ask what would change.
- **A row in the place of a row.** SQLite's REPLACE (`INSERT OR
  REPLACE`) takes a row with the same key out and puts the new row in,
  and fires no trigger for the row it takes out. That would be an edit
  by another name, so the third trigger asks before every new row
  whether its key is taken, and refuses if it is. It cannot tell what
  the statement would have done then, so it refuses them all alike: a
  plain INSERT with a key that is taken, one that would have passed
  over the new row, and one that would have edited the old row
  instead. A key that is free may be named.
- **A key is 1 or more.** A new row that names no key has none yet
  when the third trigger asks; SQLite shows it -1 then, and gives the
  row the next key afterwards. A row with the key -1 would therefore
  stop every new row. The fourth trigger refuses a row whose key is
  below 1, so there is no such row. The store gives keys from 1 up, so
  only a key written by hand is refused.
- **A statement that meets no row is not refused.** The triggers fire
  for the row that would be changed. An edit or a delete that names a
  key no row has changes nothing, and neither does one in a history
  without rows.
- **A refusal takes back the unit of work it is in**, like every other
  refusal of the store (see "Units of work").
- **`updated_at`** is there because every table has it (see "When a
  row was stored and changed"). In this table it never moves.
- **The rows that were there before the triggers** are held like any
  other: the migration asks nothing of them and changes none.
- **The run that caused a change** still cannot be deleted, which the
  reference holds (see "The changes to records"), so the history keeps
  its cause too.
- **`change` does not take a row of the history either** (see
  "Changing a record"), and says so before it writes. The triggers
  hold everything that does not go through it.

Where this ends:

- **Whoever can change the schema can take a trigger away**, or the
  table. The schema changes by migrations only, which are reviewed and
  tested, and the test of the models and the migrations fails when a
  trigger is missing from one of the two.
- **What a new row says is not held here.** The table's own checks hold
  it (see "The changes to records"); nothing holds a row to the moment
  it is written at, or to a record that exists.
- **SQLite must be able to fire triggers**, which every SQLite can that
  enforces foreign keys: a build without triggers has no foreign keys
  either. The tests refuse an edit, a delete and a replacement on every
  machine the gates run on.

## Changing a record

A record that is stored is changed with `change`, in
`motosphere.db.changes` (DAT-047):

```python
with unit_of_work(store) as work:
    track = work.get_one(Track, key)
    change(work, track, {"name": "Example Raceway", "length_in_metres": 1750}, run=run)
```

It gives the record its new values and adds one row to `record_change`
for every field that then holds another value, in the same unit of
work. So a change and its history are kept together or taken back
together: "neither exists without the other".

- **What is given.** The unit of work, the record, the fields with
  what each shall hold now, and the cause: the key of a collection run
  (`run`) or the name of a person (`decided_by`). Exactly one of the
  two, as the table asks; a call that names neither or both is refused
  before anything is changed.
- **A field that holds the value already is left alone.** It gets no
  row, and when no field differs the record is not touched at all: not
  even the moment it was last changed moves, and nothing is written.
  The function gives back the rows it wrote, in the order the fields
  were given, and an empty list when there were none.
- **Values are compared as the text of what the store keeps.** The
  type of the column is asked for what it keeps, as it is asked when a
  row is written, and the history holds the text of that:

  | The column keeps | Its text in the history | For example |
  |---|---|---|
  | Text, also text that must not be empty and a web address | The text itself, letter for letter | `Example Park` |
  | A whole number | Its digits, with `-` before a number below nothing | `1600` |
  | A time | The store's form of a time (see "Times") | `2026-11-25T09:30:00.000000+00:00` |
  | A calendar day | The store's form of a day (see "Calendar days") | `1998-05-01` |
  | A word of a list | The word (see "One of a list") | `hard pack` |
  | Yes or no | `1` or `0` (see "Yes or no") | `1` |
  | No value | No value | |

  A test asks SQLite itself for `CAST(<field> AS TEXT)` before and
  after a change, for a column of every one of these kinds, and the
  history holds exactly those two texts. So a time said with another
  offset is the same value when it is the same moment, and text that
  differs by a capital letter or by a space at its end is another
  value.
- **A column of text takes text, and a column of whole numbers a whole
  number.** `"1750"` for a whole number, `7` for a text and yes for a
  whole number are refused in one sentence, where SQLite would have
  made something of them. The record and its history then say the
  same, and the record in the code holds what the store holds.
- **A number with a fraction and bytes have no text yet.** A change to
  a column that keeps either is refused. A number with a fraction has
  more than one text (`1750.0`, `1.75e3`), and the one the history
  uses must give the same number back to the last digit when it is
  read. No real table has such a column yet, so nothing can be tried on
  real values: the task that brings the first decides it, with
  coordinates in view. A record that has such columns can have its
  other fields changed.
- **One moment for one call.** The clock is read once. Every row of
  the call is stored at that moment (`created_at`), and the record
  says it was last changed at the same moment (`updated_at`). So the
  rows of one change are found together, and a record's last change
  is the moment of its newest history.
- **Everything is refused before anything is changed**, where the
  function can tell: no cause or two; a record that is not stored yet,
  that another unit of work holds, or that was deleted; a row of the
  history itself; a field the table does not have; the three columns
  that are the store's own in every table (`id`, `created_at`,
  `updated_at`); and a value of the wrong kind. A good field given
  beside a bad one in the same call is not changed either.
- **What only the store can tell is refused when the function
  writes**, which it does before it returns: a value the record's
  table refuses, a run that does not exist, a person with an empty
  name. The unit of work then fails as a whole and keeps nothing, and
  whoever catches the refusal and carries on is stopped at the next
  thing the unit of work is asked.
- **A record that is stored for the first time has no history.** Its
  first values are not a change. The function takes it once the unit
  of work has written it.
- **Where a collected record came from goes through the function
  too.** The columns of the set (see "Where a collected record came
  from") are fields like any other. When a source says something new,
  the collector gives the new value and what says where it came from
  in one call, and the history then holds the address, the day and the
  moments that belonged to the old value: "Historical information must
  retain its original date" (CLAUDE.md §11). A test does exactly this.
- **Nothing stops a change past the function.** A field set by hand
  on a record is written when the unit of work ends, without a row. A
  test does this too, so that it is not taken for something the
  function prevents. A field set by hand before the call is compared
  as the unit of work holds it, so the history says what was set.
  Whether a record that was merely seen again unchanged (only
  `last_verified_at` moves) gets a row is for the code that collects
  to decide, by calling the function or not.

## The review queue

Where the collecting cannot tell by itself what is right, it does not
guess: "Do not automatically merge uncertain rider or track
identities." and "Use review queues when information conflicts."
(CLAUDE.md §11). What is in doubt is put down as an item and waits
until a person decides. The table `review_item` keeps the items, and
its model `ReviewItem` is in `motosphere.db.models.review_item`, with
the two lists an item is said by. The eighth migration makes the table
and its index (`make_the_review_items`, DAT-010).

This section is the table and its rules, and how an item is opened
and decided. A possible duplicate is opened by
`open_possible_duplicate` (DAT-051; see "Opening a possible duplicate"
below), and a doubt about a field by `open_field_doubt` (DAT-053; see
"Opening a doubt about a field"). An item is decided by `decide`
(DAT-052; see "Deciding an item"), which decides an item once, and
the table itself keeps a decision, whoever writes to it (DAT-054; see
"A decision is kept").

| Column | Holds | Rule |
|---|---|---|
| `id` | The key of the item | Given by the store, and never given twice (see "The rules every table keeps") |
| `kind` | What is in doubt | Never without it; one of the three kinds below |
| `record_table` | The table of the record the item is about, by its name | Never without it; not empty |
| `record_id` | The key of that record in its table | Never without it; above 0 |
| `other_record_id` | The other record of a possible duplicate, by its key in the same table | With a possible duplicate, always; with no other kind. Greater than `record_id` |
| `field` | The field that is in doubt, by the name of its column | With the two other kinds, always; never with a possible duplicate. Not empty |
| `source_id` | The source that says what the field should hold | As `field`. A source that exists (`source.id`) |
| `source_address` | The address at which the source says so | As `field`. A web address (see "A web address") |
| `source_value` | What the source says the field holds, as text | As `field`. Can be empty text |
| `reason` | Why the item is in doubt, in plain words, for the person who decides | Never without it; not empty |
| `state` | Whether the item was decided, and how | Never without it; one of the three states below. A new item is open |
| `decided_by` | The person who decided, by name | With a decision, always; never with an open item. Not empty |
| `decided_at` | When it was decided | As `decided_by` (see "Times") |
| `note` | What a person wants kept with the item | Not empty, or none |
| `created_at`, `updated_at` | When the row was stored and changed | See "When a row was stored and changed" |

**What is in doubt** is one of three kinds (`ReviewKind`):

| Kind | What it says |
|---|---|
| `possible duplicate` | Two records of one table may be the same thing |
| `sources disagree` | A source says that a field of a record holds another value than the record holds |
| `value outside its rules` | A source says that a field of a record holds a value which the rules of the field refuse |

**Whether it was decided** is one of three states (`ReviewState`):

| State | What it says |
|---|---|
| `open` | Nobody has decided it yet |
| `accepted` | What the item puts forward is taken: the two records are one, or the field shall hold what the source says |
| `rejected` | It is not taken: the two records are two, or the record stays as it is |

- **One item is one doubt about one record.** An item always names a
  record, by the name of its table and its key there, as a change in
  the history does (see "The changes to records"), and for the same
  reason: an item can be about a record of any table, and a reference
  is to one table. So SQLite does not hold the two to a row that
  exists; a test stores an item about a record of a table that is not
  there, so that this is on record. The functions that open an item
  take them from the records themselves (DAT-051, DAT-053), so what
  they open is about records that are stored. An item is about a record
  that is stored: what the collecting does with a record it cannot
  store at all is for the tasks of the collecting.
- **What else an item names goes with its kind**, and the table holds
  it to that with a check for each column. A possible duplicate names
  the other record and nothing else. The two other kinds name the
  field, the source, the address and what the source says, all four,
  and no other record. A table for each kind would say the record, the
  reason and the decision three times; one table with columns that
  are empty for some kinds says each once, and the checks make sure
  that no item is half of one kind and half of another.
- **The two records of a possible duplicate are said in one way**: the
  record is the one with the smaller key, and the other record the one
  with the greater. So "7 and 12" cannot also be stored as "12 and 7",
  and no record is its own duplicate. Both are of the same table: a
  track is not the duplicate of a rider.
- **More than two.** Three records that may all be one thing are three
  pairs, and three sources that say three things of a field are an
  item for each source that does not say what the record holds. An
  item stays small, and each can be decided by itself.
- **What the source says is kept as text, as it was given.** It is what
  a source said and no more. It is never run, followed or taken for an
  instruction (CLAUDE.md §14), and whatever shows it later shows it as
  inert text. Empty text is kept too: a source can say it of a field,
  and that is then what is in doubt.
- **Where the source says it** is kept with it, so that a person can
  look: "Keep original source material or permitted evidence
  references so that records can be checked later." (DESIGN.md §8).
  When it was found is when the item was stored (`created_at`).
- **Why, in words.** The kind says what sort of doubt it is. The
  reason says why this one arose, to the person who has to decide:
  that two tracks have one name and lie 140 metres apart, or what the
  record holds where the source says otherwise. The code that opens
  an item writes it. It can hold what a source said, and is shown as
  inert text like it.
- **A decision has who made it and when, and nothing else has.** Two
  checks hold `decided_by` and `decided_at` to the state: both are
  there when the item is accepted or rejected, and neither when it is
  open. The name of the person is text, as in the history: MotoSphere
  has no accounts, and who may decide is who may write to the
  repository (ARCHITECTURE.md §9).
- **What follows from a decision is not this table's.** Merging two
  records that are one, and giving a field what a source says, are the
  tasks that build them. An accepted value that the rules of its field
  refuse cannot be stored as it is: either the person corrects it, or
  the rule is wrong and is changed. The item says what was decided;
  the history says what was then changed.
- **The note never leaves the store.** It is for the person who
  decides and for whoever looks at the item later. No published file
  holds it; the task that publishes the detail files of the tracks
  holds the published folder to that (PUB-005).
- **A source that an item names cannot be deleted**, nor its key
  changed: the reference says nothing of what happens then, and SQLite
  refuses, as it does for the runs of a source.
- **The index over the source** (`ix_review_item_source_id`). SQLite
  looks for the items that name a source before it lets the source go,
  and indexes nothing by itself for a reference. A test of DAT-045
  reads SQLite's plan for deleting a source and holds it to reading no
  table whole, so the index comes with the table and not after it. It
  forbids nothing. The indexes that find the open items and all the
  items about one record come with what asks for them.
- **One doubt is one item**, and the store itself sees to it (DAT-050):
  the same doubt a second time is refused, whatever writes it. Two
  indexes that let no two rows be alike do that, made by the ninth
  migration (`hold_one_doubt_to_one_review_item`). A possible
  duplicate is the same doubt when it is about the same two records
  of the same table
  (`ix_review_item_record_table_record_id_other_record_id`); the pair
  is said in one way, so it cannot come a second time the other way
  round. An item about a field is the same doubt when it is about the
  same field of the same record and the same source says the same
  thing of it
  (`ix_review_item_record_table_record_id_field_source_id_source_value`).
- **What does not make it another doubt.** Its state: a doubt that a
  person has decided is not put to them again by the next collection
  run, whichever way it was decided. Its kind, between the two that
  are about a field: whether what the source says is another value or
  one the rules refuse can change when a rule changes, and the
  question to the person is the same. Nor the address at which the
  source says it, the reason or the note.
- **What does.** Another table, another record, another field, another
  source, and another thing said. What a source says is compared as
  the text it is, letter for letter: `1750` and `1750.0` are two
  doubts, and so are a value and the same value with a space after
  it. Whether two texts mean the same is for the code that collects
  to say before it opens an item. A source that says a new value
  after its first was rejected opens a new doubt, as it should.
- **Each of the two is over the items of its shape only**: the first
  over the rows that name another record (`WHERE other_record_id IS
  NOT NULL`), the second over those that name a field (`WHERE field
  IS NOT NULL`). One index over all six columns would refuse nothing,
  because SQLite counts two missing values as two different values,
  and every item is without some of the six: the trial stored the
  same pair twice under such an index. The rows are known by a column
  and not by their kind for the sake of the question "is this doubt
  there already?", which the functions that open an item ask
  (DAT-051, DAT-053). A statement that asks for `other_record_id = ?`, or for
  `field = ?`, can only be answered by rows the index has, and SQLite
  knows that, so it answers by the index in one search. An index
  `WHERE kind = 'possible duplicate'` is of no use to a statement
  that does not name the kind as well: the trial saw SQLite read the
  whole table for it.
- **A store that holds a doubt twice already** cannot be given the
  ninth migration. It fails and the store stays at version 8, with
  neither index: the migration does not choose which of two items to
  keep, and a person looks. No real store has items yet, because
  nothing collects yet.
- **Where the item that is there was decided**, the same doubt a
  second time is refused before the index is looked into, by the
  trigger that keeps a decided item from being replaced, and in its
  sentence (DAT-055; see "A decided item is never replaced"). Where
  it is open, SQLite says which index refused, as before.
- **What the table does not hold yet.** A decided item is kept from
  being edited and from being deleted (see "A decision is kept") and
  from being replaced (see "A decided item is never replaced"). An
  open item can be deleted, and replaced. Nothing holds the moment of
  a decision to the moment the item was stored.
- **Not collected records.** The table is on the list of the tables
  that hold no collected records (see "Every table says where its
  records came from, or why not"): an item is the store's own record
  of a doubt. What a source said is in it, with the source and the
  address, but the item is there to be decided and not to be shown.

### Opening a possible duplicate

`motosphere.db.review.open_possible_duplicate(work, record, other,
reason=...)` (DAT-051) is what the collecting calls when two records
may be the same thing and it cannot tell: "Do not automatically merge
uncertain rider or track identities." (CLAUDE.md §11). It puts the two
down as one open item of the review queue and gives the item back.
Nothing calls it yet.

- **It is given the two records themselves**, and takes the name of
  their table and their keys from them, as `change` does (see
  "Changing a record"). So an item it opens is about two records that
  are stored, of one table. They can be given in either order: the
  item names the one with the smaller key as its record and the one
  with the greater as the other, which is the one way the table says
  a pair.
- **The reason** is why the two may be the same, in plain words, for
  the person who decides. The code that calls the function writes it.
- **A doubt that is there already stays one item.** When the queue
  holds an item for these two records, that item is given back as it
  is, and nothing is written: not a second item, and not a change to
  the first. Its state, its reason, its note and its times stay what
  they were, and the reason given the second time is not read. That
  holds for an item that was decided as well, whichever way: a person
  is not asked again what they have answered, and the code that
  called sees from the item what the answer was.
- **The records are not touched.** Nothing is merged and nothing is
  written to the history of the changes. An item is a question; what
  follows from its answer belongs to the tasks that decide and that
  merge.
- **It is part of the unit of work** it is given. The item is written
  to it before the function returns, so it has its key then, and what
  the store refuses is refused at the call: a reason that is empty.
  Whatever is refused, the unit of work fails as a whole and no item
  is kept. A unit of work that fails later leaves no item either.
- **It looks, and then writes.** The look is one statement, for the
  table and the two keys, and SQLite answers it by the index of the
  pairs in one search (DAT-050). No other connection can store the
  same doubt between the look and the write: SQLite keeps nothing
  another connection writes while a unit of work that has read is
  open, and says "database is locked" to the other. A test tries
  exactly that. Past the function, the index refuses the same doubt
  a second time, whatever writes it.

What it refuses before anything is written, each with one sentence:

| What is given | What the function says |
|---|---|
| A record that is not stored yet, or that this unit of work did not read or store | "Only records that are stored, and that this unit of work read or stored, are put to the review queue." |
| Two records of two tables | "A possible duplicate is two records of one table: these are of … and of …." |
| Two rows of a table that holds no collected records | "The review queue is for doubts about collected records, and the table … holds none." |
| One record twice | "A record is not its own duplicate." |

- **Stored, and of this unit of work.** A new record is given to the
  unit of work and written to it (`work.flush()`) before it is put to
  the queue with the one it may be the same as: only then has it a
  key. A record that a unit of work read which has ended is read
  again. The function does not write what is pending by itself, so
  that it never stores what its caller has not yet said is ready.
- **Tables that hold no collected records** are those on the list
  `NOT_COLLECTED` (see "Every table says where its records came from,
  or why not"): the sources and what they offer, the runs, the history
  and the queue itself. Two of their rows are never a possible
  duplicate in this sense: the queue is where the collecting puts
  what it cannot settle about what it collected. Every other table
  is taken, so a table of records needs nothing to be put to the
  queue.
- **What it does not do.** It does not say whether the item is new or
  was there: the code that calls sees the state of the item, and
  nothing asks for more yet. It does not look whether the two records
  are alike in any way; that is the work of the code that finds
  possible duplicates, which comes with the tasks that collect. A
  doubt about a field is opened by a function of its own (see below).

### Opening a doubt about a field

`motosphere.db.review.open_field_doubt(work, record, field, kind=...,
source=..., address=..., says=..., reason=...)` (DAT-053) is what the
collecting calls when a source says something of a field of a stored
record and it cannot settle whether that is right: "Use review queues
when information conflicts." (CLAUDE.md §11). It puts that down as one
open item of the review queue and gives the item back. Nothing calls
it yet.

| What is given | What it is |
|---|---|
| `record` | The record itself. The name of its table and its key are taken from it |
| `field` | The name of a column of that table |
| `kind` | Which of the two doubts about a field it is: `ReviewKind.SOURCES_DISAGREE` or `ReviewKind.VALUE_OUTSIDE_ITS_RULES` |
| `source` | The key of the source that says it, as `change` is given the key of a run |
| `address` | The web address at which the source says it |
| `says` | What the source says the field holds, as the text the source gave |
| `reason` | Why it is in doubt, in plain words, for the person who decides |

- **What the source says is text, and is kept as it was given**,
  letter for letter: with its white space, in the source's own way of
  writing a number, and empty when the source says nothing of the
  field. It is never run, followed or taken for an instruction
  (CLAUDE.md §14). Only text is taken: a number, yes or no, bytes,
  nothing at all, and a class of its own that is merely like text
  are each refused, so that what is kept is what was given.
- **A doubt that is there already stays one item.** When the queue
  holds an item in which this source says this of this field of this
  record, that item is given back as it is and nothing is written.
  Its kind, its address, its state, its reason, its note and its
  times stay what they were; the kind, the address and the reason
  given the second time are not read. That is the same doubt as the
  store's index says it (DAT-050): the kind, the address and the
  reason do not make another, and a decided item counts.
- **Another field, another source, another record or another thing
  said is another doubt.** What is said is compared as the text it
  is: `1750` and `1750.0` are two doubts. Whether two texts mean the
  same is for the code that collects to say before it calls.
- **It does not look at what the record holds.** A source says a
  thing in its own words, and the record holds it in the store's. So
  the function cannot tell whether a source disagrees, and does not
  try: the code that collects has read the source and knows. A doubt
  that the sources disagree is stored even where the text given is
  the text of what the record holds; a test puts that on record.
- **The record is not touched**, and nothing is written to the
  history. What follows from a decision belongs to the tasks that
  decide and that apply decisions.
- **It is part of the unit of work** it is given, and written to it
  before the function returns, as a possible duplicate is. What the
  store refuses is refused at the call: a source that is not there
  (`FOREIGN KEY constraint failed`), an address that is no web
  address, and a reason that is empty. Whatever is refused, the unit
  of work fails as a whole.
- **It looks, and then writes**, as `open_possible_duplicate` does.
  The look is one statement, for the table, the key, the field, the
  source and what it says, and SQLite answers it by the index of
  what a source says in one search (DAT-050). It names neither the
  kind nor the address. No other connection can store the same doubt
  between the look and the write; a test tries exactly that.

What it refuses before anything is written, each with one sentence:

| What is given | What the function says |
|---|---|
| A record that is not stored yet, or that this unit of work did not read or store | "Only records that are stored, and that this unit of work read or stored, are put to the review queue." |
| A row of a table that holds no collected records | "The review queue is for doubts about collected records, and the table … holds none." |
| The kind `ReviewKind.POSSIBLE_DUPLICATE` | "A possible duplicate is two records and no field: it is opened with open_possible_duplicate." |
| `id`, `created_at` or `updated_at` as the field | "The column … is the store's own in every table: no source says what it holds." |
| A field its table does not have | "The table … has no column …." |
| Something said that is not text | "What a source says is given as the text it said, which … is not." (a `TypeError`) |

- **Which records and which tables are taken is said once.** The first
  two sentences are those of `open_possible_duplicate`, and both
  functions ask the same two rules of the module, so that they cannot
  come to differ.
- **The store's own columns** are the three that `change` refuses to
  change (see "Changing a record"), by the same list:
  `motosphere.db.changes.THE_STORES_OWN`. A doubt about one of them
  could never be applied.
- **A field is a column of the record's table**, by its name as the
  model says it, letter for letter. A doubt about a field the table
  does not have could never be applied either, and a misspelled name
  would otherwise wait in the queue for a person to find.
- **What it does not do.** It does not say whether the item is new or
  was there. It does not hold what the source says to the rules of the
  field: an item of the kind `value outside its rules` says that the
  code that collects found it outside them. It does not look whether
  the source is one that offers this kind of information.

### Deciding an item

`motosphere.db.review.decide(work, item, decision, by=..., note=...)`
(DAT-052) is how a person's decision on an open item is put down. It
gives nothing back: the item it was given says the decision
afterwards. Nothing calls it yet: what a person decides with comes
with the tasks of the administration.

| What is given | What it is |
|---|---|
| `item` | The item itself, as this unit of work read it |
| `decision` | `ReviewState.ACCEPTED` or `ReviewState.REJECTED` |
| `by` | The name of the person who decided |
| `note` | What the person wants kept with the item, or nothing |

- **What a decision changes of an item** is its state, who decided,
  when, and when the item was last changed; and its note, where one
  is given. Nothing else of the item is another afterwards, and no
  other item is touched.
- **When it was decided is not given.** It is the moment of the call,
  by the store's clock, read once: the moment of the decision is the
  moment the item was last changed.
- **The name is kept as it was given**, letter for letter. The table
  refuses one that is empty or blank, and a decision by nobody.
- **A note given is the note of the item afterwards**, in the place
  of one the item had, and kept as it was given. Without a note, the
  note the item has stays. The table refuses a note that is empty.
- **An item is decided once.** One that was decided already is
  refused, whatever is given for it: the same decision again, the
  other one, another person, and open, which would take the decision
  back. The item stays as it was and the clock is not asked.
- **Only the item is touched.** What follows from a decision, that
  two records become one or that a field gets what a source says, is
  not done here, and nothing is written to the history: the item is
  itself the record of who decided what and when. The tasks that
  merge records and that apply what a source says do what follows,
  and write the history of what they change.
- **It is part of the unit of work** it is given, and written to it
  before the function returns. What the store refuses is refused at
  the call, and the unit of work fails as a whole. A unit of work
  that fails afterwards leaves the item open.
- **It sends one statement**, which changes the item by its key. It
  does not read the item again: the unit of work has read it, and
  SQLite keeps nothing another connection writes while that unit is
  open. So no other connection can decide the item between the
  reading and the decision; a test tries exactly that, and SQLite
  says "database is locked" to the other connection.

What it refuses before anything is changed, each with one sentence:

| What is given | What the function says |
|---|---|
| An item that is not stored yet, or that this unit of work did not read or store | "Only an item that is stored, and that this unit of work read or stored, is decided." |
| An item that was decided | "The review item … was accepted already, and a decision is kept.", or "… was rejected already, …" |
| Anything but one of the two decisions | "To decide an item is to accept it or to reject it." |

- **The order** is the order of the table. An item that was decided
  is refused for that, also where what is given is no decision: who
  tries to put a decided item back to open is told that a decision
  is kept.
- **A decision is exactly one of the two values of the list.** Open is
  none, and neither is text that is spelled like one, a value of
  another list or nothing at all.
- **An item stored earlier in the same unit of work can be decided.**
  One that was given to the unit of work and is not written yet is
  refused, like a record that is put to the queue: the code that
  calls writes it first.
- **What it does not do, and what is not done yet.** It does not say
  who may decide: `by` is a name, and the administration will say
  whose. It does not hold the name to a list of people. The function
  refuses a second decision in its own words, before anything is
  written; a statement written past the function is refused by the
  table (see "A decision is kept").

### A decision is kept

"Preserve original records and update history wherever practical."
(CLAUDE.md §11). A person's decision on a doubt is such a record: the
code that later merges two records, or gives a field another value,
goes by it. The tenth migration (`keep_the_decision_of_a_review_item`,
DAT-054) makes two triggers on `review_item`, and the model makes the
same two wherever the table is made from it (see "The models and the
migrations agree"):

| Trigger | Fires | What SQLite says |
|---|---|---|
| `tr_review_item_decided_never_edited` | Before a row is changed whose state was not `open` | "A decided review item (review_item) is never edited." |
| `tr_review_item_decided_never_deleted` | Before a row is deleted whose state was not `open` | "A decided review item (review_item) is never deleted." |

- **An item that was decided is as it is for good.** It is not put
  back to open and not given the other decision, another person or
  another moment. No other column changes either: not its note, its
  reason, its record, its source, what the source says, its key, or
  the moment it says it was last changed. The whole row is the record
  of what was decided, and about what. An item whose reason or record
  could still change would come to say that a person decided
  something they never saw.
- **The note too.** `decide` takes a note with the decision. What
  comes to mind afterwards is not written onto the decided item;
  where it is written is for the administration to say (Phase 10).
- **The triggers ask what the item was before the statement**
  (`OLD.state != 'open'`), not what it would become. So an open item
  is changed as before, and to decide it is such a change, by `decide`
  or with plain SQL. From the statement that decides it on, the item
  is kept. A change that would change nothing (`SET state = state`)
  is refused as well: SQLite fires the trigger for every row a
  statement meets, whatever the row would hold afterwards.
- **An open item can still be deleted.** Whether a doubt that was
  opened may be taken back is not decided here, and nothing in the
  store's code deletes one.
- **A new item can still be stored as decided**, in one statement:
  the triggers are for a row that is there.
- **SQLite stops the statement, and no more.** What the statement had
  done to other rows before it met the decided item is taken back
  with it. What the work did before the statement stays, and code
  that catches the refusal can go on. In a unit of work nothing
  catches it, so the unit fails as a whole. A statement that is told
  to pass over what is refused (`UPDATE OR IGNORE`) is refused all
  the same.
- **In the file, not in the code**, as with the history (see "The
  history is only added to"): the refusal holds on a connection the
  store's code did not open, with foreign keys off, and through the
  models as past them. A statement that meets no decided item is not
  refused, and neither is one in an empty table.
- **A store that holds decided items already** is given the two
  triggers and nothing else. The migration reads and changes no row:
  the items are held from then on as they are. No real store has
  items yet.
- **An item that is replaced.** `INSERT OR REPLACE`, `REPLACE` and
  `UPDATE OR REPLACE` take out the row their new row clashes with, by
  its key or as the same doubt (the indexes of DAT-050), and SQLite
  fires no trigger for a row it takes out in that way. So these two
  triggers do not see it. Two more ask before every new and every
  changed row whether it would take the place of a decided item
  (DAT-055; see "A decided item is never replaced").
- **Whoever can change the schema can take a trigger away.** The test
  of the models and the migrations fails when one of the two is
  missing from either.

### A key is 1 or more

The store gives the items of the queue their keys, from 1 up. The
eleventh migration (`hold_the_key_of_a_review_item_to_1_or_more`,
DAT-056) makes two triggers on `review_item` that refuse a key below 1
written by hand, and the model makes the same two wherever the table is
made from it. The eighteenth
(`hold_the_key_of_a_review_item_under_every_name`, DAT-068) makes the
second of them anew, as it is said here:

| Trigger | Fires | What SQLite says |
|---|---|---|
| `tr_review_item_key_positive` | After a new row whose key is below 1 | "A key of the review queue (review_item) is 1 or more." |
| `tr_review_item_key_stays_positive` | After a row was given another key than it had, one below 1 | "A key of the review queue (review_item) is 1 or more." |

- **Why.** A new item that names no key has none until its row is
  written, and SQLite shows -1 for it until then. The task that keeps
  a decided item from being replaced (DAT-055) asks before every new
  row whether its key is that of a decided item. A decided item with
  the key -1 would then stop every new item that names no key. So
  there is no such item: the same rule, for the same reason, as in the
  history (see "The history is only added to").
- **Both ask after the row is written**, when a new item has the key
  the store gave it, and SQLite takes the row back with the statement.
  A trigger that asked before would refuse every new item that names
  no key.
- **A new item**: its key may be named, when it is 1 or more. Below 1
  it is refused, open or decided, of either shape, and also where the
  statement says `OR REPLACE` or `OR IGNORE`.
- **A changed key**: an open item may be given another key of 1 or
  more, as before, and none below 1. The second trigger fires after
  every change of an item and asks two things of the row as it now
  is: whether its key is below 1, and whether that is another key
  than it had (`NEW.id < 1 AND NEW.id != OLD.id`). An item that is
  given the key it has is given no other, and is not refused.
- **Every name of the key.** SQLite has four names for the key of this
  table: that of its column, `id`, and three of its own, `rowid`,
  `_rowid_` and `oid`, each in any capitals and in the marks SQLite
  takes around a name. The rule holds under all of them, in a
  statement that changes an item and in one that stores a new one,
  also where a new item that clashes with one that is there is told
  to change that one (`ON CONFLICT … DO UPDATE`). Where a statement
  names the key twice, SQLite takes the last, and the trigger sees
  the key the item got.
- **Until version 17 it did not** (DAT-068). The eleventh migration
  made the second trigger fire for a change of the column
  (`AFTER UPDATE OF id`), and SQLite does not fire such a trigger for
  a statement that sets the key by one of its own names:
  `UPDATE review_item SET rowid = -5 WHERE id = 5` was taken. The
  eighteenth migration takes that trigger out and makes it anew
  under the same name. It reads and changes no row. It is refused,
  and the store left as it was, where the trigger is not there to be
  taken out: such a store is not one the migrations built.
- **A decided item** is not given any other key: the triggers of a
  kept decision ask before the row is changed, these after it, so
  SQLite says "A decided review item (review_item) is never edited."
- **SQLite stops the statement, and no more**, as with a kept
  decision: what the statement had done to other rows is taken back
  with it, what the work did before stays, and in a unit of work the
  unit fails as a whole.
- **An item that has a key below 1 already** is left as it is:
  neither migration reads or changes a row. Such an item can still be
  changed, and given a key of 1 or more; it cannot be given another
  key below 1. No real store has items yet, and the store itself
  never gave such a key.

### A decided item is never replaced

A statement that says `REPLACE` (`INSERT OR REPLACE`, `REPLACE`,
`UPDATE OR REPLACE`) takes out the row its new row clashes with and
puts the new row in. SQLite fires no trigger for a row it takes out in
that way, unless the connection asks for it, so the two triggers of a
kept decision do not see it. The twelfth migration
(`keep_a_decided_review_item_from_being_replaced`, DAT-055) makes two
triggers on `review_item` that ask before the row is written, and the
model makes the same two wherever the table is made from it:

| Trigger | Fires | What SQLite says |
|---|---|---|
| `tr_review_item_decided_never_replaced` | Before a new row that has the key of a decided item or is its doubt | "A decided review item (review_item) is never replaced." |
| `tr_review_item_decided_never_replaced_by_another` | Before an open row is changed so that it has the key of a decided item or is its doubt | "A decided review item (review_item) is never replaced." |

- **Three ways to clash, and no other.** A row of the table clashes
  with another by its key and by the two indexes of one doubt (see
  "The review queue"): the same two records of the same table, or the
  same field of the same record of which the same source says the
  same thing. Each trigger asks about all three, in the words of the
  indexes. A row of the other shape has nothing in the column that is
  asked, and is equal to nothing. A test holds that the table has
  these two indexes of that kind and no other: an index that is added
  later is one more way to take a row out, and the triggers are then
  to ask about it too.
- **Whatever the statement says.** A trigger cannot tell what a
  statement would do with a clash. So a new row in the place of a
  decided item is refused also where the index would have refused it
  anyway (a plain `INSERT`, which now hears the sentence of the
  trigger and not SQLite's "UNIQUE constraint failed"), and where the
  statement would have passed the row over and said nothing (`INSERT
  OR IGNORE`, `ON CONFLICT DO NOTHING`). The last is stricter than
  the rule needs, and the price of asking in the file. Nothing in the
  store's code says any of these: `open_possible_duplicate` and
  `open_field_doubt` look for the doubt first and give back the item
  that is there.
- **An open item is replaced as before.** It can be edited and
  deleted, and a statement that says `REPLACE` takes it out as before.
  The same doubt as an open item is refused by the index, in SQLite's
  words, as before.
- **The key is asked from 1 on**, of a new row. A new row that names
  no key has none before it is written, and SQLite shows -1 for it.
  The first trigger asks about the key only when it is 1 or more; a
  new row with a key below 1 is taken back by the triggers of the
  keys (see "A key is 1 or more"), with whatever it took out. So a
  decided item with the key -1, which a store could be given before
  version 11, stops no new item, and is not replaced either. The
  second trigger asks about every key: a changed row always has one.
- **Of an open item only**, the second. A decided item is never
  edited, which its own trigger says in its own sentence. The second
  trigger of this rule asks only where the row was open before the
  statement, so that SQLite never has two sentences to choose from.
- **The rows of one statement.** The triggers ask before every row.
  An item that the statement itself stored as decided, or made
  decided, is a decided item for the rows after it.
- **SQLite stops the statement, and no more**, as with a kept
  decision: what the statement had done to other rows is taken back
  with it, what the work did before stays, and in a unit of work the
  unit fails as a whole.
- **In the file, not in the code**: the refusal holds on a connection
  the store's code did not open, with foreign keys off. Where such a
  connection has SQLite fire the triggers of a delete for a row that
  `REPLACE` takes out (`PRAGMA recursive_triggers`), the store has
  said no before that, in the same sentence.
- **A store that holds decided items already** is given the two
  triggers and nothing else. The migration reads and changes no row.
- **What it costs.** One question of the table before every new row
  and every changed open row. In the planner's trial SQLite answered
  it with three searches, of the key and of the two indexes, and read
  no table whole; no test holds that.
- **Whoever can change the schema can take a trigger away**, here as
  with a kept decision.

## The countries

A country is where a track, an event, a rider or a source is, and the
table `country` knows the countries (DAT-011). Its model is `Country`,
in `motosphere.db.models.country`, and the thirteenth migration,
`make_the_countries`, makes the table and its index. A country is
known by its two codes of ISO 3166-1, the international standard for
the names of countries. The table has no rows yet: the countries of
the standard are loaded by a task of its own, from a source whose
licence allows it (DAT-012).

| Column | What it holds | May be without a value |
|---|---|---|
| `alpha_2` | Its code of two letters, as `NZ` for New Zealand | No |
| `alpha_3` | Its code of three letters, as `NZL` | No |
| `name` | What it is called in English: the short name of the standard, as its source writes it. Text that is not empty (see "Text that must not be empty") | No |
| the eight columns of a collected record | Where the row came from and how far it can be trusted (see "Where a collected record came from") | Only `published_on` |

The key is before these columns and the two times are after them, as
in every table.

- **A country is a collected record**, the first the store has. Its
  codes and its name are read from a source, and every row says which
  one, at which address, when, how, and how far it can be trusted.
  `Country` is a subclass of `Collected` and names three columns; the
  eight, their checks, the reference to `source`, the index over
  `source_id` (`ix_country_source_id`) and the check that holds the two
  times together come with that. A country comes from a source that is
  there, and a source that countries came from cannot be deleted.
- **A code is capital letters of its number, and nothing else.** Two
  checks, `ck_country_alpha_2_two_capitals` and
  `ck_country_alpha_3_three_capitals`, refuse every other text: small
  letters, too few and too many, a figure, white space before or
  after, and a letter that is not one of the 26 from `A` to `Z`, also
  where it looks like one, as a Greek or a wide capital does. Each is
  written with SQLite's `GLOB`, which tells small letters from large
  ones on every machine, and with a second question, because `GLOB`
  reads text up to a character with the number 0 and no further: a
  code with such a character in it is refused too (as in "A web
  address").
- **A code is stored as it is given, or refused.** Neither the model
  nor the table puts a code into capitals. A source that writes `nz`
  has written something other than the standard's code, and whoever
  reads that source decides what it means; a code that was put right
  in silence would hide it.
- **The table knows the form of a code, not the standard's list.**
  `ZZ` is taken, and so is `XK`, which the standard leaves to its users
  and which is in use for Kosovo. Which codes there are is what the
  source says, and comes with the rows (DAT-012).
- **No two countries have one code**, of two letters or of three:
  `uq_country_alpha_2` and `uq_country_alpha_3`. Each code is held by
  itself, so a row with a new code of two letters and a code of three
  that is taken is refused. Codes are told apart letter for letter,
  which is all there is to tell where every letter is a capital.
- **Two rows can hold one name.** A country is known by its codes. A
  name is text as its source writes it, with the white space and the
  capitals it has, and the table does not judge whether two rows mean
  one country. Names in other languages, and the other names a country
  is known by, are not in this table.
- **Nothing gives itself a value.** A row cannot be without a code, a
  name or any of the seven things that are known of every collected
  record, and neither the model nor the table makes one up.
- **A country is changed with its history**, by `change` (see
  "Changing a record"), like every record: a name that its source
  writes otherwise from one day on becomes one row of history with
  what it was. Nothing in the table stops a change past that
  function, here as elsewhere. A country can be deleted while nothing
  refers to it. The sources are the first to refer to the countries: a
  country that a source is of cannot be deleted (DAT-057; see "A source
  says which country it is of"). The regions are the second: a country
  that has regions cannot be deleted (DAT-013; see "The regions").
- **What is not in the table.** The number the standard gives each
  country, which nothing in the design asks for. The parts of a
  country, which are a table of their own (DAT-013; see "The regions").
  The country of a source is a column of `source` (DAT-057).

## The regions

A country can be divided into parts: states, provinces, counties,
islands. A track says with one of them where in its country it lies,
and the table `region` knows them (DAT-013). Its model is `Region`, in
`motosphere.db.models.region`, and the sixteenth migration,
`make_the_regions`, makes the table and its index. The seventeenth,
`let_a_region_say_its_code`, builds it anew with the column of the
code (DAT-064), and the nineteenth,
`hold_the_code_of_a_region_to_its_country`, holds that code to the
country (DAT-067; see "The code of a region is of its country"). The
table has no
rows, and no reference rows are loaded into it: a region comes with the
record that needs it, from the source that names it.

| Column | What it holds | May be without a value |
|---|---|---|
| `country_id` | The country it is a part of | No |
| `name` | What it is called, as its source writes it. Text that is not empty (see "Text that must not be empty") | No |
| `iso_3166_2` | Its code of ISO 3166-2, the international standard for the parts of countries, as `NZ-CAN` for Canterbury | Yes |
| the eight columns of a collected record | Where the row came from and how far it can be trusted (see "Where a collected record came from") | Only `published_on` |

The key is before these columns and the two times are after them, as
in every table.

- **A region is a part of exactly one country**, one that is in the
  store (`fk_region_country_id_country`). A row without a country is
  refused, and so is one of a country that is not there, when the
  region is stored and when it is moved. **A country that has regions
  cannot be deleted**: its regions are taken away first. Nothing is
  said of what is to happen to the regions then, so SQLite refuses the
  deletion; it deletes nothing by itself.
- **No two regions of one country have one name**
  (`uq_region_country_id_name`), when a region is stored, when it is
  given another name and when it is moved to another country. Two
  countries can each have a region of a name.
- **Two names are one name only if they are the same text.**
  "Canterbury" and "canterbury" are two names, and so are "Canterbury"
  and "Canterbury " with a space after it. The table does not judge
  whether two names mean one region: whether "Bayern" and "Bavaria" do
  is a question for a person, and such a pair goes to the review queue
  (see "Opening a possible duplicate"). A name is stored as its source
  writes it, with the white space, the capitals and the letters it has.
- **A region can say its code of ISO 3166-2**, in the column
  `iso_3166_2` (DAT-064). **A region may be without one, and any number
  of regions may be:** not every region a source names has a code, and
  a region is not kept out of the store for lacking one. Nothing gives
  a region a code that its source did not say.
- **A code has the form of the standard**
  (`ck_region_iso_3166_2_form`): two capital letters, a hyphen, and
  one, two or three capital letters or digits, as `AT-1`, `AU-WA` and
  `FR-75C`. The letters are the 26 of the English alphabet and the
  digits the ten from 0 to 9. Everything else is refused, when a
  region is stored and when it is given a code later: small letters,
  white space before, after or within, another sign for the hyphen, a
  letter with an accent or of another script, more or fewer characters
  on either side, and a character with the number 0 anywhere. The form
  was measured on the standard's own list before it was written: all
  5046 codes of the list that comes with release 4.20.1 of iso-codes
  have it, 327 of them with one character after the hyphen, 3099 with
  two and 1620 with three. The check holds the form only and does not
  know the list. That the two letters are those of the region's
  country is a rule of its own (see "The code of a region is of its
  country").
- **No two regions have one code** (`uq_region_iso_3166_2`), whatever
  their countries, when a region is stored and when it is given a code
  later. A code is free again once the region that had it is deleted,
  has another code or has none. SQLite keeps an index for the rule
  (`sqlite_autoindex_region_2`), and it finds the region of a code
  without reading the table; a test holds what SQLite says it uses.
- **The seventeenth migration builds the table anew** (see "How the
  schema changes"): SQLite puts a column that is added in place after
  all the others and cannot give it the rule of one code. Every region
  keeps what it had and its key, none gets a code, the highest key the
  table gave is kept, so that the key of a deleted region is not given
  again, and the index over `source_id` is made again. No table points
  to a region yet. If the migration fails, at its last statement too,
  the store is as it was.
- **A region is a collected record.** `Region` is a subclass of
  `Collected` and names three columns; the eight, their checks, the
  reference to `source`, the index over `source_id`
  (`ix_region_source_id`) and the check that holds the two times
  together come with that. A region comes from a source that is there,
  and a source that regions came from cannot be deleted. The source of
  a region need not be the source of its country.
- **The regions of one country are found without reading the table.**
  SQLite keeps an index for the rule of the names
  (`sqlite_autoindex_region_1`, over the country and then the name).
  Because the country stands first in it, it finds the regions of one
  country, for whoever asks for them and for SQLite itself when a
  country is to be deleted and it looks whether the country has
  regions. So the table has no index of its own over `country_id`; a
  test holds what SQLite says it uses.
- **Nothing gives itself a value.** A row cannot be without a country,
  a name or any of the seven things that are known of every collected
  record, and neither the model nor the table makes one up. A region
  of which no code is said has none.
- **A region is changed with its history**, by `change` (see "Changing
  a record"), like every record. A region can be deleted while nothing
  refers to it; nothing refers to a region yet.
- **What is not in the table yet.** Two
  regions of one country that share a name: the standard's own list
  has 36 such pairs, as Maputo, the city and the province of
  Mozambique, which differ in their codes, and the rule of the names
  lets the table hold only one of each pair until the task that lets
  their codes tell them apart (DAT-066). A region that is a part of
  another region, as a county is of a state (DAT-065): until then
  every region is a part of its country only. Names in other
  languages, and the other names a region is known by, are not in this
  table.

### The code of a region is of its country

A code of ISO 3166-2 begins with the code of two letters of the
country: `NZ-CAN` is Canterbury in New Zealand, whose code is `NZ`.
The store holds a region to that (DAT-067). The letters of a country
are a column of another table, `country.alpha_2`, which a check of
`region` cannot read, so four triggers hold the two together. The
nineteenth migration, `hold_the_code_of_a_region_to_its_country`,
makes them, and the model `Region` makes the same four wherever the
tables are made from the models.

| Trigger | Fires | What SQLite says |
|---|---|---|
| `tr_region_code_of_its_country` | After a new region whose code does not begin with the letters of its country | "The code of a region (region) begins with the code of its country (country)." |
| `tr_region_code_stays_of_its_country` | After a change of a region that leaves it with such a code | "The code of a region (region) begins with the code of its country (country)." |
| `tr_country_code_of_its_regions` | After a new country that has a region whose code does not begin with its letters | "The codes of the regions of a country (region) begin with its code (country)." |
| `tr_country_code_stays_of_its_regions` | After a change of a country that leaves it with such a region | "The codes of the regions of a country (region) begin with its code (country)." |

- **A region is held** when it is stored, when it is given a code or
  another, and when it is moved to another country. A region can be
  moved together with its code, in one statement: what is asked is
  whether the row agrees with its country once the statement has
  written it.
- **A country is held too.** A country whose regions have codes cannot
  be given other letters, or the codes of its regions would be those
  of no country, or of another. A new country can have regions
  already: a statement that says `REPLACE` puts it in the place of the
  country that had its key, and the regions of the old are then the
  regions of the new. SQLite fires no trigger for the row it takes
  out, so the trigger for a new country asks.
- **A region without a code is asked nothing.** It is a part of any
  country and can be moved to any, and a country whose regions have no
  codes can be given any letters. The rule does not make a region
  have a code.
- **The two letters, and both of them.** The first two characters of
  the code are compared with the letters of the country as text: `NZ`
  and `NA` are two countries, and so are `NZ` and `TZ`. The rule does
  not know the standard's list. On the list that comes with release
  4.20.1 of iso-codes, measured before the rule was written, every one
  of the 5046 codes begins with the letters of a country of the same
  release.
- **What the table itself refuses, it refuses first.** The triggers
  ask after the row is written. A code that is not of the form, a code
  another region has, and letters another country has are refused by
  the check and the rules of the tables, in their own words, before a
  trigger is asked.
- **A refusal takes the statement back** and nothing else
  (`RAISE(ABORT)`), whatever the statement says is to happen on a
  clash (`OR REPLACE`, `OR IGNORE`, `OR FAIL`): of several regions
  written by one statement, one wrong code stops them all. In a unit
  of work the refusal is an error, and the unit takes back all it did.
- **None of the four names a column.** A trigger that fires for the
  change of one column is not fired by a statement that sets the key
  of a row by one of SQLite's own names for it (DAT-068; see "A key is
  1 or more"), and a country that is given another key gets the
  regions that point to that key. So each fires after every change of
  a row of its table, and asks of the row as it now is.
- **The rule stands in the file.** A connection that the store's code
  did not open is held to it, also one that does not ask SQLite to
  hold rows to what they point to.
- **A region whose country is not in the store** has no letters to be
  held to, and this rule says nothing of it. The store's own
  connections refuse such a region by the rule that a row points to a
  row that is there (`fk_region_country_id_country`). Where a
  connection of another kind has stored one, a country that is given
  the key it points to is held to its code.
- **The regions of a country are found for the rule without reading
  the table**, by the index SQLite keeps for the rule of the names
  (`sqlite_autoindex_region_1`), which a test holds.
- **The migration puts nothing right.** It makes the four triggers
  and reads and changes no row; every table, index and trigger that
  was there is as it was. A store could hold a region whose code
  begins with the letters of another country, because nothing refused
  one until version 19. Which of the two is wrong, the code or the
  country, the migration cannot know. Such a region stays as it is,
  and from then on it can be put right or deleted and nothing else:
  given a code of its country or none, moved to the country of its
  code, or deleted. Every other change of it is refused, and so is
  every change of its country, until then. No real store holds a
  region yet.
- **The migration fails where a trigger of one of the four names is
  there already**, with what it made before that taken back and the
  store left at version 18.

## The source of the countries

The countries come from the project iso-codes (`DATA_SOURCES.md`). The
module `motosphere.reference.countries_source` says what the row of that
source in the table `source` holds, and its function
`source_of_the_countries(work)` gives that row, storing it first when
the store does not have it (DAT-060). The loading of the countries
calls it (DAT-059; see "The loading of the countries"), so a store has
the row from the first time the command `countries` is run on it
(DAT-061).

| Column | What the pipeline says |
|---|---|
| `name` | `iso-codes`, as its makers call it. It is what the source is known by |
| `website` | `https://salsa.debian.org/iso-codes-team/iso-codes` |
| `category` | `reference list` |
| `collection_method` | `public dataset` |
| `terms_address` | No value: the source has no page of terms. Its terms are its licence, whose text is in the repository beside the file |
| `licence` | `LGPL-2.1-or-later`, as its release names it |
| `usage_restrictions` | "Every copy keeps the notice of copyright and comes with the licence. A changed copy says that it was changed, and when. A work that takes over the list, or part of it, is passed on under the same licence, free of charge." |

It offers one kind of information, `reference data`: one row of
`source_offer`.

- **The pipeline describes the source, and people say the rest.** The
  seven columns above are what the code knows of the source. Four are
  not the code's to say: whether a person has read its terms
  (`terms_read_at`), whether it is switched on (`switched_on`), how
  often it is looked at (`scan_every_hours`) and which country it is of
  (`country_id`). The function sets none of the four and looks at none
  of them. A test holds that every column of a source is one of the
  seven, one of the four or one of the store's own three, so a column
  that is added later has to be put on one side.
- **A new row is switched off, and says that nobody has read its
  terms.** The planner read the licence, and `DATA_SOURCES.md` says
  what it found. The column says when a person last read a source's
  terms, and no person has yet: the store is not told otherwise. The
  source need not be switched on for its countries to be loaded,
  because nothing is fetched from it: its file is in the repository.
  The owner switches it on, or leaves it, after reading the licence.
- **The source is stored once.** It is known by its name, letter for
  letter. When the store has a source of that name, the function gives
  it as it is and writes nothing: not when it is called twice in one
  unit of work, and not in a later one.
- **A source of that name that is described otherwise is refused.**
  When one of the six described columns holds something else, or the
  source does not offer `reference data`, the function raises a
  `CountriesSourceError` and changes nothing. Its sentence names what
  differs, in the order of the table: "The store has a source called
  "iso-codes" that is not the source of the countries as the pipeline
  describes it. It differs in its website and licence. Nothing was
  changed." Which of the two is right is for a person to decide: the
  code does not write over what the store holds, and it does not load
  countries under a description that is not its own. What else the
  source offers is not looked at.
- **It is part of its unit of work.** The row and its offer are kept or
  taken back with whatever else the unit of work does.

## The loading of the countries

The countries of the reference file are brought into the table
`country` by one function, `load_countries(work, countries)`, in
`motosphere.reference.countries_load` (DAT-059). It is handed what the
file says, as `countries_of_the_project()` gives it, and adds every
country the store does not have. The command `countries` calls it
(DAT-061).

**The command that loads the countries.** `python -m motosphere
countries` asks for the store the settings name
(`store_to_work_on`, DAT-063), reads the reference file that comes with
the pipeline, and calls the loading in one unit of work: either all of
what it found is kept, or none of it. Nothing is fetched. It then says
on standard output what the loading found, one line for each kind of
thing:

| What was found | What is said |
|---|---|
| Always: how many countries the release has, how many were added and how many were there as the release has them | "Of the 249 countries of release 4.20.1 of iso-codes, 249 were added to the data store … and none was there already." |
| Countries the store says something else of | "The data store says something else of 2 of them than the release does: FR, TR. They were left as they are, and what the release says waits in the review queue." |
| Countries of the store that the release does not have | "The data store has 1 country that the release does not have: XK. It was left as it is." |

The second and the third line are there only when there is such a
country. The place of the store is its whole path. In all these cases
the exit code is 0: that the store says something else of a country is
no failure of the command, and what follows from it is a person's
decision in the review queue. Run again on the same store, the command
adds nothing and writes nothing, and its first line says so ("none was
added … and 249 were there already").

Nothing is loaded, and the store is byte for byte as it was, with one
sentence on standard error and the exit code 1, where

- the store is not ready: there is none, it lacks migrations, or
  `migrate` would refuse it (what `store_to_work_on` says, with the
  advice to run `migrate` first where that puts it right);
- the reference file is damaged (what the reader of the file says);
- the store has a source called "iso-codes" that is described otherwise
  than the pipeline describes the source of the countries (what
  `source_of_the_countries` says).

Any other error is not caught: it reaches the caller as it is, and the
unit of work has then kept nothing.

**The loading adds countries, and it changes none.** A country is known
by its code of two letters.

| What the store has of a country of the file | What the loading does |
|---|---|
| Nothing: neither its code of two letters nor its code of three | Adds it |
| The code of two letters, with the same code of three and the same name | Leaves it as it is |
| The code of two letters, with another code of three or another name | Leaves it as it is, names it, and puts what the file says to the review queue |
| The code of three letters, under another code of two | Adds nothing, names it, and puts what the file says to the review queue |

A country of the store whose code of two letters the file does not have
is left as it is and named too. No country is ever changed and none is
ever deleted. A name is compared letter for letter: a capital, a space
or a letter written in another way makes it another name.

**What waits in the review queue.** Where the store and the file say
different things of a country, the loading does not choose. It puts what
the file says to the review queue (see "The review queue"), as what the
source of the countries says of one field of a stored country, and a
person decides (DAT-062).

| What the store has | The item is about | Field | What the source says |
|---|---|---|---|
| The code of two letters with another code of three | That country | `alpha_3` | The file's code of three |
| The code of two letters with another name | That country | `name` | The file's name |
| The file's code of three letters under another code of two | The country that has the code of three | `alpha_2` | The file's code of two |

A country that differs in two of these has two items. Every item is of
the kind `sources disagree`, names the source of the countries and the
address of the release, and says why in one sentence, such as "Release
4.20.1 of iso-codes has another name for the country TR." The items are
opened in the order of the file. A doubt the queue holds already is not
put to it again, whether it is open or decided: a question a person has
answered is not asked a second time. A country of the store that the
file does not have is no doubt, because the file says nothing of it. It
is only named.

**What a new row says of where it came from.**

| Column | What the loading writes |
|---|---|
| `source_id` | The source of the countries (above), which is stored first when the store does not have it |
| `source_address` | `https://archive.ubuntu.com/ubuntu/pool/main/i/iso-codes/iso-codes_4.20.1.orig.tar.xz`: the file of the release, where it was fetched |
| `collected_at` | The moment of the loading: when the store took the row from the file. One moment for all rows of one loading |
| `published_on` | `2026-01-01`, the day release 4.20.1 was published |
| `last_verified_at` | The same moment as `collected_at` |
| `extraction_method` | `public dataset` |
| `confidence` | `high`: the file gives each value in a field made for it |
| `verification_status` | `independent`: iso-codes is not the body that keeps the standard |

The release, its day and its address are said in the module (`RELEASE`,
`PUBLISHED_ON`, `ADDRESS`), and tests hold them to the note beside the
file. When the file itself was fetched is in that note; the store says
when it took the row.

- **What it gives back.** `CountriesLoaded`, four lists of codes of two
  letters: `added`, `as_they_were` and `said_otherwise` in the order of
  the file, and `not_in_the_file` in the order of the codes.
- **Loaded again, it writes nothing.** A second loading of the same
  file finds every country as it was. No row is touched, not even to
  say that it was seen again: the file is the same file, and the source
  itself was not looked at. What waits in the review queue is found
  there and not opened again.
- **It is not a collection run.** Nothing is fetched: the file was
  fetched once, by hand, and is part of the project. So a loading
  stores no run, and the source need not be switched on for it. It
  leaves no history either.
- **Why it does not change a country.** A record is changed with its
  history, and a change names what caused it: a collection run, or the
  person who decided it (see "Changing a record"). A loading is neither.
  The store and the file can only come to say different things of a
  country when a person changed the store by hand, or when a newer
  release is taken into the repository; then a person decides which is
  right. The loading names the countries, and what the file says of
  them waits in the review queue. What follows from a decision, that
  the country gets what the file says, is not done by the loading.
- **A country that is there is left whatever source it names.** Only
  the two codes and the name are compared. A country that a person put
  in from another source, and that is as the file has it, stays that
  source's.
- **A list that has one code twice is refused by the store**, as the
  reader refuses a file that has one: SQLite's own refusal reaches the
  caller, and nothing is kept.
- **It is part of its unit of work.** The source, its offer, the
  countries and the items of the review queue are written when the
  function returns, and are kept or taken back with whatever else the
  unit of work does.

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
