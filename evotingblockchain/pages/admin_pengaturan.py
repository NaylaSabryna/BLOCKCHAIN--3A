import streamlit as st

from components import tx_flow
from components.admin_gate import require_admin
from components.notifications import alert, checklist
from components.selectors import election_picker
from components.status_badge import status_badge
from services import blockchain as bc
from services import election_service as es
from services import voter_service as vs
from services.errors import EvoteError


def render():
    addr = require_admin("Pengaturan Pemilihan", "Publikasi, pembatalan, dan finalisasi periode pemilihan.", "settings-2")
    e = election_picker()
    if not e:
        return
    stt = vs.roster_stats(e["id"])
    st.markdown(f'{status_badge(e["status"], icon=True)} &nbsp; <span class="ev-note">{es.fmt_time(e["start"])} sampai {es.fmt_time(e["end"])}</span>',
                unsafe_allow_html=True)
    st.write("")
    left, right = st.columns(2)
    with left:
        st.markdown('<p class="ev-card-title">Kesiapan publikasi</p>', unsafe_allow_html=True)
        now = bc.chain_now()
        checklist([
            {"label": "Status Draft", "ok": e["state"] == es.STATE_DRAFT, "detail": "Hanya periode Draft yang dapat dipublikasikan."},
            {"label": "Minimal dua kandidat aktif", "ok": e["candidates"] >= 2, "detail": f"Saat ini {e['candidates']} kandidat."},
            {"label": "Waktu mulai belum lewat", "ok": now < e["start"], "detail": "Edit jadwal periode lebih dulu."},
            {"label": "DPT sudah diimpor (disarankan)", "ok": stt["dpt"] > 0, "detail": "Impor DPT di menu Manajemen Pemilih."},
        ])
        ready = e["state"] == es.STATE_DRAFT and e["candidates"] >= 2 and now < e["start"]
        if st.button("Publikasikan periode", type="primary", disabled=not ready, key=f"pub_{e['id']}"):
            try:
                tx_flow.start(es.prepare_publish(addr, e["id"]))
            except EvoteError as exc:
                alert("danger", str(exc))
        st.caption("Setelah dipublikasikan, pemilih terverifikasi dapat memilih saat waktu mulai tiba. Kandidat terkunci pada waktu mulai.")
    with right:
        st.markdown('<p class="ev-card-title">Pembatalan dan finalisasi</p>', unsafe_allow_html=True)
        can_cancel = e["state"] in (es.STATE_DRAFT, es.STATE_PUBLISHED) and not e["needs_finalize"]
        ok_c = st.checkbox("Saya memahami pembatalan bersifat permanen", key=f"cn_ok_{e['id']}", disabled=not can_cancel)
        if st.button("Batalkan periode", disabled=not (can_cancel and ok_c), key=f"cancel_{e['id']}"):
            try:
                tx_flow.start(es.prepare_cancel(addr, e["id"]))
            except EvoteError as exc:
                alert("danger", str(exc))
        st.divider()
        ok_f = st.checkbox("Saya memahami hasil final tidak dapat dibuka kembali", key=f"fn_ok_{e['id']}", disabled=not e["needs_finalize"])
        if st.button("Finalisasi hasil", type="primary", disabled=not (e["needs_finalize"] and ok_f), key=f"final_{e['id']}"):
            try:
                tx_flow.start(es.prepare_finalize(addr, e["id"]))
            except EvoteError as exc:
                alert("danger", str(exc))
        if not e["needs_finalize"]:
            st.caption("Finalisasi tersedia setelah waktu berakhir pada periode yang dipublikasikan. Checkpoint audit dibuat otomatis.")
