"""OME-Zarr <-> TIFF conversion around a workflow, using biomero-converter.

Inputs are converted when the images BIOMERO provides are in a format the spec's
input ``format`` list does not accept; outputs are converted back (by default to
OME-Zarr when the inputs were OME-Zarr and the tool does not write OME-Zarr itself).
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

ZARR, TIFF = "zarr", "tiff"
FORMAT_ALIASES = {
    "zarr": ZARR, "ome.zarr": ZARR, "omezarr": ZARR, "ome-zarr": ZARR, "ngff": ZARR,
    "tif": TIFF, "tiff": TIFF, "ometiff": TIFF, "ome.tiff": TIFF, "ome-tiff": TIFF, "ome.tif": TIFF,
}
# biomero-converter output_format values
CONVERTER_FORMATS = {TIFF: "ometiff", ZARR: "omezarr04"}
OUTPUT_POLICIES = ("auto", "zarr", "tiff", "keep")


def normalize_formats(formats: Iterable[str] | str | None) -> set[str]:
    """The zarr/tiff formats in a bilayers ``format`` list (other formats are ignored)."""
    if isinstance(formats, str):
        formats = [formats]
    return {FORMAT_ALIASES[entry.lower().lstrip(".")] for entry in formats or [] if entry.lower().lstrip(".") in FORMAT_ALIASES}


def image_format(path: Path) -> str | None:
    name = path.name.lower()
    if name.endswith(".zarr"):
        return ZARR
    if name.endswith((".tif", ".tiff")):
        return TIFF
    return None


def find_images(folder: Path) -> list[Path]:
    """Top-level OME-Zarr stores and TIFF files in a folder."""
    if not folder.is_dir():
        return []
    return sorted(entry for entry in folder.iterdir() if image_format(entry))


def convert(source: Path, dest_folder: Path, target: str, zarr_format: str | None = None) -> list[Path]:
    """Convert one image (file or zarr store) with biomero-converter; returns the written paths."""
    from biomero_converter.converter import convert as converter_convert

    dest_folder.mkdir(parents=True, exist_ok=True)
    output_format = zarr_format if target == ZARR and zarr_format else CONVERTER_FORMATS[target]
    logger.info("Converting %s -> %s (%s)", source, dest_folder, output_format)
    results = json.loads(converter_convert(str(source), str(dest_folder), output_format=output_format))
    return [Path(result["full_path"]) for result in results]


def link_or_copy(source: Path, dest: Path) -> None:
    try:
        os.symlink(source.resolve(), dest, target_is_directory=source.is_dir())
    except OSError:  # e.g. no symlink privilege on Windows
        if source.is_dir():
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)


def prepare_input(folder: Path, accepted: set[str], staging: Path, zarr_format: str | None = None) -> tuple[Path, set[str]]:
    """Return the folder the tool should read, and the image formats originally found.

    If images need converting, a staging folder is filled with the converted images
    plus links to (or copies of) everything else in ``folder``.
    """
    images = find_images(folder)
    found = {image_format(image) for image in images}
    if not accepted or found <= accepted:
        return folder, found
    targets = accepted & {ZARR, TIFF}
    target = TIFF if TIFF in targets else ZARR
    staging.mkdir(parents=True, exist_ok=True)
    for entry in sorted(folder.iterdir()):
        if entry in images and image_format(entry) not in accepted:
            convert(entry, staging, target, zarr_format)
        else:
            link_or_copy(entry, staging / entry.name)
    return staging, found


def output_target(policy: str, input_formats: set[str], output_formats: set[str]) -> str | None:
    """The format outputs are converted to, or None to leave them as the tool wrote them."""
    if policy not in OUTPUT_POLICIES:
        raise ValueError(f"output format policy must be one of {OUTPUT_POLICIES}, not {policy!r}")
    if policy == "keep":
        return None
    if policy in (ZARR, TIFF):
        return policy
    # auto: give OME-Zarr back when OME-Zarr came in and the tool does not write it
    return ZARR if ZARR in input_formats and ZARR not in output_formats else None


def finalize_output(tool_folder: Path, final_folder: Path, target: str, zarr_format: str | None = None) -> list[Path]:
    """Convert the tool's images to ``target`` into ``final_folder``; move everything else."""
    final_folder.mkdir(parents=True, exist_ok=True)
    written = []
    for entry in sorted(tool_folder.iterdir()):
        fmt = image_format(entry)
        if fmt is not None and fmt != target:
            written += convert(entry, final_folder, target, zarr_format)
        else:
            dest = final_folder / entry.name
            shutil.move(str(entry), str(dest))
            written.append(dest)
    return written
