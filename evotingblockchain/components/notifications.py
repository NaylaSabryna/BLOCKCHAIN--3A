from html import escape

import streamlit as st

from components.icons import svg

_ICON = {"info": "info", "success": "circle-check", "warning": "triangle-alert", "danger": "triangle-alert"}


def alert_html(kind: str, text: str, title: str | None = None) -> str:
    t = f'<p class="ev-alert-title">{escape(title)}</p>' if title else ""
    return (f'<div class="ev-alert {kind}"><span class="ev-alert-icon">{svg(_ICON[kind], 18)}</span>'
            f'<div>{t}<p class="ev-alert-text">{escape(text)}</p></div></div>')


def alert(kind: str, text: str, title: str | None = None):
    st.markdown(alert_html(kind, text, title), unsafe_allow_html=True)


def flash(kind: str, text: str, title: str | None = None):
    st.session_state.setdefault("_flash", []).append([kind, text, title, 4])


def render_flash():
    """Pesan tetap tampil selama beberapa render (komponen wallet memicu rerun tambahan)."""
    keep = []
    for item in st.session_state.get("_flash", []):
        kind, text, title, ttl = item
        alert(kind, text, title)
        if ttl > 1:
            keep.append([kind, text, title, ttl - 1])
    st.session_state["_flash"] = keep


def empty_state(title: str, text: str, icon: str = "info"):
    st.markdown(f'<div class="ev-empty"><div class="ev-empty-icon">{svg(icon, 22)}</div>'
                f'<p class="ev-empty-title">{escape(title)}</p><p class="ev-empty-text">{escape(text)}</p></div>',
                unsafe_allow_html=True)


def checklist(items: list[dict]):
    """items: [{label, ok, detail?}]"""
    rows = []
    for i in items:
        cls, ico = ("ok", "circle-check") if i["ok"] else ("bad", "x")
        detail = f"<small>{escape(i['detail'])}</small>" if (i.get("detail") and not i["ok"]) else ""
        rows.append(f'<div class="ev-check"><span class="ev-check-ico {cls}">{svg(ico, 18)}</span>'
                    f'<div>{escape(i["label"])}{detail}</div></div>')
    st.markdown('<div class="ev-card" style="padding:8px 18px">' + "".join(rows) + "</div>", unsafe_allow_html=True)
