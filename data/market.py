"""
Market data fetchers using yfinance.
Provides asset prices and crack spreads.
Uses local parquet store as primary source when available,
falling back to direct yfinance download for fresh data.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

# ── Ticker registry ──────────────────────────────────────────────────────────
ASSET_TICKERS = {
    "Brent Crude": "BZ=F",
    "WTI Crude": "CL=F",
    "S&P 500": "^GSPC",
    "Gold": "GC=F",
    "US 10Y Yield": "^TNX",
    "Dry Bulk Shipping": "SBLK",  # proxy for Baltic Dry — ^BDI delisted
}

CRACK_TICKERS = {
    "Heating Oil": "HO=F",
    "RBOB Gasoline": "RB=F",
    "WTI Crude": "CL=F",
}

# Mapping from asset label to store.py parquet key
_LABEL_TO_STORE_KEY = {
    "Brent Crude": "brent",
    "WTI Crude": "wti",
    "S&P 500": "spx",
    "Gold": "gold",
    "US 10Y Yield": "us10y",
    "Dry Bulk Shipping": "sblk",
}

_CRACK_TO_STORE_KEY = {
    "Heating Oil": "ho",
    "RBOB Gasoline": "rb",
    "WTI Crude": "wti",
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

DATA_DIR = Path(__file__).resolve().parent.parent / "local_data"


def _read_local(store_key: str) -> pd.DataFrame:
    """Read a parquet file from local store if it exists."""
    path = DATA_DIR / f"{store_key}.parquet"
    try:
        if path.exists():
            return pd.read_parquet(path)
    except Exception:
        pass
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
        except Exception:
            if attempt == 0:
                import time
                time.sleep(1)
                continue
            return pd.DataFrame()
    return pd.DataFrame()


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


# ── Crack spreads ────────────────────────────────────────────────────────────
def fetch_crack_spreads(timeframe: str = "60d") -> pd.DataFrame:
    """
    Compute crack spreads: Heating Oil – WTI and Gasoline – WTI.
    Uses local parquet when available.
    Prices are converted to $/barrel equivalent before subtraction.
    """
    days = TIMEFRAME_DAYS.get(timeframe, 60)
    cutoff = pd.Timestamp(datetime.now() - timedelta(days=days))

    # Try local parquet first
    ho_local = _read_local("ho")
    rb_local = _read_local("rb")
    cl_local = _read_local("wti")

    if not ho_local.empty and not cl_local.empty and "Close" in ho_local.columns and "Close" in cl_local.columns:
        ho = ho_local["Close"].loc[ho_local.index >= cutoff] * 42
        rb_s = rb_local["Close"].loc[rb_local.index >= cutoff] * 42 if not rb_local.empty and "Close" in rb_local.columns else pd.Series(dtype=float)
        cl = cl_local["Close"].loc[cl_local.index >= cutoff]
        result = pd.DataFrame(index=ho.index)
        if not ho.empty and not cl.empty:
            result["Heating Oil Spread"] = ho - cl
        if not rb_s.empty and not cl.empty:
            result["Gasoline Spread"] = rb_s - cl
        if not result.empty:
            return result.ffill()

    # Fallback to yfinance download
    end = datetime.now()
    start = end - timedelta(days=days + 10)

    tickers = list(CRACK_TICKERS.values())
    raw = _safe_download(tickers, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw

    # HO and RB are priced in $/gallon; convert to $/barrel (42 gallons)
    ho = closes.get("HO=F", pd.Series(dtype=float)) * 42
    rb = closes.get("RB=F", pd.Series(dtype=float)) * 42
    cl = closes.get("CL=F", pd.Series(dtype=float))

    result = pd.DataFrame(index=closes.index)
    if not ho.empty and not cl.empty:
        result["Heating Oil Spread"] = ho - cl
    if not rb.empty and not cl.empty:
        result["Gasoline Spread"] = rb - cl

    result = result.loc[result.index >= cutoff]
    return result.ffill()


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Asset Data (60d) ===")
    assets = fetch_asset_data("60d")
    print(assets.tail())

    print("\n=== Crack Spreads (60d) ===")
    cracks = fetch_crack_spreads("60d")
    print(cracks.tail())
