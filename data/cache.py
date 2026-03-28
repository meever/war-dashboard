"""
Caching wrappers for data fetchers using Streamlit's @st.cache_data.
Market data reads from local parquet (instant) then fetches incremental.
Short TTLs since local parquet is the real persistence layer.
"""

import streamlit as st
import pandas as pd

from data.market import fetch_asset_data
from data.store import (
    fetch_and_store_market_history,
    fetch_and_store_tanker_history,
    fetch_and_store_eia_history,
    fetch_and_store_fred_history,
    fetch_and_store_firms,
    fetch_and_store_flights,
)

# ── Market data (5 min TTL — reads from local parquet, fast) ─────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_asset_data(timeframe: str = "60d") -> pd.DataFrame:
    return fetch_asset_data(timeframe)


# ── Local long-term history (parquet-backed, incremental refresh) ────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_full_market_history() -> dict:
    return fetch_and_store_market_history()


@st.cache_data(ttl=3600, show_spinner=False)
def get_full_tanker_history() -> dict:
    return fetch_and_store_tanker_history()


@st.cache_data(ttl=86400, show_spinner=False)
def get_full_eia_history(api_key: str) -> pd.DataFrame:
    return fetch_and_store_eia_history(api_key)


@st.cache_data(ttl=86400, show_spinner=False)
def get_full_fred_history(api_key: str) -> pd.DataFrame:
    return fetch_and_store_fred_history(api_key)


@st.cache_data(ttl=86400, show_spinner=False)
def get_firms_data(firms_key: str) -> pd.DataFrame:
    return fetch_and_store_firms(firms_key)


@st.cache_data(ttl=86400, show_spinner=False)
def get_flight_data() -> pd.DataFrame:
    return fetch_and_store_flights()
