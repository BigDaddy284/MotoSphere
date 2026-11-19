"""Tests of a column type that brings a check, with a table made in a real SQLite file.

The type and the model here are made for the tests. The model is a
subclass of the real ``Base``, so it proves what ``Base`` gives a column
of any type that brings a check, but it is kept in a schema of its own
(``Proof.metadata``), so the real schema never sees it.
"""

import pytest
from sqlalchemy import CheckConstraint, Engine, MetaData, Text, column, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base, broken_rules
from motosphere.db.checks import WithItsCheck
from motosphere.db.texts import NotEmpty
from motosphere.db.work import unit_of_work


class ShoutedText(WithItsCheck, Text):
    """A column type of the tests' own that brings a check: text in large letters only."""

    refuses = "small letters"
    given_by = "shouted"

    def check_for(self, name: str) -> CheckConstraint:
        return CheckConstraint(column(name) == func.upper(column(name)), name=f"{name}_shouted")


class Proof(Base):
    """A model of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofSign(Proof):
    __tablename__ = "proof_sign"

    code: Mapped[str] = mapped_column(ShoutedText)
    # A column of the type the store has had so far, between two of the new one.
    name: Mapped[NotEmpty]
    # No value, or text in large letters.
    tag: Mapped[str | None] = mapped_column(ShoutedText)


@pytest.fixture
def made(store: Engine) -> Engine:
    """The store, with the table of the tests made in it."""
    with store.begin() as connection:
        Proof.metadata.create_all(connection)
    return store


def codes(made: Engine) -> list[tuple[str, str | None]]:
    """The code and the tag of every sign the file holds, read without the model."""
    with made.connect() as connection:
        rows = connection.exec_driver_sql("SELECT code, tag FROM proof_sign ORDER BY id").all()
    return [(str(code), None if tag is None else str(tag)) for code, tag in rows]


def test_base_gives_the_table_the_check_of_every_column_whose_type_brings_one(
    made: Engine,
) -> None:
    assert broken_rules(Proof.metadata) == []

    with made.connect() as connection:
        written = str(
            connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'proof_sign'"
            ).scalar_one()
        )

    checks = [line.strip().rstrip(",") for line in written.splitlines() if "CHECK" in line]
    assert [check.split(" CHECK ")[0] for check in checks] == [
        "CONSTRAINT ck_proof_sign_code_shouted",
        "CONSTRAINT ck_proof_sign_name_not_empty",
        "CONSTRAINT ck_proof_sign_tag_shouted",
    ]
    assert checks[0] == "CONSTRAINT ck_proof_sign_code_shouted CHECK (code = upper(code))"
    assert checks[2] == "CONSTRAINT ck_proof_sign_tag_shouted CHECK (tag = upper(tag))"


def test_sqlite_takes_what_the_check_of_the_type_allows(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofSign(code="STOP", name="Stop", tag=None))
        work.add(ProofSign(code="GO", name="Go", tag="GREEN"))

    assert codes(made) == [("STOP", None), ("GO", "GREEN")]


@pytest.mark.parametrize(
    ("code", "tag", "refused_by"),
    [("Stop", None, "code"), ("STOP", "red", "tag")],
    ids=["in a column that must have a value", "in a column that may be without one"],
)
def test_sqlite_refuses_what_the_check_of_the_type_refuses(
    made: Engine, code: str, tag: str | None, refused_by: str
) -> None:
    refusal = f"CHECK constraint failed: ck_proof_sign_{refused_by}_shouted"
    signs = [
        ProofSign(code="GO", name="Go", tag=None),
        ProofSign(code=code, name="Stop", tag=tag),
    ]

    with pytest.raises(IntegrityError, match=refusal), unit_of_work(made) as work:
        work.add_all(signs)

    assert codes(made) == []
