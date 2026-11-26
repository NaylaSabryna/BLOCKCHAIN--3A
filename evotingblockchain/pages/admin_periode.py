import datetime as dt

import pandas as pd
import streamlit as st

from components.tabs import tab_select

import config
from components import tx_flow
from components.admin_gate import require_admin
from components.notifications import alert, empty_state
from pages.results import results_body
from services import blockchain as bc
from services import election_service as es
from services.errors import EvoteError


def _times(prefix, start_default, end_default):
    c1, c2, c3, c4 = st.columns(4)
    sd = c1.date_input("Tanggal mulai", start_default.date(), key=f"{prefix}_sd")
    stt = c2.time_input("Jam mulai (WIB)", start_default.time(), key=f"{prefix}_st", step=300)
    ed = c3.date_input("Tanggal berakhir", end_default.date(), key=f"{prefix}_ed")
    et = c4.time_input("Jam berakhir (WIB)", end_default.time(), key=f"{prefix}_et", step=300)
    return es.to_unix(sd, stt), es.to_unix(ed, et)


def render():
    addr = require_admin("Manajemen Periode", "Buat dan kelola periode pemilihan tanpa mengubah kode program.", "calendar-range")
    labels = ["Daftar Periode", "Buat Periode", "Edit Periode", "Arsip dan Hasil"]
    sel = tab_select(labels, "tab_periode")
    items = es.list_elections()
    if sel == labels[0]:
        if not items:
            empty_state("Belum ada periode", "Gunakan tab 'Buat Periode' untuk membuat periode pertama.", "calendar-range")
        else:
            st.dataframe(pd.DataFrame([{"ID": e["id"], "Nama Pemilihan": e["name"], "Status": e["status"], "Kandidat": e["candidates"],
                                        "Pemilih": e["approved_voters"], "Suara": e["total_votes"], "Mulai": es.fmt_time(e["start"]),
                                        "Berakhir": es.fmt_time(e["end"])} for e in items]), hide_index=True, width="stretch")
            st.caption("Status mengikuti aturan waktu di blockchain: Draft, Belum Dimulai, Sedang Berlangsung, Selesai, atau Dibatalkan.")
    if sel == labels[1]:
        now = dt.datetime.fromtimestamp(bc.chain_now(), config.TZ) + dt.timedelta(minutes=15)
        now = now.replace(second=0, microsecond=0)
        name = st.text_input("Nama pemilihan", max_chars=120, key="new_name")
        desc = st.text_area("Deskripsi pemilihan", max_chars=2000, key="new_desc")
        s, e = _times("new", now, now + dt.timedelta(days=1))
        if st.button("Buat periode", type="primary", key="btn_create_election"):
            try:
                tx_flow.start(es.prepare_create(addr, name, desc, s, e))
            except EvoteError as exc:
                alert("danger", str(exc), "Tidak dapat membuat periode")
        st.caption("Periode dibuat sebagai Draft. Tambahkan minimal dua kandidat, lalu publikasikan di menu Pengaturan Pemilihan.")
    if sel == labels[2]:
        editable = [x for x in items if x["editable"]]
        if not editable:
            empty_state("Tidak ada periode yang dapat diedit", "Periode hanya dapat diedit sebelum waktu mulai.", "pencil")
        else:
            by = {x["id"]: x for x in editable}
            eid = st.selectbox("Pilih periode", list(by), format_func=lambda i: f"{by[i]['name']} (#{i})", key="edit_pick")
            cur = by[eid]
            name = st.text_input("Nama pemilihan", cur["name"], max_chars=120, key=f"en_{eid}")
            desc = st.text_area("Deskripsi", cur["description"], max_chars=2000, key=f"ed_{eid}")
            s, e = _times(f"e{eid}", dt.datetime.fromtimestamp(cur["start"], config.TZ), dt.datetime.fromtimestamp(cur["end"], config.TZ))
            if st.button("Simpan perubahan", type="primary", key=f"save_{eid}"):
                try:
                    tx_flow.start(es.prepare_update(addr, eid, name, desc, s, e))
                except EvoteError as exc:
                    alert("danger", str(exc), "Tidak dapat menyimpan")
    if sel == labels[3]:
        arch = [x for x in items if x["status"] in (es.STATUS_DONE, es.STATUS_CANCELLED)]
        if not arch:
            empty_state("Belum ada arsip", "Periode yang selesai atau dibatalkan akan tersimpan di sini dan tetap dapat dilihat.", "history")
        else:
            by = {x["id"]: x for x in arch}
            eid = st.selectbox("Arsip periode", list(by), format_func=lambda i: f"{by[i]['name']} (#{i}, {by[i]['status']})", key="arch_pick")
            results_body(eid, admin=True)
