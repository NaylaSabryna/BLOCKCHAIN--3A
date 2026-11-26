import pandas as pd
import streamlit as st

from components.tabs import tab_select

import config
from components import wallet as wl
from components.header import hash_code, page_header
from components.notifications import alert, empty_state, flash
from components.selectors import election_picker
from components.status_badge import status_badge
from services import audit_service as audit
from services import blockchain as bc
from services import election_service as es
from services import voter_service as vs
from services.errors import EvoteError


def _poll_registration():
    flow = st.session_state.get("reg_flow")
    if not flow:
        return
    resp = wl.take_response(flow["rid"])
    if resp is None:
        return
    st.session_state.pop("reg_flow", None)
    if not resp["ok"]:
        flash("warning" if resp.get("rejected") else "danger",
              "Penandatanganan dibatalkan. Permohonan belum dikirim." if resp.get("rejected") else (resp.get("error") or "Gagal menandatangani."),
              "Registrasi belum dikirim")
        return
    try:
        vs.submit_registration(flow["election_id"], flow["custom_id"], flow["code"], flow["wallet"], resp["signature"])
        flash("success", "Permohonan registrasi terkirim dan menunggu verifikasi panitia.", "Berhasil")
    except EvoteError as exc:
        flash("danger", str(exc), "Registrasi ditolak sistem")


def _status_tab(e, w):
    ws = vs.wallet_status(e["id"], w["address"]) if w["connected"] else None
    chain_name = config.CHAIN_NAME if w["chain_ok"] else ("Jaringan tidak sesuai" if w["connected"] else "-")
    wallet_badge = "Wallet Terhubung" if w["connected"] else "Wallet Belum Terhubung"
    reg = ws["registration"] if ws else "Belum Terdaftar"
    if ws and ws["eligible"]:
        elig, elig_b = "Memenuhi Syarat", "Memenuhi Syarat"
    else:
        elig_b = "Tidak Memenuhi Syarat"
    voted = "Sudah Memilih" if ws and ws["voted"] else "Belum Memilih"
    pairs = [
        ("Alamat wallet", hash_code(w["address"]) if w["address"] else "-"),
        ("Status koneksi MetaMask", status_badge(wallet_badge)),
        ("Nama jaringan", chain_name), ("Chain ID", str(w["chain_id"] or "-")),
        ("Status registrasi", status_badge(reg if reg != "Terverifikasi" else "Terverifikasi")),
        ("Status verifikasi", status_badge("Terverifikasi" if ws and ws["eligible"] else ("Menunggu Verifikasi" if reg == "Menunggu Verifikasi" else "Belum Terdaftar" if reg == "Belum Terdaftar" else reg))),
        ("Kelayakan memilih", status_badge(elig_b)),
        ("Hak suara", status_badge(voted)),
        ("Periode aktif", f"{e['name']} (Periode #{e['id']}) {status_badge(e['status'])}"),
    ]
    body = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in pairs)
    st.markdown(f'<div class="ev-card"><dl class="ev-kv">{body}</dl></div>', unsafe_allow_html=True)
    if ws and ws["alasan"] and ws["registration"] == "Ditolak":
        alert("danger", f"Alasan penolakan: {ws['alasan']}")
    if ws and ws["history"]:
        st.markdown('<p class="ev-card-title" style="margin-top:14px">Riwayat perubahan status registrasi</p>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{"Waktu": h["at"], "Status": vs.REG_LABEL.get(h["status"], h["status"]), "Catatan": h["note"]} for h in ws["history"]]),
                     hide_index=True, width="stretch")
    st.caption("Wallet yang terhubung tidak otomatis berarti pemiliknya sah. Kelayakan hanya diberikan setelah verifikasi panitia dan tercatat di smart contract.")


