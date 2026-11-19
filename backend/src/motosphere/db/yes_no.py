"""Yes or no in the data store.

A strict table has no type for yes and no, so the store keeps them as a
whole number: 1 for yes and 0 for no. A model says of such a column that it
is a ``bool``:

    active: Mapped[bool]

The column is then INTEGER with a check in its table, and SQLite itself
refuses a row with any other number in it, whoever writes it. To Python the
column is ``True`` or ``False``, and only these two are stored: a number, a
word and every other value is refused, also one that Python would take for
true or false, because "no" is a word Python takes for true.

A column that may be without a value says ``Mapped[bool | None]``: it holds
no value, yes or no. No value means that it is not known, which is not no.
"""

from typing import override

from sqlalchemy import CheckConstraint, Dialect, Integer, column
from sqlalchemy.types import TypeDecorator

from motosphere.db.checks import WithItsCheck

__all__ = ["YesOrNo", "from_number", "to_number", "yes_or_no"]


def to_number(value: bool) -> int:
    """Say yes or no as the number that is stored. What is neither is refused."""
    if not isinstance(value, bool):
        raise TypeError(
            f"Only yes or no (True or False) is stored as yes or no, not "
            f"{type(value).__name__}: {value!r}."
        )
    return int(value)


def from_number(number: int) -> bool:
    """Read the number that is stored for yes or no. Any other is refused, not taken for yes."""
    # Not Python's True, and not 1.0: both are equal to 1 and neither is the number.
    if type(number) is int and number in (0, 1):
        return number == 1
    raise ValueError(f"The store holds what is neither yes (1) nor no (0): {number!r}.")


class YesOrNo(WithItsCheck, TypeDecorator[bool]):
    """The type of a column that is yes or no. In the table it is INTEGER."""

    impl = Integer
    cache_ok = True
    refuses = "a number other than 0 and 1"
    given_by = "yes_or_no"

    def check_for(self, name: str) -> CheckConstraint:
        """Give the check of :func:`yes_or_no` for the column called ``name``."""
        return yes_or_no(name)

    @override
    def process_bind_param(self, value: bool | None, dialect: Dialect) -> int | None:
        """Turn yes or no into the number that is stored."""
        return None if value is None else to_number(value)

    @override
    def process_result_value(self, value: int | None, dialect: Dialect) -> bool | None:
        """Turn the number that is stored into yes or no."""
        return None if value is None else from_number(value)


def yes_or_no(name: str) -> CheckConstraint:
    """Give the check that refuses every number but 0 and 1 in the column called ``name``.

    The check is called ``<name>_yes_or_no``, which the naming rule makes
    ``ck_<table>_<name>_yes_or_no`` once the check is given to a table. It
    belongs to no table until then. A column without a value passes it, as
    it passes every check.
    """
    return CheckConstraint(column(name).in_((0, 1)), name=f"{name}_yes_or_no")
