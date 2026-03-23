from __future__ import annotations

from dataclasses import asdict, dataclass

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.utils import read_dataset, run_stage

from .common import persist_model, temporal_train_test_split


RISK_FEATURES = [
    "portfolio_volatility",
    "expected_drawdown",
    "correlation_spike",
    "macro_shock_score",
    "value_at_risk_95",
]

FUTURE_RISK_TARGET = "future_portfolio_volatility_7d"
RISK_NEGATIVE_LABEL = "STABLE"
RISK_POSITIVE_LABEL = "ELEVATED"


@dataclass
class ClassifierTrainingResult:
    model_path: str
    metrics_path: str
    primary_metric: float


def train_classifier(config: AppConfig | None = None) -> ClassifierTrainingResult:
    config = config or load_config()
    training = read_dataset(config.dataset_contracts()["features_portfolio_training"], config).dropna(
        subset=RISK_FEATURES + [FUTURE_RISK_TARGET]
    )
    train_frame, test_frame = temporal_train_test_split(training, date_col="date", test_fraction=0.2)
    elevated_threshold = train_frame[FUTURE_RISK_TARGET].median()

    def assign_risk_tier(series):
        tiers = series.map(lambda value: RISK_POSITIVE_LABEL if value >= elevated_threshold else RISK_NEGATIVE_LABEL)
        return tiers.astype("object")

    X_train = train_frame[RISK_FEATURES]
    y_train = assign_risk_tier(train_frame[FUTURE_RISK_TARGET])
    X_test = test_frame[RISK_FEATURES]
    y_test = assign_risk_tier(test_frame[FUTURE_RISK_TARGET])
    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    accuracy = float(accuracy_score(y_test, preds))
    macro_f1 = float(f1_score(y_test, preds, average="macro"))
    model_path, metrics_path = persist_model(
        model, {"accuracy": accuracy, "macro_f1": macro_f1}, config.artifact_root, "risk_classifier"
    )
    return ClassifierTrainingResult(str(model_path), str(metrics_path), accuracy)


def train_risk_classifier() -> ClassifierTrainingResult:
    return run_stage("train_risk_classifier", train_classifier)


def main() -> None:
    result = train_risk_classifier()
    print(asdict(result))


if __name__ == "__main__":
    main()
