from __future__ import annotations

from market_risk_platform.config.settings import load_config
from market_risk_platform.operations.verification import (
    build_deployment_verification_report,
    build_runtime_contract_status,
)
from market_risk_platform.pipeline import run_full_pipeline


def test_runtime_contract_accepts_local_mode(configured_env) -> None:
    load_config.cache_clear()
    config = load_config()
    contract = build_runtime_contract_status(config)
    assert contract.supported is True
    assert contract.runtime_mode == "local"
    assert contract.storage_backend == "local"


def test_deployment_verification_report_checks_outputs(configured_env) -> None:
    load_config.cache_clear()
    config = load_config()
    run_full_pipeline()
    report = build_deployment_verification_report(config)
    assert report.checks_passed is True
    assert report.dashboard_summary_available is True
    assert report.latest_stage_successful is True
    assert report.verified_datasets["gold_asset_risk_features"]["rows"] > 0
    assert report.model_artifacts["volatility_model"] is True
