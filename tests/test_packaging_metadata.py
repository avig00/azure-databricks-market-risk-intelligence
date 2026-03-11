from __future__ import annotations

import tomllib
from pathlib import Path


def test_pyproject_scripts_exist() -> None:
    pyproject = Path("pyproject.toml")
    data = tomllib.loads(pyproject.read_text())
    scripts = data["project"]["scripts"]
    assert "market-risk-run-all" in scripts
    assert "market-risk-dashboard-refresh" in scripts
    assert scripts["market-risk-simulate"] == "market_risk_platform.entrypoints:simulate_default"
    assert scripts["market-risk-verify-deployment"] == "market_risk_platform.entrypoints:verify_deployment"
