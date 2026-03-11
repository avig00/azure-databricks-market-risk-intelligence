from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.deploy_bundle import build_deploy_command


def test_build_deploy_command_includes_bundle_vars() -> None:
    command = build_deploy_command("dev", {"environment": "dev", "catalog_name": "finance_dev"})
    assert command[:4] == ["databricks", "bundle", "deploy", "-t"]
    assert "--var=environment=dev" in command
    assert "--var=catalog_name=finance_dev" in command


def test_deploy_bundle_script_renders_command_from_json(tmp_path: Path) -> None:
    payload = {
        "bundle_environment_name": {"value": "dev"},
        "bundle_catalog_name": {"value": "finance_dev"},
    }
    output_path = tmp_path / "terraform-output.json"
    output_path.write_text(json.dumps(payload))
    result = subprocess.run(
        [
            sys.executable,
            "scripts/deploy_bundle.py",
            "--target",
            "dev",
            "--terraform-output-json",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "databricks bundle deploy -t dev" in result.stdout
    assert "--var=environment=dev" in result.stdout

