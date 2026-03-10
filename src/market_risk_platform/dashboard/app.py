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


def _latest_asset_snapshot(asset_features: pd.DataFrame) -> pd.DataFrame:
    latest_date = asset_features["date"].max()
    return asset_features[asset_features["date"] == latest_date].sort_values("rolling_volatility_30d", ascending=False)


def _stress_regime(market_stress_index: float) -> str:
    if market_stress_index >= 0.08:
        return "HIGH"
    if market_stress_index >= 0.045:
        return "MEDIUM"
    return "LOW"


def _build_timeseries(asset_features: pd.DataFrame, stress_signals: pd.DataFrame, portfolio_metrics: pd.DataFrame) -> dict[str, list[dict[str, object]]]:
    volatility_trend = (
        asset_features.groupby("date", as_index=False)["rolling_volatility_30d"]
        .mean()
        .rename(columns={"rolling_volatility_30d": "avg_rolling_volatility_30d"})
    )
    drawdown_trend = (
        asset_features.groupby("date", as_index=False)["drawdown"]
        .mean()
        .rename(columns={"drawdown": "avg_drawdown"})
    )
    return {
        "volatility_trend": volatility_trend.to_dict(orient="records"),
        "drawdown_trend": drawdown_trend.to_dict(orient="records"),
        "stress_trend": stress_signals.sort_values("date").to_dict(orient="records"),
        "portfolio_trend": portfolio_metrics.sort_values("date").to_dict(orient="records"),
    }


def summarize_dashboard(payload: dict[str, object]) -> dict[str, object]:
    overview = payload["portfolio_overview"][0]
    stress = payload["market_stress"][0]
    simulation = payload["portfolio_simulation"]
    top_assets = payload["asset_risk_explorer"][:5]
    return {
        "headline_metrics": {
            "portfolio_volatility": overview["portfolio_volatility"],
            "value_at_risk_95": overview["value_at_risk_95"],
            "market_stress_index": stress["market_stress_index"],
            "stress_regime": _stress_regime(stress["market_stress_index"]),
            "simulation_risk_tier": simulation["predicted_risk_tier"],
        },
        "top_volatility_assets": top_assets,
        "simulation": simulation,
    }


def build_dashboard_payload() -> dict[str, object]:
    datasets = load_dashboard_data()
    simulation = asdict(simulate_portfolio())
    latest_asset = _latest_asset_snapshot(datasets["asset_risk_features"])
    latest_stress = datasets["market_stress_signals"].sort_values("date").tail(1)
    latest_portfolio = datasets["portfolio_risk_metrics"].sort_values("date").tail(1)
    correlation_network = (
        datasets["asset_risk_features"][["date", "symbol", "correlation_spike"]]
        .sort_values("date")
        .groupby("symbol")
        .tail(1)
        .sort_values("correlation_spike", ascending=False)
    )
    timeseries = _build_timeseries(
        datasets["asset_risk_features"],
        datasets["market_stress_signals"],
        datasets["portfolio_risk_metrics"],
    )
    return {
        "portfolio_overview": latest_portfolio.to_dict(orient="records"),
        "market_stress": latest_stress.to_dict(orient="records"),
        "portfolio_simulation": simulation,
        "asset_risk_explorer": latest_asset.to_dict(orient="records"),
        "correlation_network": correlation_network.to_dict(orient="records"),
        "timeseries": timeseries,
    }


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Market Risk Intelligence", layout="wide")
    st.title("Azure Databricks Market Risk Intelligence")
    st.caption("Lakehouse-native market risk analytics with simulation-driven portfolio stress testing.")

    available_assets = load_config().portfolio_symbols
    selected_assets = st.sidebar.multiselect(
        "Portfolio assets", options=available_assets, default=available_assets[:3] if len(available_assets) >= 3 else available_assets
    )
    default_weight = round(1 / len(selected_assets), 4) if selected_assets else 0.0
    weights = [
        st.sidebar.number_input(
            f"Weight: {asset}",
            min_value=0.0,
            max_value=1.0,
            value=default_weight,
            step=0.05,
            key=f"weight_{asset}",
        )
        for asset in selected_assets
    ]
    horizon = st.sidebar.selectbox("Simulation horizon", options=[7, 30, 90], index=0)
    simulate_clicked = st.sidebar.button("Run Simulation")
    weight_total = sum(weights)
    st.sidebar.caption(f"Weight total: {weight_total:.2f}")

    payload = build_dashboard_payload()
    if simulate_clicked and selected_assets:
        from market_risk_platform.simulation.portfolio_simulator import simulate_portfolio

        if abs(weight_total - 1.0) > 1e-6:
            st.sidebar.error("Weights must sum to 1.0 to run the simulation.")
        else:
            payload["portfolio_simulation"] = asdict(simulate_portfolio(selected_assets, weights, horizon))

    summary = summarize_dashboard(payload)
    metrics = summary["headline_metrics"]
    metric_columns = st.columns(5)
    metric_columns[0].metric("Portfolio Volatility", f"{metrics['portfolio_volatility']:.3f}")
    metric_columns[1].metric("95% VaR", f"{metrics['value_at_risk_95']:.3f}")
    metric_columns[2].metric("Stress Index", f"{metrics['market_stress_index']:.3f}")
    metric_columns[3].metric("Stress Regime", metrics["stress_regime"])
    metric_columns[4].metric("Risk Tier", metrics["simulation_risk_tier"])

    overview_col, stress_col = st.columns([1.3, 1])
    with overview_col:
        st.subheader("Portfolio Risk Overview")
        st.dataframe(pd.DataFrame(payload["portfolio_overview"]), use_container_width=True)
        st.subheader("Portfolio Simulation")
        st.json(payload["portfolio_simulation"])
        st.subheader("Volatility Trend")
        volatility_trend = pd.DataFrame(payload["timeseries"]["volatility_trend"]).set_index("date")
        st.line_chart(volatility_trend)
    with stress_col:
        st.subheader("Market Stress Signals")
        st.dataframe(pd.DataFrame(payload["market_stress"]), use_container_width=True)
        st.subheader("Correlation Exposure")
        st.dataframe(pd.DataFrame(payload["correlation_network"]), use_container_width=True)
        st.subheader("Stress Trend")
        stress_trend = pd.DataFrame(payload["timeseries"]["stress_trend"]).set_index("date")
        st.line_chart(stress_trend[["market_stress_index", "avg_volatility_30d"]])

    trend_col, asset_col = st.columns([1, 1.2])
    with trend_col:
        st.subheader("Portfolio Drawdown Trend")
        drawdown_trend = pd.DataFrame(payload["timeseries"]["drawdown_trend"]).set_index("date")
        st.area_chart(drawdown_trend)
    with asset_col:
        st.subheader("Asset Risk Explorer")
        st.dataframe(pd.DataFrame(payload["asset_risk_explorer"]), use_container_width=True)


if __name__ == "__main__":
    main()
