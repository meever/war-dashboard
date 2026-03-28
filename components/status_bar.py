"""
Top-level status indicator bar — compact 8-card single row.
Price cards show current value. Signal cards show danger/safe with reasoning.
"""

import streamlit as st
import pandas as pd
import numpy as np


def _card_html(label: str, value: str, color: str = "#E0E0E0") -> str:
    """Return HTML for a single compact card."""
    return f"""
    <div style="
        background:#0F0F1A; border:1px solid {color}30; border-radius:4px;
        padding:4px 6px; text-align:center; min-width:0;
    ">
        <div style="font-size:9px; color:#666; font-family:'Courier New'; text-transform:uppercase;
                    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
            {label}
        </div>
        <div style="font-size:14px; font-weight:bold; color:{color}; font-family:'Courier New';
                    white-space:nowrap;">
            {value}
        </div>
    </div>"""


def _signal_card_html(label: str, value: str, is_danger: bool, detail: str = "") -> str:
    """Return HTML for a signal card with danger/safe glow."""
    color = "#FF4136" if is_danger else "#00FF41"
    icon = "🔴" if is_danger else "🟢"
    tip = f' title="{detail}"' if detail else ""
    return f"""
    <div style="
        background:#0F0F1A; border:1px solid {color}60; border-radius:4px;
        padding:4px 6px; text-align:center; box-shadow:0 0 6px {color}25;
        min-width:0;
    "{tip}>
        <div style="font-size:9px; color:#666; font-family:'Courier New'; text-transform:uppercase;
                    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
            {label}
        </div>
        <div style="font-size:14px; font-weight:bold; color:{color}; font-family:'Courier New';
                    white-space:nowrap;">
            {icon} {value}
        </div>
    </div>"""


# ── Signal checks ────────────────────────────────────────────────────────────

def _check_crack_spread(crack_df: pd.DataFrame) -> tuple[bool, str, str]:
    """
    RED if crack spread is in the top 5% or bottom 5% of its full history,
    OR if it declined >15% in 5 days vs 30-day avg.
    """
    col = "Heating Oil Spread"
    if crack_df.empty or col not in crack_df.columns:
        return False, "N/A", "No data"

    series = crack_df[col].dropna()
    if len(series) < 30:
        return False, f"${series.iloc[-1]:.1f}" if len(series) > 0 else "N/A", "Insufficient data"

    current = series.iloc[-1]
    pctl = (series < current).sum() / len(series) * 100

    # Extreme percentile check — historically abnormal levels
    if pctl >= 95:
        return True, f"${current:.1f}", f"Pctl {pctl:.0f}% — extreme high"
    if pctl <= 5:
        return True, f"${current:.1f}", f"Pctl {pctl:.0f}% — extreme low"

    # Momentum check — rapid decline
    avg_5d = series.iloc[-5:].mean()
    avg_30d = series.iloc[-30:].mean()
    if avg_30d != 0:
        pct_change = (avg_5d - avg_30d) / abs(avg_30d) * 100
        if pct_change < -15:
            return True, f"${current:.1f}", f"5d/30d: {pct_change:+.1f}%"

    return False, f"${current:.1f}", f"Pctl {pctl:.0f}%"


def _check_inventories(inv_df: pd.DataFrame) -> tuple[bool, str, str]:
    """RED if latest weekly inventory build >2 std devs above 4-week average."""
    if inv_df.empty:
        return False, "N/A", "No EIA data"

    inv_cols = [c for c in inv_df.columns if "stock" in c.lower() or "crude" in c.lower()]
    if not inv_cols:
        inv_cols = [inv_df.columns[0]]

    col = inv_cols[0]
    series = inv_df[col].dropna()
    if len(series) < 5:
        return False, "N/A", "Insufficient data"

    current = series.iloc[-1]
    weekly_changes = series.diff().dropna()
    if len(weekly_changes) < 4:
        return False, f"{current:,.0f}", "Insufficient history"

    avg_change = weekly_changes.iloc[-4:].mean()
    std_change = weekly_changes.iloc[-4:].std()
    latest_change = weekly_changes.iloc[-1]

    if std_change == 0 or np.isnan(std_change):
        return False, f"{current:,.0f}", "Stable"

    z_score = (latest_change - avg_change) / std_change
    is_danger = z_score > 2.0
    detail = f"Δ {latest_change:+,.0f} (z={z_score:.1f})"
    return is_danger, f"{current:,.0f}", detail


