from __future__ import annotations

import argparse
from dataclasses import asdict

from market_risk_platform.dashboard.app import build_dashboard_payload, summarize_dashboard
from market_risk_platform.operations.health import build_health_report
from market_risk_platform.operations.verification import verification_report_dict
from market_risk_platform.data_ingestion.market_data_pipeline import run_ingestion
from market_risk_platform.features.feature_store_builder import build_feature_store
from market_risk_platform.lakehouse.gold_feature_builder import build_gold_layer
from market_risk_platform.lakehouse.silver_transformations import build_silver_layer
from market_risk_platform.ml.train_risk_classifier import train_risk_classifier
from market_risk_platform.ml.train_volatility_model import train_volatility_model
from market_risk_platform.pipeline import run_full_pipeline
from market_risk_platform.simulation.portfolio_simulator import simulate_portfolio
from market_risk_platform.streaming.market_signal_detection import detect_streaming_signals


def main() -> None:
    parser = argparse.ArgumentParser(description="Run market risk platform stages")
    subparsers = parser.add_subparsers(dest="stage", required=True)

    for stage in [
        "ingest",
        "silver",
        "gold",
        "features",
        "train-volatility",
        "train-classifier",
        "streaming",
        "run-all",
        "dashboard-summary",
        "health-check",
        "verify-deployment",
    ]:
        subparsers.add_parser(stage)

    simulate_parser = subparsers.add_parser("simulate")
    simulate_parser.add_argument("--assets", default="AAPL,XOM,TLT")
    simulate_parser.add_argument("--weights", default="0.4,0.3,0.3")
    simulate_parser.add_argument("--horizon", type=int, default=7, choices=[7, 30, 90])

    args = parser.parse_args()
    if args.stage == "simulate":
        assets = [item.strip() for item in args.assets.split(",") if item.strip()]
        weights = [float(item.strip()) for item in args.weights.split(",") if item.strip()]
        print(asdict(simulate_portfolio(assets=assets, weights=weights, horizon=args.horizon)))
        return
    if args.stage == "run-all":
        print(run_full_pipeline())
        return
    if args.stage == "dashboard-summary":
        print(summarize_dashboard(build_dashboard_payload()))
        return
    if args.stage == "health-check":
        print(asdict(build_health_report()))
        return
    if args.stage == "verify-deployment":
        print(verification_report_dict())
        return

    handlers = {
        "ingest": run_ingestion,
        "silver": build_silver_layer,
        "gold": build_gold_layer,
        "features": build_feature_store,
        "train-volatility": train_volatility_model,
        "train-classifier": train_risk_classifier,
        "streaming": detect_streaming_signals,
    }
    print(handlers[args.stage]())


if __name__ == "__main__":
    main()
