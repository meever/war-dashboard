"""
Asset time-series charts: Oil (Brent+WTI), S&P 500, Gold, US 10Y Yield.
Uses Plotly with a dark war-room theme.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── War-room Plotly theme ────────────────────────────────────────────────────
WAR_COLORS = {
    "bg": "#0A0A0A",
    "paper": "#0F0F1A",
    "grid": "#1A1A2E",
    "text": "#E0E0E0",
    "green": "#00FF41",
    "red": "#FF4136",
    "gold": "#FFD700",
    "cyan": "#00FFFF",
    "amber": "#FF8C00",
    "white": "#FFFFFF",
}

ASSET_COLORS = {
    "Brent Crude": WAR_COLORS["red"],
    "WTI Crude": WAR_COLORS["amber"],
    "S&P 500": WAR_COLORS["green"],
    "Gold": WAR_COLORS["gold"],
    "US 10Y Yield": WAR_COLORS["cyan"],
    "Dry Bulk Shipping": WAR_COLORS["white"],
}

# ── US recession periods (NBER) ─────────────────────────────────────────────
RECESSIONS = [
    ("1980-01-01", "1980-07-01"),
    ("1981-07-01", "1982-11-01"),
    ("1990-07-01", "1991-03-01"),
    ("2001-03-01", "2001-11-01"),
    ("2007-12-01", "2009-06-01"),
    ("2020-02-01", "2020-04-01"),
]


def add_recessions(
    fig: go.Figure,
    row: int | None = None,
    col: int | None = None,
    x_min: pd.Timestamp | None = None,
    x_max: pd.Timestamp | None = None,
):
    """Add recession shading bands to a chart or subplot.

    Only recessions that overlap the *x_min* – *x_max* window are drawn.
    If both are None every recession is included (backward-compatible).
    """
    for start, end in RECESSIONS:
        rec_start = pd.Timestamp(start)
        rec_end = pd.Timestamp(end)
        if x_min is not None and rec_end < x_min:
            continue
        if x_max is not None and rec_start > x_max:
            continue
        kwargs = dict(
            x0=start, x1=end,
            fillcolor="rgba(255, 65, 54, 0.08)",
            line_width=0,
        )
        if row is not None and col is not None:
            kwargs["row"] = row
            kwargs["col"] = col
        fig.add_vrect(**kwargs)


# Plotly chart config — enables scroll zoom and shows autoscale button
PLOTLY_CONFIG = {
    "scrollZoom": True,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def _base_layout(title: str) -> dict:
    """Shared dark layout options for all charts."""
    return dict(
        template="plotly_dark",
        title=dict(text=title, font=dict(size=16, color=WAR_COLORS["text"], family="Courier New")),
        paper_bgcolor=WAR_COLORS["paper"],
        plot_bgcolor=WAR_COLORS["bg"],
        font=dict(family="Courier New", color=WAR_COLORS["text"], size=11),
        xaxis=dict(gridcolor=WAR_COLORS["grid"], showgrid=True, zeroline=False, autorange=True),
        yaxis=dict(gridcolor=WAR_COLORS["grid"], showgrid=True, zeroline=False, autorange=True),
        margin=dict(l=50, r=20, t=40, b=30),
        height=300,
        hovermode="x unified",
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    )


def make_asset_chart(df: pd.DataFrame, column: str, title: str | None = None) -> go.Figure:
    """Create a single asset line chart."""
    if column not in df.columns or df[column].dropna().empty:
        fig = go.Figure()
        fig.update_layout(**_base_layout(title or column))
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False,
                           font=dict(size=18, color=WAR_COLORS["red"]))
        return fig

    series = df[column].dropna()
    color = ASSET_COLORS.get(column, WAR_COLORS["green"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index,
        y=series.values,
        mode="lines",
        name=column,
        line=dict(color=color, width=2),
        hovertemplate="%{y:,.2f}<extra></extra>",
    ))

    fig.update_layout(**_base_layout(title or column))
    return fig


def make_oil_chart(df: pd.DataFrame) -> go.Figure:
    """Brent and WTI on the same chart, same scale."""
    fig = go.Figure()
    has_data = False
    for col, color in [("Brent Crude", WAR_COLORS["red"]), ("WTI Crude", WAR_COLORS["amber"])]:
        if col in df.columns and not df[col].dropna().empty:
            series = df[col].dropna()
            fig.add_trace(go.Scatter(
                x=series.index, y=series.values,
                mode="lines", name=col,
                line=dict(color=color, width=2),
                hovertemplate=f"{col}: " + "%{y:,.2f}<extra></extra>",
            ))
            has_data = True

    layout = _base_layout("CRUDE OIL — BRENT vs WTI ($/bbl)")
    layout["height"] = 380
    layout["legend"] = dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=10),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    )
    fig.update_layout(**layout)
    if not has_data:
        fig.add_annotation(text="No oil data available", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False,
                           font=dict(size=16, color=WAR_COLORS["red"]))
    return fig


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

    layout_opts = _base_layout("ASSET BLOWUP TRACKER")
    layout_opts["height"] = 580
    layout_opts["legend"] = dict(
        bgcolor="rgba(0,0,0,0)", font=dict(size=9),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    )
    fig.update_layout(**layout_opts)

    # Compute visible date range from the data
    x_min = df.index.min() if not df.empty else None
    x_max = df.index.max() if not df.empty else None

    for i in range(1, 5):
        r = (i - 1) // 2 + 1
        c = (i - 1) % 2 + 1
        fig.update_xaxes(gridcolor=WAR_COLORS["grid"], autorange=True, row=r, col=c)
        fig.update_yaxes(gridcolor=WAR_COLORS["grid"], autorange=True, row=r, col=c)
        add_recessions(fig, row=r, col=c, x_min=x_min, x_max=x_max)

    return fig
