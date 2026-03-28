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
    get_full_market_history, get_full_tanker_history,
    get_full_eia_history, get_full_fred_history,
    get_firms_data, get_flight_data,
)
from data.store import build_crack_spread_history, build_tanker_index
from charts.assets import make_asset_grid, PLOTLY_CONFIG
from charts.energy import make_energy_grid
from charts.macro import make_macro_grid, SIGNAL_GUIDE


# Asset label map (used by status bar for display names)
ASSET_LABELS = {
    "wti":   "WTI Crude Oil ($/bbl)",
    "brent": "Brent Crude Oil ($/bbl)",
    "spx":   "S&P 500 Index",
    "gold":  "Gold ($/oz)",
    "us10y": "US 10-Year Yield (%)",
}

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


# ── Shared table CSS for dark war-room aesthetic ─────────────────────────────
_TABLE_CSS = """
<style>
.war-table { width:100%; border-collapse:collapse; font-family:'Courier New',monospace; font-size:12px; }
.war-table th { background:#1A1A2E; color:#FF4136; padding:6px 10px; text-align:right;
                border-bottom:2px solid #FF413660; letter-spacing:1px; }
.war-table th:first-child { text-align:left; }
.war-table td { padding:5px 10px; text-align:right; color:#E0E0E0; border-bottom:1px solid #1A1A2E; }
.war-table td:first-child { text-align:left; color:#888; }
.war-table tr:hover td { background:#1A1A2E; }
.war-table .total-col { color:#FFD700; font-weight:bold; }
.war-section-title { font-family:'Courier New',monospace; color:#FF4136; font-size:13px;
                     letter-spacing:2px; margin:10px 0 4px 0; }
</style>
"""


