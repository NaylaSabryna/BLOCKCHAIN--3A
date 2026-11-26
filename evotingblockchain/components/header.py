from html import escape

import streamlit as st

from components.icons import svg


def page_header(title: str, subtitle: str = "", icon: str = "layout-dashboard"):
    sub = f'<p class="ev-page-sub">{escape(subtitle)}</p>' if subtitle else ""
    st.markdown(f'<div class="ev-page-header"><div class="ev-page-icon">{svg(icon, 22)}</div>'
                f'<div><h1 class="ev-page-title">{escape(title)}</h1>{sub}</div></div>', unsafe_allow_html=True)


def kv_list(pairs: list[tuple[str, str]]):
    """Daftar kunci-nilai. Nilai berupa HTML tepercaya yang sudah di-escape pemanggil."""
    body = "".join(f"<dt>{escape(k)}</dt><dd>{v}</dd>" for k, v in pairs)
    st.markdown(f'<div class="ev-card"><dl class="ev-kv">{body}</dl></div>', unsafe_allow_html=True)


def hash_code(value: str | None) -> str:
    return f'<code class="ev-hash">{escape(value)}</code>' if value else "-"
