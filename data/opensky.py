"""
OpenSky Network — global flight activity pipeline.
Takes a snapshot of all aircraft currently in the air via the public
REST API (no auth required for anonymous access, 400 credits/day).

The daily airborne count serves as a high-frequency proxy for global
aviation fuel demand / economic activity.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

_API_URL = "https://opensky-network.org/api/states/all"

# Store path
DATA_DIR = Path(__file__).resolve().parent.parent / "local_data"


def fetch_flight_snapshot() -> int:
    """Return the number of aircraft currently airborne worldwide.

    Uses the anonymous OpenSky endpoint (no API key needed).
    Costs 4 API credits out of 400/day budget.
    Returns 0 on error.
    """
    try:
        resp = requests.get(_API_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        states = data.get("states", [])
        if not states:
            return 0
        # Count only airborne aircraft (on_ground == False, index 8)
        airborne = sum(1 for s in states if not s[8])
        return airborne
    except Exception:
        return 0


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
    except Exception:
        pass

    # Take snapshot
    count = fetch_flight_snapshot()
    if count == 0 and not existing.empty:
        return existing  # Don't overwrite with a failed reading

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
