from __future__ import annotations

from market_risk_platform.config.settings import load_config
from market_risk_platform.data_ingestion.providers import resolve_fred_api_key


def test_runtime_config_profile_and_secret_metadata(configured_env, monkeypatch) -> None:
    monkeypatch.setenv("CONFIG_PROFILE", "dev")
    monkeypatch.setenv("DATABRICKS_SECRET_SCOPE", "market-risk-scope")
    monkeypatch.setenv("FRED_API_KEY_SECRET_KEY", "fred-api-key")
    load_config.cache_clear()
    config = load_config()
    assert config.config_profile == "dev"
    assert config.databricks_secret_scope == "market-risk-scope"
    assert config.fred_api_key_secret_key == "fred-api-key"


def test_resolve_fred_api_key_prefers_env(configured_env, monkeypatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "inline-api-key")
    load_config.cache_clear()
    config = load_config()
    assert resolve_fred_api_key(config) == "inline-api-key"
