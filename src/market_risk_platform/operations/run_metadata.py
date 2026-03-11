from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from market_risk_platform.config import AppConfig, load_config


def _run_log_path(config: AppConfig) -> Path:
    return config.log_root / "pipeline_runs.jsonl"


def _serialize(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return str(value)


def record_stage_event(
    stage_name: str,
    status: str,
    started_at: datetime,
    finished_at: datetime,
    result: Any = None,
    error: str | None = None,
    run_id: str | None = None,
    config: AppConfig | None = None,
) -> Path:
    config = config or load_config()
    log_path = _run_log_path(config)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id or str(uuid.uuid4()),
        "stage_name": stage_name,
        "status": status,
        "runtime_mode": config.runtime_mode,
        "storage_backend": config.storage_backend,
        "started_at": started_at.astimezone(UTC).isoformat(),
        "finished_at": finished_at.astimezone(UTC).isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 4),
        "result": _serialize(result),
        "error": error,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    return log_path

