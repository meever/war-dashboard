"""
NASA FIRMS (Fire Information for Resource Management System) pipeline.
Tracks thermal anomalies at major refinery complexes as an early-warning
proxy for outages.  Uses VIIRS S-NPP Near Real-Time data via the free
public API (requires a MAP_KEY from firms.modaps.eosdis.nasa.gov).

API: /api/area/csv/[MAP_KEY]/VIIRS_SNPP_NRT/[west,south,east,north]/[days]
Returns CSV with columns: latitude, longitude, brightness, scan, track,
acq_date, acq_time, satellite, confidence, version, bright_t31, frp, ...
"""

import io
from datetime import datetime

import pandas as pd
import requests

# ── Refinery bounding boxes (west, south, east, north) ───────────────────────
# Each box is ≈50×50 km around the refinery complex centroid.
REFINERY_REGIONS = {
    "Ras Tanura (SA)":     (49.7, 26.4, 50.3, 26.9),   # Saudi Aramco — world's largest
    "Abadan (Iran)":       (48.0, 30.1, 48.6, 30.6),   # Iran — Abadan/Mahshahr
    "Jamnagar (India)":    (69.3, 22.1, 70.0, 22.7),   # Reliance — world's largest private
    "Jurong (Singapore)":  (103.5, 1.15, 103.9, 1.40),  # Shell/ExxonMobil hub
    "Yanbu (SA)":          (37.8, 23.8, 38.3, 24.3),   # Saudi Aramco west coast
    "Ruwais (UAE)":        (51.9, 24.0, 52.5, 24.5),   # ADNOC mega-refinery
    "Ulsan (S. Korea)":    (129.1, 35.4, 129.6, 35.7),  # SK Energy — Asia's 3rd largest
    "Mailiao (Taiwan)":    (120.1, 23.7, 120.5, 24.0),  # Formosa Petrochemical
}

_SOURCE = "VIIRS_SNPP_NRT"


def fetch_firms_fires(map_key: str, days: int = 2) -> pd.DataFrame:
    """Fetch recent fire detections around all monitored refinery regions.

    Parameters
    ----------
    map_key : str
        NASA FIRMS MAP_KEY (free, register at firms.modaps.eosdis.nasa.gov).
    days : int
        Number of trailing days (1–5, API limit).

    Returns
    -------
    pd.DataFrame with columns: region, acq_date, latitude, longitude,
    brightness, frp (fire radiative power), confidence.
    """
    days = max(1, min(days, 5))
    frames = []

    for region, (w, s, e, n) in REFINERY_REGIONS.items():
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv"
            f"/{map_key}/{_SOURCE}/{w},{s},{e},{n}/{days}"
        )
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            if not df.empty:
                df["region"] = region
                frames.append(df)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)

    # Normalise date column
    if "acq_date" in result.columns:
        result["acq_date"] = pd.to_datetime(result["acq_date"])

    return result


def aggregate_daily_counts(raw: pd.DataFrame) -> pd.DataFrame:
    """Roll up raw fire detections into daily fire-count per region.

    Returns a pivoted DataFrame with DatetimeIndex and one column per region.
    """
    if raw.empty or "acq_date" not in raw.columns:
        return pd.DataFrame()

    daily = (
        raw.groupby(["acq_date", "region"])
        .size()
        .reset_index(name="fire_count")
    )
    pivot = daily.pivot(index="acq_date", columns="region", values="fire_count").fillna(0)
    pivot.index.name = "Date"
    pivot = pivot.sort_index()

    # Add a total column
    pivot["Total"] = pivot.sum(axis=1)
    return pivot
