"""The MotoSphere command line: ``python -m motosphere <command>``.

Every job of the data pipeline is a command here, so the same commands work
on the owner's computer and in scheduled runs. :func:`main` is the single
entry point.
"""

from motosphere.cli.app import main

__all__ = ["main"]
