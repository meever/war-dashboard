"""
OpenSky Network — global flight activity pipeline.
Takes a snapshot of all aircraft currently in the air via the public
REST API (no auth required for anonymous access, 400 credits/day).

The daily airborne count serves as a high-frequency proxy for global
aviation fuel demand / economic activity.
"""

import logging
from datetime import datetime

import pandas as pd

from data.http import http_get
from settings import DATA_DIR

logger = logging.getLogger(__name__)

_API_URL = "https://opensky-network.org/api/states/all"


def fetch_flight_snapshot() -> int | None:
    """Return the number of aircraft currently airborne worldwide.

    Uses the anonymous OpenSky endpoint (no API key needed).
    Costs 4 API credits out of 400/day budget.
    Returns None on error.
    """
    try:
        resp = http_get(_API_URL)
        resp.raise_for_status()
        data = resp.json()
        states = data.get("states", [])
        if not states:
            logger.warning("OpenSky returned no states")
            return None
        # Count only airborne aircraft (on_ground == False, index 8)
        airborne = sum(1 for s in states if len(s) > 8 and not s[8])
        return airborne
    except Exception as exc:
        logger.warning("Failed to fetch OpenSky snapshot: %s", exc)
        return None


def update_flight_history() -> pd.DataFrame:
    """Take a snapshot and append today's count to the local parquet store.

    Returns the full time series DataFrame with columns [airborne_count].
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "opensky_flights.parquet"

    # Load existing
    existing = pd.DataFrame()
    try:
        if path.exists():
            existing = pd.read_parquet(path)
    except (OSError, ValueError) as exc:
        logger.warning("Failed to read OpenSky parquet %s: %s", path, exc)

    # Take snapshot
    count = fetch_flight_snapshot()
    if count is None:
        return existing if not existing.empty else pd.DataFrame()

    today = pd.Timestamp(datetime.now().date())
    new_row = pd.DataFrame({"airborne_count": [count]}, index=pd.DatetimeIndex([today], name="Date"))

    if not existing.empty:
        combined = pd.concat([existing, new_row])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index()
    else:
        combined = new_row

    combined.to_parquet(path)
    return combined
