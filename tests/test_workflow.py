"""Checks for this repository's own workflow (config.yaml at the root); keep these when adapting the template."""
from pathlib import Path

import pytest

from biomero_template import BilayersSpec, validate_config
from biomero_template.cli import _biomero_check
from conftest import ROOT, biomero_argv

WORKFLOW_CONFIG = ROOT / "config.yaml"


def test_config_is_valid_bilayers():
    assert validate_config(WORKFLOW_CONFIG) == []


def test_biomero_can_parse_config():
    assert _biomero_check(str(WORKFLOW_CONFIG)) == []


def test_biomero_arguments_resolve(tmp_path):
    """The arguments BIOMERO generates (with defaults) are accepted and produce a tool command."""
    spec = BilayersSpec(WORKFLOW_CONFIG)
    values = spec.parse_args(biomero_argv(WORKFLOW_CONFIG, tmp_path))
    for name in spec.folder_inputs():
        if not spec.inputs[name].get("optional"):
            assert values.inputs[name] == tmp_path / "data" / "in"
    assert any(Path(path) == tmp_path / "data" / "out" for path in [*values.outputs.values(), *(
        values.params[name] for name in spec.output_dir_params())] if path), "no output folder set to data/out"
    if spec.cli_command and "wrapper.py" not in spec.cli_command:
        assert spec.command(values)


@pytest.mark.skipif(not (ROOT / "Dockerfile").exists(), reason="no Dockerfile")
def test_dockerfile_uses_wrapper_entrypoint():
    entrypoint = [line for line in (ROOT / "Dockerfile").read_text().splitlines() if line.startswith("ENTRYPOINT")]
    assert entrypoint and "wrapper.py" in entrypoint[-1], "BIOMERO runs the image entrypoint; it must be wrapper.py"


def _dockerfile_instructions(keyword: str) -> list[str]:
    lines = (ROOT / "Dockerfile").read_text().splitlines()
    return [line.split(None, 1)[1] for line in lines if line.upper().startswith(keyword + " ")]


@pytest.mark.skipif(not (ROOT / "Dockerfile").exists(), reason="no Dockerfile")
def test_base_images_are_fully_qualified():
    """Podman does not resolve short names like python:3.12-slim by default."""
    for base in _dockerfile_instructions("FROM"):
        image = base.split()[0]
        if image.startswith("$") or image.lower() == "scratch":
            continue
        assert "." in image.split("/")[0], f"use a fully qualified image (e.g. docker.io/library/...): {image}"


@pytest.mark.skipif(not (ROOT / "Dockerfile").exists(), reason="no Dockerfile")
def test_no_user_switch():
    """Singularity runs as the calling user and rootless Podman maps root to it; a USER breaks mounted folders."""
    assert _dockerfile_instructions("USER") == []
