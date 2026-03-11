from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.utils import read_dataset


@dataclass
class HealthReport:
    runtime_mode: str
    storage_backend: str
    dataset_freshness: dict[str, str | None]
    latest_successful_stage: str | None
    latest_successful_stage_at: str | None
    latest_model_artifacts: dict[str, str | None]


def _latest_stage_success(config: AppConfig) -> tuple[str | None, str | None]:
    log_path = config.log_root / "pipeline_runs.jsonl"
    if not log_path.exists():
        return None, None
    last_success: dict | None = None
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("status") == "success":
            last_success = payload
    if last_success is None:
        return None, None
    return last_success.get("stage_name"), last_success.get("finished_at")


def _latest_artifact_timestamp(path: Path) -> str | None:
    if not path.exists():
        return None
    latest = max((child.stat().st_mtime for child in path.glob("*") if child.is_file()), default=None)
    if latest is None:
        return None
    return pd.Timestamp(latest, unit="s", tz="UTC").isoformat()


def build_health_report(config: AppConfig | None = None) -> HealthReport:
    config = config or load_config()
    contracts = config.dataset_contracts()
    dataset_freshness: dict[str, str | None] = {}
    for key in ["gold_asset_risk_features", "gold_market_stress_signals", "gold_portfolio_risk_metrics"]:
        contract = contracts[key]
        if contract.local_path.exists():
            frame = read_dataset(contract, config)
            dataset_freshness[key] = (
                pd.to_datetime(frame["date"]).max().isoformat() if not frame.empty and "date" in frame.columns else None
            )
        else:
            dataset_freshness[key] = None
    latest_stage, latest_stage_at = _latest_stage_success(config)
    return HealthReport(
        runtime_mode=config.runtime_mode,
        storage_backend=config.storage_backend,
        dataset_freshness=dataset_freshness,
        latest_successful_stage=latest_stage,
        latest_successful_stage_at=latest_stage_at,
        latest_model_artifacts={
            "volatility_model": _latest_artifact_timestamp(config.artifact_root),
            "risk_classifier": _latest_artifact_timestamp(config.artifact_root),
        },
    )

