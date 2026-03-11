from __future__ import annotations

import os
from dataclasses import asdict

from market_risk_platform.dashboard.app import build_dashboard_payload, summarize_dashboard
from market_risk_platform.operations.verification import verification_report_dict
from market_risk_platform.pipeline import run_full_pipeline
from market_risk_platform.simulation.portfolio_simulator import simulate_portfolio


def _apply_runtime_env() -> None:
    for env_name in [
        "MARKET_RISK_ENV",
        "RUNTIME_MODE",
        "CONFIG_PROFILE",
        "CATALOG_NAME",
        "STORAGE_BACKEND",
        "ADLS_PREFIX",
        "DATABRICKS_SECRET_SCOPE",
        "FRED_API_KEY_SECRET_KEY",
    ]:
        override = os.getenv(env_name)
        if override:
            os.environ[env_name] = override


def run_all() -> None:
    _apply_runtime_env()
    print(run_full_pipeline())


def dashboard_refresh() -> None:
    _apply_runtime_env()
    print(summarize_dashboard(build_dashboard_payload()))


def simulate_default() -> None:
    _apply_runtime_env()
    print(asdict(simulate_portfolio()))


def verify_deployment() -> None:
    _apply_runtime_env()
    print(verification_report_dict())
