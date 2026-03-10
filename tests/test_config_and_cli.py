from __future__ import annotations

import subprocess
import sys

from market_risk_platform.config.settings import load_config


def test_config_contracts(configured_env) -> None:
    load_config.cache_clear()
    config = load_config()
    contracts = config.dataset_contracts()
    assert contracts["gold_asset_risk_features"].table_name == "finance.gold.asset_risk_features"
    assert contracts["silver_daily_returns"].local_path.name == "daily_returns.csv"


def test_cli_smoke(configured_env) -> None:
    load_config.cache_clear()
    env = {"PYTHONPATH": "src"}
    result = subprocess.run(
        [sys.executable, "-m", "market_risk_platform.main", "streaming"],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    assert "scaffolded" in result.stdout
