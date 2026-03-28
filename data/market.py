"""
Market data fetchers using yfinance.
Provides asset prices and crack spreads.
Uses local parquet store as primary source when available,
falling back to direct yfinance download for fresh data.
"""

import logging
import time

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

from settings import DATA_DIR

logger = logging.getLogger(__name__)

# ── Ticker registry ──────────────────────────────────────────────────────────
ASSET_TICKERS = {
    "Brent Crude": "BZ=F",
    "WTI Crude": "CL=F",
    "S&P 500": "^GSPC",
    "Gold": "GC=F",
    "US 10Y Yield": "^TNX",
}

# Mapping from asset label to store.py parquet key
_LABEL_TO_STORE_KEY = {
    "Brent Crude": "brent",
    "WTI Crude": "wti",
    "S&P 500": "spx",
    "Gold": "gold",
    "US 10Y Yield": "us10y",
}

# ── Timeframe helpers ────────────────────────────────────────────────────────
TIMEFRAME_DAYS = {
    "30d": 30,
    "60d": 60,
    "90d": 90,
    "6m": 180,
    "1y": 365,
    "2y": 730,
    "5y": 1825,
    "Max": 36500,
}


def _read_local(store_key: str) -> pd.DataFrame:
    """Read a parquet file from local store if it exists."""
    path = DATA_DIR / f"{store_key}.parquet"
    try:
        if path.exists():
            return pd.read_parquet(path)
    except (OSError, ValueError) as exc:
        logger.warning("Failed to read local parquet %s: %s", path, exc)
    return pd.DataFrame()


def _safe_download(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Download data from yfinance with error handling. Retries once on transient errors."""
    for attempt in range(2):
        try:
            df = yf.download(tickers, start=start, end=end, auto_adjust=True,
                             progress=False, threads=False)
            if df.empty:
                return pd.DataFrame()
            return df
        except Exception as exc:
            if attempt == 0:
                time.sleep(1)
                continue
            logger.warning("yfinance download failed for %s: %s", tickers, exc)
            return pd.DataFrame()
    return pd.DataFrame()


def build_crack_spread_frame(
    heating_oil: pd.Series,
    wti: pd.Series,
    gasoline: pd.Series | None = None,
) -> pd.DataFrame:
    """Build crack spread series from component futures prices."""
    spreads: dict[str, pd.Series] = {}
    if not heating_oil.empty and not wti.empty:
        spreads["Heating Oil Spread"] = (heating_oil * 42) - wti
    if gasoline is not None and not gasoline.empty and not wti.empty:
        spreads["Gasoline Spread"] = (gasoline * 42) - wti
    if not spreads:
        return pd.DataFrame()
    return pd.DataFrame(spreads).dropna(how="all").sort_index().ffill()


# ── Core fetcher ─────────────────────────────────────────────────────────────
def fetch_asset_data(timeframe: str = "60d") -> pd.DataFrame:
    """
    Fetch closing prices for all major asset tickers.
    Tries local parquet first, slicing to the requested timeframe.
    Falls back to yfinance download if local data is missing.
    """
    days = TIMEFRAME_DAYS.get(timeframe, 60)
    cutoff = pd.Timestamp(datetime.now() - timedelta(days=days))

    # Try local parquet store first
    frames = {}
    missing_tickers = {}
    for label, ticker in ASSET_TICKERS.items():
        store_key = _LABEL_TO_STORE_KEY.get(label)
        if store_key:
            local = _read_local(store_key)
            if not local.empty and "Close" in local.columns:
                sliced = local["Close"].loc[local.index >= cutoff].dropna()
                if not sliced.empty:
                    frames[label] = sliced
                    continue
        missing_tickers[label] = ticker

    # Fetch anything not covered by local store
    if missing_tickers:
        end = datetime.now()
        start = end - timedelta(days=days + 10)
        tickers = list(missing_tickers.values())
        raw = _safe_download(tickers, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

        if not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                closes = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw
            else:
                closes = raw[["Close"]].copy()
                closes.columns = tickers

            reverse_map = {v: k for k, v in missing_tickers.items()}
            closes = closes.rename(columns=reverse_map)
            for label in missing_tickers:
                if label in closes.columns:
                    frames[label] = closes[label]

    if not frames:
        return pd.DataFrame()

    result = pd.DataFrame(frames)
    result = result.loc[result.index >= cutoff]
    return result.ffill()


