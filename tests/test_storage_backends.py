from __future__ import annotations

import pandas as pd
import pytest

from market_risk_platform.config.settings import load_config
from market_risk_platform.storage import DatabricksDeltaBackend, LocalFileBackend, get_dataset_backend
from market_risk_platform.utils import read_dataset, write_dataset


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


def test_databricks_backend_is_explicitly_unimplemented(configured_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "databricks")
    load_config.cache_clear()
    config = load_config()
    backend = get_dataset_backend(config)
    assert isinstance(backend, DatabricksDeltaBackend)
    contract = config.dataset_contracts()["gold_asset_risk_features"]
    with pytest.raises(NotImplementedError):
        backend.read(contract)
