from __future__ import annotations

from dataclasses import dataclass, field

from market_risk_platform.config import AppConfig, load_config
from market_risk_platform.utils import read_dataset, run_stage


@dataclass
class StreamingStatus:
    status: str
    message: str
    alerts: list[str] = field(default_factory=list)


def run_streaming_detection(config: AppConfig | None = None) -> StreamingStatus:
    config = config or load_config()
    contracts = config.dataset_contracts()
    stress = read_dataset(contracts["gold_market_stress_signals"], config).sort_values("date")
    assets = read_dataset(contracts["gold_asset_risk_features"], config).sort_values("date")
    latest_stress = stress.tail(1)
    latest_assets = assets.groupby("symbol").tail(1)
    alerts: list[str] = []
    if latest_stress.empty or latest_assets.empty:
        return StreamingStatus(status="awaiting-data", message="No Gold-layer datasets are available for signal detection.")
    stress_index = float(latest_stress["market_stress_index"].iloc[0])
    avg_volatility = float(latest_stress["avg_volatility_30d"].iloc[0])
    if stress_index >= 0.08:
        alerts.append(f"Market stress index elevated at {stress_index:.3f}")
    if avg_volatility >= 0.025:
        alerts.append(f"Average 30-day volatility elevated at {avg_volatility:.3f}")
    volatile_assets = latest_assets[latest_assets["rolling_volatility_30d"] >= 0.03].sort_values(
        "rolling_volatility_30d", ascending=False
    )
    for _, row in volatile_assets.head(3).iterrows():
        alerts.append(f"{row['symbol']} volatility spike detected ({row['rolling_volatility_30d']:.3f})")
    status = "alerting" if alerts else "normal"
    message = (
        "Signals derived from latest Gold-layer datasets; wire this module to Event Hubs or Structured Streaming for near-real-time monitoring."
    )
    return StreamingStatus(status=status, message=message, alerts=alerts)


def detect_streaming_signals() -> StreamingStatus:
    return run_stage("streaming_signal_detection", run_streaming_detection)
