"""PROBE, not for merging: what SQLite the pipeline's Python has on this machine."""

import platform
import sqlite3
import sys

print("PROBE python", sys.version.replace("\n", " "))
print("PROBE executable", sys.executable)
print("PROBE platform", platform.platform())
print("PROBE sqlite", sqlite3.sqlite_version)
c = sqlite3.connect(":memory:", autocommit=True)
print("PROBE options", sorted(r[0] for r in c.execute("pragma compile_options")))
CHECKS = [
    ("rtree", "create virtual table r using rtree(id, minx, maxx, miny, maxy)"),
    ("rtree_i32", "create virtual table ri using rtree_i32(id, minx, maxx, miny, maxy)"),
    ("fts5", "create virtual table f using fts5(body)"),
    ("fts5 trigram", "create virtual table t using fts5(body, tokenize='trigram')"),
    ("fts5 remove_diacritics 2", "create virtual table t2 using fts5(body, tokenize='unicode61 remove_diacritics 2')"),
    ("json_extract", "select json_extract('{\"a\":1}', '$.a')"),
    ("json ->>", "select '{\"a\":1}' ->> '$.a'"),
    ("jsonb", "select jsonb('{\"a\":1}')"),
    ("strict", "create table s (a integer) strict"),
    ("returning", "insert into s values (1) returning a"),
    ("math", "select sin(1.0)"),
    ("generated", "create table g (a integer, b integer generated always as (a*2) stored)"),
    ("upsert", "insert into s values (1) on conflict do nothing"),
    ("window", "select row_number() over (order by 1)"),
    ("geopoly", "create virtual table gp using geopoly()"),
    ("drop column 1", "create table d (a integer, b integer)"),
    ("drop column 2", "alter table d drop column a"),
    ("rename column", "alter table s rename column a to b"),
    ("unixepoch", "select unixepoch()"),
    ("iif", "select iif(1, 2, 3)"),
    ("without rowid", "create table w (a text primary key) without rowid"),
    ("partial index", "create index pi on s (b) where b is not null"),
    ("expression index", "create index ei on s (lower(b))"),
    ("dbstat", "select count(*) from dbstat"),
]
for name, sql in CHECKS:
    try:
        c.execute(sql)
        print("PROBE ok  ", name)
    except sqlite3.Error as error:
        print("PROBE FAIL", name, "|", error)
c.execute("pragma foreign_keys = on")
print("PROBE foreign_keys", c.execute("pragma foreign_keys").fetchone())
