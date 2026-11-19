"""Tests of the key every table has, with tables made in a real SQLite file.

The two models here are made for the tests. They are subclasses of the
real ``Base`` and name no key, so they prove what it gives them, but they
are kept in a schema of their own (``Proof.metadata``), so the real schema
never sees them.
"""

import pytest
from sqlalchemy import Engine, ForeignKey, MetaData, UniqueConstraint, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base, broken_rules
from motosphere.db.work import unit_of_work


class Proof(Base):
    """Models of the tests' own: the key ``Base`` gives, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofThing(Proof):
    __tablename__ = "proof_thing"

    name: Mapped[str]


class ProofPart(Proof):
    __tablename__ = "proof_part"
    # A model that says something of its table itself. Its key is the same all the same.
    __table_args__ = (UniqueConstraint("thing_id", "name"),)

    thing_id: Mapped[int] = mapped_column(ForeignKey("proof_thing.id"))
    name: Mapped[str]


@pytest.fixture
def made(store: Engine) -> Engine:
    """The store, with the two tables of the tests made in it."""
    with store.begin() as connection:
        Proof.metadata.create_all(connection)
    return store


def add(made: Engine, *names: str) -> list[int]:
    """Store a thing of each name, each in a unit of work of its own, and say their keys."""
    keys = []
    for name in names:
        with unit_of_work(made) as work:
            thing = ProofThing(name=name)
            work.add(thing)
            work.flush()
            keys.append(thing.id)
    return keys


def remove(made: Engine, *keys: int) -> None:
    with unit_of_work(made) as work:
        work.execute(delete(ProofThing).where(ProofThing.id.in_(keys)))


def test_the_models_of_these_tests_break_no_rule() -> None:
    assert broken_rules(Proof.metadata) == []


@pytest.mark.parametrize(
    ("table", "others"),
    [
        ("proof_thing", ["name", "created_at", "updated_at"]),
        ("proof_part", ["thing_id", "name", "created_at", "updated_at"]),
    ],
    ids=["a model that says nothing of its table", "a model that says something of its table"],
)
def test_the_key_is_the_first_column_and_a_whole_number(
    made: Engine, table: str, others: list[str]
) -> None:
    with made.connect() as connection:
        columns = [
            (name, declared, bool(required), key)
            for _, name, declared, required, _, key in connection.exec_driver_sql(
                f"PRAGMA table_info({table})"
            )
        ]

    assert columns[0] == ("id", "INTEGER", True, 1)
    assert [(name, key) for name, _, _, key in columns[1:]] == [(other, 0) for other in others]


@pytest.mark.parametrize("table", ["proof_thing", "proof_part"])
def test_the_file_says_that_a_key_is_never_given_twice(made: Engine, table: str) -> None:
    with made.connect() as connection:
        written = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE name = ?", (table,)
        ).scalar_one()

    assert "id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT" in written


def test_new_rows_get_the_next_key(made: Engine) -> None:
    assert add(made, "first", "second", "third") == [1, 2, 3]


def test_the_key_of_the_last_row_is_not_given_again_when_the_row_is_deleted(made: Engine) -> None:
    add(made, "first", "second")
    remove(made, 2)

    assert add(made, "third") == [3]


def test_no_key_is_given_again_when_every_row_is_deleted(made: Engine) -> None:
    add(made, "first", "second", "third")
    remove(made, 1, 2, 3)

    assert add(made, "fourth") == [4]


def test_no_key_is_given_again_after_the_store_was_closed(made: Engine) -> None:
    add(made, "first", "second")
    remove(made, 1, 2)
    made.dispose()

    assert add(made, "third") == [3]


def test_a_row_written_past_the_model_gets_a_key_that_was_never_given(made: Engine) -> None:
    add(made, "first", "second")
    remove(made, 2)

    with made.begin() as connection:
        # A row written with plain SQL says its two times itself.
        connection.exec_driver_sql(
            "INSERT INTO proof_thing (name, created_at, updated_at) VALUES ('third', "
            "'2026-11-19T08:00:00.000000+00:00', '2026-11-19T08:00:00.000000+00:00')"
        )
        keys = connection.exec_driver_sql("SELECT id FROM proof_thing ORDER BY id").scalars().all()

    assert keys == [1, 3]


def test_a_row_stored_with_a_key_of_its_own_keeps_it_and_later_keys_come_after_it(
    made: Engine,
) -> None:
    add(made, "first")
    with unit_of_work(made) as work:
        work.add(ProofThing(id=40, name="fortieth"))

    assert add(made, "next") == [41]
    with unit_of_work(made) as work:
        assert work.scalars(select(ProofThing.id).order_by(ProofThing.id)).all() == [1, 40, 41]


def test_every_table_counts_its_own_keys(made: Engine) -> None:
    (thing,) = add(made, "first")
    with unit_of_work(made) as work:
        part = ProofPart(thing_id=thing, name="a part")
        work.add(part)
        work.flush()
        first_part = part.id
    add(made, "second", "third")

    with made.connect() as connection:
        last_keys = connection.exec_driver_sql(
            "SELECT name, seq FROM sqlite_sequence ORDER BY name"
        ).all()

    assert first_part == 1
    assert [tuple(row) for row in last_keys] == [("proof_part", 1), ("proof_thing", 3)]
