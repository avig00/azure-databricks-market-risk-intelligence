from __future__ import annotations

from pathlib import Path


def test_environment_tfvars_exist() -> None:
    assert Path("infra/terraform/env/dev.tfvars").exists()
    assert Path("infra/terraform/env/prod.tfvars").exists()


def test_terraform_outputs_expose_bundle_alignment_values() -> None:
    outputs_text = Path("infra/terraform/outputs.tf").read_text()
    assert "bundle_catalog_name" in outputs_text
    assert "bundle_adls_prefix" in outputs_text
    assert "bundle_secret_scope" in outputs_text
    assert "bundle_notification_email" in outputs_text
