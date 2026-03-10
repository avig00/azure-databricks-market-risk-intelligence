from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


INDEX_SYMBOLS = {"^GSPC", "^IXIC", "^VIX"}


@dataclass
class SampleMarketDataProvider:
    seed: int = 42

    def fetch_prices(self, symbols: list[str], start_date: str) -> pd.DataFrame:
        dates = pd.bdate_range(start=start_date, end=pd.Timestamp.today().normalize())
        rows: list[dict[str, float | str | pd.Timestamp]] = []
        rng = np.random.default_rng(self.seed)
        for idx, symbol in enumerate(symbols):
            base = 100 + (idx * 15)
            drift = 0.0004 + idx * 0.00003
            vol = 0.01 + idx * 0.002
            rets = rng.normal(drift, vol, len(dates))
            prices = base * np.exp(np.cumsum(rets))
            high = prices * (1 + np.abs(rng.normal(0.003, 0.002, len(dates))))
            low = prices * (1 - np.abs(rng.normal(0.003, 0.002, len(dates))))
            opens = prices * (1 + rng.normal(0, 0.001, len(dates)))
            volume = rng.integers(1_000_000, 6_000_000, len(dates))
            for date, open_price, high_price, low_price, close_price, vol_value in zip(
                dates, opens, high, low, prices, volume
            ):
                rows.append(
                    {
                        "date": date,
                        "symbol": symbol,
                        "open": round(float(open_price), 4),
                        "high": round(float(max(high_price, close_price)), 4),
                        "low": round(float(min(low_price, close_price)), 4),
                        "close": round(float(close_price), 4),
                        "adj_close": round(float(close_price), 4),
                        "volume": int(vol_value),
                        "source": "sample",
                    }
                )
        return pd.DataFrame(rows)

    def fetch_macro(self, series_ids: list[str], start_date: str) -> pd.DataFrame:
        dates = pd.date_range(start=start_date, end=pd.Timestamp.today().normalize(), freq="MS")
        rows: list[dict[str, float | str | pd.Timestamp]] = []
        rng = np.random.default_rng(self.seed + 7)
        for idx, series_id in enumerate(series_ids):
            level = 2 + idx * 1.2
            trend = np.linspace(0, idx + 1, len(dates))
            noise = rng.normal(0, 0.15 + idx * 0.05, len(dates))
            values = level + trend + noise
            for date, value in zip(dates, values):
                rows.append(
                    {
                        "date": date,
                        "series_id": series_id,
                        "value": round(float(value), 4),
                        "source": "sample",
                    }
                )
        return pd.DataFrame(rows)


@dataclass
class LiveMarketDataProvider:
    fred_api_key: str | None

    def fetch_prices(self, symbols: list[str], start_date: str) -> pd.DataFrame:
        import yfinance as yf

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
            raise ValueError("No supported ticker data returned from Yahoo Finance")
        return pd.concat(frames, ignore_index=True)

    def fetch_macro(self, series_ids: list[str], start_date: str) -> pd.DataFrame:
        if not self.fred_api_key:
            raise ValueError("FRED_API_KEY is required when USE_SAMPLE_DATA=false")
        from fredapi import Fred

        fred = Fred(api_key=self.fred_api_key)
        rows: list[dict[str, object]] = []
        for series_id in series_ids:
            series = fred.get_series(series_id, observation_start=start_date)
            if series.empty:
                raise ValueError(f"FRED returned no data for series '{series_id}'")
            for date, value in series.items():
                rows.append(
                    {
                        "date": pd.Timestamp(date),
                        "series_id": series_id,
                        "value": float(value),
                        "source": "fred",
                    }
                )
        return pd.DataFrame(rows)


def split_index_and_assets(price_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    market_indices = price_df[price_df["symbol"].isin(INDEX_SYMBOLS)].copy()
    stock_prices = price_df[~price_df["symbol"].isin(INDEX_SYMBOLS)].copy()
    return stock_prices, market_indices


def get_provider(use_sample_data: bool, fred_api_key: str | None) -> SampleMarketDataProvider | LiveMarketDataProvider:
    if use_sample_data:
        return SampleMarketDataProvider()
    return LiveMarketDataProvider(fred_api_key=fred_api_key)
