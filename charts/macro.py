"""
Macro indicator charts: industrial production, manufacturing, yield curve, BDI.
Includes directional guidance — what's good vs bad for each signal.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from charts.assets import WAR_COLORS, _base_layout, add_recessions

# ── Signal direction guidance ────────────────────────────────────────────────
SIGNAL_GUIDE = {
    "yc": "⚠ Below 0 = inverted → recession signal. Above 0 = normal.",
    "indpro": "▲ Rising = expansion. ▼ Falling = contraction / recession risk.",
    "tcu": "▲ Above 80% = strong. ▼ Below 75% = weak demand / recession risk.",
    "bdi": "▲ Rising = global trade growing. ▼ Sharp drop = demand destruction.",
}


def _add_direction_note(fig: go.Figure, text: str):
    """Add a small directional annotation at bottom-right of chart."""
    fig.add_annotation(
        text=text,
        xref="paper", yref="paper", x=0.99, y=0.02,
        showarrow=False, xanchor="right", yanchor="bottom",
        font=dict(size=9, color="#888", family="Courier New"),
        bgcolor="rgba(10,10,10,0.7)",
        bordercolor=WAR_COLORS["grid"],
        borderwidth=1,
    )


def make_yield_curve_chart(df: pd.DataFrame) -> go.Figure:
    """Yield curve (10Y-2Y spread) with recession danger zone."""
    col = "Yield Curve (10Y-2Y)"
    fig = go.Figure()

    if col not in df.columns or df[col].dropna().empty:
        fig.update_layout(**_base_layout("YIELD CURVE SPREAD (10Y - 2Y)"))
        fig.add_annotation(text="FRED data unavailable — add API key in sidebar",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=14, color=WAR_COLORS["amber"]))
        return fig

    series = df[col].dropna()

    # Recession zone shading (below zero)
    fig.add_hrect(y0=-5, y1=0, fillcolor=WAR_COLORS["red"], opacity=0.1,
                  line_width=0, annotation_text="INVERTED", annotation_position="top left",
                  annotation_font=dict(color=WAR_COLORS["red"], size=10))

    fig.add_trace(go.Scatter(
        x=series.index, y=series.values,
        mode="lines", name="10Y-2Y Spread",
        line=dict(color=WAR_COLORS["cyan"], width=2),
        fill="tozeroy",
        fillcolor="rgba(0, 255, 65, 0.05)",
        hovertemplate="%{y:.2f}%<extra></extra>",
    ))

    fig.add_hline(y=0, line_dash="dash", line_color=WAR_COLORS["red"], opacity=0.8)

    layout = _base_layout("YIELD CURVE SPREAD (10Y - 2Y)")
    layout["height"] = 380
    layout["legend"] = dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=9),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    )
    fig.update_layout(**layout)
    _add_direction_note(fig, SIGNAL_GUIDE["yc"])
    return fig


def make_industrial_chart(df: pd.DataFrame) -> go.Figure:
    """Industrial production and manufacturing employment."""
    fig = go.Figure()
    added = False

    series_config = [
        ("Industrial Production", WAR_COLORS["green"], "left"),
        ("Manufacturing Employment", WAR_COLORS["amber"], "right"),
        ("Capacity Utilization", WAR_COLORS["cyan"], "left"),
    ]

    for col, color, _ in series_config:
        if col in df.columns and not df[col].dropna().empty:
            series = df[col].dropna()
            fig.add_trace(go.Scatter(
                x=series.index, y=series.values,
                mode="lines", name=col,
                line=dict(color=color, width=2),
                hovertemplate="%{y:,.1f}<extra></extra>",
            ))
            added = True

    layout = _base_layout("MANUFACTURING & INDUSTRIAL HEALTH")
    layout["height"] = 380
    layout["legend"] = dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=9),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    )
    fig.update_layout(**layout)

    if not added:
        fig.add_annotation(text="FRED data unavailable — add API key in sidebar",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=14, color=WAR_COLORS["amber"]))
    else:
        _add_direction_note(fig, SIGNAL_GUIDE["indpro"])

    return fig


def make_bdi_chart(df: pd.DataFrame) -> go.Figure:
    """Dry Bulk Shipping chart (SBLK ETF as freight proxy)."""
    col = "Dry Bulk Shipping"
    fig = go.Figure()

    if col not in df.columns or df[col].dropna().empty:
        fig.update_layout(**_base_layout("DRY BULK SHIPPING (SBLK)"))
        fig.add_annotation(text="No shipping data available",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=16, color=WAR_COLORS["red"]))
        return fig

    series = df[col].dropna()

    fig.add_trace(go.Scatter(
        x=series.index, y=series.values,
        mode="lines", name="SBLK",
        line=dict(color=WAR_COLORS["green"], width=2),
        fill="tozeroy",
        fillcolor="rgba(0, 255, 65, 0.05)",
        hovertemplate="%{y:,.0f}<extra></extra>",
    ))

    layout = _base_layout("DRY BULK SHIPPING — SBLK (Freight Proxy)")
    layout["height"] = 380
    layout["legend"] = dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=9),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    )
    fig.update_layout(**layout)
    _add_direction_note(fig, SIGNAL_GUIDE["bdi"])
    return fig


def make_macro_grid(fred_df: pd.DataFrame, asset_df: pd.DataFrame) -> go.Figure:
    """Combined 2x2 grid: yield curve, industrial, BDI, capacity utilization.
    Each panel has a short directional note in the subtitle.
    """
    titles = [
        "Yield Curve (10Y-2Y)",
        "Industrial Production",
        "Dry Bulk Shipping (SBLK)",
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

    # BDI
    if not asset_df.empty and "Dry Bulk Shipping" in asset_df.columns:
        s = asset_df["Dry Bulk Shipping"].dropna()
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name="SBLK",
                                 line=dict(color=WAR_COLORS["amber"], width=2), showlegend=False), row=2, col=1)

    # Capacity utilization
    if not fred_df.empty and "Capacity Utilization" in fred_df.columns:
        s = fred_df["Capacity Utilization"].dropna()
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name="TCU",
                                 line=dict(color=WAR_COLORS["gold"], width=2), showlegend=False), row=2, col=2)
        # Reference lines at 75% and 80%
        fig.add_hline(y=80, line_dash="dot", line_color=WAR_COLORS["green"], opacity=0.4, row=2, col=2)
        fig.add_hline(y=75, line_dash="dot", line_color=WAR_COLORS["red"], opacity=0.4, row=2, col=2)

    layout = _base_layout("MACRO RECESSION SIGNALS")
    layout["height"] = 580
    fig.update_layout(**layout)

    # Compute visible date range from both data sources
    idx_parts = []
    if not fred_df.empty:
        idx_parts.append(fred_df.index)
    if not asset_df.empty:
        idx_parts.append(asset_df.index)
    if idx_parts:
        combined = idx_parts[0].append(idx_parts[1:]) if len(idx_parts) > 1 else idx_parts[0]
        x_min, x_max = combined.min(), combined.max()
    else:
        x_min = x_max = None

    for i in range(1, 5):
        r = (i - 1) // 2 + 1
        c = (i - 1) % 2 + 1
        fig.update_xaxes(gridcolor=WAR_COLORS["grid"], autorange=True, row=r, col=c)
        fig.update_yaxes(gridcolor=WAR_COLORS["grid"], autorange=True, row=r, col=c)
        add_recessions(fig, row=r, col=c, x_min=x_min, x_max=x_max)

    return fig
