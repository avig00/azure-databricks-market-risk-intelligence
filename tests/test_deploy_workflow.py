from __future__ import annotations

from pathlib import Path


def test_deploy_workflow_exists_and_has_manual_controls() -> None:
    workflow = Path(".github/workflows/deploy.yml")
    text = workflow.read_text()
    assert "workflow_dispatch:" in text
    assert "apply_infra" in text
    assert "deploy_bundle" in text
    assert "run_post_deploy_smoke" in text
    assert "databricks bundle validate" in text
    assert "terraform -chdir=infra/terraform plan" in text
    assert "market-risk-terraform-output-${{ inputs.target }}" in text
    assert "Download Terraform output artifact" in text
    assert "market-risk-post-deploy-smoke" in text
