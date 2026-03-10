from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.utils import run_stage, write_dataset

from .providers import get_provider, split_index_and_assets


@dataclass
class IngestionResult:
    stock_prices_path: str
    market_indices_path: str
    macro_indicators_path: str
    record_counts: dict[str, int]


def _prepare_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    prepared = dataframe.copy()
    prepared["ingested_at"] = pd.Timestamp.utcnow().isoformat()
    return prepared


def ingest_market_data(config: AppConfig | None = None) -> IngestionResult:
    config = config or load_config()
    provider = get_provider(config.use_sample_data, config.fred_api_key)
    price_df = provider.fetch_prices(config.market_symbols, config.yfinance_start)
    macro_df = provider.fetch_macro(config.fred_series, config.fred_start)
    if price_df.empty:
        raise ValueError("No price data was ingested")
    if macro_df.empty:
        raise ValueError("No macroeconomic data was ingested")
    stock_prices, market_indices = split_index_and_assets(price_df)
    contracts = config.dataset_contracts()
    write_dataset(_prepare_frame(stock_prices), contracts["bronze_stock_prices"].local_path)
    write_dataset(_prepare_frame(market_indices), contracts["bronze_market_indices"].local_path)
    write_dataset(_prepare_frame(macro_df), contracts["bronze_macro_indicators"].local_path)
    return IngestionResult(
        stock_prices_path=str(contracts["bronze_stock_prices"].local_path),
        market_indices_path=str(contracts["bronze_market_indices"].local_path),
        macro_indicators_path=str(contracts["bronze_macro_indicators"].local_path),
        record_counts={
            "stock_prices": len(stock_prices),
            "market_indices": len(market_indices),
            "macro_indicators": len(macro_df),
        },
    )


def run_ingestion() -> IngestionResult:
    return run_stage("data_ingestion", ingest_market_data)


def main() -> None:
    result = run_ingestion()
    print(asdict(result))


if __name__ == "__main__":
    main()
