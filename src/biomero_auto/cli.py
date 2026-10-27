"""``biomero-auto`` command: check and convert bilayers specs while building a container."""
from __future__ import annotations

import argparse
import json
import logging
import shlex
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

from . import biaflows
from .spec import BilayersSpec, SpecError, validate_config


def _read_mapping(source: str) -> dict:
    """Read a JSON/YAML mapping from a path or URL (GitHub blob URLs are fetched raw)."""
    if source.startswith(("http://", "https://")):
        url = source.replace("://github.com/", "://raw.githubusercontent.com/").replace("/blob/", "/")
        with urllib.request.urlopen(url) as response:
            return yaml.safe_load(response.read().decode("utf-8"))
    return yaml.safe_load(Path(source).read_text(encoding="utf-8"))


def _write(data: dict, output: str | None, as_json: bool) -> None:
    text = json.dumps(data, indent=2) + "\n" if as_json else yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _biomero_check(config: str) -> list[str]:
    """Parse the config with BIOMERO's own bilayers adapter (needs the biomero package)."""
    from biomero.schema_parsers import WorkflowDescriptorParser

    try:
        WorkflowDescriptorParser.parse_descriptor(yaml.safe_load(Path(config).read_text(encoding="utf-8")))
    except Exception as error:  # noqa: BLE001 - report whatever BIOMERO rejects
        return [f"[BIOMERO] {error}"]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="biomero-auto", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate a bilayers config (bilayers-schema LinkML schema)")
    validate.add_argument("config")
    validate.add_argument("--biomero", action="store_true", help="also parse it with BIOMERO's bilayers adapter")

    for name, help_text in (("parse", "print the values resolved from ARGS as JSON"),
                            ("command", "print the tool command built from ARGS")):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("config")
        sub.add_argument("args", nargs=argparse.REMAINDER, help="container arguments (after --)")

    from_biaflows = commands.add_parser("from-biaflows", help="draft a bilayers config from a BIAFLOWS descriptor.json")
    from_biaflows.add_argument("descriptor", help="path or URL")
    from_biaflows.add_argument("-o", "--output")
    from_biaflows.add_argument("--cli-command", default="python /app/biaflows/wrapper.py",
                               help="command running the BIAFLOWS wrapper inside the container")
    from_biaflows.add_argument("--input-format", nargs="+", default=["tiff"])
    from_biaflows.add_argument("--output-format", nargs="+", default=["tiff"])

    check = commands.add_parser("container-test", help="build the image with Docker and run it on a sample job like BIOMERO")
    check.add_argument("config", nargs="?", default="config.yaml")
    check.add_argument("--runtime", choices=("docker", "podman"), default="docker")
    check.add_argument("--sample", help="folder of input images (default: a generated OME-Zarr)")
    check.add_argument("--param", action="append", default=[], metavar="NAME=VALUE", help="parameter value (repeatable)")
    check.add_argument("--no-build", action="store_true", help="use the already built image")
    check.add_argument("--keep", help="job folder to use and keep (default: a new temporary folder)")

    to_biaflows = commands.add_parser("to-biaflows", help="write a BIAFLOWS descriptor.json for a bilayers config")
    to_biaflows.add_argument("config")
    to_biaflows.add_argument("-o", "--output")

    args = parser.parse_args(argv)
    try:
        return _run(args)
    except SpecError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def _run(args) -> int:
    if args.command == "validate":
        issues = validate_config(args.config) + (_biomero_check(args.config) if args.biomero else [])
        print("\n".join(issues) if issues else "No issues found")
        return int(bool(issues))
    if args.command in ("parse", "command"):
        spec = BilayersSpec(args.config)
        values = spec.parse_args(args.args[1:] if args.args[:1] == ["--"] else args.args)
        if args.command == "parse":
            print(json.dumps(values.as_dict(), indent=2, default=str))
        else:
            print(shlex.join(spec.command(values)))
        return 0
    if args.command == "from-biaflows":
        config = biaflows.bilayers_from_descriptor(_read_mapping(args.descriptor), cli_command=args.cli_command,
                                                   input_formats=args.input_format, output_formats=args.output_format)
        _write(config, args.output, as_json=False)
        return 0
    if args.command == "container-test":
        from .container_test import container_test

        logging.basicConfig(level=logging.INFO, format="%(message)s")
        params = dict(param.split("=", 1) for param in args.param)
        try:
            container_test(Path(args.config), runtime=args.runtime, sample=args.sample, params=params,
                           build=not args.no_build, keep=args.keep)
        except (RuntimeError, subprocess.CalledProcessError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        print("Container test passed")
        return 0
    _write(biaflows.descriptor_from_bilayers(BilayersSpec(args.config)), args.output, as_json=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
