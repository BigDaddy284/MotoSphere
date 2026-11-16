"""Health check endpoint that tells callers whether the API is up."""

from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

import motosphere

__all__ = ["APP_NAME", "HealthResponse", "router"]

APP_NAME = "MotoSphere"


class HealthResponse(BaseModel):
    """The answer to a health check."""

    status: Literal["ok"] = Field(
        description='Always "ok" when the API is running and able to answer.',
    )
    name: str = Field(description="The name of the application.")
    version: str = Field(description="The version of the application that is running.")


router = APIRouter(tags=["Health"])


@router.get("/api/health", summary="Health check", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    """Report that the API is running, with the application's name and version."""
    # The frontend polls this to show whether the backend is reachable, so a
    # cached answer would be a wrong answer.
    response.headers["Cache-Control"] = "no-store"
    return HealthResponse(status="ok", name=APP_NAME, version=motosphere.__version__)
