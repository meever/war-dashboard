"""Sidebar controls: API key inputs and refresh."""

import os

import streamlit as st

from settings import APP_VERSION


def _clean_key(value: str) -> str:
    """Normalize text input and ignore example placeholder values."""
    cleaned = (value or "").strip()
    if cleaned.startswith("your_") and cleaned.endswith("_here"):
        return ""
    return cleaned


def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 6px 0 12px 0;">
            <span style="font-size: 24px;">⚔️</span>
            <div style="font-family: 'Courier New'; font-size: 12px; color: #FF4136;
                        letter-spacing: 3px; margin-top: 2px;">
                COMMAND CENTER
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── API Keys ─────────────────────────────────────────────────────
        st.markdown("##### 🔑 API KEYS")

        eia_key = _clean_key(os.environ.get("EIA_API_KEY", ""))
        fred_key = _clean_key(os.environ.get("FRED_API_KEY", ""))
        firms_key = _clean_key(os.environ.get("FIRMS_MAP_KEY", ""))

        if not eia_key:
            eia_key = _clean_key(st.text_input(
                "EIA API Key",
                type="password",
                placeholder="Get free key at eia.gov/opendata",
                help="Required for petroleum inventory data",
            ))
        else:
            st.success("EIA key loaded from environment", icon="✅")

        if not fred_key:
            fred_key = _clean_key(st.text_input(
                "FRED API Key",
                type="password",
                placeholder="Get free key at fred.stlouisfed.org",
                help="Required for macro indicator data",
            ))
        else:
            st.success("FRED key loaded from environment", icon="✅")

        if not firms_key:
            firms_key = _clean_key(st.text_input(
                "NASA FIRMS Key",
                type="password",
                placeholder="Get free key at firms.modaps.eosdis.nasa.gov",
                help="Required for refinery fire monitoring",
            ))
        else:
            st.success("FIRMS key loaded from environment", icon="✅")

        st.markdown("---")

        # ── Refresh ──────────────────────────────────────────────────────
        refresh = st.button("🔄 REFRESH DATA", use_container_width=True, type="primary")
        if refresh:
            st.cache_data.clear()

        st.markdown("""
        <div style="text-align: center; padding: 12px 0 0 0; font-size: 10px;
                    color: #555; font-family: 'Courier New';">
            WAR DASHBOARD %s<br>
            Data: Yahoo Finance · EIA · FRED · NASA FIRMS · OpenSky
        </div>
        """ % APP_VERSION, unsafe_allow_html=True)

    return {
        "eia_key": eia_key,
        "fred_key": fred_key,
        "firms_key": firms_key,
        "refresh": refresh,
    }
