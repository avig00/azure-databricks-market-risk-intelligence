from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import altair as alt
import pandas as pd

from market_risk_platform.config import load_config
from market_risk_platform.operations.health import build_health_report
from market_risk_platform.pipeline import run_full_pipeline
from market_risk_platform.simulation import simulate_portfolio
from market_risk_platform.utils import read_dataset


def load_dashboard_data() -> dict[str, pd.DataFrame]:
    config = load_config()
    contracts = config.dataset_contracts()
    return {
        "asset_risk_features": read_dataset(contracts["gold_asset_risk_features"], config),
        "market_stress_signals": read_dataset(contracts["gold_market_stress_signals"], config),
        "portfolio_risk_metrics": read_dataset(contracts["gold_portfolio_risk_metrics"], config),
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


def _build_timeseries(
    asset_features: pd.DataFrame, stress_signals: pd.DataFrame, portfolio_metrics: pd.DataFrame
) -> dict[str, list[dict[str, object]]]:
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
            "snapshot_portfolio_volatility": overview["portfolio_volatility"],
            "snapshot_value_at_risk_95": overview["value_at_risk_95"],
            "snapshot_market_stress_index": stress["market_stress_index"],
            "snapshot_stress_regime": _stress_regime(stress["market_stress_index"]),
            # Backward-compatible aliases for tests and any older callers.
            "portfolio_volatility": overview["portfolio_volatility"],
            "value_at_risk_95": overview["value_at_risk_95"],
            "market_stress_index": stress["market_stress_index"],
            "stress_regime": _stress_regime(stress["market_stress_index"]),
            "simulation_risk_tier": simulation["predicted_risk_tier"],
        },
        "top_volatility_assets": top_assets,
        "simulation": simulation,
        "health": payload.get("health", build_health_report().__dict__),
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
        "metadata": {
            "data_mode": "sample",
            "data_note": "Sample Gold-layer datasets bundled with the repo",
        },
    }


