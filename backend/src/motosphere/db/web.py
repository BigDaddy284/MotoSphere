"""A web address.

A source has a website, and every record says at which address it was
found. A model says of such a column that it holds a web address:

    website: Mapped[WebAddress]

The column is then TEXT with a check in its table, and SQLite itself
refuses text that is not a web address, whoever writes the row. To the
check, a web address is text that

- begins with ``https://`` or ``http://``, in small or in large letters;
- goes on after that with the name of a site: with at least one character,
  which is not ``/``, ``?`` or ``#``, the three that end such a name;
- has no white space anywhere, by the store's own list of white space
  (:data:`motosphere.db.texts.WHITE_SPACE`);
- has no character with the number 0, after which SQLite would not look.

That is as far as a check in a table goes. It does not know whether there
is such a site, and it does not hold the rest of the address to the rules
an address has. An address is stored as it was given: nothing is put in
small letters and nothing is taken off.

A column that may be without a value says ``Mapped[WebAddress | None]``: it
holds no value or a web address, and never empty text.
"""

from typing import Annotated

from sqlalchemy import CheckConstraint, ColumnClause, Text, and_, column, func, literal, not_, or_

from motosphere.db.checks import WithItsCheck
from motosphere.db.texts import WHITE_SPACE

__all__ = ["WebAddress", "WebAddressText", "web_address"]

# How a web address begins, as SQLite's GLOB is told it: the letters of
# "https" or "http", each small or large, then "://", then one character
# that is none of the three in the brackets, then anything. GLOB tells
# small letters from large ones on every machine, whatever a connection
# has been told about LIKE.
_BEGINS_WITH_HTTPS = "[Hh][Tt][Tt][Pp][Ss]://[^/?#]*"
_BEGINS_WITH_HTTP = "[Hh][Tt][Tt][Pp]://[^/?#]*"


class WebAddressText(WithItsCheck, Text):
    """The column type of a web address. In the table it is TEXT."""

    refuses = "text that is not a web address"
    given_by = "web_address"

    def check_for(self, name: str) -> CheckConstraint:
        """Give the check of :func:`web_address` for the column called ``name``."""
        return web_address(name)


# What a model says a column is: ``Mapped[WebAddress]``. To Python and to
# the type check it is a ``str``.
WebAddress = Annotated[str, WebAddressText]


def web_address(name: str) -> CheckConstraint:
    """Give the check that refuses text that is not a web address in the column ``name``.

    The check is called ``<name>_web_address``, which the naming rule makes
    ``ck_<table>_<name>_web_address`` once the check is given to a table. It
    belongs to no table until then. A column without a value passes it, as
    it passes every check.
    """
    text: ColumnClause[str] = column(name)
    begins_as_one = or_(
        text.bool_op("GLOB")(_BEGINS_WITH_HTTPS),
        text.bool_op("GLOB")(_BEGINS_WITH_HTTP),
    )
    # The white space is written by its numbers, as in the check for empty
    # text, so that the check is the same text on every machine.
    has_white_space = text.bool_op("GLOB")(literal("*[") + func.char(*WHITE_SPACE) + literal("]*"))
    # GLOB reads text up to a character with the number 0 and no further,
    # so white space after one would go unseen.
    has_no_nought = func.instr(text, func.char(0)) == 0
    return CheckConstraint(
        and_(begins_as_one, not_(has_white_space), has_no_nought),
        name=f"{name}_web_address",
    )
