"""Logging configuration shared by the API and the collection worker.

:func:`configure_logging` sets up the root logger once at start-up: the level
comes from the settings, every line has the same predictable format with a UTC
timestamp, and line breaks inside messages are escaped so that untrusted text
(for example collected website content) cannot forge extra log lines.
"""

import logging
import time
from typing import override

from motosphere.core.settings import Settings

__all__ = ["DATE_FORMAT", "HANDLER_NAME", "LOG_FORMAT", "configure_logging"]

HANDLER_NAME = "motosphere"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class _SingleLineUTCFormatter(logging.Formatter):
    """Format records on one line with UTC timestamps and escaped line breaks.

    Only the formatted message line is escaped. Exception tracebacks are added
    after it by :meth:`logging.Formatter.format`, so they are still written in
    full over several lines.
    """

    converter = staticmethod(time.gmtime)

    @override
    def formatMessage(self, record: logging.LogRecord) -> str:
        line = super().formatMessage(record)
        return line.replace("\r", "\\r").replace("\n", "\\n")


def configure_logging(settings: Settings) -> None:
    """Install the MotoSphere log handler on the root logger.

    Calling this more than once replaces the previous MotoSphere handler instead
    of adding another one. Handlers installed by anything else are left alone.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        if handler.name == HANDLER_NAME:
            root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.set_name(HANDLER_NAME)
    handler.setFormatter(_SingleLineUTCFormatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(settings.log_level.value)
