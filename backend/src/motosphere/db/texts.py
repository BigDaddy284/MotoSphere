"""Text that must not be empty.

Much of the store's text is names, and a name that is empty means nothing.
A model says of such a column that its text must not be empty:

    name: Mapped[NotEmpty]

The column is then TEXT with a check in its table, and SQLite itself
refuses a row whose text is empty, whoever writes it. Empty is text with no
characters, and text with nothing but white space: the characters Python's
``str.strip`` takes off, among them the space that cannot be broken, which
web pages are full of. Text that is not empty is stored as it was given,
with the white space it has around it.

A column that may be without a value says ``Mapped[NotEmpty | None]``: it
holds no value or text that is not empty, and never empty text.
"""

from typing import Annotated

from sqlalchemy import CheckConstraint, Text, column, func

from motosphere.db.checks import WithItsCheck

__all__ = ["WHITE_SPACE", "NotEmpty", "NotEmptyText", "not_empty"]

# The characters that are white space, each by its number in Unicode: the
# ones Python's str.isspace and str.strip know. They are written out, and
# not asked of Python, so that the check is the same text on every machine
# and with every version of Python. A test holds the list to Python's.
WHITE_SPACE = (
    *(9, 10, 11, 12, 13),  # tab, line feed, vertical tab, form feed, carriage return
    *(28, 29, 30, 31),  # the four separators of ASCII
    32,  # the space
    133,  # next line
    160,  # the space that cannot be broken
    5760,  # the Ogham space mark
    *(8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202),  # the spaces of print
    *(8232, 8233),  # the line and the paragraph separator
    8239,  # the narrow space that cannot be broken
    8287,  # the mathematical space
    12288,  # the wide space of Chinese, Japanese and Korean
)


class NotEmptyText(WithItsCheck, Text):
    """The column type of text that must not be empty. In the table it is TEXT."""

    refuses = "empty text"
    given_by = "not_empty"

    def check_for(self, name: str) -> CheckConstraint:
        """Give the check of :func:`not_empty` for the column called ``name``."""
        return not_empty(name)


# What a model says a column is: ``Mapped[NotEmpty]``. To Python and to the
# type check it is a ``str``.
NotEmpty = Annotated[str, NotEmptyText]


def not_empty(name: str) -> CheckConstraint:
    """Give the check that refuses empty text in the column called ``name``.

    The check is called ``<name>_not_empty``, which the naming rule makes
    ``ck_<table>_<name>_not_empty`` once the check is given to a table. It
    belongs to no table until then. A column without a value passes it, as
    it passes every check.
    """
    without_white_space = func.trim(column(name), func.char(*WHITE_SPACE))
    return CheckConstraint(without_white_space != "", name=f"{name}_not_empty")
