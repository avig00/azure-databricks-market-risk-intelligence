#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


OUTPUT_MAPPING = {
    "bundle_environment_name": "environment",
    "bundle_catalog_name": "catalog_name",
    "bundle_adls_prefix": "adls_prefix",
    "bundle_secret_scope": "databricks_secret_scope",
    "bundle_fred_api_key_secret_key": "fred_api_key_secret_key",
    "bundle_notification_email": "notification_email",
}


def _load_terraform_output(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid terraform output JSON in {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Terraform output JSON must be a JSON object")
    return payload


def build_bundle_vars(terraform_output: dict[str, Any]) -> dict[str, str]:
    bundle_vars: dict[str, str] = {}
    for terraform_key, bundle_key in OUTPUT_MAPPING.items():
        value = terraform_output.get(terraform_key, {}).get("value")
        if value is None:
            continue
        bundle_vars[bundle_key] = str(value)
    return bundle_vars


def render_cli_args(bundle_vars: dict[str, str]) -> str:
    return " ".join(f'--var="{key}={value}"' for key, value in bundle_vars.items() if value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Databricks bundle vars from terraform output JSON")
    parser.add_argument("terraform_output_json", help="Path to a file created by `terraform output -json`")
    parser.add_argument("--format", choices=["cli", "json"], default="cli")
    args = parser.parse_args()

    terraform_output = _load_terraform_output(Path(args.terraform_output_json))
    bundle_vars = build_bundle_vars(terraform_output)
    if args.format == "json":
        print(json.dumps(bundle_vars, indent=2, sort_keys=True))
        return
    print(render_cli_args(bundle_vars))


if __name__ == "__main__":
    main()
