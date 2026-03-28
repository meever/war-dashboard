"""
FRED (Federal Reserve Economic Data) API client.
Fetches macro indicators: industrial production, manufacturing, yield curve, etc.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

FRED_SERIES = {
    "Industrial Production": "INDPRO",
    "Manufacturing Employment": "MANEMP",
    "Capacity Utilization": "TCU",
    "Yield Curve (10Y-2Y)": "T10Y2Y",
    "WTI Crude (FRED)": "DCOILWTICO",
    "Retail Gasoline": "GASREGW",
    "Retail Diesel": "GASDESW",
}


def fetch_fred_series(
    api_key: str,
    series_ids: dict[str, str] | None = None,
    start_date: str = "2005-01-01",
) -> dict[str, pd.Series]:
    """
    Fetch multiple FRED series. Returns dict of {label: pd.Series}.
    Gracefully skips any series that errors.
    """
    if not api_key:
        return {}

    try:
        from fredapi import Fred
    except ImportError as exc:
        logger.warning("fredapi is unavailable: %s", exc)
        return {}

    if series_ids is None:
        series_ids = FRED_SERIES

    fred = Fred(api_key=api_key)
    results = {}

    for label, sid in series_ids.items():
        try:
            s = fred.get_series(sid, observation_start=start_date)
            if s is not None and not s.empty:
                s.name = label
                results[label] = s.dropna()
        except Exception as exc:
            logger.warning("Failed to fetch FRED series %s (%s): %s", label, sid, exc)

    return results


def fetch_fred_dataframe(
    api_key: str,
    series_ids: dict[str, str] | None = None,
    start_date: str = "2005-01-01",
) -> pd.DataFrame:
    """
    Fetch FRED series and merge into a single DataFrame.
    Columns named by label. Forward-fills to align different frequencies.
    """
    data = fetch_fred_series(api_key, series_ids, start_date)
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    return df.ffill()
