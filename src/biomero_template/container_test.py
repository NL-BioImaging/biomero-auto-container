"""Build the workflow image and run it on a sample job the way BIOMERO would (Docker; Podman optional)."""
from __future__ import annotations

import logging
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Sequence

import yaml

from .contract import biomero_argv, write_sample_input
from .fair import CRATE_METADATA

logger = logging.getLogger(__name__)

RUNTIMES = ("docker", "podman")
CONTAINER_DATA = PurePosixPath("/")  # BIOMERO's $DATA_PATH inside the container: /data/in, /data/out


def detect_runtime(runtime: str = "docker") -> str:
    """Check the container engine (Docker by default) responds."""
    if runtime not in RUNTIMES:
        raise ValueError(f"runtime must be one of {RUNTIMES}")
    if shutil.which(runtime) and subprocess.run([runtime, "info"], capture_output=True).returncode == 0:
        return runtime
    raise RuntimeError(f"{runtime} is not running; start Docker Desktop (or pass the runtime you use)")


def image_name(config: Path) -> tuple[str, str]:
    """``(org/name:tag, platform)`` from the config's docker_image."""
    docker = yaml.safe_load(config.read_text())["docker_image"]
    return f"{docker['org']}/{docker['name']}:{docker['tag']}", docker.get("platform", "linux/amd64")


def build_command(runtime: str, context: Path, image: str, platform: str) -> list[str]:
    return [runtime, "build", "--platform", platform, "-t", image, str(context)]


def run_command(runtime: str, image: str, platform: str, data_folder: Path, args: Sequence[str]) -> list[str]:
    volume = f"{data_folder.resolve()}:/data" + (":Z" if runtime == "podman" else "")
    return [runtime, "run", "--rm", "--platform", platform, "-v", volume, image, *args]


def container_test(config: Path, *, context: Path | None = None, runtime: str = "docker",
                   sample: Path | None = None, params: dict | None = None, build: bool = True,
                   keep: Path | None = None) -> list[Path]:
    """Build the image, run it on a BIOMERO-style job and check the results; returns the outputs."""
    config = Path(config)
    context = Path(context) if context else config.parent
    runtime = detect_runtime(runtime)
    image, platform = image_name(config)
    if build:
        _run(build_command(runtime, context, image, platform))
    job = Path(keep) if keep else Path(tempfile.mkdtemp(prefix="biomero-job-"))
    data = job / "data"
    if (data / "in").exists():
        shutil.rmtree(data / "in")
    if sample:
        shutil.copytree(sample, data / "in")
    else:
        write_sample_input(data / "in")
    (data / "out").mkdir(parents=True, exist_ok=True)
    args = biomero_argv(config, CONTAINER_DATA, **(params or {}))
    _run(run_command(runtime, image, platform, data, args))
    outputs = sorted((data / "out").iterdir())
    if not outputs:
        raise RuntimeError(f"The workflow produced no files in {data / 'out'} (BIOMERO fails such jobs)")
    if not (data / "out" / CRATE_METADATA).exists():
        logger.warning("No %s in the output folder", CRATE_METADATA)
    logger.info("Outputs in %s: %s", data / "out", [path.name for path in outputs])
    return outputs


def _run(argv: Sequence[str]) -> None:
    logger.info("$ %s", shlex.join(argv))
    subprocess.run(argv, check=True)
