from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class CatalogConfig:
    catalog: str
    bronze_schema: str
    silver_schema: str
    gold_schema: str
    feature_schema: str

    def table(self, schema: str, name: str) -> str:
        return f"{self.catalog}.{schema}.{name}"


@dataclass(frozen=True)
class DatasetContract:
    layer: str
    name: str
    local_path: Path
    table_name: str
    adls_path: str


@dataclass(frozen=True)
class AppConfig:
    env: str
    project_root: Path
    data_root: Path
    artifact_root: Path
    log_root: Path
    use_sample_data: bool
    market_symbols: list[str]
    portfolio_symbols: list[str]
    fred_series: list[str]
    yfinance_start: str
    fred_start: str
    fred_api_key: str | None
    catalog: CatalogConfig
    adls_container: str
    adls_prefix: str
    key_vault_name: str
    databricks_workspace_url: str

    def dataset_contracts(self) -> dict[str, DatasetContract]:
        items = {
            "bronze_stock_prices": ("bronze", "stock_prices"),
            "bronze_market_indices": ("bronze", "market_indices"),
            "bronze_macro_indicators": ("bronze", "macro_indicators"),
            "silver_daily_returns": ("silver", "daily_returns"),
            "silver_volatility_metrics": ("silver", "volatility_metrics"),
            "silver_market_correlations": ("silver", "market_correlations"),
            "silver_asset_drawdowns": ("silver", "asset_drawdowns"),
            "gold_asset_risk_features": ("gold", "asset_risk_features"),
            "gold_market_stress_signals": ("gold", "market_stress_signals"),
            "gold_portfolio_risk_metrics": ("gold", "portfolio_risk_metrics"),
            "features_asset_training": ("features", "asset_training_features"),
            "features_portfolio_training": ("features", "portfolio_training_features"),
        }
        contracts: dict[str, DatasetContract] = {}
        for key, (layer, name) in items.items():
            schema = self.catalog.feature_schema if layer == "features" else getattr(self.catalog, f"{layer}_schema")
            contracts[key] = DatasetContract(
                layer=layer,
                name=name,
                local_path=self.data_root / layer / f"{name}.csv",
                table_name=self.catalog.table(schema, name),
                adls_path=f"abfss://{self.adls_container}@storageaccount.dfs.core.windows.net/{self.adls_prefix}/{layer}/{name}",
            )
        return contracts


@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    load_dotenv()
    project_root = Path(__file__).resolve().parents[3]
    data_root = project_root / os.getenv("DATA_ROOT", "data/local")
    artifact_root = project_root / os.getenv("ARTIFACT_ROOT", "data/sample/artifacts")
    log_root = project_root / os.getenv("LOG_ROOT", "data/sample/logs")
    catalog = CatalogConfig(
        catalog=os.getenv("CATALOG_NAME", "finance"),
        bronze_schema=os.getenv("BRONZE_SCHEMA", "bronze"),
        silver_schema=os.getenv("SILVER_SCHEMA", "silver"),
        gold_schema=os.getenv("GOLD_SCHEMA", "gold"),
        feature_schema=os.getenv("FEATURE_SCHEMA", "features"),
    )
    return AppConfig(
        env=os.getenv("MARKET_RISK_ENV", "local"),
        project_root=project_root,
        data_root=data_root,
        artifact_root=artifact_root,
        log_root=log_root,
        use_sample_data=os.getenv("USE_SAMPLE_DATA", "true").lower() == "true",
        market_symbols=_split_csv(os.getenv("MARKET_SYMBOLS", "AAPL,MSFT,NVDA,XOM,SPY,TLT,^GSPC,^IXIC,^VIX")),
        portfolio_symbols=_split_csv(os.getenv("PORTFOLIO_SYMBOLS", "AAPL,MSFT,NVDA,XOM,SPY,TLT")),
        fred_series=_split_csv(os.getenv("FRED_SERIES", "FEDFUNDS,CPIAUCSL,UNRATE,DGS10")),
        yfinance_start=os.getenv("YFINANCE_START", "2018-01-01"),
        fred_start=os.getenv("FRED_START", "2018-01-01"),
        fred_api_key=os.getenv("FRED_API_KEY"),
        catalog=catalog,
        adls_container=os.getenv("ADLS_CONTAINER", "market-risk"),
        adls_prefix=os.getenv("ADLS_PREFIX", "lakehouse"),
        key_vault_name=os.getenv("KEY_VAULT_NAME", "kv-market-risk"),
        databricks_workspace_url=os.getenv("DATABRICKS_WORKSPACE_URL", "https://adb-placeholder.azuredatabricks.net"),
    )
