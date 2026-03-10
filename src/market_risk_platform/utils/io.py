from __future__ import annotations

from pathlib import Path

import pandas as pd


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_dataset(dataframe: pd.DataFrame, path: Path) -> Path:
    ensure_parent(path)
    dataframe.to_csv(path, index=False)
    return path


def read_dataset(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"])
