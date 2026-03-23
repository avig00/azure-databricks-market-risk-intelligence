from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.utils import read_dataset, run_stage

from .common import persist_model, temporal_train_test_split


VOL_FEATURES = [
    "rolling_volatility_7d",
    "rolling_volatility_30d",
    "rolling_volatility_90d",
    "drawdown",
    "correlation_spike",
    "momentum_signal",
    "macro_shock_score",
]


@dataclass
class ModelTrainingResult:
    model_path: str
    metrics_path: str
    primary_metric: float


def train_model(config: AppConfig | None = None) -> ModelTrainingResult:
    config = config or load_config()
    training = read_dataset(config.dataset_contracts()["features_asset_training"], config).dropna(
        subset=VOL_FEATURES + ["future_volatility_7d"]
    )
    train_frame, test_frame = temporal_train_test_split(training, date_col="date", test_fraction=0.2)
    X_train = train_frame[VOL_FEATURES]
    y_train = train_frame["future_volatility_7d"]
    X_test = test_frame[VOL_FEATURES]
    y_test = test_frame["future_volatility_7d"]
    model = GradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(sqrt(mean_squared_error(y_test, preds)))
    r2 = float(r2_score(y_test, preds))
    model_path, metrics_path = persist_model(model, {"mae": mae, "rmse": rmse, "r2": r2}, config.artifact_root, "volatility_model")
    return ModelTrainingResult(str(model_path), str(metrics_path), mae)


def train_volatility_model() -> ModelTrainingResult:
    return run_stage("train_volatility_model", train_model)


def main() -> None:
    result = train_volatility_model()
    print(asdict(result))


if __name__ == "__main__":
    main()
