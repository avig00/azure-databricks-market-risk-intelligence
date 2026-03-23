from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yfinance as yf

from market_risk_platform.config import load_config
from market_risk_platform.ml.train_risk_classifier import RISK_FEATURES
from market_risk_platform.ml.train_volatility_model import VOL_FEATURES
from market_risk_platform.operations.health import build_health_report
from market_risk_platform.simulation import simulate_portfolio
from market_risk_platform.data_ingestion.providers import split_index_and_assets
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


def _rolling_drawdown(close_series: pd.Series) -> pd.Series:
    running_max = close_series.cummax()
    return (close_series / running_max) - 1.0


def _build_correlation_frame(daily_returns: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    pivot = daily_returns.pivot(index="date", columns="symbol", values="daily_return").fillna(0.0)
    records: list[dict[str, object]] = []
    for idx in range(window - 1, len(pivot)):
        window_frame = pivot.iloc[idx - window + 1 : idx + 1]
        corr_matrix = window_frame.corr()
        as_of_date = pivot.index[idx]
        for symbol_a in corr_matrix.index:
            for symbol_b in corr_matrix.columns:
                if symbol_a >= symbol_b:
                    continue
                records.append(
                    {
                        "date": as_of_date,
                        "symbol_a": symbol_a,
                        "symbol_b": symbol_b,
                        "correlation": float(corr_matrix.loc[symbol_a, symbol_b]),
                    }
                )
    return pd.DataFrame(records)


def _fetch_live_prices(symbols: list[str], start_date: str) -> pd.DataFrame:
    data = yf.download(symbols, start=start_date, auto_adjust=False, progress=False, group_by="ticker")
    if data.empty:
        raise ValueError("Yahoo Finance returned no market data")
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        symbol_frame = data[symbol].reset_index() if isinstance(data.columns, pd.MultiIndex) else data.reset_index()
        if symbol_frame.empty:
            continue
        symbol_frame = symbol_frame.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            }
        )
        symbol_frame["symbol"] = symbol
        symbol_frame["source"] = "yfinance"
        frames.append(symbol_frame[["date", "symbol", "open", "high", "low", "close", "adj_close", "volume", "source"]])
    if not frames:
        raise ValueError("Yahoo Finance did not return supported ticker data")
    return pd.concat(frames, ignore_index=True)


def _fetch_live_macro(config: Any, start_date: str) -> tuple[pd.DataFrame, bool]:
    if not config.fred_api_key:
        return pd.DataFrame(columns=["date", "series_id", "value", "source"]), False
    from fredapi import Fred

    fred = Fred(api_key=config.fred_api_key)
    rows: list[dict[str, object]] = []
    for series_id in config.fred_series:
        series = fred.get_series(series_id, observation_start=start_date)
        for date, value in series.items():
            rows.append(
                {
                    "date": pd.Timestamp(date),
                    "series_id": series_id,
                    "value": float(value),
                    "source": "fred",
                }
            )
    return pd.DataFrame(rows), True


