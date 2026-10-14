import shutil
import subprocess
from pathlib import Path

import pytest

from biomero_template import container_test as ct
from biomero_template.conversion import ZARR, find_images, image_format
from conftest import ROOT

WORKFLOW_CONFIG = ROOT / "config.yaml"


def test_image_name_from_config():
    image, platform = ct.image_name(WORKFLOW_CONFIG)
    assert image.count("/") == 1 and ":" in image
    assert platform.startswith("linux/")


def test_run_command_mounts_the_job_data_folder(tmp_path):
    docker = ct.run_command("docker", "org/name:v1", "linux/amd64", tmp_path, ["--folder=/data/in"])
    assert docker[:6] == ["docker", "run", "--rm", "--platform", "linux/amd64", "-v"]
    assert docker[6] == f"{tmp_path.resolve()}:/data"
    assert docker[7:] == ["org/name:v1", "--folder=/data/in"]
    podman = ct.run_command("podman", "org/name:v1", "linux/amd64", tmp_path, [])
    assert podman[6].endswith(":/data:Z")  # SELinux relabel


def test_biomero_arguments_use_container_paths():
    args = ct.biomero_argv(WORKFLOW_CONFIG, ct.CONTAINER_DATA)
    assert any(arg.endswith("=/data/in") for arg in args)
    assert any(arg.endswith("=/data/out") for arg in args)


def test_sample_input_is_ome_zarr(tmp_path):
    [store] = ct.write_sample_input(tmp_path / "in")
    assert image_format(store) == ZARR and find_images(tmp_path / "in") == [store]


def test_no_engine_is_reported(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="docker is not running"):
        ct.detect_runtime()


def _engine():
    try:
        return ct.detect_runtime()
    except RuntimeError:
        return None


@pytest.mark.container
@pytest.mark.skipif(_engine() is None, reason="Docker is not running")
def test_build_and_run_like_biomero(tmp_path):
    outputs = ct.container_test(WORKFLOW_CONFIG, keep=tmp_path / "job")
    assert outputs, "no outputs"