def _format_decimal(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _format_percent(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def _prepare_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    if "date" in display.columns:
        display["date"] = pd.to_datetime(display["date"]).dt.strftime("%Y-%m-%d")
    return display


def _build_combined_snapshot(overview: pd.DataFrame, stress: pd.DataFrame, stress_regime: str) -> pd.DataFrame:
    overview_row = overview.iloc[0].to_dict()
    stress_row = stress.iloc[0].to_dict()
    combined = {
        "date": overview_row.get("date", stress_row.get("date")),
        "portfolio_volatility": overview_row.get("portfolio_volatility"),
        "value_at_risk_95": overview_row.get("value_at_risk_95"),
        "expected_drawdown": overview_row.get("expected_drawdown"),
        "correlation_spike": overview_row.get("correlation_spike"),
        "macro_shock_score": overview_row.get("macro_shock_score"),
        "market_stress_index": stress_row.get("market_stress_index"),
        "stress_regime": stress_regime,
    }
    return _prepare_display_frame(pd.DataFrame([combined]))


def _risk_tone(label: str) -> str:
    return {
        "LOW": "Stable",
        "MEDIUM": "Watchlist",
        "HIGH": "Elevated",
        "STABLE": "Stable",
        "ELEVATED": "Elevated",
    }.get(label, label.title())


def _normalize_weights(weights: list[float]) -> list[float]:
    total = sum(weights)
    if total <= 0:
        return weights
    return [weight / total for weight in weights]


def _build_insight_cards(payload: dict[str, object], summary: dict[str, object]) -> list[dict[str, str]]:
    top_asset = payload["asset_risk_explorer"][0]
    simulation = payload["portfolio_simulation"]
    stress_index = summary["headline_metrics"]["snapshot_market_stress_index"]
    return [
        {
            "title": "Snapshot: Top Risk Concentration",
            "value": top_asset["symbol"],
            "detail": f"Latest pipeline snapshot shows the highest 30d volatility at {_format_percent(top_asset['rolling_volatility_30d'])}.",
        },
        {
            "title": "Snapshot: Stress Regime",
            "value": _risk_tone(summary["headline_metrics"]["snapshot_stress_regime"]),
            "detail": f"Market stress index is {_format_decimal(stress_index)} based on latest Gold-layer signals.",
        },
        {
            "title": "Simulation Outlook",
            "value": simulation["predicted_risk_tier"],
            "detail": (
                "Your selected portfolio projects future volatility of "
                f"{_format_percent(simulation['predicted_future_volatility'])} over the selected horizon."
            ),
        },
    ]


def _build_health_table(summary: dict[str, object]) -> pd.DataFrame:
    health = summary["health"]
    return pd.DataFrame(
        [
            {"check": "storage backend", "value": health.get("storage_backend", "unknown")},
            {"check": "runtime mode", "value": health.get("runtime_mode", "unknown")},
            {"check": "latest pipeline stage", "value": health.get("latest_stage", health.get("latest_successful_stage", "not recorded")) or "not recorded"},
            {"check": "pipeline status", "value": health.get("latest_status", "success" if health.get("checks_passed") else "unknown")},
            {"check": "fresh datasets", "value": str(health.get("checks_passed", False))},
        ]
    )


def _correlation_narrative(correlation: pd.DataFrame) -> str:
    if correlation.empty:
        return "Correlation exposure is unavailable for the current sample."
    rounded = correlation["correlation_spike"].round(6)
    if rounded.nunique() == 1:
        return (
            "Correlation exposure is currently uniform across the tracked assets at "
            f"{_format_decimal(float(correlation.iloc[0]['correlation_spike']))}."
        )
    top_value = float(correlation.iloc[0]["correlation_spike"])
    leaders = correlation[correlation["correlation_spike"].round(6) == round(top_value, 6)]["symbol"].tolist()
    if len(leaders) > 1:
        leader_text = ", ".join(leaders[:-1]) + f" and {leaders[-1]}" if len(leaders) > 2 else " and ".join(leaders)
        return (
            f"{leader_text} currently share the highest correlation exposure at "
            f"{_format_decimal(top_value)}."
        )
    return (
        f"{leaders[0]} currently leads correlation exposure with a reading of "
        f"{_format_decimal(top_value)}."
    )


def _line_chart(
    frame: pd.DataFrame, x: str, y_columns: list[str], color_range: list[str], y_title: str = ""
) -> alt.Chart:
    chart_data = frame.reset_index().melt(id_vars=[x], value_vars=y_columns, var_name="series", value_name="value")
    return (
        alt.Chart(chart_data)
        .mark_line(strokeWidth=2.5)
        .encode(
            x=alt.X(f"{x}:T", title="Date"),
            y=alt.Y("value:Q", title=y_title or ""),
            color=alt.Color("series:N", scale=alt.Scale(domain=y_columns, range=color_range), legend=alt.Legend(title="")),
            tooltip=[alt.Tooltip(f"{x}:T", title="Date"), alt.Tooltip("series:N", title="Series"), alt.Tooltip("value:Q", title="Value", format=".4f")],
        )
        .properties(height=280)
    )


def _area_chart(frame: pd.DataFrame, x: str, y: str, fill: str, line: str, y_title: str = "") -> alt.Chart:
    chart_data = frame.reset_index()
    area = (
        alt.Chart(chart_data)
        .mark_area(line={"color": line}, color=fill, opacity=0.88)
        .encode(
            x=alt.X(f"{x}:T", title="Date"),
            y=alt.Y(f"{y}:Q", title=y_title or ""),
            tooltip=[alt.Tooltip(f"{x}:T", title="Date"), alt.Tooltip(f"{y}:Q", title="Value", format=".4f")],
        )
        .properties(height=280)
    )
    return area


def _dataset_setup_message() -> str:
    config = load_config()
    sample_path = config.dataset_contracts()["gold_asset_risk_features"].local_path
    return (
        "The dashboard could not find the Gold-layer datasets it needs. "
        f"Expected local sample data such as `{sample_path}` or a configured Databricks-backed runtime. "
        "Run the ingestion and feature-building pipeline first, then reload the app."
    )


def _bootstrap_sample_data() -> bool:
    config = load_config()
    if not config.use_sample_data:
        return False
    run_full_pipeline()
    return True


def _safe_build_payload() -> tuple[dict[str, object] | None, str | None]:
    try:
        return build_dashboard_payload(), None
    except FileNotFoundError:
        try:
            bootstrapped = _bootstrap_sample_data()
        except Exception as exc:  # pragma: no cover - UI guardrail
            return None, f"{_dataset_setup_message()} Bootstrap failed: {exc}"
        if not bootstrapped:
            return None, _dataset_setup_message()
        try:
            return build_dashboard_payload(), None
        except Exception as exc:  # pragma: no cover - UI guardrail
            return None, f"{_dataset_setup_message()} Bootstrap completed but reload failed: {exc}"
    except Exception as exc:  # pragma: no cover - UI guardrail
        return None, str(exc)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Market Risk Intelligence", layout="wide")
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(17, 122, 101, 0.14), transparent 34%),
                linear-gradient(180deg, #f4fbf7 0%, #e8f4ee 100%);
        }
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(21, 53, 45, 0.08);
            border-radius: 16px;
            padding: 0.9rem 1rem;
            box-shadow: 0 10px 28px rgba(20, 48, 41, 0.06);
        }
        .dashboard-card {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(21, 53, 45, 0.08);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            min-height: 150px;
            box-shadow: 0 12px 28px rgba(20, 48, 41, 0.06);
        }
        .dashboard-card h4 {
            margin: 0 0 0.35rem 0;
            color: #16352f;
            font-size: 0.95rem;
        }
        .dashboard-card .value {
            font-size: 1.65rem;
            font-weight: 700;
            color: #117a65;
            margin-bottom: 0.45rem;
        }
        .dashboard-hero {
            background: linear-gradient(120deg, rgba(15, 98, 79, 0.97), rgba(32, 138, 97, 0.88));
            color: white;
            border-radius: 24px;
            padding: 1.35rem 1.4rem;
            margin-bottom: 1rem;
            box-shadow: 0 18px 36px rgba(16, 94, 77, 0.2);
        }
        .dashboard-hero h1 {
            margin: 0;
            color: white;
            font-size: 2rem;
        }
        .dashboard-hero p {
            margin: 0.45rem 0 0 0;
            color: rgba(255, 255, 255, 0.88);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="dashboard-hero">
            <h1>Market Risk Intelligence</h1>
            <p>
                Portfolio stress testing, volatility monitoring, and scenario simulation for a
                lakehouse-native market risk platform.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    config = load_config()
    available_assets = config.portfolio_symbols

    st.sidebar.header("Simulation Controls")
    st.sidebar.caption("Use this panel to pressure-test a custom portfolio allocation.")
    selected_assets = st.sidebar.multiselect(
        "Portfolio assets",
        options=available_assets,
        default=available_assets[:3] if len(available_assets) >= 3 else available_assets,
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
    auto_normalize = st.sidebar.checkbox("Auto-normalize weights", value=True)
    horizon = st.sidebar.selectbox("Simulation horizon", options=[7, 30, 90], index=0)
    simulate_clicked = st.sidebar.button("Run Simulation", type="primary")
    weight_total = sum(weights)
    st.sidebar.caption(f"Weight total: {weight_total:.2f}")
    payload, error = _safe_build_payload()

    if payload is None:
        st.error(error or "Dashboard data could not be loaded.")
        st.info(
            "Suggested next step: run the local ingestion, silver, gold, feature, and model training "
            "commands before reopening the dashboard."
        )
        st.stop()

    if "simulation_has_run" not in st.session_state:
        st.session_state["simulation_has_run"] = False
    if "last_simulation" not in st.session_state:
        st.session_state["last_simulation"] = None

    if simulate_clicked and selected_assets:
        adjusted_weights = _normalize_weights(weights) if auto_normalize else weights
        if not auto_normalize and abs(weight_total - 1.0) > 1e-6:
            st.sidebar.error("Weights must sum to 1.0 to run the simulation.")
        else:
            payload["portfolio_simulation"] = asdict(simulate_portfolio(selected_assets, adjusted_weights, horizon))
            st.session_state["last_simulation"] = payload["portfolio_simulation"]
            st.session_state["simulation_has_run"] = True
            if auto_normalize and abs(weight_total - 1.0) > 1e-6:
                st.sidebar.success("Weights were normalized automatically for the simulation run.")
    elif st.session_state["simulation_has_run"] and st.session_state["last_simulation"] is not None:
        payload["portfolio_simulation"] = st.session_state["last_simulation"]

    summary = summarize_dashboard(payload)

    overview = pd.DataFrame(payload["portfolio_overview"])
    stress = pd.DataFrame(payload["market_stress"])
    asset_risk = pd.DataFrame(payload["asset_risk_explorer"])
    correlation = pd.DataFrame(payload["correlation_network"])
    if selected_assets:
        asset_risk = asset_risk[asset_risk["symbol"].isin(selected_assets)].reset_index(drop=True)
        correlation = correlation[correlation["symbol"].isin(selected_assets)].reset_index(drop=True)
    simulation = payload["portfolio_simulation"]
    simulation_has_run = st.session_state["simulation_has_run"]
    metrics = summary["headline_metrics"]
    insights = _build_insight_cards(payload, summary)
    snapshot_display = _build_combined_snapshot(overview, stress, metrics["snapshot_stress_regime"])
    asset_risk_display = _prepare_display_frame(asset_risk)
    correlation_display = _prepare_display_frame(correlation)

    meta_left, meta_right = st.columns([1.5, 1])
    with meta_left:
        st.caption(
            f"Runtime: `{config.runtime_mode}` | Storage backend: `{config.storage_backend}` | "
            f"Catalog: `{config.catalog.catalog}`"
        )
    with meta_right:
        latest_date = pd.to_datetime(asset_risk["date"]).max().date()
        st.caption(f"Latest pipeline snapshot date: `{latest_date.isoformat()}`")

    st.markdown("#### Latest Pipeline Snapshot")
    st.caption(
        "These cards reflect the most recent Gold-layer baseline produced by the pipeline. "
        "They provide current market context and do not change when you rerun a sidebar simulation."
    )
    snapshot_metric_columns = st.columns(4)
    snapshot_metric_columns[0].metric("Volatility", _format_percent(metrics["snapshot_portfolio_volatility"]))
    snapshot_metric_columns[1].metric("95% VaR", _format_percent(metrics["snapshot_value_at_risk_95"]))
    snapshot_metric_columns[2].metric("Stress Index", _format_decimal(metrics["snapshot_market_stress_index"]))
    snapshot_metric_columns[3].metric("Stress Regime", metrics["snapshot_stress_regime"])

    snapshot_insight_columns = st.columns(2)
    for column, card in zip(snapshot_insight_columns, insights[:2]):
        column.markdown(
            f"""
            <div class="dashboard-card">
                <h4>{card["title"]}</h4>
                <div class="value">{card["value"]}</div>
                <div>{card["detail"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    if simulation_has_run:
        st.markdown("#### Custom Simulation")
        st.caption(
            "These cards reflect the latest successful run using the assets, weights, and horizon "
            "selected in the sidebar."
        )
        st.markdown(
            f"""
            <div class="dashboard-card">
                <h4>{insights[2]["title"]}</h4>
                <div class="value">{insights[2]["value"]}</div>
                <div>{insights[2]["detail"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown("#### Custom Simulation")
        st.caption("No custom simulation has been run yet.")
        st.info("Choose assets, weights, and a horizon in the sidebar, then click Run Simulation to populate this section.")

    overview_tab, trends_tab, assets_tab, ops_tab = st.tabs(
        ["Executive View", "Trend Analysis", "Asset Drilldown", "Operations"]
    )

    with overview_tab:
        top_left, top_right = st.columns([1.2, 0.8])
        with top_left:
            st.subheader("Latest Pipeline Snapshot")
            st.caption(
                "Combined baseline view from the most recent pipeline date. "
                "Use this as the current market backdrop, not your custom simulation result."
            )
            st.dataframe(snapshot_display, use_container_width=True, hide_index=True)
            st.subheader("Custom Portfolio Simulation")
            if simulation_has_run:
                st.caption(
                    "Scenario result for the assets, weights, and horizon from the latest successful run."
                )
                sim_cols = st.columns(5)
                sim_cols[0].metric("Horizon", f"{simulation['horizon']}d")
                sim_cols[1].metric("Future Volatility", _format_percent(simulation["predicted_future_volatility"]))
                sim_cols[2].metric("95% VaR", _format_percent(simulation["value_at_risk_95"]))
                sim_cols[3].metric("Drawdown", _format_percent(simulation["expected_drawdown"]))
                sim_cols[4].metric("Corr Exposure", _format_decimal(simulation["correlation_exposure"]))
                st.json(simulation)
            else:
                st.caption("Run a custom simulation from the sidebar to populate this section.")
                st.info("No custom simulation has been run yet.")
        with top_right:
            st.subheader("Snapshot Stress Context")
            st.caption("Stress summary from the same latest pipeline snapshot shown on the left.")
            stress_cols = st.columns(2)
            stress_cols[0].metric("Stress Index", _format_decimal(metrics["snapshot_market_stress_index"]))
            stress_cols[1].metric("Stress Regime", metrics["snapshot_stress_regime"])
            st.subheader("Operating Notes")
            st.markdown(
                """
                - The snapshot table combines baseline portfolio and stress context from the latest Gold-layer datasets.
                - Custom simulations reuse the trained risk classifier and volatility model for your selected portfolio.
                - This MVP is designed to show portfolio sensitivity, not trade execution.
                """
            )

    with trends_tab:
        if not simulation_has_run:
            st.info("Run a custom simulation from the sidebar to unlock the trend analysis view.")
        else:
            trend_left, trend_right = st.columns(2)
            with trend_left:
                st.subheader("Average Volatility Trend")
                volatility_trend = pd.DataFrame(payload["timeseries"]["volatility_trend"]).set_index("date")
                st.altair_chart(
                    _line_chart(
                        volatility_trend,
                        "date",
                        list(volatility_trend.columns),
                        ["#117a65"],
                        y_title="Volatility",
                    ),
                    use_container_width=True,
                )
                st.subheader("Average Drawdown Trend")
                drawdown_trend = pd.DataFrame(payload["timeseries"]["drawdown_trend"]).set_index("date")
                st.altair_chart(
                    _area_chart(drawdown_trend, "date", "avg_drawdown", "#7bc6a4", "#117a65", y_title="Drawdown"),
                    use_container_width=True,
                )
            with trend_right:
                st.subheader("Stress Trend")
                stress_trend = pd.DataFrame(payload["timeseries"]["stress_trend"]).set_index("date")
                st.altair_chart(
                    _line_chart(
                        stress_trend,
                        "date",
                        ["market_stress_index", "avg_volatility_30d"],
                        ["#3aa17e", "#117a65"],
                        y_title="Stress",
                    ),
                    use_container_width=True,
                )
                st.subheader("Portfolio Trend")
                portfolio_trend = pd.DataFrame(payload["timeseries"]["portfolio_trend"]).set_index("date")
                chart_columns = [col for col in ["portfolio_volatility", "value_at_risk_95"] if col in portfolio_trend.columns]
                st.altair_chart(
                    _line_chart(
                        portfolio_trend,
                        "date",
                        chart_columns,
                        ["#117a65", "#66b68f"][: len(chart_columns)],
                        y_title="Portfolio Metrics",
                    ),
                    use_container_width=True,
                )

    with assets_tab:
        if not simulation_has_run:
            st.info("Run a custom simulation from the sidebar to unlock the asset drilldown view.")
        else:
            drill_left, drill_right = st.columns([1.25, 1])
            with drill_left:
                st.subheader("Asset Risk Explorer")
                if selected_assets:
                    st.caption("Latest snapshot for the assets currently selected in the simulation sidebar.")
                display_columns = [
                    "symbol",
                    "rolling_volatility_30d",
                    "drawdown",
                    "correlation_spike",
                    "macro_shock_score",
                ]
                st.dataframe(asset_risk_display[display_columns], use_container_width=True, hide_index=True)
            with drill_right:
                st.subheader("Correlation Exposure")
                if selected_assets:
                    st.caption("Per-asset correlation exposure for the currently selected portfolio components.")
                st.dataframe(correlation_display, use_container_width=True, hide_index=True)
                st.subheader("Current Narrative")
                st.info(_correlation_narrative(correlation_display))

    with ops_tab:
        ops_left, ops_right = st.columns([1, 1.1])
        with ops_left:
            st.subheader("Platform Health")
            st.dataframe(_build_health_table(summary), use_container_width=True, hide_index=True)
        with ops_right:
            st.subheader("Deployment Context")
            contracts = config.dataset_contracts()
            st.code(
                "\n".join(
                    [
                        f"gold asset features: {Path(contracts['gold_asset_risk_features'].local_path)}",
                        f"gold market stress: {Path(contracts['gold_market_stress_signals'].local_path)}",
                        f"gold portfolio metrics: {Path(contracts['gold_portfolio_risk_metrics'].local_path)}",
                    ]
                ),
                language="text",
            )
            st.caption(
                "These paths are used in local mode. In Databricks mode, the same contracts resolve to "
                "catalog-backed Delta tables and ADLS paths."
            )


if __name__ == "__main__":
    main()
