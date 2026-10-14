# How BIOMERO runs a bilayers workflow

From BIOMERO 2.x (`biomero/schema_parsers.py`, `biomero/slurm_client.py`), which reads the
repository's `config.yaml` directly at the configured tag (no `descriptor.json` needed):

- The config is mapped to biomero-schema by `BilayersSchemaAdapter`; types map as
  `checkbox`→boolean, `radio`/`dropdown`/`textbox`→string, `integer`/`float` as is,
  folder types (`image`, `file`, `array`, `measurement`, `executable`) are kept.
- The job runs `singularity run <image>.sif $INPARAMS $OUTPARAMS $PARAMS`, i.e. the image
  **entrypoint** gets:
  - `INPARAMS`: `<cli_tag>="$DATA_PATH/data/in"` for each non-optional folder-type input;
  - `OUTPARAMS`: `<cli_tag>="$DATA_PATH/data/out"` for each output with a `cli_tag`, and for
    each parameter with `output_dir_set: true`;
  - `PARAMS`: `<cli_tag>="<value>"` for every other parameter (trailing `=` stripped from the
    tag), booleans as `True`/`False`, values from the OMERO script UI (defaults from the spec).
- Images are exported from OMERO into `data/in` (OME-Zarr, or TIFF when converted by BIOMERO);
  everything in `data/out` is imported back. The job fails if `data/out` is empty.
- `docker_image.org/name` is the image; the version comes from the repository tag.
- `label` is shown as the parameter name in OMERO, `description` as help, `mode`/`section_id`
  are informational.

`tests/conftest.py::biomero_argv` reproduces these arguments with BIOMERO's own functions.

## What the wrapper does with them

`biomero_template.run`:

1. Parses the arguments against the spec (also bilayers-UI style and BIAFLOWS style, plus
   `--params params.yaml`); validates choices, numbers and required values.
2. For each `image` input whose files are not in the input's `format` list, converts them
   (biomero-converter) into a staging folder next to `data/out`.
3. Runs the tool on the staging/real folders.
4. Converts outputs (`BIOMERO_OUTPUT_FORMAT`: `auto` gives OME-Zarr back when OME-Zarr came
   in and the tool writes TIFF; `zarr`, `tiff`, `keep`).
5. Writes `ro-crate-metadata.json` and the config into `data/out` (fair-metadata-integration).

Environment overrides: `BIOMERO_CONVERT_INPUTS`, `BIOMERO_OUTPUT_FORMAT`, `BIOMERO_ZARR_FORMAT`,
`BIOMERO_RO_CRATE`, `BIOMERO_WORKDIR` (see `src/biomero_template/runner.py`).

## Running outside Slurm (Docker)

Only the entrypoint arguments matter. Mirror the BIOMERO job layout and mount the `data`
folder, so staging stays on the host disk:

```
docker run --rm -v <job>/data:/data <image> --<input tag>=/data/in --<output tag>=/data/out --<param>=<value>
docker run --rm -v <job>/data:/data <image> --params /data/params.yaml
```

Podman takes the same arguments (add `:Z` to the volume on SELinux hosts).

## Older deployments

BIOMERO versions that only read `descriptor.json` (BIAFLOWS, `cytomine-0.1`) call the
container with `--infolder --outfolder --gtfolder --local -nmc --<id> <value>`. The wrapper
accepts these too; generate the descriptor with `biomero-template to-biaflows config.yaml -o descriptor.json`.
