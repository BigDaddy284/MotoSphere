"""The manifest: the first published file the site reads.

It says which version of the data format the files use, when they were
generated and by which MotoSphere version, and how many records of each kind
they contain.
"""

import json
from datetime import UTC, datetime
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    StringConstraints,
    field_validator,
)

import motosphere

__all__ = [
    "FORMAT_VERSION",
    "MANIFEST_FILE_NAME",
    "Manifest",
    "build_manifest",
    "manifest_to_json",
]

# Raised whenever a published file changes in a way an older site could not read.
FORMAT_VERSION = 1
MANIFEST_FILE_NAME = "manifest.json"

type RecordKind = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z_]*$")]


class Manifest(BaseModel):
    """The content of ``manifest.json``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    format_version: int = Field(ge=1, description="The version of the published data format.")
    generated_at: AwareDatetime = Field(
        description="When the published files were generated, in UTC, to the second."
    )
    application_version: str = Field(
        min_length=1, description="The MotoSphere version that generated the files."
    )
    counts: dict[RecordKind, NonNegativeInt] = Field(
        description="The number of published records of each kind, for example tracks."
    )

    @field_validator("generated_at", mode="after")
    @classmethod
    def _to_utc_seconds(cls, value: datetime) -> datetime:
        return value.astimezone(UTC).replace(microsecond=0)


def build_manifest(now: datetime) -> Manifest:
    """Return the manifest for the data as it is at ``now``.

    ``now`` must carry its time zone. Nothing is published yet, so there are no
    record counts.
    """
    return Manifest(
        format_version=FORMAT_VERSION,
        generated_at=now,
        application_version=motosphere.__version__,
        counts={},
    )


def manifest_to_json(manifest: Manifest) -> str:
    """Return the manifest as JSON text.

    The same manifest always gives the same text: keys are sorted, the layout
    is fixed and the text ends with one line break.
    """
    return (
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n"
    )
