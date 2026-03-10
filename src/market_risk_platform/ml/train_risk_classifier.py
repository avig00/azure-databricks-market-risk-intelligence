from __future__ import annotations

from dataclasses import asdict, dataclass

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.utils import read_dataset, run_stage

from .common import persist_model


RISK_FEATURES = [
    "portfolio_volatility",
    "expected_drawdown",
    "correlation_spike",
    "macro_shock_score",
    "value_at_risk_95",
]


@dataclass
class ClassifierTrainingResult:
    model_path: str
    metrics_path: str
    primary_metric: float


def train_classifier(config: AppConfig | None = None) -> ClassifierTrainingResult:
    config = config or load_config()
    training = read_dataset(config.dataset_contracts()["features_portfolio_training"].local_path).dropna(subset=RISK_FEATURES)
    X = training[RISK_FEATURES]
    y = training["risk_tier"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    accuracy = float(accuracy_score(y_test, preds))
    model_path, metrics_path = persist_model(model, {"accuracy": accuracy}, config.artifact_root, "risk_classifier")
    return ClassifierTrainingResult(str(model_path), str(metrics_path), accuracy)


def train_risk_classifier() -> ClassifierTrainingResult:
    return run_stage("train_risk_classifier", train_classifier)


def main() -> None:
    result = train_risk_classifier()
    print(asdict(result))


if __name__ == "__main__":
    main()

