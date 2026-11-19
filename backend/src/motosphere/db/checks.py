"""Column types that bring a check.

A strict table knows a handful of types, and much of what the store must
promise of a column is narrower than any of them: text that is not empty
is narrower than TEXT. Such a promise is kept by a check in the table, so
that SQLite itself refuses the row, whoever writes it.

A column type that is a subclass of :class:`WithItsCheck`, beside its
SQLAlchemy type, brings the check for its column. ``Base`` gives that
check to the table of every model that has a column of such a type, and
``broken_rules`` names a column of such a type whose table is without it.
A new type of this kind therefore needs no change to either.
"""

from typing import ClassVar

from sqlalchemy import CheckConstraint

__all__ = ["WithItsCheck"]


class WithItsCheck:
    """What a column type is a subclass of, beside its SQLAlchemy type, when it brings a check."""

    # What the check refuses, as the words of a sentence: "empty text".
    refuses: ClassVar[str]
    # The name of the function that gives the check, for whoever must give
    # it to a table by hand: "not_empty".
    given_by: ClassVar[str]

    def check_for(self, name: str) -> CheckConstraint:
        """Give the check for the column called ``name``.

        The check has the last part of its name, which the naming rule
        completes once the check is given to a table, and belongs to no
        table until then.
        """
        raise NotImplementedError
