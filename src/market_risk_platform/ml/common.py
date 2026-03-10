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

