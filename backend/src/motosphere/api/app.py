"""Factory that builds the MotoSphere FastAPI application."""

from fastapi import FastAPI

import motosphere
from motosphere.api.health import router as health_router
from motosphere.core.settings import Settings, get_settings

__all__ = ["API_TITLE", "create_app"]

API_TITLE = "MotoSphere API"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return a new, independent MotoSphere API application.

    Uses ``settings`` when given, otherwise the settings from :func:`get_settings`.
    Everything the API serves lives under ``/api/``, so the frontend can own
    every other path.
    """
    app = FastAPI(
        title=API_TITLE,
        version=motosphere.__version__,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings if settings is not None else get_settings()
    app.include_router(health_router)
    return app
