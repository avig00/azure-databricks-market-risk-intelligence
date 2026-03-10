from __future__ import annotations

from dataclasses import asdict, dataclass

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.utils import read_dataset, run_stage, write_dataset


@dataclass
class FeatureStoreResult:
    asset_features_path: str
    portfolio_features_path: str


def build_features(config: AppConfig | None = None) -> FeatureStoreResult:
    config = config or load_config()
    contracts = config.dataset_contracts()
    asset_features = read_dataset(contracts["gold_asset_risk_features"].local_path)
    portfolio_metrics = read_dataset(contracts["gold_portfolio_risk_metrics"].local_path)
    portfolio_features = portfolio_metrics.copy()
    risk_score = (
        portfolio_features["portfolio_volatility"].rank(pct=True)
        + portfolio_features["value_at_risk_95"].rank(pct=True)
        + portfolio_features["expected_drawdown"].abs().rank(pct=True)
    ) / 3
    portfolio_features["risk_tier"] = "MEDIUM"
    portfolio_features.loc[risk_score <= 0.33, "risk_tier"] = "LOW"
    portfolio_features.loc[risk_score >= 0.67, "risk_tier"] = "HIGH"
    write_dataset(asset_features, contracts["features_asset_training"].local_path)
    write_dataset(portfolio_features, contracts["features_portfolio_training"].local_path)
    return FeatureStoreResult(
        asset_features_path=str(contracts["features_asset_training"].local_path),
        portfolio_features_path=str(contracts["features_portfolio_training"].local_path),
    )


def build_feature_store() -> FeatureStoreResult:
    return run_stage("feature_store_builder", build_features)


def main() -> None:
    result = build_feature_store()
    print(asdict(result))


if __name__ == "__main__":
    main()
