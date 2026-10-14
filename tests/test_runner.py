import json

import pytest
import tifffile

from biomero_template import BilayersSpec, run
from biomero_template.conversion import find_images, output_target
from conftest import biomero_argv


@pytest.fixture
def spec(config_path, python_cli_command):
    spec = BilayersSpec(config_path)
    spec.parsed["exec_function"]["cli_command"] = python_cli_command
    return spec


def test_zarr_in_zarr_out_with_ro_crate(spec, config_path, zarr_folder):
    """BIOMERO gives OME-Zarr; the TIFF tool runs on converted input; OME-Zarr labels come back."""
    data_path = zarr_folder.parents[1]
    argv = biomero_argv(config_path, data_path, threshold_method="otsu", min_diameter=1, max_diameter=50)
    assert run(argv, spec=spec) == 0
    out = data_path / "data" / "out"
    assert [path.name for path in find_images(out)] == ["blobs_output.ome.zarr"]
    crate = json.loads((out / "ro-crate-metadata.json").read_text())
    ids = {entity["@id"] for entity in crate["@graph"]}
    assert {config_path.name, "blobs_output.ome.zarr/", "in/"} <= ids
    assert (out / config_path.name).exists()
    assert not list(data_path.glob("data/.biomero-work-*"))  # staging removed


def test_tiff_in_tiff_out(spec, config_path, tmp_path, tiff_folder):
    data_path = tmp_path / "job"
    (data_path / "data").mkdir(parents=True)
    tiff_folder.rename(data_path / "data" / "in")
    argv = biomero_argv(config_path, data_path, min_diameter=1, max_diameter=50)
    assert run(argv, spec=spec, ro_crate=False) == 0
    out = data_path / "data" / "out"
    labels = tifffile.imread(out / "blobs_output.tiff")
    assert labels.max() == 2


def test_output_format_override(spec, config_path, tmp_path, tiff_folder, monkeypatch):
    data_path = tmp_path / "job"
    (data_path / "data").mkdir(parents=True)
    tiff_folder.rename(data_path / "data" / "in")
    monkeypatch.setenv("BIOMERO_OUTPUT_FORMAT", "zarr")
    argv = biomero_argv(config_path, data_path, min_diameter=1, max_diameter=50)
    assert run(argv, spec=spec, ro_crate=False) == 0
    assert [path.name for path in find_images(data_path / "data" / "out")] == ["blobs_output.ome.zarr"]


def test_tool_failure_returns_nonzero(spec, config_path, tmp_path):
    def failing_tool(ctx):
        raise RuntimeError("boom")
    assert run(["--folder", str(tmp_path), "--save_dir", str(tmp_path / "out")], spec=spec, tool=failing_tool) == 1


def test_tool_function_gets_context(spec, tmp_path, tiff_folder):
    seen = {}

    def tool(ctx):
        seen.update(params=dict(ctx.params), inputs=dict(ctx.inputs), command=ctx.command())
        (ctx.outputs["segmented_images"] / "x.txt").write_text("x")

    out = tmp_path / "out"
    assert run(["--folder", str(tiff_folder), "--save_dir", str(out)], spec=spec, tool=tool, ro_crate=False) == 0
    assert seen["inputs"] == {"input_images": tiff_folder}
    assert seen["command"][seen["command"].index("--save_dir") + 1] == str(out)
    assert (out / "x.txt").exists()


@pytest.mark.parametrize("policy, inputs, outputs, expected", [
    ("auto", {"zarr"}, {"tiff"}, "zarr"),
    ("auto", {"tiff"}, {"tiff"}, None),
    ("auto", {"zarr"}, {"zarr"}, None),
    ("keep", {"zarr"}, {"tiff"}, None),
    ("tiff", {"zarr"}, {"zarr"}, "tiff"),
])
def test_output_target(policy, inputs, outputs, expected):
    assert output_target(policy, inputs, outputs) == expected
