"""Tests for the backend logging configuration."""

import logging
import re
from collections.abc import Iterator

import pytest

from motosphere.core.logging_config import HANDLER_NAME, configure_logging
from motosphere.core.settings import LogLevel, Settings

LINE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z INFO \[motosphere\.test\] hello$")


def _named_handlers() -> list[logging.Handler]:
    return [handler for handler in logging.getLogger().handlers if handler.name == HANDLER_NAME]


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:
    """Undo every change configure_logging makes to the root logger."""
    root = logging.getLogger()
    original_level = root.level
    yield
    for handler in _named_handlers():
        root.removeHandler(handler)
    root.setLevel(original_level)


@pytest.mark.parametrize("level", list(LogLevel))
def test_root_level_follows_settings(level: LogLevel) -> None:
    configure_logging(Settings(log_level=level))

    assert logging.getLogger().level == logging.getLevelNamesMapping()[level.value]


def test_single_named_handler_is_installed() -> None:
    configure_logging(Settings())

    handlers = _named_handlers()
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.StreamHandler)


def test_configuring_twice_does_not_duplicate_handlers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(Settings())
    configure_logging(Settings())

    assert len(_named_handlers()) == 1
    logging.getLogger("motosphere.test").info("only once")
    assert capsys.readouterr().err.count("only once") == 1


def test_reconfiguring_changes_the_level(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(log_level=LogLevel.INFO))
    configure_logging(Settings(log_level=LogLevel.DEBUG))

    assert logging.getLogger().level == logging.DEBUG
    logging.getLogger("motosphere.test").debug("debug detail")
    assert "DEBUG [motosphere.test] debug detail" in capsys.readouterr().err


def test_other_handlers_are_preserved() -> None:
    root = logging.getLogger()
    other = logging.NullHandler()
    other.set_name("someone-else")
    root.addHandler(other)
    try:
        configure_logging(Settings())

        assert other in root.handlers
    finally:
        root.removeHandler(other)


def test_output_line_format(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(log_level=LogLevel.INFO))

    logging.getLogger("motosphere.test").info("hello")

    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 1
    assert LINE_PATTERN.fullmatch(lines[0])


def test_timestamp_is_utc() -> None:
    configure_logging(Settings())
    formatter = _named_handlers()[0].formatter
    assert formatter is not None
    record = logging.LogRecord(
        name="motosphere.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="epoch",
        args=None,
        exc_info=None,
    )
    record.created = 0.0

    assert formatter.format(record).startswith("1970-01-01T00:00:00Z ")


def test_messages_below_level_are_not_written(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(log_level=LogLevel.WARNING))
    logger = logging.getLogger("motosphere.test")

    logger.info("not written")
    assert capsys.readouterr().err == ""

    logger.warning("written")
    assert "WARNING [motosphere.test] written" in capsys.readouterr().err


def test_line_breaks_in_messages_are_escaped(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings())

    logging.getLogger("motosphere.test").info("first\nFAKE ERROR [admin] forged\r\nsecond")

    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 1
    assert "first\\nFAKE" in lines[0]
    assert "forged\\r\\nsecond" in lines[0]


def test_exception_traceback_is_written(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings())
    logger = logging.getLogger("motosphere.test")

    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("failed")

    output = capsys.readouterr().err
    lines = output.splitlines()
    assert any(line.endswith("ERROR [motosphere.test] failed") for line in lines)
    assert "Traceback (most recent call last)" in output
    assert "ValueError: boom" in output