def _build_live_asset_features(config: Any) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    end_date = pd.Timestamp.today().normalize()
    price_start = (end_date - pd.Timedelta(days=420)).strftime("%Y-%m-%d")
    macro_start = (end_date - pd.Timedelta(days=540)).strftime("%Y-%m-%d")
    price_df = _fetch_live_prices(config.market_symbols, price_start)
    stock_prices, _market_indices = split_index_and_assets(price_df)
    stock_prices = stock_prices.sort_values(["symbol", "date"])
    stock_prices["daily_return"] = stock_prices.groupby("symbol")["adj_close"].pct_change().fillna(0.0)
    daily_returns = stock_prices[["date", "symbol", "daily_return"]].copy()
    metrics = daily_returns.copy()
    for window in (7, 30, 90):
        metrics[f"rolling_volatility_{window}d"] = (
            metrics.groupby("symbol")["daily_return"].transform(lambda s: s.rolling(window).std(ddof=0)).fillna(0.0)
        )
    drawdowns = stock_prices[["date", "symbol", "adj_close"]].copy()
    drawdowns["drawdown"] = stock_prices.groupby("symbol")["adj_close"].transform(_rolling_drawdown)
    corr = _build_correlation_frame(daily_returns, window=30)
    corr_agg = corr.groupby("date", as_index=False)["correlation"].mean().rename(columns={"correlation": "mean_correlation"})
    macro_df, fred_enabled = _fetch_live_macro(config, macro_start)
    if macro_df.empty:
        macro_daily = pd.DataFrame({"date": metrics["date"].drop_duplicates().sort_values(), "macro_shock_score": 0.0})
    else:
        macro_df["macro_shock_score"] = macro_df.groupby("series_id")["value"].pct_change().fillna(0.0).abs()
        macro_daily = macro_df.groupby("date", as_index=False)["macro_shock_score"].mean()
    asset_features = metrics.merge(drawdowns[["date", "symbol", "drawdown"]], on=["date", "symbol"], how="left")
    asset_features["momentum_signal"] = asset_features.groupby("symbol")["daily_return"].transform(lambda s: s.rolling(14).mean()).fillna(0.0)
    asset_features = asset_features.merge(corr_agg, on="date", how="left").merge(macro_daily, on="date", how="left")
    asset_features["correlation_spike"] = asset_features["mean_correlation"].fillna(0.0)
    asset_features["macro_shock_score"] = asset_features["macro_shock_score"].fillna(0.0)
    asset_features["future_volatility_7d"] = asset_features.groupby("symbol")["rolling_volatility_7d"].shift(-7).fillna(
        asset_features["rolling_volatility_7d"]
    )
    stress = (
        asset_features.groupby("date", as_index=False)[["rolling_volatility_30d", "drawdown", "correlation_spike", "macro_shock_score"]]
        .mean()
        .rename(columns={"rolling_volatility_30d": "avg_volatility_30d"})
    )
    stress["market_stress_index"] = (
        stress["avg_volatility_30d"] * 0.4
        + stress["drawdown"].abs() * 0.2
        + stress["correlation_spike"].clip(lower=0) * 0.2
        + stress["macro_shock_score"].clip(lower=0) * 0.2
    )
    portfolio = (
        asset_features.groupby("date", as_index=False)[["rolling_volatility_30d", "drawdown", "correlation_spike", "macro_shock_score"]]
        .mean()
        .rename(columns={"rolling_volatility_30d": "portfolio_volatility", "drawdown": "expected_drawdown"})
    )
    portfolio["value_at_risk_95"] = portfolio["portfolio_volatility"] * 1.65
    metadata = {
        "data_mode": "live",
        "data_note": "Yahoo Finance live market data with optional FRED macro enrichment",
        "fred_enabled": fred_enabled,
        "price_start": price_start,
    }
    return asset_features, stress, portfolio, metadata


def _build_live_simulation(asset_features: pd.DataFrame, config: Any, assets: list[str], weights: list[float], horizon: int) -> dict[str, object]:
    latest = asset_features.sort_values("date").groupby("symbol").tail(1).set_index("symbol")
    selected_assets = assets or config.portfolio_symbols[:3]
    missing = [asset for asset in selected_assets if asset not in latest.index]
    if missing:
        raise ValueError(f"Live data is missing assets: {', '.join(missing)}")
    chosen = latest.loc[selected_assets]
    chosen_weights = np.array(weights or [1 / len(selected_assets)] * len(selected_assets))
    portfolio_vol = float(np.dot(chosen_weights, chosen["rolling_volatility_30d"]))
    expected_drawdown = float(np.dot(chosen_weights, chosen["drawdown"]))
    correlation_exposure = float(chosen["correlation_spike"].mean())
    macro_shock = float(chosen["macro_shock_score"].mean())
    value_at_risk_95 = abs(portfolio_vol) * 1.65 * np.sqrt(horizon / 7)
    predicted_risk_tier = "MEDIUM"
    predicted_future_volatility = float(np.dot(chosen_weights, chosen["rolling_volatility_7d"]))
    try:
        risk_model = joblib.load(config.artifact_root / "risk_classifier.joblib")
        vol_model = joblib.load(config.artifact_root / "volatility_model.joblib")
        risk_frame = {
            "portfolio_volatility": portfolio_vol,
            "expected_drawdown": expected_drawdown,
            "correlation_spike": correlation_exposure,
            "macro_shock_score": macro_shock,
            "value_at_risk_95": value_at_risk_95,
        }
        predicted_risk_tier = str(risk_model.predict(pd.DataFrame([risk_frame], columns=RISK_FEATURES))[0])
        predicted_future_volatility = float(np.dot(chosen_weights, vol_model.predict(chosen[VOL_FEATURES].copy())))
    except FileNotFoundError:
        if value_at_risk_95 >= 0.035:
            predicted_risk_tier = "HIGH"
        elif value_at_risk_95 >= 0.02:
            predicted_risk_tier = "MEDIUM"
        else:
            predicted_risk_tier = "LOW"
    return {
        "horizon": horizon,
        "portfolio_volatility": portfolio_vol,
        "value_at_risk_95": value_at_risk_95,
        "expected_drawdown": expected_drawdown,
        "correlation_exposure": correlation_exposure,
        "predicted_risk_tier": predicted_risk_tier,
        "predicted_future_volatility": predicted_future_volatility,
    }


