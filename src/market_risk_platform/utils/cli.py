from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from market_risk_platform.config import load_config
from market_risk_platform.operations.run_metadata import record_stage_event

from .logging_utils import get_logger


def run_stage(stage_name: str, handler: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    logger = get_logger(stage_name)
    config = load_config()
    started_at = datetime.now(UTC)
    logger.info("Starting stage '%s'", stage_name)
    try:
        result = handler(*args, **kwargs)
    except Exception as exc:
        finished_at = datetime.now(UTC)
        record_stage_event(
            stage_name=stage_name,
            status="failed",
            started_at=started_at,
            finished_at=finished_at,
            error=str(exc),
            config=config,
        )
        logger.exception("Stage '%s' failed", stage_name)
        raise
    finished_at = datetime.now(UTC)
    record_stage_event(
        stage_name=stage_name,
        status="success",
        started_at=started_at,
        finished_at=finished_at,
        result=result,
        config=config,
    )
    logger.info("Completed stage '%s'", stage_name)
    return result
