"""
EIA (U.S. Energy Information Administration) API v2 client.
Fetches petroleum inventories and refinery utilization data.
"""

import os
import pandas as pd
import requests
from datetime import datetime

EIA_BASE_URL = "https://api.eia.gov/v2"

# Key EIA series for petroleum inventories (Short-Term Energy Outlook)
# These are routes under /petroleum/steo/
EIA_INVENTORY_SERIES = {
    "Crude Oil Stocks": "STEO.COSXP.M",
    "Distillate Stocks": "STEO.DFSXP.M",
    "Gasoline Stocks": "STEO.MGSXP.M",
    "Refinery Utilization": "STEO.CRUOPP.M",
}

# Weekly petroleum status report series (more granular)
EIA_WEEKLY_SERIES = {
    "Weekly Crude Stocks (Mbbls)": "PET.WCESTUS1.W",
    "Weekly Distillate Stocks": "PET.WDISTUS1.W",
    "Weekly Gasoline Stocks": "PET.WGTSTUS1.W",
    "Weekly Refinery Utilization %": "PET.WPULEUS3.W",
}


def fetch_eia_data(
    api_key: str,
    series_map: dict[str, str] | None = None,
    start_date: str = "2020-01-01",
) -> dict[str, pd.DataFrame]:
    """
    Fetch data from EIA API v2.

    Returns a dict of {label: DataFrame} where each DataFrame has
    columns ['date', 'value'] with datetime index.
    """
    if not api_key:
        return {}

    if series_map is None:
        series_map = EIA_WEEKLY_SERIES

    results = {}

    for label, series_id in series_map.items():
        try:
            # Use the v2 series endpoint
            url = f"{EIA_BASE_URL}/seriesid/{series_id}"
            params = {
                "api_key": api_key,
                "start": start_date,
                "sort[0][column]": "period",
                "sort[0][direction]": "asc",
                "length": 5000,
            }

            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "response" not in data or "data" not in data["response"]:
                continue

            rows = data["response"]["data"]
            if not rows:
                continue

            df = pd.DataFrame(rows)

            # Normalize columns
            if "period" in df.columns and "value" in df.columns:
                df["date"] = pd.to_datetime(df["period"], errors="coerce")
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                df = df.dropna(subset=["date", "value"])
                df = df.set_index("date").sort_index()
                results[label] = df[["value"]].rename(columns={"value": label})

        except Exception:
            continue

    return results


def fetch_eia_inventories(api_key: str, start_date: str = "2020-01-01") -> pd.DataFrame:
    """
    Fetch weekly petroleum inventory data and return a single merged DataFrame.
    Columns: Crude Stocks, Distillate Stocks, Gasoline Stocks, Refinery Utilization.
    """
    data_dict = fetch_eia_data(api_key, EIA_WEEKLY_SERIES, start_date)
    if not data_dict:
        return pd.DataFrame()

    # Merge all series on date index
    frames = list(data_dict.values())
    if not frames:
        return pd.DataFrame()

    merged = frames[0]
    for f in frames[1:]:
        merged = merged.join(f, how="outer")

    return merged.ffill()


def fetch_eia_monthly(api_key: str, start_date: str = "2005-01-01") -> pd.DataFrame:
    """Fetch monthly STEO inventory/utilization data (longer history)."""
    data_dict = fetch_eia_data(api_key, EIA_INVENTORY_SERIES, start_date)
    if not data_dict:
        return pd.DataFrame()

    frames = list(data_dict.values())
    if not frames:
        return pd.DataFrame()

    merged = frames[0]
    for f in frames[1:]:
        merged = merged.join(f, how="outer")

    return merged.ffill()


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("EIA_API_KEY", "")
    if not key:
        print("⚠ EIA_API_KEY not set — set it in .env or environment")
    else:
        print("=== EIA Weekly Inventories ===")
        inv = fetch_eia_inventories(key)
        print(inv.tail(10))

        print("\n=== EIA Monthly STEO ===")
        monthly = fetch_eia_monthly(key)
        print(monthly.tail(10))