def _register_tab(w):
    st.write("Registrasi memerlukan Custom ID dan kode registrasi dari panitia (berasal dari Daftar Pemilih Tetap). "
             "Wallet Anda harus menandatangani permohonan sebagai bukti kepemilikan.")
    open_items = [x for x in es.list_elections() if x["state"] in (es.STATE_DRAFT, es.STATE_PUBLISHED) and bc.chain_now() <= x["end"]]
    if not open_items:
        empty_state("Tidak ada periode yang membuka registrasi", "Registrasi dibuka untuk periode yang belum berakhir.", "calendar-range")
        return
    ids = [x["id"] for x in open_items]
    by = {x["id"]: x for x in open_items}
    eid = st.selectbox("Periode untuk registrasi", ids, format_func=lambda i: f"{by[i]['name']} (Periode #{i})", key="reg_election")
    if not w["connected"]:
        alert("info", "Hubungkan MetaMask melalui panel samping untuk mendaftar.")
    elif not w["chain_ok"]:
        alert("warning", f"Gunakan jaringan dengan Chain ID {w['expected_chain']}.")
    elif st.session_state.get("reg_flow"):
        alert("info", "Menunggu tanda tangan di MetaMask...")
        if st.button("Batalkan", key="reg_cancel"):
            st.session_state.pop("reg_flow", None)
            st.session_state.pop("wallet_request", None)
            st.rerun()
        return
    with st.form("form_registrasi"):
        st.text_input("Wallet", value=w["address"] or "", disabled=True)
        cid = st.text_input("Custom ID (mis. NIM)", max_chars=64)
        code = st.text_input("Kode registrasi", max_chars=32, type="password", help="Kode diberikan panitia dan hanya berlaku sekali.")
        ok = st.form_submit_button("Kirim permohonan dan tanda tangani", type="primary", disabled=not (w["connected"] and w["chain_ok"]))
    if ok:
        if not cid.strip() or not code.strip():
            alert("danger", "Custom ID dan kode registrasi wajib diisi.")
            return
        msg = vs.registration_message(eid, w["address"], cid)
        rid = wl.request_sign(msg, w["address"])
        st.session_state["reg_flow"] = {"rid": rid, "election_id": eid, "custom_id": cid.strip(), "code": code, "wallet": w["address"]}
        st.rerun()


def _audit_tab():
    st.write("Pencarian read-only atas checkpoint audit. Tidak menampilkan data pribadi maupun pilihan pemilih.")
    q = st.text_input("Batch ID", placeholder="Contoh: BATCH-1-A atau FINAL-1", key="pub_batch")
    if q.strip():
        res = audit.search_batch(q)
        if not res:
            empty_state("Batch tidak ditemukan", "Periksa kembali Batch ID.", "search")
            return
        b = res["block"]
        st.markdown(f'<div class="ev-card"><dl class="ev-kv"><dt>Batch ID</dt><dd>{b["batchId"]}</dd><dt>Nomor blok</dt><dd>{b["index"]}</dd>'
                    f'<dt>Waktu</dt><dd>{es.fmt_time(b["timestamp"])}</dd><dt>Status</dt><dd>{status_badge(b["status_label"])}</dd>'
                    f'<dt>Previous Hash</dt><dd>{hash_code(b["previousHash"])}</dd><dt>Current Hash</dt><dd>{hash_code(b["blockHash"])}</dd></dl></div>',
                    unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{"Waktu": es.fmt_time(h["timestamp"]), "Peristiwa": h["event"], "Status": h["status"], "Keterangan": h["detail"]} for h in res["history"]]),
                     hide_index=True, width="stretch")


def render():
    page_header("Verifikasi Pemilih", "Periksa status wallet, kelayakan memilih, dan lakukan registrasi.", "user-check")
    _poll_registration()
    from components.notifications import render_flash
    render_flash()
    w = wl.current()
    e = election_picker()
    labels = ["Status Saya", "Registrasi Pemilih", "Audit Batch"]
    sel = tab_select(labels, "tab_verif")
    if sel == labels[0]:
        if e:
            _status_tab(e, w)
    if sel == labels[1]:
        _register_tab(w)
    if sel == labels[2]:
        _audit_tab()
