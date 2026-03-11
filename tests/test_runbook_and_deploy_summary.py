from __future__ import annotations

from pathlib import Path


def test_runbook_exists_with_verification_commands() -> None:
    text = Path("docs/runbook.md").read_text()
    assert "health-check" in text
    assert "verify-deployment" in text
    assert "dashboard-summary" in text
    assert "Promotion order" in text


def test_deploy_workflow_has_summary_and_rollback_note() -> None:
    text = Path(".github/workflows/deploy.yml").read_text()
    assert "rollback_note" in text
    assert "run_post_deploy_smoke" in text
    assert "GITHUB_STEP_SUMMARY" in text
