"""
Local data persistence layer.
Fetches maximum available history from yfinance / EIA / FRED and stores
as parquet files under local_data/. On subsequent runs, only fetches
incremental new data since the last stored date and appends it.
"""

import logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

from data.market import build_crack_spread_frame
from settings import DATA_DIR

logger = logging.getLogger(__name__)

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
    except (OSError, ValueError) as exc:
        logger.warning("Failed to read parquet %s: %s", path, exc)
    return pd.DataFrame()


def _download_start(existing: pd.DataFrame) -> str:
    """Return the correct start date for an incremental download."""
    if existing.empty:
        return HISTORY_START
    last_date = existing.index.max()
    return (last_date - timedelta(days=3)).strftime("%Y-%m-%d")


def _prepare_downloaded_history(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance history into a parquet-friendly frame."""
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame.index.name = "Date"
    return frame


def _combine_history(existing: pd.DataFrame, new_frame: pd.DataFrame) -> pd.DataFrame:
    """Merge existing and newly downloaded time-series frames."""
    if existing.empty:
        return new_frame.sort_index()
    combined = pd.concat([existing, new_frame])
    combined = combined[~combined.index.duplicated(keep="last")]
    return combined.sort_index()


def _get_close(df: pd.DataFrame) -> pd.Series:
    """Extract the Close column, falling back to the first column."""
    return df["Close"] if "Close" in df.columns else df.iloc[:, 0]


# ── yfinance incremental fetcher ─────────────────────────────────────────────
def _fetch_and_store_yf_group(
    tickers: dict[str, str], force: bool = False,
) -> dict[str, pd.DataFrame]:
    """For each ticker: load existing parquet, fetch only new data since the
    last stored date, append and save back."""
    _ensure_dir()
    results: dict[str, pd.DataFrame] = {}
    today_str = datetime.now().strftime("%Y-%m-%d")

    for name, ticker in tickers.items():
        path = _parquet_path(name)

        if not force and not _is_stale(path):
            existing = _read_parquet_safe(path)
            if not existing.empty:
                results[name] = existing
                continue

        existing = _read_parquet_safe(path)
        start = _download_start(existing)

        try:
            new_df = yf.download(
                ticker, start=start, end=today_str,
                auto_adjust=True, progress=False, threads=False,
            )
            if new_df.empty:
                results[name] = existing if not existing.empty else pd.DataFrame()
                continue

            combined = _combine_history(existing, _prepare_downloaded_history(new_df))
            combined.to_parquet(path)
            results[name] = combined
        except Exception as exc:
            logger.warning("Failed to refresh %s (%s): %s", name, ticker, exc)
            results[name] = existing if not existing.empty else pd.DataFrame()

    return results


def fetch_and_store_market_history(force: bool = False) -> dict[str, pd.DataFrame]:
    """Fetch full history for core market tickers."""
    return _fetch_and_store_yf_group(HISTORY_TICKERS, force)


def fetch_and_store_tanker_history(force: bool = False) -> dict[str, pd.DataFrame]:
    """Fetch full history for tanker equities (wet freight proxy)."""
    return _fetch_and_store_yf_group(TANKER_TICKERS, force)


def build_tanker_index(tanker_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build equal-weight normalised tanker equity index from stored data.

    Each component is normalised to 100 at its first available date, then
    averaged across names.  The result column is ``Tanker Freight``.
    """
    closes = {}
    for name, df in tanker_data.items():
        if df is None or df.empty:
            continue
        s = _get_close(df).dropna()
        if len(s) > 1:
            closes[name] = s

    if not closes:
        return pd.DataFrame()

    combined = pd.DataFrame(closes)
    # Normalise each to 100 at its own first valid observation
    normed = combined / combined.bfill().iloc[0] * 100
    idx = normed.mean(axis=1).rename("Tanker Freight")
    return pd.DataFrame({"Tanker Freight": idx}).dropna()


# ── EIA / FRED full history ──────────────────────────────────────────────────

def _fetch_and_store_cached(
    name: str, fetcher, force: bool = False,
) -> pd.DataFrame:
    """Fetch a DataFrame via *fetcher*, cache to parquet, return cached if fresh."""
    _ensure_dir()
    path = _parquet_path(name)

    if not force and not _is_stale(path):
        cached = _read_parquet_safe(path)
        if not cached.empty:
            return cached

    df = fetcher()
    if not df.empty:
        df.to_parquet(path)
        return df

    return _read_parquet_safe(path)


def fetch_and_store_eia_history(api_key: str, force: bool = False) -> pd.DataFrame:
    """Fetch and store EIA weekly inventory data going back as far as possible."""
    from data.energy import fetch_eia_inventories
    return _fetch_and_store_cached(
        "eia_weekly", lambda: fetch_eia_inventories(api_key, start_date="1990-01-01"), force,
    )


def fetch_and_store_fred_history(api_key: str, force: bool = False) -> pd.DataFrame:
    """Fetch and store FRED macro series going back as far as possible."""
    from data.macro import fetch_fred_dataframe
    return _fetch_and_store_cached(
        "fred_macro", lambda: fetch_fred_dataframe(api_key, start_date="1960-01-01"), force,
    )


# ── NASA FIRMS fire data ─────────────────────────────────────────────────────
def fetch_and_store_firms(firms_key: str, force: bool = False) -> pd.DataFrame:
    """Fetch NASA FIRMS fire detections and append to the local parquet store."""
    _ensure_dir()
    path = _parquet_path("firms_fires")

    existing = _read_parquet_safe(path) if not force else pd.DataFrame()
    days = 5
    if not existing.empty:
        latest_date = pd.Timestamp(existing.index.max()).normalize()
        today = pd.Timestamp(datetime.now().date())
        days = max(1, min((today - latest_date).days + 1, 5))

    from data.firms import fetch_firms_fires, aggregate_daily_counts
    raw = fetch_firms_fires(firms_key, days=days)
    new = aggregate_daily_counts(raw)

    if new.empty:
        return existing if not existing.empty else pd.DataFrame()

    if not existing.empty:
        combined = _combine_history(existing, new)
    else:
        combined = new

    combined.to_parquet(path)
    return combined


# ── OpenSky flight data ──────────────────────────────────────────────────────
def fetch_and_store_flights() -> pd.DataFrame:
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

    ho_close = _get_close(ho_df)
    cl_close = _get_close(cl_df)
    rb_close = _get_close(rb_df) if rb_df is not None else None

    result = build_crack_spread_frame(ho_close, cl_close, rb_close)
    if result.empty:
        return result
    return result.reindex(cl_df.index).dropna(how="all").ffill()
