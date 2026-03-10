from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .logging_utils import get_logger


def run_stage(stage_name: str, handler: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    logger = get_logger(stage_name)
    logger.info("Starting stage '%s'", stage_name)
    result = handler(*args, **kwargs)
    logger.info("Completed stage '%s'", stage_name)
    return result

