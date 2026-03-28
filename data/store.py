"""
Local data persistence layer.
Fetches maximum available history from yfinance / EIA / FRED and stores
as parquet files under local_data/. On subsequent runs, only fetches
incremental new data since the last stored date and appends it.
"""

import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "local_data"

# How often to check for new incremental data (hours)
REFRESH_HOURS = 1

# ── All tickers we want full history for ─────────────────────────────────────
HISTORY_TICKERS = {
    "brent":    "BZ=F",
    "wti":      "CL=F",
    "spx":      "^GSPC",
    "gold":     "GC=F",
    "us10y":    "^TNX",
    "ho":       "HO=F",
    "rb":       "RB=F",
}

# Crude tanker equities for wet freight index
TANKER_TICKERS = {
    "fro":  "FRO",
    "stng": "STNG",
    "dht":  "DHT",
    "insw": "INSW",
    "tnk":  "TNK",
}

# Start dates — go as far back as each ticker allows
HISTORY_START = "1980-01-01"


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _parquet_path(name: str) -> Path:
    return DATA_DIR / f"{name}.parquet"


def _is_stale(path: Path, hours: int = REFRESH_HOURS) -> bool:
    """Return True if file doesn't exist or was last modified more than `hours` ago."""
    if not path.exists():
        return True
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (datetime.now() - mtime) > timedelta(hours=hours)


def _read_parquet_safe(path: Path) -> pd.DataFrame:
    """Read parquet file, return empty DataFrame on error."""
    try:
        if path.exists():
            return pd.read_parquet(path)
    except Exception:
        pass
    return pd.DataFrame()


# ── yfinance incremental fetcher ─────────────────────────────────────────────
def fetch_and_store_market_history(force: bool = False) -> dict[str, pd.DataFrame]:
    """
    For each ticker: load existing parquet, then fetch only new data
    since the last stored date. Appends and saves back.
    On first run, fetches full history from HISTORY_START.
    """
    _ensure_dir()
    results = {}
    today_str = datetime.now().strftime("%Y-%m-%d")

    for name, ticker in HISTORY_TICKERS.items():
        path = _parquet_path(name)

        # If file is fresh enough, just load it
        if not force and not _is_stale(path):
            existing = _read_parquet_safe(path)
            if not existing.empty:
                results[name] = existing
                continue

        # Load existing data
        existing = _read_parquet_safe(path)

        if existing.empty:
            # Full fetch from scratch
            start = HISTORY_START
        else:
            # Incremental: start from last date (overlap 3 days for safety)
            last_date = existing.index.max()
            start = (last_date - timedelta(days=3)).strftime("%Y-%m-%d")

        try:
            new_df = yf.download(
                ticker, start=start, end=today_str,
                auto_adjust=True, progress=False, threads=False,
            )
            if new_df.empty:
                results[name] = existing if not existing.empty else pd.DataFrame()
                continue

            if isinstance(new_df.columns, pd.MultiIndex):
                new_df.columns = new_df.columns.get_level_values(0)
            new_df.index.name = "Date"

            if not existing.empty:
                # Combine: new data overwrites overlapping dates
                combined = pd.concat([existing, new_df])
                combined = combined[~combined.index.duplicated(keep="last")]
                combined = combined.sort_index()
            else:
                combined = new_df

            combined.to_parquet(path)
            results[name] = combined
        except Exception:
            results[name] = existing if not existing.empty else pd.DataFrame()

    return results


def fetch_and_store_tanker_history(force: bool = False) -> dict[str, pd.DataFrame]:
    """Fetch full history for tanker equities (wet freight proxy)."""
    _ensure_dir()
    results = {}
    today_str = datetime.now().strftime("%Y-%m-%d")

    for name, ticker in TANKER_TICKERS.items():
        path = _parquet_path(name)

        if not force and not _is_stale(path):
            existing = _read_parquet_safe(path)
            if not existing.empty:
                results[name] = existing
                continue

        existing = _read_parquet_safe(path)

        if existing.empty:
            start = HISTORY_START
        else:
            last_date = existing.index.max()
            start = (last_date - timedelta(days=3)).strftime("%Y-%m-%d")

        try:
            new_df = yf.download(
                ticker, start=start, end=today_str,
                auto_adjust=True, progress=False, threads=False,
            )
            if new_df.empty:
                results[name] = existing if not existing.empty else pd.DataFrame()
                continue

            if isinstance(new_df.columns, pd.MultiIndex):
                new_df.columns = new_df.columns.get_level_values(0)
            new_df.index.name = "Date"

            if not existing.empty:
                combined = pd.concat([existing, new_df])
                combined = combined[~combined.index.duplicated(keep="last")]
                combined = combined.sort_index()
            else:
                combined = new_df

            combined.to_parquet(path)
            results[name] = combined
        except Exception:
            results[name] = existing if not existing.empty else pd.DataFrame()

    return results


