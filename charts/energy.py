"""
Energy-specific charts: crack spreads, inventory levels, refinery utilization.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from charts.assets import WAR_COLORS, _base_layout, add_recessions


def make_crack_spread_chart(df: pd.DataFrame) -> go.Figure:
    """Crack spread time series (Heating Oil & Gasoline vs WTI)."""
    fig = go.Figure()

    if df.empty:
        fig.update_layout(**_base_layout("CRACK SPREADS ($/bbl)"))
        fig.add_annotation(text="No crack spread data available",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=16, color=WAR_COLORS["red"]))
        return fig

    color_map = {
        "Heating Oil Spread": WAR_COLORS["amber"],
        "Gasoline Spread": WAR_COLORS["cyan"],
    }

    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values,
            mode="lines", name=col,
            line=dict(color=color_map.get(col, WAR_COLORS["green"]), width=2),
            hovertemplate="%{y:,.2f}<extra></extra>",
        ))

    # Zero line for reference
    fig.add_hline(y=0, line_dash="dash", line_color=WAR_COLORS["red"], opacity=0.5)

    layout = _base_layout("CRACK SPREADS ($/bbl)")
    layout["height"] = 380
    layout["legend"] = dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=9),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    )
    fig.update_layout(**layout)
    return fig


def make_inventory_chart(df: pd.DataFrame) -> go.Figure:
    """EIA petroleum inventory levels."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(**_base_layout("PETROLEUM INVENTORIES"))
        fig.add_annotation(text="EIA data unavailable — add API key in sidebar",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=14, color=WAR_COLORS["amber"]))
        return fig

    # Filter to inventory columns (exclude utilization)
    inv_cols = [c for c in df.columns if "Stock" in c or "stock" in c.lower()]
    util_cols = [c for c in df.columns if "Util" in c or "util" in c.lower()]

    if not inv_cols and not util_cols:
        inv_cols = list(df.columns)

    has_util = len(util_cols) > 0 and len(inv_cols) > 0

    if has_util:
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=["Inventory Levels", "Refinery Utilization %"],
            vertical_spacing=0.15,
            row_heights=[0.6, 0.4],
        )
    else:
        fig = go.Figure()

    colors = [WAR_COLORS["cyan"], WAR_COLORS["amber"], WAR_COLORS["green"], WAR_COLORS["gold"]]

    for i, col in enumerate(inv_cols):
        series = df[col].dropna()
        if series.empty:
            continue
        trace = go.Scatter(
            x=series.index, y=series.values,
            mode="lines", name=col,
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate="%{y:,.0f}<extra></extra>",
        )
        if has_util:
            fig.add_trace(trace, row=1, col=1)
        else:
            fig.add_trace(trace)

    for i, col in enumerate(util_cols):
        series = df[col].dropna()
        if series.empty:
            continue
        if has_util:
            fig.add_trace(go.Scatter(
                x=series.index, y=series.values,
                mode="lines", name=col,
                line=dict(color=WAR_COLORS["red"], width=2),
                hovertemplate="%{y:.1f}%<extra></extra>",
            ), row=2, col=1)

    layout = _base_layout("PETROLEUM INVENTORIES")
    layout["height"] = 380
    layout["legend"] = dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=9),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    )
    fig.update_layout(**layout)
    return fig


def make_energy_grid(crack_df: pd.DataFrame, eia_df: pd.DataFrame) -> go.Figure:
    """2x2 energy grid: Crack spreads, Crude stocks, Product stocks, Refinery util."""
    titles = [
        "Crack Spreads ($/bbl)",
        "Crude Oil Stocks (k bbl)",
        "Product Stocks (k bbl)",
        "Refinery Utilization (%)",
    ]
    fig = make_subplots(rows=2, cols=2, subplot_titles=titles,
                        vertical_spacing=0.14, horizontal_spacing=0.08)

    # Panel 1: crack spreads
    if not crack_df.empty:
        color_map = {"Heating Oil Spread": WAR_COLORS["amber"], "Gasoline Spread": WAR_COLORS["cyan"]}
        for col in crack_df.columns:
            s = crack_df[col].dropna()
            if s.empty:
                continue
            fig.add_trace(go.Scatter(
                x=s.index, y=s.values, mode="lines", name=col,
                line=dict(color=color_map.get(col, WAR_COLORS["green"]), width=2),
                legendgroup="crack", showlegend=True,
                hovertemplate="%{y:,.2f}<extra></extra>",
            ), row=1, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color=WAR_COLORS["red"], opacity=0.4, row=1, col=1)

    if not eia_df.empty:
        inv_cols = [c for c in eia_df.columns if "Stock" in c or "stock" in c.lower()]
        util_cols = [c for c in eia_df.columns if "Util" in c or "util" in c.lower()]
        crude_cols = [c for c in inv_cols if "Crude" in c or "crude" in c.lower()]
        product_cols = [c for c in inv_cols if c not in crude_cols]
        colors = [WAR_COLORS["cyan"], WAR_COLORS["amber"], WAR_COLORS["green"], WAR_COLORS["gold"]]

        # Panel 2: crude stocks
        for i, col in enumerate(crude_cols):
            s = eia_df[col].dropna()
            if s.empty:
                continue
            fig.add_trace(go.Scatter(
                x=s.index, y=s.values, mode="lines", name=col,
                line=dict(color=colors[i % len(colors)], width=2),
                legendgroup="crude", showlegend=(len(crude_cols) > 1),
                hovertemplate="%{y:,.0f}<extra></extra>",
            ), row=1, col=2)

        # Panel 3: product stocks
        for i, col in enumerate(product_cols):
            s = eia_df[col].dropna()
            if s.empty:
                continue
            fig.add_trace(go.Scatter(
                x=s.index, y=s.values, mode="lines", name=col,
                line=dict(color=colors[i % len(colors)], width=2),
                legendgroup="product", showlegend=(len(product_cols) > 1),
                hovertemplate="%{y:,.0f}<extra></extra>",
            ), row=2, col=1)

        # Panel 4: refinery utilization
        for col in util_cols:
            s = eia_df[col].dropna()
            if s.empty:
                continue
            fig.add_trace(go.Scatter(
                x=s.index, y=s.values, mode="lines", name=col,
                line=dict(color=WAR_COLORS["red"], width=2),
                legendgroup="util", showlegend=False,
                hovertemplate="%{y:.1f}%<extra></extra>",
            ), row=2, col=2)

    layout = _base_layout("ENERGY & DEMAND OVERVIEW")
    layout["height"] = 580
    layout["legend"] = dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=9),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    )
    fig.update_layout(**layout)
    # Compute visible date range from both data sources
    idx_parts = []
    if not crack_df.empty:
        idx_parts.append(crack_df.index)
    if not eia_df.empty:
        idx_parts.append(eia_df.index)
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
