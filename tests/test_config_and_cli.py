from __future__ import annotations

import os
import subprocess
import sys

from market_risk_platform.config.settings import load_config


def test_config_contracts(configured_env) -> None:
    load_config.cache_clear()
    config = load_config()
    contracts = config.dataset_contracts()
    assert config.storage_backend == "local"
    assert config.local_storage_format == "parquet"
    assert contracts["gold_asset_risk_features"].table_name == "finance.gold.asset_risk_features"
    assert contracts["silver_daily_returns"].local_path.name == "daily_returns.parquet"
    assert contracts["silver_daily_returns"].storage_format == "parquet"


def test_cli_smoke(configured_env) -> None:
    load_config.cache_clear()
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    bootstrap = subprocess.run(
        [sys.executable, "-m", "market_risk_platform.main", "run-all"],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    assert "PipelineRunResult" in bootstrap.stdout
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "market_risk_platform.main",
            "simulate",
            "--assets",
            "AAPL,XOM,TLT",
            "--weights",
            "0.4,0.3,0.3",
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    assert "predicted_risk_tier" in result.stdout
