import pandas as pd
import streamlit as st

import config
from components import wallet as wl
from components.header import hash_code, page_header
from components.notifications import alert, empty_state
from components.status_badge import status_badge
from services import auth_service as auth
from services import blockchain as bc
from services import election_service as es
from services import voter_service as vs


def render():
    page_header("Profil / Wallet", "Informasi wallet dan status Anda pada setiap periode.", "wallet")
    w = wl.current()
    if not w["has_provider"]:
        alert("warning", "MetaMask tidak terdeteksi di browser ini.")
    if not w["connected"]:
        alert("info", "Hubungkan wallet melalui tombol 'Hubungkan Wallet' pada panel samping.")
        return
    balance = bc.get_w3().eth.get_balance(w["address"]) / 10**18
    role = "Panitia" if auth.is_panitia(w["address"]) else "Pemilih"
    st.markdown(f'<div class="ev-card"><dl class="ev-kv"><dt>Alamat wallet</dt><dd>{hash_code(w["address"])}</dd>'
                f'<dt>Jaringan</dt><dd>{config.CHAIN_NAME if w["chain_ok"] else "Tidak sesuai"} (Chain ID {w["chain_id"]})</dd>'
                f'<dt>Saldo</dt><dd>{balance:,.4f} {config.CURRENCY_SYMBOL}</dd>'
                f'<dt>Peran di smart contract</dt><dd>{status_badge(role, "info")}</dd>'
                f'<dt>Alamat kontrak</dt><dd>{hash_code(bc.contract_address())}</dd></dl></div>', unsafe_allow_html=True)
    if not w["chain_ok"]:
        if st.button("Pindah ke jaringan EVOTE", key="prof_switch", type="primary"):
            wl.request_switch_network()
            st.rerun()
    st.markdown('<p class="ev-card-title" style="margin-top:16px">Status pada setiap periode</p>', unsafe_allow_html=True)
    items = es.list_elections()
    if not items:
        empty_state("Belum ada periode", "Status akan tampil setelah panitia membuat periode.", "calendar-range")
        return
    rows = []
    for e in items:
        s = vs.wallet_status(e["id"], w["address"])
        rows.append({"Periode": f"#{e['id']} {e['name']}", "Status Periode": e["status"], "Registrasi": s["registration"],
                     "Memenuhi Syarat": "Ya" if s["eligible"] else "Tidak", "Hak Suara": "Sudah digunakan" if s["voted"] else "Belum digunakan"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