def _check_yield_curve(fred_df: pd.DataFrame) -> tuple[bool, str, str]:
    """RED if yield curve (10Y-2Y) is inverted (below zero)."""
    col = "Yield Curve (10Y-2Y)"
    if fred_df.empty or col not in fred_df.columns:
        return False, "N/A", "No FRED data"

    series = fred_df[col].dropna()
    if series.empty:
        return False, "N/A", "No data"

    current = series.iloc[-1]
    is_danger = current < 0
    detail = "INVERTED" if is_danger else "Normal"
    return is_danger, f"{current:.2f}%", detail


def _check_bdi(asset_df: pd.DataFrame) -> tuple[bool, str, str]:
    """RED if Dry Bulk Shipping (SBLK) declined >15% over trailing 30 days."""
    col = "Dry Bulk Shipping"
    if asset_df.empty or col not in asset_df.columns:
        return False, "N/A", "No BDI data"

    series = asset_df[col].dropna()
    if len(series) < 2:
        return False, "N/A", "Insufficient data"

    current = series.iloc[-1]
    baseline = series.iloc[-30] if len(series) >= 30 else series.iloc[0]

    if baseline == 0:
        return False, f"${current:,.0f}", "—"

    pct_change = (current - baseline) / abs(baseline) * 100
    is_danger = pct_change < -15
    detail = f"30d: {pct_change:+.1f}%"
    return is_danger, f"${current:,.0f}", detail


def render_status_bar(
    price_data: dict,
    crack_df: pd.DataFrame,
    inv_df: pd.DataFrame,
    fred_df: pd.DataFrame,
    asset_df: pd.DataFrame,
    asset_labels: dict,
):
    """Render a single compact row of 8 cards: 4 price + 4 signal."""
    # Price cards
    price_cards = []
    for key in ["wti", "spx", "gold", "us10y"]:
        df = price_data.get(key)
        label = asset_labels.get(key, key)
        # Shorten labels
        short = {"WTI Crude Oil ($/bbl)": "WTI", "S&P 500 Index": "S&P 500",
                 "Gold ($/oz)": "Gold", "US 10-Year Yield (%)": "10Y Yield"}.get(label, label)
        if df is not None and not df.empty:
            s = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
            s = s.dropna()
            val = f"{s.iloc[-1]:,.2f}" if len(s) > 0 else "N/A"
        else:
            val = "N/A"
        price_cards.append(_card_html(short, val))

    # Signal cards
    crack_d, crack_v, crack_det = _check_crack_spread(crack_df)
    inv_d, inv_v, inv_det = _check_inventories(inv_df)
    yc_d, yc_v, yc_det = _check_yield_curve(fred_df)
    bdi_d, bdi_v, bdi_det = _check_bdi(asset_df)

    signal_cards = [
        _signal_card_html("Crack", crack_v, crack_d, crack_det),
        _signal_card_html("Inventory", inv_v, inv_d, inv_det),
        _signal_card_html("Yield Crv", yc_v, yc_d, yc_det),
        _signal_card_html("Shipping", bdi_v, bdi_d, bdi_det),
    ]

    all_cards = price_cards + signal_cards
    grid = "".join(all_cards)

    st.markdown(f"""
    <div style="display:grid; grid-template-columns:repeat(8, 1fr); gap:6px; margin:4px 0;">
        {grid}
    </div>
    """, unsafe_allow_html=True)
