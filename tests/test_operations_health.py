from __future__ import annotations

from market_risk_platform.config.settings import load_config
from market_risk_platform.operations.health import build_health_report
from market_risk_platform.pipeline import run_full_pipeline


def test_health_report_tracks_freshness_and_latest_stage(configured_env) -> None:
    load_config.cache_clear()
    config = load_config()
    run_full_pipeline()
    report = build_health_report(config)
    assert report.runtime_mode == "local"
    assert report.storage_backend == "local"
    assert report.dataset_freshness["gold_asset_risk_features"] is not None
    assert report.latest_successful_stage is not None
    assert report.latest_model_artifacts["volatility_model"] is not None
