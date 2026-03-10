from __future__ import annotations

from market_risk_platform.config.settings import load_config
from market_risk_platform.dashboard.app import build_dashboard_payload
from market_risk_platform.data_ingestion.market_data_pipeline import ingest_market_data
from market_risk_platform.features.feature_store_builder import build_features
from market_risk_platform.lakehouse.gold_feature_builder import build_gold_outputs
from market_risk_platform.lakehouse.silver_transformations import transform_to_silver
from market_risk_platform.ml.train_risk_classifier import train_classifier
from market_risk_platform.ml.train_volatility_model import train_model
from market_risk_platform.streaming.market_signal_detection import detect_streaming_signals


def test_dashboard_payload_and_streaming(configured_env) -> None:
    load_config.cache_clear()
    config = load_config()
    ingest_market_data(config)
    transform_to_silver(config)
    build_gold_outputs(config)
    build_features(config)
    train_model(config)
    train_classifier(config)
    payload = build_dashboard_payload()
    assert payload["portfolio_overview"]
    assert payload["market_stress"]
    assert payload["asset_risk_explorer"]
    assert payload["portfolio_simulation"]["predicted_risk_tier"] in {"LOW", "MEDIUM", "HIGH"}
    status = detect_streaming_signals()
    assert status.status == "scaffolded"