def build_live_dashboard_payload(config: Any, assets: list[str] | None = None, weights: list[float] | None = None, horizon: int = 7) -> dict[str, object]:
    asset_features, stress, portfolio, metadata = _build_live_asset_features(config)
    simulation = _build_live_simulation(asset_features, config, assets or [], weights or [], horizon)
    latest_asset = _latest_asset_snapshot(asset_features)
    latest_stress = stress.sort_values("date").tail(1)
    latest_portfolio = portfolio.sort_values("date").tail(1)
    correlation_network = (
        asset_features[["date", "symbol", "correlation_spike"]]
        .sort_values("date")
        .groupby("symbol")
        .tail(1)
        .sort_values("correlation_spike", ascending=False)
    )
    timeseries = _build_timeseries(asset_features, stress, portfolio)
    return {
        "portfolio_overview": latest_portfolio.to_dict(orient="records"),
        "market_stress": latest_stress.to_dict(orient="records"),
        "portfolio_simulation": simulation,
        "asset_risk_explorer": latest_asset.to_dict(orient="records"),
        "correlation_network": correlation_network.to_dict(orient="records"),
        "timeseries": timeseries,
        "health": {
            "runtime_mode": "live-api",
            "storage_backend": "external-api",
            "latest_stage": "live_market_fetch",
            "latest_status": "success",
            "checks_passed": True,
        },
        "metadata": metadata,
    }


