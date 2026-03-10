from __future__ import annotations

from dataclasses import dataclass

from market_risk_platform.utils import run_stage


@dataclass
class StreamingStatus:
    status: str
    message: str


def run_streaming_detection() -> StreamingStatus:
    return StreamingStatus(
        status="scaffolded",
        message="Streaming anomaly detection is intentionally scaffolded for Azure Event Hubs or Databricks Structured Streaming integration.",
    )


def detect_streaming_signals() -> StreamingStatus:
    return run_stage("streaming_signal_detection", run_streaming_detection)

