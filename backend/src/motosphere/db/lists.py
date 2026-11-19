"""A column whose value is one of a list.

Much of what the store holds is one of a few values the code knows: what
kind of source this is, how a run ended, how sure a record is. Such a list
is said once, as a ``StrEnum``, whose values are the texts that are stored:

    class Surface(StrEnum):
        SAND = "sand"
        HARD_PACK = "hard pack"

A model says of a column that its value is one of the list:

    surface: Mapped[Surface] = mapped_column(OneOf(Surface))

The column is then TEXT with a check in its table that names the values,
and SQLite itself refuses a row with any other text in it, whoever writes
it. To Python the column is a value of the list, and only such a value is
stored: text is refused, also text that is spelled like a value, and so is
a value of another list.

A column that may be without a value says ``Mapped[Surface | None]``: it
holds no value or a value of the list.
"""

from enum import StrEnum
from inspect import isclass
from typing import override

from sqlalchemy import CheckConstraint, Dialect, Text, column
from sqlalchemy.types import TypeDecorator

from motosphere.db.checks import WithItsCheck

__all__ = ["OneOf", "one_of"]


def _is_a_list(what: object) -> bool:
    """Say whether this is a list as the store means one: a ``StrEnum``, the class itself."""
    return isclass(what) and issubclass(what, StrEnum)


class OneOf(WithItsCheck, TypeDecorator[StrEnum]):
    """The type of a column whose value is one of a list. In the table it is TEXT."""

    impl = Text
    cache_ok = True
    refuses = "text that is not on its list"
    given_by = "one_of"

    def __init__(self, the_list: type[StrEnum]) -> None:
        """Take the list the column's values are of. What is not a list is refused.

        A list is a ``StrEnum`` with at least one value, none of them empty:
        a column says "not known" with no value, not with a value that is
        empty text.
        """
        if not _is_a_list(the_list):
            raise TypeError(f"A list is a StrEnum, with the texts that are stored: {the_list!r}.")
        if not list(the_list):
            raise ValueError(f"The list {the_list.__name__} has nothing on it.")
        for value in the_list:
            if not value.value.strip():
                raise ValueError(f"The list {the_list.__name__} has an empty value: {value!r}.")
        super().__init__()
        # SQLAlchemy tells two such types apart by this, which is why it has
        # the name it has above: a statement is kept for one list only.
        self.the_list = the_list

    def check_for(self, name: str) -> CheckConstraint:
        """Give the check of :func:`one_of` for the column called ``name`` and this list."""
        return one_of(name, self.the_list)

    @override
    def process_bind_param(self, value: StrEnum | None, dialect: Dialect) -> str | None:
        """Turn a value of the list into the text that is stored."""
        if value is None:
            return None
        if not isinstance(value, self.the_list):
            raise TypeError(
                f"Only a value of the list {self.the_list.__name__} is stored in this column, "
                f"not {type(value).__name__}: {value!r}."
            )
        return value.value

    @override
    def process_result_value(self, value: str | None, dialect: Dialect) -> StrEnum | None:
        """Turn the text that is stored into the value of the list."""
        if value is None:
            return None
        try:
            return self.the_list(value)
        except ValueError:
            raise ValueError(
                f"The store holds what is not on the list {self.the_list.__name__}: {value!r}."
            ) from None


def one_of(name: str, the_list: type[StrEnum]) -> CheckConstraint:
    """Give the check that refuses every text but the list's in the column called ``name``.

    The check names the texts in the order of the list. It is called
    ``<name>_one_of``, which the naming rule makes
    ``ck_<table>_<name>_one_of`` once the check is given to a table. It
    belongs to no table until then. A column without a value passes it, as
    it passes every check.
    """
    texts = [value.value for value in the_list]
    return CheckConstraint(column(name).in_(texts), name=f"{name}_one_of")
