# biomero-template-container

Template for [BIOMERO](https://github.com/NL-BioImaging/biomero) workflow containers described by a
[bilayers](https://github.com/bilayer-containers/bilayers) spec, with OME-Zarr ⇄ TIFF conversion
([biomero-converter](https://github.com/NL-BioImaging/biomero-converter)) and Workflow RO-Crate
metadata ([fair-metadata-integration](https://github.com/NL-BioImaging/fair-metadata-integration)).

To create a container for a workflow, ask Claude Code in this repository, e.g.
*"create a BIOMERO container for https://github.com/Neubias-WG5/W_NucleiSegmentation-CellProfiler"*;
the [`create-biomero-container`](.claude/skills/create-biomero-container/SKILL.md) skill does the rest.

## Layout

| File | Role |
|---|---|
| `config.yaml` | bilayers spec of the workflow; BIOMERO reads it from the repository at a release tag |
| `wrapper.py` | image entrypoint; picks the tool hook |
| `Dockerfile` | tool layer + BIOMERO layer |
| `src/biomero_template/` | generic glue (below) |

The example workflow is bilayers' classical segmentation, which reads TIFF: OME-Zarr from BIOMERO is
converted to TIFF for it and its TIFF labels back to OME-Zarr.

## What runs in the container

`wrapper.py` → `biomero_template.run`:

1. **Reads the spec and the arguments** (`spec.py`): BIOMERO style (`--<cli_tag>="value"`, folders
   set to `data/in`/`data/out`), bilayers-interface style, BIAFLOWS style
   (`--infolder --outfolder --gtfolder --local -nmc --<name> value`), and/or `--params params.yaml`
   (`{name: value}`). Precedence: spec defaults < params file < command line. Gives a
   `RunValues` with `.as_dict()` for use inside the container.
2. **Converts inputs** to a `format` the spec accepts (`conversion.py`).
3. **Runs the tool**: by default `exec_function.cli_command` with the arguments built by bilayers'
   own `generate_cli_command`; or `biaflows_tool(...)` for an existing BIAFLOWS wrapper
   (`biaflows.py`); or any `tool(ctx)` function.
4. **Converts outputs** back (`auto`: OME-Zarr in → OME-Zarr out).
5. **Writes `ro-crate-metadata.json`** next to the outputs (`fair.py`).

Overrides via environment: `BIOMERO_CONVERT_INPUTS`, `BIOMERO_OUTPUT_FORMAT` (`auto|zarr|tiff|keep`),
`BIOMERO_ZARR_FORMAT`, `BIOMERO_RO_CRATE`, `BIOMERO_WORKDIR`.

## Running the image

Build and test with Docker; BIOMERO runs the same image with Singularity/Apptainer on Slurm:

```
docker build -t w_classical_segmentation .
docker run --rm -v ./job/data:/data w_classical_segmentation --folder=/data/in --save_dir=/data/out --threshold_method=li
```

`job/data/in` holds the images (OME-Zarr or TIFF), results land in `job/data/out`. Mounting the
whole `data` folder keeps the conversion staging folder on the host disk.

## Command line

```
biomero-template validate config.yaml [--biomero]     # bilayers LinkML schema (+ BIOMERO's parser)
biomero-template parse config.yaml -- <args>          # resolved values as JSON
biomero-template command config.yaml -- <args>        # the tool command line
biomero-template from-biaflows <descriptor.json|URL>  # draft config.yaml for a BIAFLOWS workflow
biomero-template to-biaflows config.yaml              # descriptor.json for BIAFLOWS-only deployments
biomero-template container-test [config.yaml]         # build the image with Docker and run it like BIOMERO
```

`container-test` options: `--sample <folder>` (default: generated OME-Zarr), `--param name=value`,
`--runtime podman` (default `docker`), `--no-build`, `--keep <job folder>`.

## Development

```
pip install -e ".[test]"
pytest
```

`tests/conftest.py::biomero_argv` builds container arguments with BIOMERO's own code, so the tests
check the actual BIOMERO contract.

bilayers' `parse.py` and `cli_generator.py` are vendored unmodified in
`src/biomero_template/_vendor/bilayers` (BSD-3-Clause): bilayers is not on PyPI and its repository
cannot be checked out on Windows. Update them with `python scripts/sync_vendor.py`.

## Release

Tag `vX.Y.Z` equal to `docker_image.tag` in `config.yaml`; `.github/workflows/docker-image.yml`
pushes the image (secrets `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`). Register in BIOMERO's
`slurm-config.ini`:

```ini
[WORKFLOWS]
<key>=<key>
<key>_repo=https://github.com/<org>/<repo>/tree/vX.Y.Z
<key>_image=<docker org>/<docker name>
```
