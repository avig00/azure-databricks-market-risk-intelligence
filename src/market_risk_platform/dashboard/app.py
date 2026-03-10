from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from market_risk_platform.config import load_config
from market_risk_platform.simulation import simulate_portfolio
from market_risk_platform.utils import read_dataset


def load_dashboard_data() -> dict[str, pd.DataFrame]:
    config = load_config()
    contracts = config.dataset_contracts()
    return {
        "asset_risk_features": read_dataset(contracts["gold_asset_risk_features"].local_path),
        "market_stress_signals": read_dataset(contracts["gold_market_stress_signals"].local_path),
        "portfolio_risk_metrics": read_dataset(contracts["gold_portfolio_risk_metrics"].local_path),
    }


def build_dashboard_payload() -> dict[str, object]:
    datasets = load_dashboard_data()
    simulation = asdict(simulate_portfolio())
    latest_asset = datasets["asset_risk_features"].sort_values("date").groupby("symbol").tail(1)
    latest_stress = datasets["market_stress_signals"].sort_values("date").tail(1)
    latest_portfolio = datasets["portfolio_risk_metrics"].sort_values("date").tail(1)
    return {
        "portfolio_overview": latest_portfolio.to_dict(orient="records"),
        "market_stress": latest_stress.to_dict(orient="records"),
        "portfolio_simulation": simulation,
        "asset_risk_explorer": latest_asset.to_dict(orient="records"),
    }


def main() -> None:
    import streamlit as st

    payload = build_dashboard_payload()
    st.set_page_config(page_title="Market Risk Intelligence", layout="wide")
    st.title("Azure Databricks Market Risk Intelligence")
    st.subheader("Portfolio Risk Overview")
    st.dataframe(pd.DataFrame(payload["portfolio_overview"]))
    st.subheader("Market Stress Signals")
    st.dataframe(pd.DataFrame(payload["market_stress"]))
    st.subheader("Portfolio Simulation")
    st.json(payload["portfolio_simulation"])
    st.subheader("Asset Risk Explorer")
    st.dataframe(pd.DataFrame(payload["asset_risk_explorer"]))


if __name__ == "__main__":
    main()

