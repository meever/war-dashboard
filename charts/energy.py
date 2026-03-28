"""Energy-specific charts: crack spreads, inventory levels, refinery utilization."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from charts.utils import WAR_COLORS, base_layout, get_combined_date_range, finalize_2x2_grid


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

    layout = base_layout("ENERGY & DEMAND OVERVIEW")
    layout["height"] = 580
    layout["legend"] = dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=9),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    )
    fig.update_layout(**layout)
    x_min, x_max = get_combined_date_range(crack_df, eia_df)
    finalize_2x2_grid(fig, x_min, x_max)
    return fig
