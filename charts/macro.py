"""Macro indicator charts and direction guidance."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from charts.utils import WAR_COLORS, base_layout, get_combined_date_range, finalize_2x2_grid

# ── Signal direction guidance ────────────────────────────────────────────────
SIGNAL_GUIDE = {
    "yc": "⚠ Below 0 = inverted → recession signal. Above 0 = normal.",
    "indpro": "▲ Rising = expansion. ▼ Falling = contraction / recession risk.",
    "tcu": "▲ Above 80% = strong. ▼ Below 75% = weak demand / recession risk.",
    "tanker": "▲ Rising = crude shipping demand up. ▼ Sharp drop = demand destruction.",
}


def make_macro_grid(fred_df: pd.DataFrame, asset_df: pd.DataFrame) -> go.Figure:
    """Combined 2x2 grid: yield curve, industrial, BDI, capacity utilization.
    Each panel has a short directional note in the subtitle.
    """
    titles = [
        "Yield Curve (10Y-2Y)",
        "Industrial Production",
        "Tanker Freight Index",
        "Capacity Utilization (%)",
    ]
    fig = make_subplots(rows=2, cols=2, subplot_titles=titles, vertical_spacing=0.16, horizontal_spacing=0.08)

    # Yield curve
    if not fred_df.empty and "Yield Curve (10Y-2Y)" in fred_df.columns:
        s = fred_df["Yield Curve (10Y-2Y)"].dropna()
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name="10Y-2Y",
                                 line=dict(color=WAR_COLORS["cyan"], width=2), showlegend=False), row=1, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color=WAR_COLORS["red"], opacity=0.5, row=1, col=1)

    # Industrial production
    if not fred_df.empty and "Industrial Production" in fred_df.columns:
        s = fred_df["Industrial Production"].dropna()
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name="INDPRO",
                                 line=dict(color=WAR_COLORS["green"], width=2), showlegend=False), row=1, col=2)

    # Tanker freight
    if not asset_df.empty and "Tanker Freight" in asset_df.columns:
        s = asset_df["Tanker Freight"].dropna()
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name="Tanker",
                                 line=dict(color=WAR_COLORS["amber"], width=2), showlegend=False), row=2, col=1)

    # Capacity utilization
    if not fred_df.empty and "Capacity Utilization" in fred_df.columns:
        s = fred_df["Capacity Utilization"].dropna()
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name="TCU",
                                 line=dict(color=WAR_COLORS["gold"], width=2), showlegend=False), row=2, col=2)
        # Reference lines at 75% and 80%
        fig.add_hline(y=80, line_dash="dot", line_color=WAR_COLORS["green"], opacity=0.4, row=2, col=2)
        fig.add_hline(y=75, line_dash="dot", line_color=WAR_COLORS["red"], opacity=0.4, row=2, col=2)

    layout = base_layout("MACRO RECESSION SIGNALS")
    layout["height"] = 580
    fig.update_layout(**layout)

    x_min, x_max = get_combined_date_range(fred_df, asset_df)
    finalize_2x2_grid(fig, x_min, x_max)

    return fig
