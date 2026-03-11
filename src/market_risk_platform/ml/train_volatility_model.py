from __future__ import annotations

from dataclasses import asdict, dataclass

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.utils import read_dataset, run_stage

from .common import persist_model


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
    training = read_dataset(config.dataset_contracts()["features_asset_training"], config).dropna(subset=VOL_FEATURES)
    X = training[VOL_FEATURES]
    y = training["future_volatility_7d"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = GradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))
    model_path, metrics_path = persist_model(model, {"mae": mae}, config.artifact_root, "volatility_model")
    return ModelTrainingResult(str(model_path), str(metrics_path), mae)


def train_volatility_model() -> ModelTrainingResult:
    return run_stage("train_volatility_model", train_model)


def main() -> None:
    result = train_volatility_model()
    print(asdict(result))


if __name__ == "__main__":
    main()
