from __future__ import annotations

from pathlib import Path


def test_ci_workflow_exists_and_covers_core_checks() -> None:
    workflow = Path(".github/workflows/ci.yml")
    text = workflow.read_text()
    assert "python -m pytest -q" in text
    assert "terraform fmt -check -recursive infra/terraform" in text
    assert "python -m build" in text
    assert "scripts/deploy_bundle.py" in text

