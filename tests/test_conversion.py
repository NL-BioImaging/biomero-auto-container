import numpy as np
import pytest
import tifffile

from biomero_template.conversion import TIFF, ZARR, convert, normalize_formats, prepare_input
from conftest import add_omero_metadata


def test_normalize_formats():
    assert normalize_formats(["tiff", "ometiff", "png"]) == {TIFF}
    assert normalize_formats(["ome.zarr", "TIF"]) == {ZARR, TIFF}
    assert normalize_formats(None) == set()


def test_zarr_tiff_round_trip(tmp_path, tiff_folder):
    original = tifffile.imread(tiff_folder / "blobs.tif")
    [store] = convert(tiff_folder / "blobs.tif", tmp_path / "zarr", ZARR)
    add_omero_metadata(store)
    [tiff] = convert(store, tmp_path / "tiff_out", TIFF)
    np.testing.assert_array_equal(np.squeeze(tifffile.imread(tiff)), original)


@pytest.mark.xfail(strict=True, raises=Exception,
                   reason="biomero-converter 0.2.0: convert() indexes an empty window for OME-Zarr without omero metadata")
def test_zarr_without_omero_metadata_to_tiff(tmp_path, tiff_folder):
    [store] = convert(tiff_folder / "blobs.tif", tmp_path / "zarr", ZARR)
    convert(store, tmp_path / "tiff_out", TIFF)


def test_prepare_input_passes_accepted_formats_through(tiff_folder, tmp_path):
    assert prepare_input(tiff_folder, {TIFF}, tmp_path / "staging") == (tiff_folder, {TIFF})
    assert not (tmp_path / "staging").exists()


def test_prepare_input_converts_and_keeps_other_files(zarr_folder, tmp_path):
    (zarr_folder / "notes.txt").write_text("keep me")
    folder, found = prepare_input(zarr_folder, {TIFF}, tmp_path / "staging")
    assert found == {ZARR}
    assert sorted(path.name for path in folder.iterdir()) == ["blobs.ome.tiff", "notes.txt"]
