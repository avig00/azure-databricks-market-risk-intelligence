from __future__ import annotations

import joblib

from market_risk_platform.config.settings import load_config
from market_risk_platform.data_ingestion.market_data_pipeline import ingest_market_data
from market_risk_platform.features.feature_store_builder import build_features
from market_risk_platform.lakehouse.gold_feature_builder import build_gold_outputs
from market_risk_platform.lakehouse.silver_transformations import transform_to_silver
from market_risk_platform.ml.train_risk_classifier import train_classifier
from market_risk_platform.ml.train_volatility_model import train_model
from market_risk_platform.simulation.portfolio_simulator import SimulationInput, run_simulation


def test_full_pipeline(configured_env) -> None:
    load_config.cache_clear()
    config = load_config()
    ingestion = ingest_market_data(config)
    assert ingestion.record_counts["stock_prices"] > 0
    silver = transform_to_silver(config)
    gold = build_gold_outputs(config)
    features = build_features(config)
    volatility_model = train_model(config)
    classifier = train_classifier(config)
    result = run_simulation(SimulationInput(assets=["AAPL", "XOM", "TLT"], weights=[0.4, 0.3, 0.3]), config)
    assert silver.daily_returns_path.endswith("daily_returns.parquet")
    assert gold.asset_risk_features_path.endswith("asset_risk_features.parquet")
    assert features.portfolio_features_path.endswith("portfolio_training_features.parquet")
    assert volatility_model.primary_metric >= 0
    assert 0 <= classifier.primary_metric <= 1
    assert result.predicted_risk_tier in {"LOW", "MEDIUM", "HIGH"}
    assert joblib.load(config.artifact_root / "volatility_model.joblib")
    assert joblib.load(config.artifact_root / "risk_classifier.joblib")
