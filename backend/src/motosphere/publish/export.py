"""The export step: write the published files into a directory."""

from datetime import datetime
from pathlib import Path

from motosphere.publish.files import write_text_atomically
from motosphere.publish.manifest import MANIFEST_FILE_NAME, build_manifest, manifest_to_json

__all__ = ["export_published_data"]


def export_published_data(directory: Path, now: datetime) -> Path:
    """Write the published files into ``directory`` and return the manifest's path.

    The directory is created if it does not exist. ``now`` is the generation
    time recorded in the manifest and must carry its time zone. Raises
    :class:`OSError` if the directory cannot be created or written to.
    """
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / MANIFEST_FILE_NAME
    write_text_atomically(manifest_path, manifest_to_json(build_manifest(now)))
    return manifest_path
