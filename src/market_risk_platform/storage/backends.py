from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from market_risk_platform.config import AppConfig, DatasetContract


def _parse_dates(dataframe: pd.DataFrame) -> pd.DataFrame:
    parsed = dataframe.copy()
    if "date" in parsed.columns:
        parsed["date"] = pd.to_datetime(parsed["date"])
    return parsed


class DatasetBackend(ABC):
    @abstractmethod
    def read(self, contract: DatasetContract) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def write(self, contract: DatasetContract, dataframe: pd.DataFrame) -> str:
        raise NotImplementedError


class LocalFileBackend(DatasetBackend):
    def read(self, contract: DatasetContract) -> pd.DataFrame:
        path = contract.local_path
        if path.suffix == ".csv":
            return pd.read_csv(path, parse_dates=["date"] if path.exists() else None)
        if path.suffix == ".parquet":
            return _parse_dates(pd.read_parquet(path))
        raise ValueError(f"Unsupported dataset format for path: {path}")

    def write(self, contract: DatasetContract, dataframe: pd.DataFrame) -> str:
        path = contract.local_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".csv":
            dataframe.to_csv(path, index=False)
            return str(path)
        if path.suffix == ".parquet":
            _parse_dates(dataframe).to_parquet(path, index=False)
            return str(path)
        raise ValueError(f"Unsupported dataset format for path: {path}")


class DatabricksDeltaBackend(DatasetBackend):
    def __init__(self, config: AppConfig):
        self.config = config

    def read(self, contract: DatasetContract) -> pd.DataFrame:
        raise NotImplementedError(
            f"Delta backend read for '{contract.table_name}' is not implemented locally. "
            "Execute this backend inside Databricks with Spark/Delta support."
        )

    def write(self, contract: DatasetContract, dataframe: pd.DataFrame) -> str:
        raise NotImplementedError(
            f"Delta backend write for '{contract.table_name}' is not implemented locally. "
            "Execute this backend inside Databricks with Spark/Delta support."
        )


def get_dataset_backend(config: AppConfig) -> DatasetBackend:
    if config.storage_backend == "local":
        return LocalFileBackend()
    if config.storage_backend == "databricks":
        return DatabricksDeltaBackend(config)
    raise ValueError(f"Unsupported storage backend: {config.storage_backend}")
