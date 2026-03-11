#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from render_bundle_vars import build_bundle_vars


def _load_terraform_output(terraform_dir: Path, env_file: str | None) -> dict:
    command = ["terraform", "-chdir=" + str(terraform_dir), "output", "-json"]
    if env_file:
        command.extend(["-var-file", env_file])
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def build_deploy_command(bundle_target: str, bundle_vars: dict[str, str]) -> list[str]:
    command = ["databricks", "bundle", "deploy", "-t", bundle_target]
    for key, value in bundle_vars.items():
        if value:
            command.append(f'--var={key}={value}')
    return command


def main() -> None:
    parser = argparse.ArgumentParser(description="Render or run Databricks bundle deploy from terraform outputs")
    parser.add_argument("--target", default="dev", choices=["dev", "prod"], help="Databricks bundle target")
    parser.add_argument(
        "--terraform-dir",
        default="infra/terraform",
        help="Terraform directory to read outputs from",
    )
    parser.add_argument(
        "--terraform-output-json",
        help="Optional pre-rendered terraform output JSON file; if omitted, terraform output -json is executed",
    )
    parser.add_argument(
        "--var-file",
        help="Optional terraform var-file to use when reading outputs directly from terraform",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run databricks bundle deploy. Without this flag the script prints the command only.",
    )
    args = parser.parse_args()

    if args.terraform_output_json:
        terraform_output = json.loads(Path(args.terraform_output_json).read_text())
    else:
        terraform_output = _load_terraform_output(Path(args.terraform_dir), args.var_file)

    bundle_vars = build_bundle_vars(terraform_output)
    command = build_deploy_command(args.target, bundle_vars)

    if not args.execute:
        print(" ".join(command))
        return

    if shutil.which("databricks") is None:
        raise SystemExit("The databricks CLI is not installed or not on PATH")

    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
