from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.utils import read_dataset, run_stage, write_dataset


@dataclass
class GoldResult:
    asset_risk_features_path: str
    market_stress_signals_path: str
    portfolio_risk_metrics_path: str


def build_gold_outputs(config: AppConfig | None = None) -> GoldResult:
    config = config or load_config()
    contracts = config.dataset_contracts()
    volatility = read_dataset(contracts["silver_volatility_metrics"], config)
    drawdowns = read_dataset(contracts["silver_asset_drawdowns"], config)
    correlations = read_dataset(contracts["silver_market_correlations"], config)
    macro = read_dataset(contracts["bronze_macro_indicators"], config)
    macro["macro_shock_score"] = macro.groupby("series_id")["value"].pct_change().fillna(0.0).abs()
    macro_daily = macro.groupby("date", as_index=False)["macro_shock_score"].mean()
    corr_by_symbol = pd.concat(
        [
            correlations.rename(columns={"symbol_a": "symbol"})[["date", "symbol", "correlation"]],
            correlations.rename(columns={"symbol_b": "symbol"})[["date", "symbol", "correlation"]],
        ],
        ignore_index=True,
    )
    corr_agg = (
        corr_by_symbol.groupby(["date", "symbol"], as_index=False)["correlation"]
        .apply(lambda s: s.abs().mean())
        .rename(columns={"correlation": "mean_correlation"})
    )
    asset_features = volatility.merge(drawdowns, on=["date", "symbol"], how="left")
    asset_features["momentum_signal"] = asset_features.groupby("symbol")["daily_return"].transform(
        lambda s: s.rolling(14).mean()
    ).fillna(0.0)
    asset_features = asset_features.merge(corr_agg, on=["date", "symbol"], how="left").merge(macro_daily, on="date", how="left")
    asset_features["correlation_spike"] = asset_features["mean_correlation"].fillna(0.0)
    asset_features["macro_shock_score"] = asset_features["macro_shock_score"].fillna(0.0)
    # Keep the target strictly future-looking; trailing rows without a horizon stay null.
    asset_features["future_volatility_7d"] = asset_features.groupby("symbol")["rolling_volatility_7d"].shift(-7)
    stress = (
        asset_features.groupby("date", as_index=False)[
            ["rolling_volatility_30d", "drawdown", "correlation_spike", "macro_shock_score"]
        ]
        .mean()
        .rename(columns={"rolling_volatility_30d": "avg_volatility_30d"})
    )
    stress["market_stress_index"] = (
        stress["avg_volatility_30d"] * 0.4
        + stress["drawdown"].abs() * 0.2
        + stress["correlation_spike"].clip(lower=0) * 0.2
        + stress["macro_shock_score"].clip(lower=0) * 0.2
    )
    portfolio = (
        asset_features.groupby("date", as_index=False)[
            ["rolling_volatility_30d", "drawdown", "correlation_spike", "macro_shock_score"]
        ]
        .mean()
        .rename(columns={"rolling_volatility_30d": "portfolio_volatility", "drawdown": "expected_drawdown"})
    )
    portfolio["value_at_risk_95"] = portfolio["portfolio_volatility"] * 1.65
    write_dataset(contracts["gold_asset_risk_features"], asset_features, config)
    write_dataset(contracts["gold_market_stress_signals"], stress, config)
    write_dataset(contracts["gold_portfolio_risk_metrics"], portfolio, config)
    return GoldResult(
        asset_risk_features_path=str(contracts["gold_asset_risk_features"].local_path),
        market_stress_signals_path=str(contracts["gold_market_stress_signals"].local_path),
        portfolio_risk_metrics_path=str(contracts["gold_portfolio_risk_metrics"].local_path),
    )


def build_gold_layer() -> GoldResult:
    return run_stage("gold_feature_builder", build_gold_outputs)


def main() -> None:
    result = build_gold_layer()
    print(asdict(result))


if __name__ == "__main__":
    main()
