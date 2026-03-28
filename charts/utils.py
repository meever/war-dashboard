"""Shared chart infrastructure: colours, layout, recession bands, grid helpers."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


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

# ── US recession periods (NBER) ─────────────────────────────────────────────
RECESSIONS = [
    ("1980-01-01", "1980-07-01"),
    ("1981-07-01", "1982-11-01"),
    ("1990-07-01", "1991-03-01"),
    ("2001-03-01", "2001-11-01"),
    ("2007-12-01", "2009-06-01"),
    ("2020-02-01", "2020-04-01"),
]

# Plotly chart config — enables scroll zoom and shows autoscale button
PLOTLY_CONFIG = {
    "scrollZoom": True,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def add_recessions(
    fig: go.Figure,
    row: int | None = None,
    col: int | None = None,
    x_min: pd.Timestamp | None = None,
    x_max: pd.Timestamp | None = None,
):
    """Add recession shading bands to a chart or subplot.

    Only recessions that overlap the *x_min* – *x_max* window are drawn.
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


def base_layout(title: str) -> dict:
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


def get_combined_date_range(*frames: pd.DataFrame) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """Return the min and max timestamp across multiple DataFrames."""
    indices = [frame.index for frame in frames if frame is not None and not frame.empty]
    if not indices:
        return None, None

    combined = indices[0]
    for index in indices[1:]:
        combined = combined.union(index)
    return combined.min(), combined.max()


def finalize_2x2_grid(
    fig: go.Figure,
    x_min: pd.Timestamp | None,
    x_max: pd.Timestamp | None,
) -> None:
    """Apply war-room axis styling and recession bands to all 4 panels."""
    for i in range(1, 5):
        r = (i - 1) // 2 + 1
        c = (i - 1) % 2 + 1
        fig.update_xaxes(gridcolor=WAR_COLORS["grid"], autorange=True, row=r, col=c)
        fig.update_yaxes(gridcolor=WAR_COLORS["grid"], autorange=True, row=r, col=c)
        add_recessions(fig, row=r, col=c, x_min=x_min, x_max=x_max)