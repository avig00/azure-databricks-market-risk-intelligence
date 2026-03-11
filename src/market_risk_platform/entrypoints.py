from __future__ import annotations

from dataclasses import asdict

from market_risk_platform.dashboard.app import build_dashboard_payload, summarize_dashboard
from market_risk_platform.pipeline import run_full_pipeline
from market_risk_platform.simulation.portfolio_simulator import simulate_portfolio


def run_all() -> None:
    print(run_full_pipeline())


def dashboard_refresh() -> None:
    print(summarize_dashboard(build_dashboard_payload()))


def simulate_default() -> None:
    print(asdict(simulate_portfolio()))

