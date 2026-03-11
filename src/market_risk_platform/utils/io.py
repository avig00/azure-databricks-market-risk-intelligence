from __future__ import annotations

import pandas as pd

from market_risk_platform.config import AppConfig, DatasetContract, load_config
from market_risk_platform.storage import get_dataset_backend


def write_dataset(contract: DatasetContract, dataframe: pd.DataFrame, config: AppConfig | None = None) -> str:
    config = config or load_config()
    return get_dataset_backend(config).write(contract, dataframe)


def read_dataset(contract: DatasetContract, config: AppConfig | None = None) -> pd.DataFrame:
    config = config or load_config()
    return get_dataset_backend(config).read(contract)
