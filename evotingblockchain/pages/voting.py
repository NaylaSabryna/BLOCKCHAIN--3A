import streamlit as st

from components import tx_flow, wallet as wl
from components.candidate_card import candidate_card_html
from components.header import page_header
from components.notifications import alert, checklist, empty_state
from components.status_badge import status_badge
from services import election_service as es
from services import voting_service as vt
from services.errors import EvoteError


@st.dialog("Konfirmasi Pilihan")
def _confirm(e, c, wallet_addr):
    
    st.markdown(f'<div class="ev-card"><dl class="ev-kv"><dt>Kandidat</dt><dd><b>{c["nama"]}</b></dd>'
                f'<dt>Nomor urut</dt><dd>{c["nomor"]}</dd><dt>Periode</dt><dd>{e["name"]}</dd></dl></div>', unsafe_allow_html=True)
    st.write("")
    alert("warning", "Pilihan tidak dapat diubah setelah transaksi berhasil. Anda akan diminta menyetujui transaksi di MetaMask.",
          "Peringatan")
    a, b = st.columns(2)
    if a.button("Kembali", use_container_width=True):
        st.rerun()
    if b.button("Konfirmasi Pilihan", type="primary", use_container_width=True):
        try:
            plan = vt.prepare_vote(wallet_addr, e["id"], c["cid"])
        except EvoteError as exc:
            st.error(str(exc))
            return
        tx_flow.start(plan)


def render():
    page_header("Pemungutan Suara", "Pilih satu kandidat dan setujui transaksi melalui MetaMask.", "vote")
    from components.selectors import election_picker
    e = election_picker()
    if not e:
        return
    w = wl.current()
    gate = vt.vote_gate(e["id"], w["address"], w["chain_id"])
    badge = status_badge(e["status"], icon=True)
    st.markdown(f'{badge} &nbsp; <span class="ev-note">{es.fmt_time(e["start"])} sampai {es.fmt_time(e["end"])}</span>',
                unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1, 2])
    with left:
        st.markdown('<p class="ev-card-title">Syarat pemungutan suara</p>', unsafe_allow_html=True)
        checklist([{"label": c["label"], "ok": c["ok"], "detail": c["detail"]} for c in gate["checks"]])
        if w["connected"] and not w["chain_ok"]:
            if st.button("Pindah ke jaringan EVOTE", key="vote_switch"):
                wl.request_switch_network()
                st.rerun()
        st.markdown('<p class="ev-note" style="margin-top:10px">Mode prototipe transparan: transaksi voting bersifat publik di blockchain '
                    'sehingga bukan secret ballot. Lihat catatan privasi pada dokumentasi.</p>', unsafe_allow_html=True)
    with right:
        cands = gate["candidates"]
        if not cands:
            empty_state("Belum ada kandidat aktif", "Periode ini belum memiliki kandidat untuk dipilih.", "users")
            return
        if gate["can_vote"]:
            alert("success", "Semua syarat terpenuhi. Pilih satu kandidat di bawah ini.")
        else:
            alert("warning", gate["reason"] or "Syarat pemungutan suara belum terpenuhi.", "Voting belum dapat dilakukan")
        pending = st.session_state.pop("confirm_cid", None)
        cols = st.columns(min(len(cands), 3))
        for i, c in enumerate(cands):
            with cols[i % len(cols)]:
                st.markdown(candidate_card_html(c), unsafe_allow_html=True)
                if st.button("Pilih Kandidat", key=f"vote_{e['id']}_{c['cid']}", type="primary",
                             use_container_width=True, disabled=not gate["can_vote"]):
                    _confirm(e, c, w["address"])
                st.write("")
        if pending and pending[0] == e["id"] and gate["can_vote"]:
            target = next((c for c in cands if c["cid"] == pending[1]), None)
            if target:
                _confirm(e, target, w["address"])