def _format_decimal(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _format_percent(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def _risk_tone(label: str) -> str:
    return {
        "LOW": "Stable",
        "MEDIUM": "Watchlist",
        "HIGH": "Elevated",
    }.get(label, label.title())


def _normalize_weights(weights: list[float]) -> list[float]:
    total = sum(weights)
    if total <= 0:
        return weights
    return [weight / total for weight in weights]


def _build_insight_cards(payload: dict[str, object], summary: dict[str, object]) -> list[dict[str, str]]:
    top_asset = payload["asset_risk_explorer"][0]
    simulation = payload["portfolio_simulation"]
    stress_index = summary["headline_metrics"]["market_stress_index"]
    return [
        {
            "title": "Top Risk Concentration",
            "value": top_asset["symbol"],
            "detail": f"Highest 30d volatility at {_format_percent(top_asset['rolling_volatility_30d'])}.",
        },
        {
            "title": "Stress Regime",
            "value": _risk_tone(summary["headline_metrics"]["stress_regime"]),
            "detail": f"Market stress index is {_format_decimal(stress_index)} based on latest Gold-layer signals.",
        },
        {
            "title": "Simulation Outlook",
            "value": simulation["predicted_risk_tier"],
            "detail": (
                "Projected future volatility is "
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


def _dataset_setup_message() -> str:
    config = load_config()
    sample_path = config.dataset_contracts()["gold_asset_risk_features"].local_path
    return (
        "The dashboard could not find the Gold-layer datasets it needs. "
        f"Expected local sample data such as `{sample_path}` or a configured Databricks-backed runtime. "
        "Run the ingestion and feature-building pipeline first, then reload the app."
    )


def _safe_build_payload() -> tuple[dict[str, object] | None, str | None]:
    try:
        return build_dashboard_payload(), None
    except FileNotFoundError:
        return None, _dataset_setup_message()
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

    st.sidebar.header("Data Source")
    data_mode = st.sidebar.radio("Dashboard mode", options=["Sample datasets", "Live market data"], index=0)
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

    if data_mode == "Live market data":
        st.sidebar.caption("Live mode pulls fresh Yahoo Finance data and uses FRED only if `FRED_API_KEY` is configured.")
        try:
            adjusted_weights = _normalize_weights(weights) if selected_assets and auto_normalize else weights
            payload = build_live_dashboard_payload(config, selected_assets, adjusted_weights, horizon)
            error = None
        except Exception as exc:  # pragma: no cover - UI guardrail
            payload, error = None, str(exc)
    else:
        payload, error = _safe_build_payload()

    if payload is None:
        st.error(error or "Dashboard data could not be loaded.")
        st.info(
            "Suggested next step: run the local ingestion, silver, gold, feature, and model training "
            "commands before reopening the dashboard."
        )
        st.stop()

    summary = summarize_dashboard(payload)

    if simulate_clicked and selected_assets:
        adjusted_weights = _normalize_weights(weights) if auto_normalize else weights
        if not auto_normalize and abs(weight_total - 1.0) > 1e-6:
            st.sidebar.error("Weights must sum to 1.0 to run the simulation.")
        else:
            if data_mode == "Live market data":
                asset_features, _stress, _portfolio, _metadata = _build_live_asset_features(config)
                payload["portfolio_simulation"] = _build_live_simulation(asset_features, config, selected_assets, adjusted_weights, horizon)
            else:
                payload["portfolio_simulation"] = asdict(simulate_portfolio(selected_assets, adjusted_weights, horizon))
            summary = summarize_dashboard(payload)
            if auto_normalize and abs(weight_total - 1.0) > 1e-6:
                st.sidebar.success("Weights were normalized automatically for the simulation run.")

    overview = pd.DataFrame(payload["portfolio_overview"])
    stress = pd.DataFrame(payload["market_stress"])
    asset_risk = pd.DataFrame(payload["asset_risk_explorer"])
    correlation = pd.DataFrame(payload["correlation_network"])
    simulation = payload["portfolio_simulation"]
    metrics = summary["headline_metrics"]
    insights = _build_insight_cards(payload, summary)

    meta_left, meta_right = st.columns([1.5, 1])
    with meta_left:
        metadata = payload.get("metadata", {})
        if metadata.get("data_mode") == "live":
            fred_status = "enabled" if metadata.get("fred_enabled") else "not configured"
            st.caption(
                f"Runtime: `live-api` | Sources: `Yahoo Finance` + `FRED ({fred_status})` | "
                f"Fetch window start: `{metadata.get('price_start')}`"
            )
        else:
            st.caption(
                f"Runtime: `{config.runtime_mode}` | Storage backend: `{config.storage_backend}` | "
                f"Catalog: `{config.catalog.catalog}`"
            )
    with meta_right:
        latest_date = pd.to_datetime(asset_risk["date"]).max().date()
        st.caption(f"Latest dataset snapshot: `{latest_date.isoformat()}`")

    metric_columns = st.columns(5)
    metric_columns[0].metric("Portfolio Volatility", _format_percent(metrics["portfolio_volatility"]))
    metric_columns[1].metric("95% VaR", _format_percent(metrics["value_at_risk_95"]))
    metric_columns[2].metric("Stress Index", _format_decimal(metrics["market_stress_index"]))
    metric_columns[3].metric("Stress Regime", metrics["stress_regime"])
    metric_columns[4].metric("Risk Tier", metrics["simulation_risk_tier"])

    insight_columns = st.columns(3)
    for column, card in zip(insight_columns, insights):
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

    overview_tab, trends_tab, assets_tab, ops_tab = st.tabs(
        ["Executive View", "Trend Analysis", "Asset Drilldown", "Operations"]
    )

    with overview_tab:
        top_left, top_right = st.columns([1.2, 0.8])
        with top_left:
            st.subheader("Portfolio Risk Overview")
            st.dataframe(overview, use_container_width=True, hide_index=True)
            st.subheader("Portfolio Simulation")
            sim_cols = st.columns(4)
            sim_cols[0].metric("Horizon", f"{simulation['horizon']}d")
            sim_cols[1].metric("Future Volatility", _format_percent(simulation["predicted_future_volatility"]))
            sim_cols[2].metric("Expected Drawdown", _format_percent(simulation["expected_drawdown"]))
            sim_cols[3].metric("Correlation Exposure", _format_decimal(simulation["correlation_exposure"]))
            st.json(simulation)
        with top_right:
            st.subheader("Market Stress Snapshot")
            st.dataframe(stress, use_container_width=True, hide_index=True)
            st.subheader("Operating Notes")
            if payload.get("metadata", {}).get("data_mode") == "live":
                st.markdown(
                    """
                    - Live mode pulls fresh market data from Yahoo Finance on demand.
                    - FRED enrichment is used only when `FRED_API_KEY` is configured.
                    - Custom simulations reuse the packaged local model artifacts when available.
                    """
                )
            else:
                st.markdown(
                    """
                    - The dashboard uses the latest Gold-layer datasets and model artifacts.
                    - Custom simulations reuse the trained risk classifier and volatility model.
                    - This MVP is designed to show portfolio sensitivity, not trade execution.
                    """
                )

    with trends_tab:
        trend_left, trend_right = st.columns(2)
        with trend_left:
            st.subheader("Average Volatility Trend")
            volatility_trend = pd.DataFrame(payload["timeseries"]["volatility_trend"]).set_index("date")
            st.line_chart(volatility_trend)
            st.subheader("Average Drawdown Trend")
            drawdown_trend = pd.DataFrame(payload["timeseries"]["drawdown_trend"]).set_index("date")
            st.area_chart(drawdown_trend)
        with trend_right:
            st.subheader("Stress Trend")
            stress_trend = pd.DataFrame(payload["timeseries"]["stress_trend"]).set_index("date")
            st.line_chart(stress_trend[["market_stress_index", "avg_volatility_30d"]])
            st.subheader("Portfolio Trend")
            portfolio_trend = pd.DataFrame(payload["timeseries"]["portfolio_trend"]).set_index("date")
            chart_columns = [col for col in ["portfolio_volatility", "value_at_risk_95"] if col in portfolio_trend.columns]
            st.line_chart(portfolio_trend[chart_columns])

    with assets_tab:
        drill_left, drill_right = st.columns([1.25, 1])
        with drill_left:
            st.subheader("Asset Risk Explorer")
            display_columns = [
                "symbol",
                "rolling_volatility_30d",
                "drawdown",
                "correlation_spike",
                "macro_shock_score",
            ]
            st.dataframe(asset_risk[display_columns], use_container_width=True, hide_index=True)
        with drill_right:
            st.subheader("Correlation Exposure")
            st.dataframe(correlation, use_container_width=True, hide_index=True)
            st.subheader("Current Narrative")
            highest_corr = correlation.iloc[0]
            st.info(
                f"{highest_corr['symbol']} currently leads correlation exposure with a reading of "
                f"{_format_decimal(highest_corr['correlation_spike'])}."
            )

    with ops_tab:
        ops_left, ops_right = st.columns([1, 1.1])
        with ops_left:
            st.subheader("Platform Health")
            st.dataframe(_build_health_table(summary), use_container_width=True, hide_index=True)
        with ops_right:
            st.subheader("Deployment Context")
            if payload.get("metadata", {}).get("data_mode") == "live":
                st.code(
                    "\n".join(
                        [
                            "price source: Yahoo Finance API",
                            f"fred source enabled: {payload['metadata'].get('fred_enabled', False)}",
                            "execution path: in-memory live feature engineering",
                        ]
                    ),
                    language="text",
                )
                st.caption("Live mode bypasses Databricks and local parquet files so the app can demo fresh market conditions.")
            else:
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
