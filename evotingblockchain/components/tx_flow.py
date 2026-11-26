"""Alur transaksi: siapkan -> MetaMask menandatangani -> menunggu receipt -> verifikasi status -> hook.
Transaksi baru dianggap berhasil bila receipt valid dengan status 1."""
import time

import streamlit as st

import config
from components import wallet as wl
from components.header import hash_code
from components.notifications import alert, flash
from components.status_badge import status_badge
from services import blockchain as bc
from services import election_service as es
from services.errors import EvoteError
from services.flow import run_after


def start(plan: dict, done_page: str | None = None):
    rid = wl.request_tx(plan["request"])
    st.session_state["tx_flow"] = {"plan": plan, "rid": rid, "stage": "wallet", "hash": None, "t0": time.time(),
                                   "done_page": done_page}
    st.session_state.pop("tx_receipt_card", None)
    st.rerun()


def _clear():
    st.session_state.pop("tx_flow", None)
    st.session_state.pop("wallet_request", None)


def _receipt_card(card: dict):
    st.markdown(
        f'<div class="ev-card" style="margin-bottom:14px"><p class="ev-card-title">{card["title"]} '
        f'{status_badge("Berhasil", icon=True)}</p>'
        f'<dl class="ev-kv"><dt>Transaction Hash</dt><dd>{hash_code(card["hash"])}</dd>'
        f'<dt>Nomor Blok</dt><dd>{card["block"]}</dd><dt>Waktu</dt><dd>{card["time"]}</dd>'
        f'{card.get("extra", "")}</dl></div>', unsafe_allow_html=True)
    if card.get("message"):
        alert("success", card["message"])
    if st.button("Tutup bukti transaksi", key="close_receipt"):
        st.session_state.pop("tx_receipt_card", None)
        st.rerun()


def render():
    """Dipanggil sekali per eksekusi sebelum konten halaman."""
    card = st.session_state.get("tx_receipt_card")
    flow = st.session_state.get("tx_flow")
    if not flow:
        if card:
            _receipt_card(card)
        return
    plan, stage = flow["plan"], flow["stage"]
    box = st.container(border=True)
    with box:
        st.markdown(f'<p class="ev-card-title">{plan["label"]}</p>', unsafe_allow_html=True)
        if stage == "wallet":
            resp = wl.take_response(flow["rid"])
            if resp is None:
                st.markdown(status_badge("Menunggu Persetujuan Wallet", icon=True), unsafe_allow_html=True)
                st.caption("Buka jendela MetaMask dan setujui transaksi. Periksa akun dan jaringan yang aktif.")
                if st.button("Batalkan permintaan", key="tx_cancel"):
                    _clear()
                    flash("warning", "Permintaan transaksi dibatalkan.", "Dibatalkan Pengguna")
                    st.rerun()
                return
            if not resp["ok"]:
                _clear()
                if resp.get("rejected"):
                    flash("warning", "Anda menolak transaksi di MetaMask. Tidak ada perubahan yang tercatat.", "Dibatalkan Pengguna")
                elif "nonce" in (resp.get("error") or "").lower():
                    flash(
                        "danger",
                        "Transaksi gagal karena nonce wallet tidak sesuai dengan nonce node blockchain. "
                        "Periksa koneksi MetaMask dan pastikan node Hardhat tidak dimulai ulang "
                        "selama proses pemungutan suara. Transaksi belum tercatat.",
                        "Nonce tidak sinkron"
                    )
                else:
                    flash("danger", resp.get("error") or "Transaksi gagal dikirim.", "Gagal")
                st.rerun()
            flow.update(stage="confirm", hash=resp["txHash"])
            stage = "confirm"
        if stage == "confirm":
            st.markdown(status_badge("Menunggu Konfirmasi Blockchain", icon=True), unsafe_allow_html=True)
            st.markdown(f"Transaction Hash: {hash_code(flow['hash'])}", unsafe_allow_html=True)
            with st.spinner("Menunggu receipt transaksi..."):
                receipt = bc.wait_receipt(flow["hash"], timeout=45)
            if receipt is None:
                alert("warning", "Transaksi belum dikonfirmasi. Transaksi pending tidak dihitung sebagai berhasil.", "Masih Diproses")
                if st.button("Periksa lagi", key="tx_recheck", type="primary"):
                    st.rerun()
                if st.button("Tutup", key="tx_drop"):
                    _clear()
                    st.rerun()
                return
            if receipt["status"] != 1:
                _clear()
                flash("danger", "Transaksi dibatalkan oleh smart contract (status receipt gagal).", "Gagal")
                st.rerun()
            hook_error = None
            try:
                run_after(plan["after"], plan["payload"], receipt, plan["request"]["from"])
            except EvoteError as exc:
                hook_error = str(exc)
            ts = bc.block_timestamp(receipt["blockNumber"])
            extra = ""
            if plan["after"] == "vote_cast":
                extra = "<dt>Hak suara</dt><dd>Sudah digunakan pada periode ini</dd>"
                e = es.get_election(plan["payload"]["election_id"])
                if e:
                    extra = f"<dt>Periode</dt><dd>{e['name']}</dd>" + extra
            st.session_state["tx_receipt_card"] = {
                "title": plan["label"], "hash": receipt["transactionHash"].hex(), "block": receipt["blockNumber"],
                "time": es.fmt_time(ts), "extra": extra,
                "message": None if hook_error else plan["success"]}
            _clear()
            if hook_error:
                flash("danger", hook_error, "Perhatian")
            st.rerun()
