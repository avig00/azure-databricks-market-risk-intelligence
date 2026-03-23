from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd


def persist_model(model: object, metrics: dict[str, float], output_dir: Path, model_name: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"{model_name}.joblib"
    metrics_path = output_dir / f"{model_name}_metrics.csv"
    joblib.dump(model, model_path)
    pd.DataFrame([metrics]).to_csv(metrics_path, index=False)
    return model_path, metrics_path


def temporal_train_test_split(
    frame: pd.DataFrame, date_col: str = "date", test_fraction: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = sorted(pd.to_datetime(frame[date_col]).dropna().unique())
    if len(dates) < 2:
        raise ValueError("Temporal split requires at least two distinct dates.")
    split_idx = max(1, int(len(dates) * (1 - test_fraction)))
    if split_idx >= len(dates):
        split_idx = len(dates) - 1
    cutoff = dates[split_idx]
    train = frame[pd.to_datetime(frame[date_col]) < cutoff].copy()
    test = frame[pd.to_datetime(frame[date_col]) >= cutoff].copy()
    if train.empty or test.empty:
        raise ValueError("Temporal split produced an empty train or test set.")
    return train, test
