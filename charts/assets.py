"""
Asset time-series charts: Oil (Brent+WTI), S&P 500, Gold, US 10Y Yield.
Uses Plotly with a dark war-room theme.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from charts.utils import (
    WAR_COLORS, PLOTLY_CONFIG, add_recessions, base_layout, finalize_2x2_grid,
)


def make_asset_grid(df: pd.DataFrame) -> go.Figure:
    """2x2 grid: Oil (Brent+WTI), S&P 500, Gold, US 10Y Yield."""
    panels = [
        ("Crude Oil (Brent vs WTI)", [("Brent Crude", WAR_COLORS["red"]), ("WTI Crude", WAR_COLORS["amber"])]),
        ("S&P 500", [("S&P 500", WAR_COLORS["green"])]),
        ("Gold ($/oz)", [("Gold", WAR_COLORS["gold"])]),
        ("US 10Y Yield (%)", [("US 10Y Yield", WAR_COLORS["cyan"])]),
    ]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[p[0] for p in panels],
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
    )

    for i, (_, traces) in enumerate(panels):
        r = (i // 2) + 1
        c = (i % 2) + 1
        for col_name, color in traces:
            if col_name not in df.columns:
                continue
            series = df[col_name].dropna()
            if series.empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=series.index, y=series.values,
                    mode="lines", name=col_name,
                    line=dict(color=color, width=2),
                    hovertemplate="%{y:,.2f}<extra></extra>",
                    showlegend=(len(traces) > 1),
                ),
                row=r, col=c,
            )

    layout_opts = base_layout("ASSET BLOWUP TRACKER")
    layout_opts["height"] = 580
    layout_opts["legend"] = dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=9),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    )
    fig.update_layout(**layout_opts)

    x_min = df.index.min() if not df.empty else None
    x_max = df.index.max() if not df.empty else None
    finalize_2x2_grid(fig, x_min, x_max)

    return fig
