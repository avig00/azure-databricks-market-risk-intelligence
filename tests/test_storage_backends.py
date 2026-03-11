from __future__ import annotations

import pandas as pd

from market_risk_platform.config.settings import load_config
from market_risk_platform.storage import DatabricksDeltaBackend, LocalFileBackend, SparkAdapter, get_dataset_backend
from market_risk_platform.utils import read_dataset, write_dataset


class FakeSparkAdapter(SparkAdapter):
    def __init__(self) -> None:
        self.tables: dict[str, pd.DataFrame] = {}
        self.paths: dict[str, pd.DataFrame] = {}

    def read_dataset(self, table_name: str, storage_path: str) -> pd.DataFrame:
        return self.tables.get(table_name, self.paths[storage_path]).copy()

    def write_dataset(self, table_name: str, storage_path: str, dataframe: pd.DataFrame) -> str:
        self.tables[table_name] = dataframe.copy()
        self.paths[storage_path] = dataframe.copy()
        return table_name


def test_local_backend_roundtrip(configured_env) -> None:
    load_config.cache_clear()
    config = load_config()
    contract = config.dataset_contracts()["bronze_stock_prices"]
    frame = pd.DataFrame({"date": pd.to_datetime(["2026-03-10"]), "symbol": ["AAPL"], "close": [100.0]})
    target = write_dataset(contract, frame, config)
    loaded = read_dataset(contract, config)
    assert target.endswith(".parquet")
    assert loaded.iloc[0]["symbol"] == "AAPL"
    assert isinstance(get_dataset_backend(config), LocalFileBackend)


def test_databricks_backend_roundtrip_with_adapter(configured_env, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "databricks")
    load_config.cache_clear()
    config = load_config()
    backend = get_dataset_backend(config)
    assert isinstance(backend, DatabricksDeltaBackend)
    contract = config.dataset_contracts()["gold_asset_risk_features"]
    fake_adapter = FakeSparkAdapter()
    backend = DatabricksDeltaBackend(config, adapter=fake_adapter)
    frame = pd.DataFrame({"date": pd.to_datetime(["2026-03-10"]), "symbol": ["AAPL"], "metric": [0.25]})
    destination = backend.write(contract, frame)
    loaded = backend.read(contract)
    assert destination == contract.table_name
    assert loaded.iloc[0]["symbol"] == "AAPL"
