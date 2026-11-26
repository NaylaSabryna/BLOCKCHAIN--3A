import pandas as pd
import streamlit as st

from components import tx_flow
from components.admin_gate import require_admin
from components.header import hash_code
from components.metric_card import metric_row
from components.notifications import alert, empty_state
from components.status_badge import status_badge
from services import audit_service as audit
from services import blockchain as bc
from services import election_service as es
from services.errors import EvoteError


def render():
    addr = require_admin("Blockchain Audit", "Rantai hash checkpoint, verifikasi integritas, dan riwayat status batch.", "shield-check")
    blocks = audit.list_blocks()
    integ = audit.chain_integrity() if blocks else {"valid": True, "first_invalid": 0}
    metric_row([
        {"label": "Total Batch Suara", "value": len(blocks), "icon": "box"},
        {"label": "Integritas Rantai", "value": "Valid" if integ["valid"] else f"Rusak pada blok {integ['first_invalid']}",
         "icon": "shield-check", "tone": "success" if integ["valid"] else "danger", "small": True},
        {"label": "Tinggi Blok Jaringan", "value": f"#{bc.get_w3().eth.block_number}", "icon": "hash"},
        {"label": "Blok Terakhir", "value": blocks[-1]["batchId"] if blocks else "-", "icon": "clock", "small": True},
    ])
    if not blocks:
        empty_state("Belum ada checkpoint", "Checkpoint dibuat di menu Rekapitulasi Suara atau otomatis saat finalisasi.", "shield-check")
        return
    tx_map = {}
    for ev in bc.get_events("CheckpointCreated"):
        tx_map[ev["args"]["batchId"]] = (ev["transactionHash"].hex(), ev["blockNumber"])
    st.dataframe(pd.DataFrame([{
        "Blok": b["index"], "Batch ID": b["batchId"], "Periode": b["electionId"], "Waktu": es.fmt_time(b["timestamp"]),
        "Previous Hash": b["previousHash"][:12] + "...", "Current Hash": b["blockHash"][:12] + "...",
        "Status Verifikasi": b["status_label"], "Transaction Hash": tx_map.get(b["batchId"], ("-",))[0][:14] + "...",
    } for b in blocks]), hide_index=True, width="stretch")
    st.markdown('<p class="ev-card-title" style="margin-top:16px">Cari dan kelola batch</p>', unsafe_allow_html=True)
    q = st.text_input("Cari berdasarkan Batch ID", key="audit_q")
    ids = [b["batchId"] for b in blocks]
    default = q.strip() if q.strip() in ids else None
    pick = st.selectbox("Batch", ids, index=ids.index(default) if default else len(ids) - 1, key="audit_pick")
    if q.strip() and not default:
        alert("warning", "Batch ID yang dicari tidak ditemukan. Menampilkan batch terpilih.")
    res = audit.search_batch(pick)
    b = res["block"]
    txh, blk = tx_map.get(pick, (None, None))
    st.markdown(f'<div class="ev-card"><dl class="ev-kv"><dt>Batch ID</dt><dd>{b["batchId"]}</dd><dt>Nomor blok</dt><dd>{b["index"]}</dd>'
                f'<dt>Periode</dt><dd>#{b["electionId"]}</dd><dt>Waktu</dt><dd>{es.fmt_time(b["timestamp"])}</dd>'
                f'<dt>Total suara (snapshot)</dt><dd>{b["totalVotes"]}</dd><dt>Snapshot Hash</dt><dd>{hash_code(b["snapshotHash"])}</dd>'
                f'<dt>Previous Hash</dt><dd>{hash_code(b["previousHash"])}</dd><dt>Current Hash</dt><dd>{hash_code(b["blockHash"])}</dd>'
                f'<dt>Status integritas</dt><dd>{status_badge("Valid" if integ["valid"] else "Tidak Valid")}</dd>'
                f'<dt>Status verifikasi</dt><dd>{status_badge(b["status_label"])}</dd>'
                f'<dt>Transaction Hash</dt><dd>{hash_code(txh)}</dd><dt>Catatan</dt><dd>{b["catatan"] or "-"}</dd></dl></div>', unsafe_allow_html=True)
    st.markdown('<p class="ev-card-title" style="margin-top:14px">Riwayat perubahan status</p>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"Waktu": es.fmt_time(h["timestamp"]), "Peristiwa": h["event"], "Status": h["status"], "Keterangan": h["detail"]} for h in res["history"]]),
                 hide_index=True, width="stretch")
    st.markdown('<p class="ev-card-title" style="margin-top:14px">Tindakan Panitia</p>', unsafe_allow_html=True)
    a, c, d = st.columns(3)
    st_name = b["status_name"]
    try:
        if a.button("Verifikasi lokal", disabled=st_name != "CREATED", key=f"vl_{b['index']}", use_container_width=True):
            tx_flow.start(audit.prepare_verify(addr, b["index"]))
        if c.button("Rekapitulasi bertingkat", disabled=st_name != "VERIFIED_LOCAL", key=f"rb_{b['index']}", use_container_width=True):
            tx_flow.start(audit.prepare_recap(addr, b["index"]))
        el = es.get_election(b["electionId"])
        if d.button("Penghitungan akhir", disabled=not (st_name == "IN_RECAP" and el and el["state"] == es.STATE_FINALIZED),
                    key=f"pa_{b['index']}", type="primary", use_container_width=True):
            tx_flow.start(audit.prepare_final(addr, b["index"]))
    except EvoteError as exc:
        alert("danger", str(exc))
    st.caption("Urutan status: Dibuat, Terverifikasi Lokal, Dalam Rekapitulasi, lalu Penghitungan Akhir (memerlukan periode final). "
               "Audit tidak memuat data pribadi maupun pilihan pemilih.")
