"""
WAR DASHBOARD — Global Macro War Room
Main Streamlit entry point.
"""

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="WAR DASHBOARD",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS: war-room terminal aesthetic ──────────────────────────────────
st.markdown("""
<style>
    /* Global overrides */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
    }

    /* Title banner — compact single line */
    .war-title {
        display: flex;
        align-items: baseline;
        gap: 12px;
        padding: 4px 0 3px 0;
        border-bottom: 1px solid #FF4136;
        margin-bottom: 4px;
    }
    .war-title h1 {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        color: #FF4136;
        font-size: 16px;
        letter-spacing: 4px;
        margin: 0;
        white-space: nowrap;
    }
    .war-title .subtitle {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        color: #00FF41;
        font-size: 10px;
        letter-spacing: 2px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: #0F0F1A;
        border-radius: 4px;
        padding: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 12px;
        letter-spacing: 1px;
        color: #888;
        border-radius: 4px;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1A1A2E;
        color: #FF4136;
        border-bottom: 2px solid #FF4136;
    }

    /* Metric styling */
    [data-testid="stMetric"] {
        background-color: #0F0F1A;
        border: 1px solid #1A1A2E;
        border-radius: 6px;
        padding: 6px 8px;
    }
    [data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-size: 10px;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 18px;
    }

    /* Spinner */
    .stSpinner > div {
        border-top-color: #FF4136 !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0A0A0A; }
    ::-webkit-scrollbar-thumb { background: #1A1A2E; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #FF4136; }

    /* Hide default Streamlit chrome.
       toolbarMode = "minimal" in config.toml ensures the toolbar only
       renders the sidebar expand arrow — no deploy / status / settings.
       We just need transparent backgrounds so no header bar shows. */
    #MainMenu {display: none;}
    footer {display: none;}
    [data-testid="stHeader"] {
        background: transparent !important;
    }
    [data-testid="stToolbar"] {
        background: transparent !important;
    }
    [data-testid="stStatusWidget"] {
        display: none;
    }

    /* Kill Streamlit default padding */
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0;
    }
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 0.5rem;
        padding-bottom: 0;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 0.25rem;
    }

    /* Divider */
    .war-divider {
        border: 0;
        height: 1px;
        background: linear-gradient(to right, transparent, #FF413660, transparent);
        margin: 4px 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Imports (after page config) ──────────────────────────────────────────────
from components.sidebar import render_sidebar
from components.status_bar import render_status_bar
from data.cache import (
    get_asset_data, get_crack_spreads,
    get_full_market_history, get_full_eia_history, get_full_fred_history,
)
from data.store import build_crack_spread_history
from charts.assets import make_asset_grid, PLOTLY_CONFIG
from charts.energy import make_energy_grid
from charts.macro import make_macro_grid, SIGNAL_GUIDE
from charts.history import ASSET_LABELS

# ── Timeframe options (shared across all tabs) ──────────────────────────────
TF_OPTIONS = ["30d", "60d", "90d", "6m", "1y", "2y", "5y", "Max"]
TF_DEFAULT_IDX = 1  # 60d


def _slice_df(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Slice a DataFrame to the most recent N days."""
    if df.empty or days >= 36500:
        return df
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    return df.loc[df.index >= cutoff]


def _tf_days(tf: str) -> int:
    """Convert timeframe string to days."""
    from data.market import TIMEFRAME_DAYS
    return TIMEFRAME_DAYS.get(tf, 60)


def main():
    # ── Sidebar (API keys + refresh) ─────────────────────────────────────
    config = render_sidebar()

    # ── Title Banner ─────────────────────────────────────────────────────
    st.markdown("""
    <div class="war-title">
        <h1>⚔️ WAR DASHBOARD</h1>
        <div class="subtitle">GLOBAL MACRO WAR ROOM — ENERGY SHOCK MONITOR</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Fetch all full-history data ──────────────────────────────────────
    with st.spinner("Acquiring market intelligence..."):
        market_hist = get_full_market_history()

    # Full-history crack spreads from stored HO/RB/WTI
    full_crack_df = build_crack_spread_history(market_hist) if market_hist else pd.DataFrame()

    # Full-history BDI
    full_bdi_df = pd.DataFrame()
    if market_hist and "sblk" in market_hist:
        sblk = market_hist["sblk"]
        if not sblk.empty:
            s = sblk["Close"] if "Close" in sblk.columns else sblk.iloc[:, 0]
            full_bdi_df = pd.DataFrame({"Dry Bulk Shipping": s})

    # Full-history asset df for status bar (short-term)
    asset_df = get_asset_data("60d")

    # EIA / FRED — full history
    eia_df = pd.DataFrame()
    fred_df = pd.DataFrame()

    if config["eia_key"]:
        with st.spinner("Fetching EIA inventory data..."):
            eia_df = get_full_eia_history(config["eia_key"])

    if config["fred_key"]:
        with st.spinner("Fetching FRED macro data..."):
            fred_df = get_full_fred_history(config["fred_key"])

    # ── Compact status row (8 cards: 4 price + 4 signal) ────────────────
    render_status_bar(
        price_data=market_hist or {},
        crack_df=full_crack_df,
        inv_df=eia_df,
        fred_df=fred_df,
        asset_df=asset_df,
        asset_labels=ASSET_LABELS,
    )

    # ── Tabs ─────────────────────────────────────────────────────────────
    tabs = st.tabs(["💥 ASSET BLOWUP", "🛢️ ENERGY & DEMAND", "📉 MACRO SIGNALS"])

    # ── TAB: Asset Blowup ────────────────────────────────────────────────
    with tabs[0]:
        tf = st.radio(
            "Period", options=TF_OPTIONS, index=TF_DEFAULT_IDX,
            horizontal=True, label_visibility="collapsed", key="asset_tf",
        )
        days = _tf_days(tf)
        if days >= 36500 and market_hist:
            # Max: build asset_df from full market history
            frames = {}
            label_map = {"wti": "WTI Crude", "brent": "Brent Crude", "spx": "S&P 500",
                         "gold": "Gold", "us10y": "US 10Y Yield", "sblk": "Dry Bulk Shipping"}
            for k, lbl in label_map.items():
                d = market_hist.get(k)
                if d is not None and not d.empty:
                    frames[lbl] = d["Close"] if "Close" in d.columns else d.iloc[:, 0]
            blowup_df = pd.DataFrame(frames).ffill() if frames else pd.DataFrame()
        else:
            blowup_df = get_asset_data(tf)
        if blowup_df.empty:
            st.error("⚠ Failed to fetch market data.")
        else:
            st.plotly_chart(make_asset_grid(blowup_df), width='stretch', config=PLOTLY_CONFIG)

    # ── TAB: Energy & Demand ─────────────────────────────────────────────
    with tabs[1]:
        tf = st.radio(
            "Period", options=TF_OPTIONS, index=TF_DEFAULT_IDX,
            horizontal=True, label_visibility="collapsed", key="energy_tf",
        )
        days = _tf_days(tf)
        crack_view = _slice_df(full_crack_df, days) if not full_crack_df.empty else pd.DataFrame()
        eia_view = _slice_df(eia_df, days) if not eia_df.empty else pd.DataFrame()
        st.plotly_chart(make_energy_grid(crack_view, eia_view), width='stretch', config=PLOTLY_CONFIG)

    # ── TAB: Macro Signals ───────────────────────────────────────────────
    with tabs[2]:
        tf = st.radio(
            "Period", options=TF_OPTIONS, index=TF_DEFAULT_IDX,
            horizontal=True, label_visibility="collapsed", key="macro_tf",
        )
        days = _tf_days(tf)
        fred_view = _slice_df(fred_df, days) if not fred_df.empty else pd.DataFrame()
        bdi_view = _slice_df(full_bdi_df, days) if not full_bdi_df.empty else pd.DataFrame()
        if fred_view.empty and bdi_view.empty:
            st.warning("Add FRED API key in the sidebar to unlock macro indicators.")
        else:
            st.markdown("""
            <div style="font-family:'Courier New'; color:#888; font-size:11px;
                        background:#0F0F1A; border:1px solid #1A1A2E; border-radius:6px;
                        padding:10px 14px; margin-bottom:12px;">
                <b style="color:#FF4136;">SIGNAL GUIDE</b><br>
                <span style="color:#00FFFF;">Yield Curve:</span> Below 0 = inverted = recession warning &nbsp;|&nbsp;
                <span style="color:#00FF41;">Industrial Production:</span> Rising = expansion, falling = contraction<br>
                <span style="color:#FF8C00;">Dry Bulk Shipping:</span> Rising = global trade growing &nbsp;|&nbsp;
                <span style="color:#FFD700;">Capacity Util:</span> &gt;80% strong, &lt;75% = weak demand
            </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(make_macro_grid(fred_view, bdi_view), width='stretch', config=PLOTLY_CONFIG)


if __name__ == "__main__":
    main()
