"""Run the MotoSphere command line: ``python -m motosphere <command>``.

See :mod:`motosphere.cli` for the commands.
"""

import sys

from motosphere.cli import main

if __name__ == "__main__":
    sys.exit(main())
