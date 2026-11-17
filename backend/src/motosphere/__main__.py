"""Start the MotoSphere API server: ``python -m motosphere``.

Settings, including the host and port to listen on, come only from the
environment and the optional ``.env`` file (see :mod:`motosphere.core.settings`).
Stop the server with Ctrl+C.
"""

import sys

import uvicorn
from pydantic import ValidationError

from motosphere.api.app import create_app
from motosphere.core.logging_config import configure_logging
from motosphere.core.settings import get_settings

__all__ = ["main"]

EXIT_OK = 0
EXIT_CONFIGURATION_ERROR = 2


def _describe_configuration_error(error: ValidationError) -> str:
    """Return one line naming every invalid setting and what is wrong with it."""
    problems = "; ".join(
        f"{'.'.join(str(part) for part in problem['loc'])}: {problem['msg']}"
        for problem in error.errors()
    )
    return f"Configuration error: {problems}"


def main() -> int:
    """Load the settings, set up logging and run the API server until it stops.

    Returns the process exit code: 0 after a normal shut-down, 2 when the
    settings are invalid.
    """
    try:
        settings = get_settings()
    except ValidationError as error:
        sys.stderr.write(_describe_configuration_error(error) + "\n")
        return EXIT_CONFIGURATION_ERROR

    configure_logging(settings)
    # log_config=None keeps uvicorn from installing its own log handlers, so
    # its messages go through the MotoSphere handler and format.
    uvicorn.run(
        create_app(settings),
        host=settings.api_host,
        port=settings.api_port,
        log_config=None,
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
