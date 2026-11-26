import streamlit as st

from components import nav
from components.candidate_card import candidate_card_html, candidate_detail_html
from components.header import page_header
from components.notifications import empty_state
from components.selectors import election_picker
from services import candidate_service as cs
from services import election_service as es


@st.dialog("Detail Kandidat", width="large")
def _detail(c):
    st.markdown(candidate_detail_html(c), unsafe_allow_html=True)


def render():
    page_header("Daftar Kandidat", "Kandidat resmi pada periode pemilihan yang dipilih.", "users")
    e = election_picker()
    if not e:
        return
    cands = cs.list_candidates(e["id"])
    if not cands:
        empty_state("Belum ada kandidat", "Periode ini belum memiliki kandidat aktif. Panitia dapat menambahkannya dari dashboard.", "users")
        return
    can_pick = e["status"] == es.STATUS_RUNNING
    cols_n = 3
    for i in range(0, len(cands), cols_n):
        cols = st.columns(cols_n)
        for col, c in zip(cols, cands[i:i + cols_n]):
            with col:
                st.markdown(candidate_card_html(c), unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                if b1.button("Lihat Detail", key=f"det_{e['id']}_{c['cid']}", use_container_width=True):
                    _detail(c)
                if b2.button("Pilih Kandidat", key=f"pick_{e['id']}_{c['cid']}", type="primary",
                             use_container_width=True, disabled=not can_pick,
                             help=None if can_pick else "Pemungutan suara hanya dapat dilakukan saat pemilihan berlangsung."):
                    st.session_state["confirm_cid"] = (e["id"], c["cid"])
                    nav.goto("voting")
        st.write("")
