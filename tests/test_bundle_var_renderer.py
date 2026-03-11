from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.render_bundle_vars import _load_terraform_output, build_bundle_vars, render_cli_args


def test_build_bundle_vars_maps_expected_outputs() -> None:
    terraform_output = {
        "bundle_environment_name": {"value": "dev"},
        "bundle_catalog_name": {"value": "finance_dev"},
        "bundle_adls_prefix": {"value": "lakehouse/dev"},
        "bundle_secret_scope": {"value": "market-risk-scope-dev"},
        "bundle_fred_api_key_secret_key": {"value": "fred-api-key"},
        "bundle_notification_email": {"value": "risk-alerts-dev@example.com"},
    }
    bundle_vars = build_bundle_vars(terraform_output)
    assert bundle_vars["environment"] == "dev"
    assert bundle_vars["catalog_name"] == "finance_dev"
    assert bundle_vars["databricks_secret_scope"] == "market-risk-scope-dev"


def test_render_cli_args_outputs_databricks_var_flags() -> None:
    rendered = render_cli_args({"environment": "prod", "catalog_name": "finance_prod"})
    assert '--var="environment=prod"' in rendered
    assert '--var="catalog_name=finance_prod"' in rendered


def test_script_outputs_json(tmp_path: Path) -> None:
    json_path = tmp_path / "terraform-output.json"
    json_path.write_text(
        json.dumps(
            {
                "bundle_environment_name": {"value": "dev"},
                "bundle_catalog_name": {"value": "finance_dev"},
            }
        )
    )
    result = subprocess.run(
        [sys.executable, "scripts/render_bundle_vars.py", str(json_path), "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == {"catalog_name": "finance_dev", "environment": "dev"}


def test_load_terraform_output_rejects_invalid_json(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("")
    with pytest.raises(ValueError, match="Invalid terraform output JSON"):
        _load_terraform_output(invalid_path)
