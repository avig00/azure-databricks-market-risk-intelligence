from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture()
def configured_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("LOG_ROOT", str(tmp_path / "logs"))
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_FORMAT", "parquet")
    monkeypatch.setenv("USE_SAMPLE_DATA", "true")
    monkeypatch.setenv("MARKET_SYMBOLS", "AAPL,MSFT,NVDA,XOM,SPY,TLT,^GSPC,^IXIC,^VIX")
    monkeypatch.setenv("PORTFOLIO_SYMBOLS", "AAPL,MSFT,NVDA,XOM,SPY,TLT")
    monkeypatch.setenv("FRED_SERIES", "FEDFUNDS,CPIAUCSL,UNRATE,DGS10")
    os.environ.pop("PYTHONPATH", None)
    return tmp_path