def build_tanker_index(tanker_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build equal-weight normalised tanker equity index from stored data.

    Each component is normalised to 100 at its first available date, then
    averaged across names.  The result column is ``Tanker Freight``.
    """
    closes = {}
    for name, df in tanker_data.items():
        if df is None or df.empty:
            continue
        s = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
        s = s.dropna()
        if len(s) > 1:
            closes[name] = s

    if not closes:
        return pd.DataFrame()

    combined = pd.DataFrame(closes)
    # Normalise each to 100 at its own first valid observation
    normed = combined / combined.bfill().iloc[0] * 100
    idx = normed.mean(axis=1).rename("Tanker Freight")
    return pd.DataFrame({"Tanker Freight": idx}).dropna()


def load_market_history() -> dict[str, pd.DataFrame]:
    """Load all stored market history from parquet. Fetch if missing."""
    _ensure_dir()
    results = {}
    any_missing = False

    for name in HISTORY_TICKERS:
        path = _parquet_path(name)
        if path.exists():
            try:
                results[name] = pd.read_parquet(path)
            except Exception:
                any_missing = True
        else:
            any_missing = True

    if any_missing:
        results = fetch_and_store_market_history()

    return results


# ── EIA full history ─────────────────────────────────────────────────────────
def fetch_and_store_eia_history(api_key: str, force: bool = False) -> pd.DataFrame:
    """Fetch and store EIA weekly inventory data going back as far as possible."""
    _ensure_dir()
    path = _parquet_path("eia_weekly")

    if not force and not _is_stale(path):
        try:
            return pd.read_parquet(path)
        except Exception:
            pass

    from data.energy import fetch_eia_inventories
    df = fetch_eia_inventories(api_key, start_date="1990-01-01")
    if not df.empty:
        df.to_parquet(path)
        return df

    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


def load_eia_history(api_key: str = "") -> pd.DataFrame:
    """Load stored EIA data, or fetch if missing."""
    path = _parquet_path("eia_weekly")
    if path.exists():
        try:
            return pd.read_parquet(path)
        except Exception:
            pass
    if api_key:
        return fetch_and_store_eia_history(api_key)
    return pd.DataFrame()


# ── FRED full history ────────────────────────────────────────────────────────
def fetch_and_store_fred_history(api_key: str, force: bool = False) -> pd.DataFrame:
    """Fetch and store FRED macro series going back as far as possible."""
    _ensure_dir()
    path = _parquet_path("fred_macro")

    if not force and not _is_stale(path):
        try:
            return pd.read_parquet(path)
        except Exception:
            pass

    from data.macro import fetch_fred_dataframe
    df = fetch_fred_dataframe(api_key, start_date="1960-01-01")
    if not df.empty:
        df.to_parquet(path)
        return df

    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


def load_fred_history(api_key: str = "") -> pd.DataFrame:
    """Load stored FRED data, or fetch if missing."""
    path = _parquet_path("fred_macro")
    if path.exists():
        try:
            return pd.read_parquet(path)
        except Exception:
            pass
    if api_key:
        return fetch_and_store_fred_history(api_key)
    return pd.DataFrame()


# ── NASA FIRMS fire data ─────────────────────────────────────────────────────
def fetch_and_store_firms(firms_key: str, force: bool = False) -> pd.DataFrame:
    """Fetch NASA FIRMS fire detections and append to the local parquet store."""
    _ensure_dir()
    path = _parquet_path("firms_fires")

    existing = _read_parquet_safe(path) if not force else pd.DataFrame()

    from data.firms import fetch_firms_fires, aggregate_daily_counts
    raw = fetch_firms_fires(firms_key, days=5)
    new = aggregate_daily_counts(raw)

    if new.empty:
        return existing if not existing.empty else pd.DataFrame()

    if not existing.empty:
        combined = pd.concat([existing, new])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index()
    else:
        combined = new

    combined.to_parquet(path)
    return combined


# ── OpenSky flight data ──────────────────────────────────────────────────────
def fetch_and_store_flights(force: bool = False) -> pd.DataFrame:
    """Snapshot global airborne aircraft count and append to parquet."""
    from data.opensky import update_flight_history
    return update_flight_history()


# ── Crack spread full history ────────────────────────────────────────────────
def build_crack_spread_history(market_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute historical crack spreads from stored HO, RB, WTI data."""
    ho_df = market_data.get("ho")
    rb_df = market_data.get("rb")
    cl_df = market_data.get("wti")

    if ho_df is None or cl_df is None:
        return pd.DataFrame()

    result = pd.DataFrame(index=cl_df.index)

    ho_close = ho_df["Close"] if "Close" in ho_df.columns else ho_df.iloc[:, 0]
    cl_close = cl_df["Close"] if "Close" in cl_df.columns else cl_df.iloc[:, 0]

    result["Heating Oil Spread"] = (ho_close * 42) - cl_close

    if rb_df is not None:
        rb_close = rb_df["Close"] if "Close" in rb_df.columns else rb_df.iloc[:, 0]
        result["Gasoline Spread"] = (rb_close * 42) - cl_close

    return result.dropna(how="all").ffill()


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Fetching full market history...")
    data = fetch_and_store_market_history(force=True)
    for name, df in data.items():
        if not df.empty:
            print(f"  {name}: {df.index.min().date()} → {df.index.max().date()}  ({len(df)} rows)")
        else:
            print(f"  {name}: EMPTY")

    print(f"\nFiles saved to: {DATA_DIR}")
