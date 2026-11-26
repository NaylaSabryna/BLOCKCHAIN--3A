import pandas as pd
import streamlit as st

from components.tabs import tab_select

from components import tx_flow
from components.admin_gate import require_admin
from components.header import hash_code
from components.metric_card import metric_row
from components.notifications import alert, empty_state, flash, render_flash
from components.selectors import election_picker
from components.status_badge import status_badge
from services import blockchain as bc
from services import voter_service as vs
from services.errors import EvoteError

TEMPLATE = "custom_id,nama,kode_registrasi\n"


def render():
    addr = require_admin("Manajemen Pemilih", "Daftar pemilih tetap, verifikasi registrasi, dan status hak suara.", "user-check")
    render_flash()
    e = election_picker()
    if not e:
        return
    stt = vs.roster_stats(e["id"])
    metric_row([
        {"label": "Daftar Pemilih Tetap", "value": stt["dpt"], "icon": "users"},
        {"label": "Menunggu Verifikasi", "value": stt["menunggu"], "icon": "clock", "tone": "warning" if stt["menunggu"] else ""},
        {"label": "Terverifikasi", "value": stt["terverifikasi"], "icon": "circle-check", "tone": "success"},
        {"label": "Ditolak", "value": stt["ditolak"], "icon": "x", "tone": "danger" if stt["ditolak"] else ""},
    ])
    labels = ["Permohonan Registrasi", "Daftar Pemilih Tetap (CSV)", "Status Hak Suara"]
    sel = tab_select(labels, "tab_pemilih")
    if sel == labels[0]:
        c1, c2 = st.columns([1, 2])
        flt = c1.selectbox("Status", ["Semua", "Menunggu Verifikasi", "Terverifikasi", "Ditolak"], key="reg_flt")
        q = c2.text_input("Cari Custom ID atau wallet", key="reg_q")
        rev = {v: k for k, v in vs.REG_LABEL.items()}
        regs = vs.list_registrations(addr, e["id"], rev.get(flt), q)
        if not regs:
            empty_state("Tidak ada permohonan", "Belum ada permohonan registrasi yang cocok.", "clipboard-list")
        else:
            st.dataframe(pd.DataFrame([{"ID": r["id"], "Custom ID": r["custom_id"], "Nama": r["nama"], "Wallet": r["wallet"],
                                        "Status": vs.REG_LABEL[r["status"]], "Diajukan": r["submitted_at"]} for r in regs]),
                         hide_index=True, width="stretch")
            by = {r["id"]: r for r in regs}
            rid = st.selectbox("Pilih permohonan", list(by), key="reg_pick",
                               format_func=lambda i: f"#{i} - {by[i]['custom_id']} - {vs.REG_LABEL[by[i]['status']]}")
            r = by[rid]
            st.markdown(f'<div class="ev-card"><dl class="ev-kv"><dt>Custom ID</dt><dd>{r["custom_id"]}</dd><dt>Nama (DPT)</dt><dd>{r["nama"]}</dd>'
                        f'<dt>Wallet</dt><dd>{hash_code(r["wallet"])}</dd><dt>Status</dt><dd>{status_badge(vs.REG_LABEL[r["status"]])}</dd>'
                        f'<dt>Alasan</dt><dd>{r["alasan"] or "-"}</dd><dt>Transaksi persetujuan</dt><dd>{hash_code(r["approve_tx_hash"])}</dd></dl></div>',
                        unsafe_allow_html=True)
            with st.expander("Riwayat perubahan status"):
                st.dataframe(pd.DataFrame(vs.registration_history(rid)), hide_index=True, width="stretch")
            if r["status"] == "menunggu":
                a, b = st.columns(2)
                with a:
                    if st.button("Setujui dan catat hak memilih di blockchain", type="primary", key=f"appr_{rid}", use_container_width=True):
                        try:
                            tx_flow.start(vs.prepare_approve(addr, rid))
                        except EvoteError as exc:
                            alert("danger", str(exc), "Tidak dapat menyetujui")
                with b:
                    alasan = st.text_input("Alasan penolakan", key=f"rej_why_{rid}")
                    if st.button("Tolak permohonan", key=f"rej_{rid}", use_container_width=True):
                        try:
                            vs.reject_registration(addr, rid, alasan)
                            flash("success", "Permohonan ditolak dan tercatat di audit log.", "Berhasil")
                            st.rerun()
                        except EvoteError as exc:
                            alert("danger", str(exc), "Tidak dapat menolak")
    if sel == labels[1]:
        alert("info", "Verifikasi identitas dilakukan melalui DPT yang diimpor panitia. Pemilih hanya dapat mendaftar jika Custom ID dan "
                      "kode registrasi sekali pakai cocok dengan DPT. Identitas mentah hanya disimpan di database server, tidak di blockchain.",
              "Cara kerja verifikasi")
        st.download_button("Unduh templat CSV", TEMPLATE, "templat_dpt.csv", "text/csv")
        up = st.file_uploader("Impor DPT (CSV: custom_id, nama, kode_registrasi opsional)", type=["csv"], key="dpt_up")
        if up is not None and st.button("Impor DPT", type="primary", key="btn_import"):
            try:
                res = vs.import_roster(addr, e["id"], up.getvalue())
                st.session_state["new_codes"] = (e["id"], res)
                st.rerun()
            except EvoteError as exc:
                alert("danger", str(exc), "Impor gagal")
        nc = st.session_state.get("new_codes")
        if nc and nc[0] == e["id"]:
            res = nc[1]
            alert("success", f"{len(res['imported'])} pemilih diimpor, {len(res['skipped'])} baris dilewati.", "Impor selesai")
            if res["imported"]:
                alert("warning", "Kode registrasi hanya ditampilkan SEKALI. Unduh dan bagikan ke masing-masing pemilih secara aman.", "Simpan kode sekarang")
                df = pd.DataFrame(res["imported"])
                st.dataframe(df, hide_index=True, width="stretch")
                st.download_button("Unduh daftar kode (CSV)", df.to_csv(index=False), f"kode_registrasi_periode_{e['id']}.csv", "text/csv")
            if res["skipped"]:
                st.dataframe(pd.DataFrame(res["skipped"]), hide_index=True, width="stretch")
            if st.button("Sembunyikan kode", key="hide_codes"):
                st.session_state.pop("new_codes", None)
                st.rerun()
        with st.expander("Atur ulang kode registrasi pemilih"):
            from database import db
            with db.connect() as conn:
                roster = [dict(r) for r in conn.execute("SELECT id, custom_id, nama, kode_terpakai, gagal_verifikasi FROM voter_roster WHERE election_id=? ORDER BY custom_id", (e["id"],))]
            if roster:
                by = {r["id"]: r for r in roster}
                rid = st.selectbox("Pemilih", list(by), format_func=lambda i: f"{by[i]['custom_id']} - {by[i]['nama']}", key="reset_pick")
                if st.button("Buat kode baru", key="btn_reset"):
                    try:
                        st.code(vs.reset_code(addr, rid))
                        st.caption("Kode baru hanya ditampilkan sekali.")
                    except EvoteError as exc:
                        alert("danger", str(exc))
            else:
                st.caption("DPT periode ini masih kosong.")
    if sel == labels[2]:
        regs = [r for r in vs.list_registrations(addr, e["id"], "terverifikasi")]
        if not regs:
            empty_state("Belum ada pemilih terverifikasi", "Status hak suara tampil setelah ada pemilih terverifikasi.", "user-check")
        else:
            c = bc.get_contract()
            rows = [{"Custom ID": r["custom_id"], "Wallet": r["wallet"],
                     "Hak Suara": "Sudah digunakan" if c.functions.hasVoted(e["id"], r["wallet"]).call() else "Belum digunakan"} for r in regs]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            st.caption("Tabel ini hanya menunjukkan apakah hak suara dipakai, bukan pilihan kandidat.")
