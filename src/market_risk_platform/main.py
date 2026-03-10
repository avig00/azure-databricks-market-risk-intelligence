from __future__ import annotations

import argparse

from market_risk_platform.data_ingestion.market_data_pipeline import run_ingestion
from market_risk_platform.features.feature_store_builder import build_feature_store
from market_risk_platform.lakehouse.gold_feature_builder import build_gold_layer
from market_risk_platform.lakehouse.silver_transformations import build_silver_layer
from market_risk_platform.ml.train_risk_classifier import train_risk_classifier
from market_risk_platform.ml.train_volatility_model import train_volatility_model
from market_risk_platform.simulation.portfolio_simulator import simulate_portfolio
from market_risk_platform.streaming.market_signal_detection import detect_streaming_signals


def main() -> None:
    parser = argparse.ArgumentParser(description="Run market risk platform stages")
    parser.add_argument(
        "stage",
        choices=[
            "ingest",
            "silver",
            "gold",
            "features",
            "train-volatility",
            "train-classifier",
            "simulate",
            "streaming",
        ],
    )
    args = parser.parse_args()
    handlers = {
        "ingest": run_ingestion,
        "silver": build_silver_layer,
        "gold": build_gold_layer,
        "features": build_feature_store,
        "train-volatility": train_volatility_model,
        "train-classifier": train_risk_classifier,
        "simulate": simulate_portfolio,
        "streaming": detect_streaming_signals,
    }
    print(handlers[args.stage]())


if __name__ == "__main__":
    main()

