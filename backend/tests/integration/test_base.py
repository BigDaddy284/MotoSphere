"""Tests of the base of every model, with tables made in a real SQLite file.

The two models here are made for the tests. They are subclasses of the
real ``Base``, so they prove what it does, but they are kept in a schema of
their own (``Proof.metadata``), so the real schema never sees them.
"""

import sqlite3

import pytest
from sqlalchemy import (
    CheckConstraint,
    Engine,
    ForeignKey,
    Index,
    MetaData,
    UniqueConstraint,
    inspect,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base, broken_rules
from motosphere.db.work import unit_of_work


class Proof(Base):
    """Models of the tests' own: the rules of ``Base``, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofOwner(Proof):
    __tablename__ = "proof_owner"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


class ProofItem(Proof):
    __tablename__ = "proof_item"
    # A model that says something of its table itself. The table is strict all the same.
    __table_args__ = (
        UniqueConstraint("owner_id", "number"),
        CheckConstraint("number > 0", name="number_positive"),
        Index(None, "place", "length"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("proof_owner.id"))
    number: Mapped[int]
    place: Mapped[str] = mapped_column(index=True)
    length: Mapped[float | None]
    picture: Mapped[bytes | None]


@pytest.fixture
def made(store: Engine) -> Engine:
    """The store, with the two tables of the tests made in it."""
    with store.begin() as connection:
        Proof.metadata.create_all(connection)
    return store


def test_the_tables_of_models_are_strict_in_the_store(made: Engine) -> None:
    with made.connect() as connection:
        strict = {
            name: bool(is_strict)
            for _, name, kind, _, _, is_strict in connection.exec_driver_sql("PRAGMA table_list")
            if kind == "table" and name.startswith("proof_")
        }

    assert strict == {"proof_owner": True, "proof_item": True}


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO proof_owner (name) VALUES (x'00ff')",
        "INSERT INTO proof_item (owner_id, number, place) VALUES (1, 'seven', 'a place')",
        "INSERT INTO proof_item (owner_id, number, place, length) VALUES (1, 7, 'a place', 'long')",
        "INSERT INTO proof_item (owner_id, number, place, picture) VALUES (1, 7, 'a place', 1.5)",
    ],
    ids=[
        "bytes as text",
        "text as a whole number",
        "text as a number",
        "a number as bytes",
    ],
)
def test_a_value_that_is_not_of_its_columns_type_is_refused(made: Engine, statement: str) -> None:
    with made.begin() as connection:
        connection.exec_driver_sql("INSERT INTO proof_owner (id, name) VALUES (1, 'the owner')")

    with pytest.raises(IntegrityError) as refused, made.begin() as connection:
        connection.exec_driver_sql(statement)

    assert isinstance(refused.value.orig, sqlite3.IntegrityError)
    assert "cannot store" in str(refused.value.orig)


def test_python_types_become_the_column_types_a_strict_table_takes(made: Engine) -> None:
    with made.connect() as connection:
        types = {
            name: declared
            for _, name, declared, _, _, _ in connection.exec_driver_sql(
                "PRAGMA table_info(proof_item)"
            )
        }

    assert types == {
        "id": "INTEGER",
        "owner_id": "INTEGER",
        "number": "INTEGER",
        "place": "TEXT",
        "length": "REAL",
        "picture": "BLOB",
    }


def test_values_come_back_as_they_were_stored(made: Engine) -> None:
    with unit_of_work(made) as work:
        owner = ProofOwner(name="the owner")
        work.add(owner)
        work.flush()
        work.add(
            ProofItem(
                owner_id=owner.id, number=7, place="a place", length=1.75, picture=b"\x00\xff"
            )
        )

    with unit_of_work(made) as work:
        item = work.scalars(select(ProofItem)).one()

    assert (item.number, item.place, item.length, item.picture) == (7, "a place", 1.75, b"\x00\xff")
    assert type(item.length) is float
    assert type(item.picture) is bytes


def test_constraints_and_indexes_are_named_by_the_rule_in_the_store(made: Engine) -> None:
    schema = inspect(made)

    assert schema.get_pk_constraint("proof_owner")["name"] == "pk_proof_owner"
    assert [found["name"] for found in schema.get_unique_constraints("proof_owner")] == [
        "uq_proof_owner_name"
    ]
    assert schema.get_pk_constraint("proof_item")["name"] == "pk_proof_item"
    assert [found["name"] for found in schema.get_foreign_keys("proof_item")] == [
        "fk_proof_item_owner_id_proof_owner"
    ]
    assert [found["name"] for found in schema.get_unique_constraints("proof_item")] == [
        "uq_proof_item_owner_id_number"
    ]
    assert [found["name"] for found in schema.get_check_constraints("proof_item")] == [
        "ck_proof_item_number_positive"
    ]
    assert sorted(str(found["name"]) for found in schema.get_indexes("proof_item")) == [
        "ix_proof_item_place",
        "ix_proof_item_place_length",
    ]


def test_the_models_of_these_tests_break_no_rule() -> None:
    assert broken_rules(Proof.metadata) == []
