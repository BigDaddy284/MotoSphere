"""Tests of yes or no in the store, with a table made in a real SQLite file.

The model here is made for the tests. It is a subclass of the real
``Base``, so it proves what a model gets when it says that a column is yes
or no, but it is kept in a schema of its own (``Proof.metadata``), so the
real schema never sees it.
"""

from typing import Any

import pytest
from sqlalchemy import Engine, MetaData, func, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Mapped, mapped_column

from motosphere.db.base import Base, broken_rules
from motosphere.db.work import unit_of_work
from motosphere.db.yes_no import YesOrNo

A_TIME = "2026-11-19T08:00:00.000000+00:00"
REFUSED = "CHECK constraint failed: ck_proof_gate_{}_yes_or_no"
NOT_YES_OR_NO = "Only yes or no \\(True or False\\) is stored as yes or no"
# A row written with plain SQL. Its first three "?" are open, lit and locked;
# the last two are its two times, which only the store's code sets.
PAST_THE_MODEL = (
    "INSERT INTO proof_gate (open, lit, locked, created_at, updated_at) VALUES (?, ?, ?, ?, ?)"
)


class Proof(Base):
    """A model of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofGate(Proof):
    __tablename__ = "proof_gate"

    open: Mapped[bool]
    # No value, yes or no.
    lit: Mapped[bool | None]
    # A model that says more of the column: the value it has when none is given.
    locked: Mapped[bool] = mapped_column(default=False)
    # A whole number that is not yes or no, as before.
    width: Mapped[int | None]


@pytest.fixture
def made(store: Engine) -> Engine:
    """The store, with the table of the tests made in it."""
    with store.begin() as connection:
        Proof.metadata.create_all(connection)
    return store


def stored(made: Engine) -> list[tuple[Any, ...]]:
    """What the file holds of every gate, with what kind of value it is, read without the model."""
    with made.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT open, typeof(open), lit, typeof(lit), locked, typeof(locked) "
            "FROM proof_gate ORDER BY id"
        ).all()
    return [tuple(row) for row in rows]


def test_yes_or_no_is_a_whole_number_in_a_strict_table(made: Engine) -> None:
    columns = ProofGate.__table__.c

    assert [column.name for column in columns if isinstance(column.type, YesOrNo)] == [
        "open",
        "lit",
        "locked",
    ]
    assert broken_rules(Proof.metadata) == []

    with made.connect() as connection:
        in_the_file = {
            name: (declared, bool(required))
            for _, name, declared, required, _, _ in connection.exec_driver_sql(
                "PRAGMA table_info(proof_gate)"
            )
        }

    assert in_the_file == {
        "id": ("INTEGER", True),
        "open": ("INTEGER", True),
        "lit": ("INTEGER", False),
        "locked": ("INTEGER", True),
        "width": ("INTEGER", False),
        "created_at": ("TEXT", True),
        "updated_at": ("TEXT", True),
    }


def test_the_file_has_a_check_named_by_the_rule_for_each_such_column_and_for_no_other(
    made: Engine,
) -> None:
    with made.connect() as connection:
        written = str(
            connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'proof_gate'"
            ).scalar_one()
        )

    assert [line.strip().rstrip(",") for line in written.splitlines() if "CHECK" in line] == [
        "CONSTRAINT ck_proof_gate_open_yes_or_no CHECK (open IN (0, 1))",
        "CONSTRAINT ck_proof_gate_lit_yes_or_no CHECK (lit IN (0, 1))",
        "CONSTRAINT ck_proof_gate_locked_yes_or_no CHECK (locked IN (0, 1))",
    ]


def test_yes_and_no_are_stored_as_1_and_0_and_come_back_as_true_and_false(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofGate(open=True, lit=False, locked=True))
        work.add(ProofGate(open=False, lit=True, locked=False))

    assert stored(made) == [
        (1, "integer", 0, "integer", 1, "integer"),
        (0, "integer", 1, "integer", 0, "integer"),
    ]
    with unit_of_work(made) as work:
        first, second = work.scalars(select(ProofGate).order_by(ProofGate.id)).all()
        assert (first.open, first.lit, first.locked) == (True, False, True)
        assert (second.open, second.lit, second.locked) == (False, True, False)
        assert first.open is True
        assert second.open is False


def test_a_column_that_may_be_without_a_value_holds_none_yes_or_no(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all([ProofGate(open=True, lit=lit) for lit in (None, True, False)])

    assert [(lit, kind) for _, _, lit, kind, _, _ in stored(made)] == [
        (None, "null"),
        (1, "integer"),
        (0, "integer"),
    ]
    with unit_of_work(made) as work:
        gates = work.scalars(select(ProofGate).order_by(ProofGate.id)).all()
        assert [gate.lit for gate in gates] == [None, True, False]


def test_a_column_given_no_value_gets_the_one_its_model_says(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofGate(open=True))

    assert stored(made) == [(1, "integer", None, "null", 0, "integer")]
    with unit_of_work(made) as work:
        assert work.scalars(select(ProofGate)).one().locked is False


def test_a_change_from_yes_to_no_is_stored(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofGate(open=True, lit=True))
    with unit_of_work(made) as work:
        gate = work.scalars(select(ProofGate)).one()
        gate.open = False
        gate.lit = None

    assert stored(made) == [(0, "integer", None, "null", 0, "integer")]


@pytest.mark.parametrize(
    "value",
    [1, 0, "no", "", 1.0],
    ids=["the number 1", "the number 0", "the word no", "empty text", "a number with a fraction"],
)
def test_what_is_neither_true_nor_false_is_refused_and_nothing_is_stored(
    made: Engine, value: Any
) -> None:
    gates = [ProofGate(open=True), ProofGate(open=value)]

    with pytest.raises(StatementError, match=NOT_YES_OR_NO) as refused, unit_of_work(made) as work:
        work.add_all(gates)

    assert isinstance(refused.value.orig, TypeError)
    assert stored(made) == []


@pytest.mark.parametrize(
    ("values", "refused_by"),
    [
        ((2, None, 0), "open"),
        ((-1, None, 0), "open"),
        (("2", None, 0), "open"),
        ((1, 2, 0), "lit"),
        ((1, None, 2), "locked"),
    ],
    ids=[
        "two",
        "less than nothing",
        "two as text",
        "in a column that may be without a value",
        "in a column with a value of its own",
    ],
)
def test_another_number_written_past_the_model_is_refused(
    made: Engine, values: tuple[Any, ...], refused_by: str
) -> None:
    with made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (1, None, 0, A_TIME, A_TIME))

    refusal = REFUSED.format(refused_by)
    with pytest.raises(IntegrityError, match=refusal), made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (*values, A_TIME, A_TIME))

    assert stored(made) == [(1, "integer", None, "null", 0, "integer")]


@pytest.mark.parametrize(
    ("written", "number"),
    [("1", 1), (1.0, 1), ("0", 0), (0.0, 0)],
    ids=["1 as text", "1 with a fraction of nothing", "0 as text", "0 with a fraction of nothing"],
)
def test_what_sqlite_takes_for_one_of_the_two_numbers_is_stored_as_the_number(
    made: Engine, written: Any, number: int
) -> None:
    with made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (written, written, written, A_TIME, A_TIME))

    assert stored(made) == [(number, "integer", number, "integer", number, "integer")]
    with unit_of_work(made) as work:
        assert work.scalars(select(ProofGate)).one().open is (number == 1)


@pytest.mark.parametrize(
    ("written", "refusal"),
    [
        ("yes", "cannot store TEXT value in INTEGER column proof_gate.open"),
        (1.5, "cannot store REAL value in INTEGER column proof_gate.open"),
    ],
    ids=["a word", "a number with a fraction"],
)
def test_what_cannot_be_a_whole_number_is_refused_because_the_table_is_strict(
    made: Engine, written: Any, refusal: str
) -> None:
    with pytest.raises(IntegrityError, match=refusal), made.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (written, None, 0, A_TIME, A_TIME))

    assert stored(made) == []


def test_a_change_to_another_number_is_refused_and_the_row_stays_as_it_was(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofGate(open=True, lit=False))

    with pytest.raises(IntegrityError, match=REFUSED.format("open")), made.begin() as connection:
        connection.exec_driver_sql("UPDATE proof_gate SET open = 2")
    with pytest.raises(IntegrityError, match=REFUSED.format("lit")), made.begin() as connection:
        connection.exec_driver_sql("UPDATE proof_gate SET lit = -1")

    assert stored(made) == [(1, "integer", 0, "integer", 0, "integer")]


def test_rows_are_found_by_yes_by_no_and_by_no_value(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add_all(
            [
                ProofGate(open=True, lit=None),
                ProofGate(open=False, lit=True),
                ProofGate(open=True, lit=False),
            ]
        )

    def found(*asked: Any) -> list[int]:
        with unit_of_work(made) as work:
            return list(work.scalars(select(ProofGate.id).where(*asked).order_by(ProofGate.id)))

    assert found(ProofGate.open.is_(True)) == [1, 3]
    assert found(ProofGate.open.is_(False)) == [2]
    assert found(ProofGate.open) == [1, 3]
    assert found(~ProofGate.open) == [2]
    assert found(ProofGate.open.in_([False])) == [2]
    assert found(ProofGate.lit.is_(None)) == [1]
    assert found(ProofGate.lit.is_(True)) == [2]
    assert found(ProofGate.lit.is_(False)) == [3]
    with unit_of_work(made) as work:
        assert work.scalar(select(func.count()).where(ProofGate.open.is_(True))) == 2


def test_a_question_with_what_is_neither_true_nor_false_is_refused(made: Engine) -> None:
    with pytest.raises(StatementError, match=NOT_YES_OR_NO) as refused, unit_of_work(made) as work:
        work.scalars(select(ProofGate).where(ProofGate.open == 1))

    assert isinstance(refused.value.orig, TypeError)


def test_a_sum_over_such_a_column_is_read_as_yes_or_no_or_refused(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofGate(open=True))
        # Not the number of rows that are yes: the sum, read through the type.
        assert work.scalar(select(func.sum(ProofGate.open))) is True
        work.add(ProofGate(open=True))

    refusal = "The store holds what is neither yes \\(1\\) nor no \\(0\\): 2\\."
    with pytest.raises(ValueError, match=refusal), unit_of_work(made) as work:
        work.scalar(select(func.sum(ProofGate.open)))


def test_a_whole_number_that_is_not_yes_or_no_is_stored_as_before(made: Engine) -> None:
    with unit_of_work(made) as work:
        work.add(ProofGate(open=True, width=2))

    with made.connect() as connection:
        assert connection.exec_driver_sql("SELECT width FROM proof_gate").scalar_one() == 2
