from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.utils import read_dataset, run_stage, write_dataset


@dataclass
class SilverResult:
    daily_returns_path: str
    volatility_metrics_path: str
    market_correlations_path: str
    asset_drawdowns_path: str


def _rolling_drawdown(close_series: pd.Series) -> pd.Series:
    running_max = close_series.cummax()
    return (close_series / running_max) - 1.0


def _build_correlation_frame(daily_returns: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    pivot = daily_returns.pivot(index="date", columns="symbol", values="daily_return").fillna(0.0)
    records: list[dict[str, object]] = []
    for idx in range(window - 1, len(pivot)):
        window_frame = pivot.iloc[idx - window + 1 : idx + 1]
        corr_matrix = window_frame.corr()
        as_of_date = pivot.index[idx]
        for symbol_a in corr_matrix.index:
            for symbol_b in corr_matrix.columns:
                if symbol_a >= symbol_b:
                    continue
                records.append(
                    {
                        "date": as_of_date,
                        "symbol_a": symbol_a,
                        "symbol_b": symbol_b,
                        "correlation": float(corr_matrix.loc[symbol_a, symbol_b]),
                    }
                )
    return pd.DataFrame(records)


def transform_to_silver(config: AppConfig | None = None) -> SilverResult:
    config = config or load_config()
    contracts = config.dataset_contracts()
    prices = read_dataset(contracts["bronze_stock_prices"], config).sort_values(["symbol", "date"])
    prices["daily_return"] = prices.groupby("symbol")["adj_close"].pct_change().fillna(0.0)
    daily_returns = prices[["date", "symbol", "daily_return"]].copy()
    metrics = daily_returns.copy()
    for window in (7, 30, 90):
        metrics[f"rolling_volatility_{window}d"] = (
            metrics.groupby("symbol")["daily_return"].transform(lambda s: s.rolling(window).std(ddof=0)).fillna(0.0)
        )
    drawdowns = prices[["date", "symbol", "adj_close"]].copy()
    drawdowns["drawdown"] = prices.groupby("symbol")["adj_close"].transform(_rolling_drawdown)
    corr = _build_correlation_frame(daily_returns, window=30)
    write_dataset(contracts["silver_daily_returns"], daily_returns, config)
    write_dataset(contracts["silver_volatility_metrics"], metrics, config)
    write_dataset(contracts["silver_market_correlations"], corr, config)
    write_dataset(contracts["silver_asset_drawdowns"], drawdowns[["date", "symbol", "drawdown"]], config)
    return SilverResult(
        daily_returns_path=str(contracts["silver_daily_returns"].local_path),
        volatility_metrics_path=str(contracts["silver_volatility_metrics"].local_path),
        market_correlations_path=str(contracts["silver_market_correlations"].local_path),
        asset_drawdowns_path=str(contracts["silver_asset_drawdowns"].local_path),
    )


def build_silver_layer() -> SilverResult:
    return run_stage("silver_transformations", transform_to_silver)


def main() -> None:
    result = build_silver_layer()
    print(asdict(result))


if __name__ == "__main__":
    main()
