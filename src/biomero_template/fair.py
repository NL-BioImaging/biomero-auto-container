"""Workflow RO-Crate for a run, using fair-metadata-integration."""
from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

CRATE_METADATA = "ro-crate-metadata.json"


def write_ro_crate(config_path: Path, input_path: Path, output_paths: Sequence[Path], dest_folder: Path) -> Path:
    """Write ``ro-crate-metadata.json`` (and the bilayers config it describes) into ``dest_folder``.

    create_ro_crate copies all described data into the crate; to avoid duplicating
    images in the folder BIOMERO imports, the crate is built in a temporary folder
    and only its metadata and the config are kept, next to the outputs they describe.
    """
    from fair_metadata_integration import create_ro_crate

    with tempfile.TemporaryDirectory(dir=dest_folder.parent, prefix=".ro-crate-") as tmp:
        create_ro_crate(dest_path=tmp, workflow_schema_filename=str(config_path), input_path=str(input_path),
                        output_paths=[str(path) for path in output_paths])
        dest_folder.mkdir(parents=True, exist_ok=True)
        for name in (CRATE_METADATA, config_path.name):
            shutil.copy2(Path(tmp) / name, dest_folder / name)
    logger.info("RO-Crate metadata written to %s", dest_folder / CRATE_METADATA)
    return dest_folder / CRATE_METADATA
