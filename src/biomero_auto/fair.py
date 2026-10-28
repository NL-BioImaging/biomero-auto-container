"""FAIRification of a run's output: Workflow RO-Crate (fair-metadata-integration) and packaging."""
from __future__ import annotations

import logging
import shutil
import zipfile
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

CRATE_METADATA = "ro-crate-metadata.json"


def write_ro_crate(config_path: Path, input_paths: Sequence[Path], output_paths: Sequence[Path], dest_folder: Path,
                   copy_inputs: bool = False) -> Path:
    """Make ``dest_folder`` the run's RO-Crate, with fair-metadata-integration.

    The crate holds ``ro-crate-metadata.json``, the bilayers config (the workflow, as
    mainEntity) and copies of each output, linked as FormalParameters. The inputs are
    described the same way, but referenced by their file URI unless ``copy_inputs``: BIOMERO
    imports every image found in the output folder, so a copy would re-import the input
    into OMERO.
    """
    from fair_metadata_integration import create_ro_crate

    create_ro_crate(dest_path=str(dest_folder), workflow_schema_filename=str(config_path),
                    input_paths=[str(path) for path in input_paths], output_paths=[str(path) for path in output_paths],
                    copy_inputs=copy_inputs, copy_outputs=True)
    logger.info("RO-Crate written to %s", dest_folder)
    return dest_folder / CRATE_METADATA


def zip_folder(folder: Path, name: str) -> Path:
    """Replace the contents of ``folder`` by ``<name>.zip`` holding them, stored without compression."""
    archive = folder.parent / f".{name}.zip.partial"
    entries = sorted(folder.rglob("*"))
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zip_file:
        for entry in entries:
            zip_file.write(entry, entry.relative_to(folder).as_posix())
    for entry in folder.iterdir():
        shutil.rmtree(entry) if entry.is_dir() and not entry.is_symlink() else entry.unlink()
    target = folder / f"{name}.zip"
    shutil.move(str(archive), str(target))
    logger.info("Output zipped (stored) to %s", target)
    return target