def _render_altdata_tables(firms_df: pd.DataFrame, flights_df: pd.DataFrame):
    """Render Alt Intel data as styled HTML tables."""
    st.markdown(_TABLE_CSS, unsafe_allow_html=True)

    # ── FIRMS fire detections table ──────────────────────────────────────
    st.markdown('<p class="war-section-title">🔥 REFINERY FIRE DETECTIONS — NASA FIRMS / VIIRS</p>',
                unsafe_allow_html=True)

    if firms_df.empty:
        st.caption("No FIRMS data — add NASA FIRMS key in sidebar")
    else:
        region_cols = [c for c in firms_df.columns if c != "Total"]
        header = "<tr><th>DATE</th>" + "".join(f"<th>{c}</th>" for c in region_cols) + "<th>TOTAL</th></tr>"
        rows = []
        for date, row in firms_df.iterrows():
            date_str = date.strftime("%Y-%m-%d")
            cells = "".join(
                f'<td style="color:#FF4136">{int(row[c])}</td>' if row[c] > 0
                else f"<td>0</td>"
                for c in region_cols
            )
            total = int(row["Total"]) if "Total" in row.index else int(sum(row[c] for c in region_cols))
            rows.append(f'<tr><td>{date_str}</td>{cells}<td class="total-col">{total}</td></tr>')
        st.markdown(f'<table class="war-table">{header}{"".join(rows)}</table>', unsafe_allow_html=True)

    # ── OpenSky flight activity table ────────────────────────────────────
    st.markdown('<p class="war-section-title">✈️ GLOBAL AIRBORNE AIRCRAFT — OpenSky Network</p>',
                unsafe_allow_html=True)

    if flights_df.empty or "airborne_count" not in flights_df.columns:
        st.caption("No flight data yet — builds over time")
    else:
        header = "<tr><th>DATE</th><th>AIRBORNE AIRCRAFT</th><th>Δ DAY</th></tr>"
        s = flights_df["airborne_count"].dropna().sort_index()
        rows = []
        prev = None
        for date, count in s.items():
            date_str = date.strftime("%Y-%m-%d")
            count_int = int(count)
            if prev is not None:
                delta = count_int - prev
                sign = "+" if delta > 0 else ""
                color = "#00FF41" if delta >= 0 else "#FF4136"
                delta_cell = f'<td style="color:{color}">{sign}{delta:,}</td>'
            else:
                delta_cell = "<td>—</td>"
            rows.append(f'<tr><td>{date_str}</td><td style="color:#00FFFF">{count_int:,}</td>{delta_cell}</tr>')
            prev = count_int
        st.markdown(f'<table class="war-table">{header}{"".join(rows)}</table>', unsafe_allow_html=True)


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
        tanker_hist = get_full_tanker_history()

    # Full-history crack spreads from stored HO/RB/WTI
    full_crack_df = build_crack_spread_history(market_hist) if market_hist else pd.DataFrame()

    # Full-history tanker freight index (wet freight proxy)
    full_tanker_df = build_tanker_index(tanker_hist) if tanker_hist else pd.DataFrame()

    # EIA / FRED — full history
    eia_df = pd.DataFrame()
    fred_df = pd.DataFrame()

    if config["eia_key"]:
        with st.spinner("Fetching EIA inventory data..."):
            eia_df = get_full_eia_history(config["eia_key"])

    if config["fred_key"]:
        with st.spinner("Fetching FRED macro data..."):
            fred_df = get_full_fred_history(config["fred_key"])

    # Alt data — FIRMS fires + OpenSky flights
    firms_df = pd.DataFrame()
    flights_df = pd.DataFrame()

    if config.get("firms_key"):
        with st.spinner("Scanning refinery thermal signatures..."):
            firms_df = get_firms_data(config["firms_key"])

    with st.spinner("Polling global flight activity..."):
        flights_df = get_flight_data()

    # ── Compact status row (8 cards: 4 price + 4 signal) ────────────────
    render_status_bar(
        price_data=market_hist or {},
        crack_df=full_crack_df,
        inv_df=eia_df,
        fred_df=fred_df,
        tanker_df=full_tanker_df,
        asset_labels=ASSET_LABELS,
    )

    # ── Tabs ─────────────────────────────────────────────────────────────
    tabs = st.tabs(["💥 ASSET BLOWUP", "🛢️ ENERGY & DEMAND", "📉 MACRO SIGNALS", "🛰️ ALT INTEL"])

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
                         "gold": "Gold", "us10y": "US 10Y Yield"}
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
        tanker_view = _slice_df(full_tanker_df, days) if not full_tanker_df.empty else pd.DataFrame()
        if fred_view.empty and tanker_view.empty:
            st.warning("Add FRED API key in the sidebar to unlock macro indicators.")
        else:
            st.markdown("""
            <div style="font-family:'Courier New'; color:#888; font-size:11px;
                        background:#0F0F1A; border:1px solid #1A1A2E; border-radius:6px;
                        padding:10px 14px; margin-bottom:12px;">
                <b style="color:#FF4136;">SIGNAL GUIDE</b><br>
                <span style="color:#00FFFF;">Yield Curve:</span> Below 0 = inverted = recession warning &nbsp;|&nbsp;
                <span style="color:#00FF41;">Industrial Production:</span> Rising = expansion, falling = contraction<br>
                <span style="color:#FF8C00;">Tanker Freight:</span> Rising = crude shipping demand growing &nbsp;|&nbsp;
                <span style="color:#FFD700;">Capacity Util:</span> &gt;80% strong, &lt;75% = weak demand
            </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(make_macro_grid(fred_view, tanker_view), width='stretch', config=PLOTLY_CONFIG)

    # ── TAB: Alt Intel ───────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("""
        <div style="font-family:'Courier New'; color:#888; font-size:11px;
                    background:#0F0F1A; border:1px solid #1A1A2E; border-radius:6px;
                    padding:10px 14px; margin-bottom:12px;">
            <b style="color:#FF4136;">ALT DATA GUIDE</b><br>
            <span style="color:#FF4136;">FIRMS Fires:</span> Thermal anomalies near major refineries — spike = potential outage &nbsp;|&nbsp;
            <span style="color:#00FFFF;">Airborne Aircraft:</span> Daily snapshot of global flights — proxy for jet fuel demand
        </div>
        """, unsafe_allow_html=True)
        _render_altdata_tables(firms_df, flights_df)


if __name__ == "__main__":
    main()
