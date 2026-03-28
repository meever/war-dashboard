"""
Long-term historical context charts.
Shows full available history for each asset with the current level highlighted,
recession bands, and key crisis markers — so you can see where we are today
relative to decades of data.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from charts.assets import WAR_COLORS, _base_layout, RECESSIONS, add_recessions

# Key crisis events (date, label)
CRISIS_EVENTS = [
    ("2001-09-11", "9/11"),
    ("2008-09-15", "Lehman"),
    ("2011-08-05", "US Downgrade"),
    ("2014-11-27", "OPEC\nPrice War"),
    ("2020-03-09", "COVID\nCrash"),
    ("2022-02-24", "Russia\nInvades"),
]

ASSET_LABELS = {
    "wti":   "WTI Crude Oil ($/bbl)",
    "brent": "Brent Crude Oil ($/bbl)",
    "spx":   "S&P 500 Index",
    "gold":  "Gold ($/oz)",
    "us10y": "US 10-Year Yield (%)",
    "sblk":  "Dry Bulk Shipping — SBLK ($)",
}

ASSET_COLORS_MAP = {
    "wti":   WAR_COLORS["amber"],
    "brent": WAR_COLORS["red"],
    "spx":   WAR_COLORS["green"],
    "gold":  WAR_COLORS["gold"],
    "us10y": WAR_COLORS["cyan"],
    "sblk":  WAR_COLORS["white"],
}


# Use add_recessions imported from charts.assets
_add_recessions = add_recessions


def _add_crisis_markers(fig: go.Figure, series: pd.Series, row: int | None = None, col: int | None = None):
    """Add crisis event annotations where they fall within the series date range."""
    if series.empty:
        return
    min_date = series.index.min()
    max_date = series.index.max()
    for date_str, label in CRISIS_EVENTS:
        dt = pd.Timestamp(date_str)
        if min_date <= dt <= max_date:
            # Find nearest value
            idx = series.index.get_indexer([dt], method="nearest")[0]
            if 0 <= idx < len(series):
                val = series.iloc[idx]
                kwargs = dict(
                    x=series.index[idx], y=val,
                    text=label,
                    showarrow=True, arrowhead=2,
                    arrowcolor="rgba(255,65,54,0.5)",
                    font=dict(size=8, color="#888", family="Courier New"),
                    bgcolor="rgba(10,10,10,0.7)",
                    bordercolor="rgba(255,65,54,0.25)",
                    borderwidth=1,
                )
                if row is not None and col is not None:
                    kwargs["row"] = row
                    kwargs["col"] = col
                fig.add_annotation(**kwargs)


def make_long_term_chart(
    df: pd.DataFrame,
    asset_key: str,
    col_name: str = "Close",
) -> go.Figure:
    """
    Single-asset full-history chart with recession shading,
    crisis markers, and a 'you are here' highlight on the current level.
    """
    label = ASSET_LABELS.get(asset_key, asset_key)
    color = ASSET_COLORS_MAP.get(asset_key, WAR_COLORS["green"])
    fig = go.Figure()

    if df.empty:
        fig.update_layout(**_base_layout(label))
        fig.add_annotation(text="No historical data available",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=16, color=WAR_COLORS["red"]))
        return fig

    series = df[col_name] if col_name in df.columns else df.iloc[:, 0]
    series = series.dropna()

    if series.empty:
        fig.update_layout(**_base_layout(label))
        return fig

    # Main price line
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values,
        mode="lines", name=label,
        line=dict(color=color, width=1.5),
        hovertemplate="%{x|%Y-%m-%d}: %{y:,.2f}<extra></extra>",
    ))

    # Recession shading
    for start, end in RECESSIONS:
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor="rgba(255, 65, 54, 0.08)",
            line_width=0,
        )

    # Crisis markers
    _add_crisis_markers(fig, series)

    # "YOU ARE HERE" — current level horizontal line + annotation
    current = series.iloc[-1]
    fig.add_hline(y=current, line_dash="dot", line_color=WAR_COLORS["red"], opacity=0.6)
    fig.add_annotation(
        x=series.index[-1], y=current,
        text=f"  NOW: {current:,.2f}",
        showarrow=False,
        font=dict(size=11, color=WAR_COLORS["red"], family="Courier New"),
        xanchor="left",
        bgcolor="rgba(10,10,10,0.8)",
        bordercolor=WAR_COLORS["red"],
        borderwidth=1,
    )

    # Historical percentile
    pct = (series < current).sum() / len(series) * 100
    fig.add_annotation(
        text=f"Historical Percentile: {pct:.0f}%",
        xref="paper", yref="paper", x=0.02, y=0.98,
        showarrow=False,
        font=dict(size=11, color=WAR_COLORS["green"] if pct < 80 else WAR_COLORS["red"],
                  family="Courier New"),
        bgcolor="rgba(10,10,10,0.8)",
        bordercolor=WAR_COLORS["grid"],
        borderwidth=1,
    )

    layout = _base_layout(f"{label} — FULL HISTORY")
    layout["height"] = 350
    fig.update_layout(**layout)
    return fig


def make_crack_spread_history_chart(crack_df: pd.DataFrame) -> go.Figure:
    """Long-term crack spread chart with current level highlighted."""
    fig = go.Figure()

    if crack_df.empty:
        fig.update_layout(**_base_layout("CRACK SPREADS — FULL HISTORY ($/bbl)"))
        fig.add_annotation(text="No historical crack spread data",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=14, color=WAR_COLORS["red"]))
        return fig

    color_map = {
        "Heating Oil Spread": WAR_COLORS["amber"],
        "Gasoline Spread": WAR_COLORS["cyan"],
    }

    for col in crack_df.columns:
        s = crack_df[col].dropna()
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values,
            mode="lines", name=col,
            line=dict(color=color_map.get(col, WAR_COLORS["green"]), width=1.5),
            hovertemplate="%{x|%Y-%m-%d}: %{y:,.2f}<extra></extra>",
        ))

        # Current level line
        current = s.iloc[-1]
        fig.add_annotation(
            x=s.index[-1], y=current,
            text=f"  {col}: ${current:.1f}",
            showarrow=False, xanchor="left",
            font=dict(size=9, color=color_map.get(col, WAR_COLORS["green"]), family="Courier New"),
            bgcolor="rgba(10,10,10,0.8)",
        )

    fig.add_hline(y=0, line_dash="dash", line_color=WAR_COLORS["red"], opacity=0.5)

    # Recession shading
    for start, end in RECESSIONS:
        fig.add_vrect(x0=start, x1=end, fillcolor="rgba(255, 65, 54, 0.08)", line_width=0)

    layout = _base_layout("CRACK SPREADS — FULL HISTORY ($/bbl)")
    layout["height"] = 300
    fig.update_layout(**layout)
    return fig


def make_long_term_grid(market_data: dict[str, pd.DataFrame]) -> go.Figure:
    """2x2 grid: Oil (WTI+Brent), S&P 500, Gold, US 10Y Yield with full history."""
    titles = ["Crude Oil — WTI & Brent ($/bbl)", "S&P 500 Index", "Gold ($/oz)", "US 10-Year Yield (%)"]

    fig = make_subplots(rows=2, cols=2, subplot_titles=titles,
                        vertical_spacing=0.12, horizontal_spacing=0.08)

    # Panel configs: list of (store_key, color) per panel
    panel_configs = [
        [("wti", WAR_COLORS["amber"]), ("brent", WAR_COLORS["red"])],
        [("spx", WAR_COLORS["green"])],
        [("gold", WAR_COLORS["gold"])],
        [("us10y", WAR_COLORS["cyan"])],
    ]

    for i, traces in enumerate(panel_configs):
        r = (i // 2) + 1
        c = (i % 2) + 1
        for key, color in traces:
            df = market_data.get(key)
            if df is None or df.empty:
                continue
            series = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
            series = series.dropna()
            if series.empty:
                continue

            fig.add_trace(go.Scatter(
                x=series.index, y=series.values,
                mode="lines", name=ASSET_LABELS.get(key, key),
                line=dict(color=color, width=1.5),
                showlegend=(len(traces) > 1),
                hovertemplate="%{y:,.2f}<extra></extra>",
            ), row=r, col=c)

            # Current value hline
            current = series.iloc[-1]
            fig.add_hline(y=current, line_dash="dot", line_color=WAR_COLORS["red"],
                          opacity=0.4, row=r, col=c)

        # Recession shading
        _add_recessions(fig, row=r, col=c)

    layout = _base_layout("LONG-TERM ASSET CONTEXT")
    layout["height"] = 580
    fig.update_layout(**layout)

    for i in range(1, 5):
        fig.update_xaxes(gridcolor=WAR_COLORS["grid"], row=(i - 1) // 2 + 1, col=(i - 1) % 2 + 1)
        fig.update_yaxes(gridcolor=WAR_COLORS["grid"], row=(i - 1) // 2 + 1, col=(i - 1) % 2 + 1)

    return fig
