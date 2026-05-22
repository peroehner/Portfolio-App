"""Plotly technical analysis chart."""
import plotly.graph_objects as go

from portfolio_app.config import CHART_HEIGHT


def create_chart(ticker, hist, fibs, f_trends, inspect_active):
    fig = go.Figure()
    if hist is None or hist.empty:
        return fig

    if getattr(hist.index, "tz", None) is not None:
        hist.index = hist.index.tz_localize(None)
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=hist["Close"],
            name="Price",
            line=dict(color="#1f77b4", width=2),
        )
    )

    fibo_colors = ["#d62728", "#ff7f0e", "#2ca02c", "#ff7f0e", "#d62728"]
    for (label, val), color in zip(fibs.items(), fibo_colors):
        fig.add_hline(y=val, line_dash="dash", line_color=color, annotation_text=label)

    fig.update_layout(
        template="plotly_white",
        height=CHART_HEIGHT,
        margin=dict(l=12, r=12, t=8, b=8),
    )

    if inspect_active and f_trends:
        trend_colors = {
            "T1": "#00CC96",
            "T2": "#AB63FA",
            "T3": "#FFA15A",
            "T4": "#19D3F3",
        }
        for t in f_trends:
            width = 4 if t["id"] == "T1" else 2
            dash = "solid" if t["id"] == "T1" else "dash"

            fig.add_trace(
                go.Scatter(
                    x=[t["f_start"], t["f_end"]],
                    y=[t["price_start"], t["price_end"]],
                    mode="lines+markers",
                    name=f"Trend {t['id']} ({t['type']})",
                    line=dict(
                        color=trend_colors.get(t["id"], "#7f7f7f"),
                        width=width,
                        dash=dash,
                    ),
                    marker=dict(size=6, color=trend_colors.get(t["id"], "#7f7f7f")),
                    hoverinfo="text",
                    hovertext=f"Trend {t['id']}: {t['type']} ({t['move_pct']*100:.1f}%)",
                )
            )
    return fig
