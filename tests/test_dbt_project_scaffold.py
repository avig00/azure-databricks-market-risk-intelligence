from __future__ import annotations

from pathlib import Path


def test_dbt_project_and_key_models_exist() -> None:
    root = Path("dbt")
    assert (root / "dbt_project.yml").exists()
    assert (root / "profiles.yml.example").exists()
    assert (root / "models" / "sources.yml").exists()
    assert (root / "models" / "silver" / "silver_daily_returns.sql").exists()
    assert (root / "models" / "silver" / "silver_volatility_metrics.sql").exists()
    assert (root / "models" / "silver" / "silver_asset_drawdowns.sql").exists()
    assert (root / "models" / "gold" / "gold_asset_risk_features.sql").exists()
    assert (root / "models" / "gold" / "gold_market_stress_signals.sql").exists()
    assert (root / "models" / "gold" / "gold_portfolio_risk_metrics.sql").exists()


def test_readme_mentions_dbt_and_hybrid_transform_layer() -> None:
    text = Path("README.md").read_text()
    assert "dbt" in text.lower()
    assert "requirements-dbt.txt" in text
