from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import joblib

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.ml.train_risk_classifier import RISK_FEATURES
from market_risk_platform.ml.train_volatility_model import VOL_FEATURES
from market_risk_platform.utils import read_dataset, run_stage


@dataclass
class SimulationInput:
    assets: list[str]
    weights: list[float]
    horizon: int = 7


@dataclass
class SimulationResult:
    horizon: int
    portfolio_volatility: float
    value_at_risk_95: float
    expected_drawdown: float
    correlation_exposure: float
    predicted_risk_tier: str
    predicted_future_volatility: float


def _validate_request(request: SimulationInput) -> None:
    if len(request.assets) != len(request.weights):
        raise ValueError("assets and weights must have the same length")
    if len(set(request.assets)) != len(request.assets):
        raise ValueError("duplicate assets are not allowed")
    if request.horizon not in {7, 30, 90}:
        raise ValueError("horizon must be one of 7, 30, or 90 days")
    if not np.isclose(sum(request.weights), 1.0, atol=1e-6):
        raise ValueError("weights must sum to 1.0")


def run_simulation(request: SimulationInput, config: AppConfig | None = None) -> SimulationResult:
    _validate_request(request)
    config = config or load_config()
    contracts = config.dataset_contracts()
    asset_features = read_dataset(contracts["gold_asset_risk_features"].local_path)
    latest = asset_features.sort_values("date").groupby("symbol").tail(1).set_index("symbol")
    missing = [asset for asset in request.assets if asset not in latest.index]
    if missing:
        raise ValueError(f"missing assets in feature store: {', '.join(missing)}")
    weights = np.array(request.weights)
    selected = latest.loc[request.assets]
    portfolio_vol = float(np.dot(weights, selected["rolling_volatility_30d"]))
    expected_drawdown = float(np.dot(weights, selected["drawdown"]))
    correlation_exposure = float(selected["correlation_spike"].mean())
    macro_shock = float(selected["macro_shock_score"].mean())
    value_at_risk_95 = abs(portfolio_vol) * 1.65 * np.sqrt(request.horizon / 7)
    risk_model = joblib.load(config.artifact_root / "risk_classifier.joblib")
    vol_model = joblib.load(config.artifact_root / "volatility_model.joblib")
    risk_frame = {
        "portfolio_volatility": portfolio_vol,
        "expected_drawdown": expected_drawdown,
        "correlation_spike": correlation_exposure,
        "macro_shock_score": macro_shock,
        "value_at_risk_95": value_at_risk_95,
    }
    predicted_risk_tier = str(risk_model.predict(pd.DataFrame([risk_frame], columns=RISK_FEATURES))[0])
    feature_matrix = selected[VOL_FEATURES].copy()
    predicted_future_volatility = float(np.dot(weights, vol_model.predict(feature_matrix)))
    return SimulationResult(
        horizon=request.horizon,
        portfolio_volatility=float(portfolio_vol),
        value_at_risk_95=float(value_at_risk_95),
        expected_drawdown=float(expected_drawdown),
        correlation_exposure=float(correlation_exposure),
        predicted_risk_tier=predicted_risk_tier,
        predicted_future_volatility=float(predicted_future_volatility),
    )


def simulate_portfolio(
    assets: list[str] | None = None, weights: list[float] | None = None, horizon: int = 7
) -> SimulationResult:
    assets = assets or ["AAPL", "XOM", "TLT"]
    weights = weights or [0.4, 0.3, 0.3]
    return run_stage("portfolio_simulation", run_simulation, SimulationInput(assets=assets, weights=weights, horizon=horizon))


def main() -> None:
    result = simulate_portfolio()
    print(asdict(result))


if __name__ == "__main__":
    main()
