"""Plotly chart helpers with consistent styling."""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

COLORS = {
    "primary": "#E8735A",      # coral
    "secondary": "#7EAE8B",    # sage green
    "accent": "#F4A261",       # warm orange
    "info": "#5B9BD5",         # blue
    "danger": "#E06C6C",       # red
    "muted": "#B0B0B0",       # gray
}

PALETTE = [
    COLORS["primary"],
    COLORS["secondary"],
    COLORS["accent"],
    COLORS["info"],
    "#9B7ED8",  # purple
    COLORS["danger"],
]

_LAYOUT_DEFAULTS = dict(
    template="plotly_white",
    font=dict(family="Inter, system-ui, sans-serif", size=14),
    margin=dict(l=40, r=20, t=40, b=40),
    height=380,
)


def _apply_layout(fig: go.Figure, **kwargs) -> go.Figure:
    merged = {**_LAYOUT_DEFAULTS, **kwargs}
    fig.update_layout(**merged)
    return fig


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def line_chart(
    df: pd.DataFrame,
    x: str,
    y: str | list[str],
    title: str = "",
    **kwargs,
) -> go.Figure:
    if isinstance(y, str):
        y = [y]
    fig = go.Figure()
    for i, col in enumerate(y):
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], name=col, mode="lines+markers",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2),
            marker=dict(size=4),
        ))
    return _apply_layout(fig, title=title, **kwargs)


def dual_axis_chart(
    df: pd.DataFrame,
    x: str,
    y1: str,
    y2: str,
    name1: str = "",
    name2: str = "",
    title: str = "",
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[x], y=df[y1], name=name1 or y1,
        marker_color=COLORS["primary"], opacity=0.8,
    ))
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y2], name=name2 or y2,
        line=dict(color=COLORS["secondary"], width=2),
        marker=dict(size=5), yaxis="y2",
    ))
    return _apply_layout(fig, title=title, yaxis2=dict(
        overlaying="y", side="right", showgrid=False,
    ))


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: str | None = None,
    horizontal: bool = False,
    **kwargs,
) -> go.Figure:
    orient = "h" if horizontal else "v"
    fig = px.bar(
        df, x=y if horizontal else x, y=x if horizontal else y,
        color=color, orientation=orient,
        color_discrete_sequence=PALETTE,
    )
    return _apply_layout(fig, title=title, **kwargs)


def stacked_bar_chart(
    df: pd.DataFrame,
    x: str,
    y_cols: list[str],
    title: str = "",
    colors: list[str] | None = None,
) -> go.Figure:
    fig = go.Figure()
    colors = colors or PALETTE
    for i, col in enumerate(y_cols):
        fig.add_trace(go.Bar(
            x=df[x], y=df[col], name=col,
            marker_color=colors[i % len(colors)],
        ))
    return _apply_layout(fig, title=title, barmode="stack")


def pie_chart(
    df: pd.DataFrame,
    names: str,
    values: str,
    title: str = "",
    hole: float = 0.4,
) -> go.Figure:
    fig = px.pie(
        df, names=names, values=values, hole=hole,
        color_discrete_sequence=PALETTE,
    )
    fig.update_traces(textposition="inside", textinfo="label+percent")
    return _apply_layout(fig, title=title)


def funnel_chart(
    df: pd.DataFrame,
    stage_col: str,
    value_col: str,
    title: str = "",
) -> go.Figure:
    fig = go.Figure(go.Funnel(
        y=df[stage_col],
        x=df[value_col],
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=PALETTE[:len(df)]),
    ))
    return _apply_layout(fig, title=title)


def histogram(
    values: pd.Series,
    title: str = "",
    nbins: int = 20,
    xaxis_title: str = "",
) -> go.Figure:
    fig = go.Figure(go.Histogram(
        x=values, nbinsx=nbins,
        marker_color=COLORS["primary"], opacity=0.8,
    ))
    return _apply_layout(fig, title=title, xaxis_title=xaxis_title, yaxis_title="Count")


def timing_heatmap(
    df: pd.DataFrame,
    x: str,
    y: str,
    z: str,
    title: str = "",
) -> go.Figure:
    """Day-of-week × hour heatmap for response rate analysis."""
    pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc="first")
    # Sort days: Sun=0 .. Sat=6
    day_order = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    pivot = pivot.reindex(index=[d for d in day_order if d in pivot.index])

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{h}:00" for h in pivot.columns],
        y=pivot.index,
        colorscale=[
            [0.0, "#f7f7f7"],
            [0.5, COLORS["accent"]],
            [1.0, COLORS["primary"]],
        ],
        text=pivot.values,
        texttemplate="%{text:.0f}%",
        textfont=dict(size=12),
        hoverongaps=False,
        colorbar=dict(title="%"),
    ))
    return _apply_layout(fig, title=title, height=300)


def heatmap_table(
    df: pd.DataFrame,
    title: str = "",
) -> go.Figure:
    """Styled table rendered as a heatmap-like Plotly table."""
    fig = go.Figure(go.Table(
        header=dict(
            values=list(df.columns),
            fill_color=COLORS["primary"],
            font=dict(color="white", size=14),
            align="center",
        ),
        cells=dict(
            values=[df[col] for col in df.columns],
            fill_color="white",
            align="center",
            font=dict(size=13),
        ),
    ))
    return _apply_layout(fig, title=title, height=min(400, 60 + 30 * len(df)))
