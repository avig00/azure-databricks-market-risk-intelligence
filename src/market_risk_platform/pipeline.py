from __future__ import annotations

from dataclasses import dataclass

from market_risk_platform.data_ingestion.market_data_pipeline import IngestionResult, run_ingestion
from market_risk_platform.features.feature_store_builder import FeatureStoreResult, build_feature_store
from market_risk_platform.lakehouse.gold_feature_builder import GoldResult, build_gold_layer
from market_risk_platform.lakehouse.silver_transformations import SilverResult, build_silver_layer
from market_risk_platform.ml.train_risk_classifier import ClassifierTrainingResult, train_risk_classifier
from market_risk_platform.ml.train_volatility_model import ModelTrainingResult, train_volatility_model


@dataclass
class PipelineRunResult:
    ingestion: IngestionResult
    silver: SilverResult
    gold: GoldResult
    features: FeatureStoreResult
    volatility_model: ModelTrainingResult
    risk_classifier: ClassifierTrainingResult


def run_full_pipeline() -> PipelineRunResult:
    ingestion = run_ingestion()
    silver = build_silver_layer()
    gold = build_gold_layer()
    features = build_feature_store()
    volatility_model = train_volatility_model()
    risk_classifier = train_risk_classifier()
    return PipelineRunResult(
        ingestion=ingestion,
        silver=silver,
        gold=gold,
        features=features,
        volatility_model=volatility_model,
        risk_classifier=risk_classifier,
    )

