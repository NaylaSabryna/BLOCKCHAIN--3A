from html import escape

import streamlit as st

from components.icons import svg


def metric_card_html(label: str, value, icon: str = "info", hint: str | None = None,
                     tone: str = "", small: bool = False) -> str:
    hint_html = f'<div class="ev-metric-hint">{escape(str(hint))}</div>' if hint else ""
    size = " small" if small else ""
    return (f'<div class="ev-metric"><div class="ev-metric-top"><span class="ev-metric-label">{escape(label)}</span>'
            f'<span class="ev-metric-icon {tone}">{svg(icon, 18)}</span></div>'
            f'<div class="ev-metric-value{size}">{escape(str(value))}</div>{hint_html}</div>')


def metric_row(cards: list[dict], per_row: int = 4):
    """cards: [{label, value, icon, hint?, tone?, small?}] ditata dalam grid kolom."""
    for start in range(0, len(cards), per_row):
        chunk = cards[start:start + per_row]
        cols = st.columns(per_row)
        for col, card in zip(cols, chunk):
            with col:
                st.markdown(metric_card_html(**card), unsafe_allow_html=True)
        st.write("")
