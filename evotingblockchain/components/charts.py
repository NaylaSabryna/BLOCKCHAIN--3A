import plotly.graph_objects as go

PALETTE = ["#2563EB", "#14243A", "#16A36A", "#D99A25", "#0EA5E9", "#64748B", "#DC4545", "#0F766E"]
_BASE = dict(font=dict(family="Inter, system-ui, sans-serif", color="#1E293B", size=13),
             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
             margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.15))
CONFIG = {"displayModeBar": False}


def _label(r):
    return f"No. {r['nomor']} - {r['nama']}"


def bar_votes(rows):
    fig = go.Figure(go.Bar(x=[_label(r) for r in rows], y=[r["suara"] for r in rows],
                           marker_color=PALETTE[0], text=[r["suara"] for r in rows], textposition="outside",
                           hovertemplate="%{x}<br>%{y} suara<extra></extra>"))
    fig.update_layout(**_BASE, height=340, yaxis=dict(title="Suara", gridcolor="#E2E8F0", rangemode="tozero", dtick=1 if max([r["suara"] for r in rows] or [0]) < 8 else None),
                      xaxis=dict(title=None), showlegend=False)
    return fig


def donut_votes(rows):
    fig = go.Figure(go.Pie(labels=[_label(r) for r in rows], values=[r["suara"] for r in rows], hole=0.62,
                           marker=dict(colors=PALETTE[:len(rows)], line=dict(color="#fff", width=2)),
                           textinfo="percent", sort=False))
    fig.update_layout(**_BASE, height=340)
    return fig


def participation_line(series):
    fig = go.Figure(go.Scatter(x=[s["waktu"] for s in series], y=[s["kumulatif"] for s in series],
                               mode="lines+markers", line=dict(color=PALETTE[0], width=3), marker=dict(size=7),
                               hovertemplate="%{x|%d %b %H:%M}<br>%{y} suara<extra></extra>"))
    fig.update_layout(**_BASE, height=280, yaxis=dict(title="Suara kumulatif", gridcolor="#E2E8F0", rangemode="tozero"),
                      xaxis=dict(title=None), showlegend=False)
    return fig


def activity_bar(series):
    fig = go.Figure(go.Bar(x=[s["waktu"] for s in series], y=[s["per_jam"] for s in series], marker_color=PALETTE[2],
                           hovertemplate="%{x|%d %b %H:%M}<br>%{y} suara<extra></extra>"))
    fig.update_layout(**_BASE, height=280, yaxis=dict(title="Suara per jam", gridcolor="#E2E8F0", rangemode="tozero"),
                      xaxis=dict(title=None), showlegend=False)
    return fig


def gauge(percent):
    fig = go.Figure(go.Indicator(mode="gauge+number", value=percent, number=dict(suffix="%", font=dict(size=34)),
                                 gauge=dict(axis=dict(range=[0, 100]), bar=dict(color=PALETTE[0]),
                                            bgcolor="#EEF2F6", borderwidth=0)))
    fig.update_layout(**_BASE, height=220)
    return fig
