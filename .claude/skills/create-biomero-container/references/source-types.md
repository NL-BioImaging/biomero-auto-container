# Source types

How to get from a source URL to `config.yaml` and the tool hook. Mixed sources exist; pick
the closest and combine.

## Existing bilayers workflow (`config.yaml` with `docker_image`, `exec_function`)

Reuse its `config.yaml`; check folder inputs/outputs against the BIOMERO contract (an
output folder BIOMERO can set), fix types the schema rejects (`biomero-auto validate`).
If its image entrypoint is already a BIOMERO-aware wrapper, it may not need this template.

## BIAFLOWS / NEUBIAS workflow (`descriptor.json` with `schema-version: cytomine-0.1`, `wrapper.py`)

- Draft: `biomero-auto from-biaflows <descriptor URL or path> -o config.yaml`, then delete
  `descriptor.json` (BIOMERO would otherwise pick it before `config.yaml`).
  (`--input-format`/`--output-format` from what the wrapper reads/writes). Then fill in
  citations, license, image flags (`depth`, `timepoints`, ...), output `subtype`, labels.
- Keep the original wrapper and its pipeline/macros unchanged in `/app/biaflows/`; install
  its own dependencies (BIAFLOWS utilities, Cytomine client, tool) as in its Dockerfile.
- Hook: `biaflows_tool("<its python> /app/biaflows/wrapper.py")`. Parameter ids stay the
  descriptor ids. If the wrapper needs Python < 3.12, give `biomero_auto` its own venv.

## Command-line tool (a CLI with flags for input/output folders)

- Parameters from its `--help` / argparse / click definitions; `cli_tag` = its flags.
- An input folder flag → `image` input; output folder flag → output with `cli_tag` or an
  `output_dir_set` parameter. Tools that take single files rather than folders need a
  `tool(ctx)` that loops over `ctx.inputs[...]` and calls the CLI per file.
- Hook: default (`run(spec=CONFIG)`).

## Python package / library / notebook

- Prefer an existing CLI entry point of the package. Otherwise write a minimal
  `tool(ctx)` in `wrapper.py` calling the package's public API with `ctx.params`; read and
  write images with the formats you declared (the wrapper converts around them).
- Parameters: the function's documented arguments that a user would tune.

## Pipeline/macro for a GUI application run headless (e.g. CellProfiler, Fiji/ImageJ, QuPath, ilastik)

- The application is the tool; the pipeline/macro/project file is part of the workflow repo.
- Parameters: the settings the source exposes (or that its README says to tune). Map them
  into the pipeline in `tool(ctx)` using the application's own mechanism where it has one
  (command-line overrides, macro arguments, project parameters); edit the file only if there
  is no such mechanism, and keep that edit minimal and covered by a test.
- Install a pinned application version; mind its Python/Java requirements.

## Container image only

Inspect the image's documentation and entrypoint for its CLI; write `config.yaml` for that
CLI and build `FROM` that image, adding the BIOMERO layer.
