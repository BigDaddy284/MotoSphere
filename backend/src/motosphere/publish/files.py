"""Writing published files safely."""

import contextlib
import os
import secrets
from pathlib import Path

__all__ = ["write_text_atomically"]


def write_text_atomically(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` as UTF-8 so that a reader never sees half a file.

    The text goes to a temporary file in the same directory, which then takes
    the place of ``path`` in one step. If anything fails, the temporary file is
    removed and whatever was at ``path`` before is left untouched. Line breaks
    are written exactly as given, on every operating system.
    """
    temporary = path.with_name(f"{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()
        raise
