import pandas as pd
import streamlit as st

from components import wallet as wl
from components.header import hash_code, page_header
from components.notifications import empty_state
from services import blockchain as bc
from services import election_service as es
from services import transactions as txs


def _body(is_admin: bool):
    w = wl.current()
    items = es.list_elections()
    names = {e["id"]: e["name"] for e in items}
    c1, c2, c3 = st.columns([2, 1, 1])
    q = c1.text_input("Cari Transaction Hash", placeholder="0x...", key=f"txq_{is_admin}")
    per = c2.selectbox("Periode", [0] + [e["id"] for e in items], key=f"txp_{is_admin}",
                       format_func=lambda i: "Semua periode" if i == 0 else f"#{i} {names[i]}")
    stt = c3.selectbox("Status", ["Semua", "Berhasil"], key=f"txs_{is_admin}")
    rows = txs.list_transactions(viewer=w["address"], is_admin=is_admin, election_id=per or None,
                                 status=None if stt == "Semua" else stt, query=q)
    if not rows:
        empty_state("Tidak ada transaksi", "Belum ada transaksi yang cocok dengan filter.", "history")
        return
    df = pd.DataFrame([{"Transaction Hash": r["tx_hash"], "Blok": r["block"], "Jenis": r["jenis"],
                        "Periode": names.get(r["election_id"], "-") if r["election_id"] else "-",
                        "Waktu": r["waktu"], "Status": r["status"], "Wallet": r["wallet_display"]} for r in rows])
    st.dataframe(df, hide_index=True, width="stretch")
    st.caption("Hanya transaksi yang berhasil dan tercatat sebagai event kontrak yang ditampilkan. "
               "Wallet pemilih disamarkan kecuali milik Anda sendiri atau bila Anda Panitia.")
    pick = st.selectbox("Detail transaksi", [r["tx_hash"] for r in rows], key=f"txd_{is_admin}", format_func=lambda h: h[:18] + "...")
    r = next(x for x in rows if x["tx_hash"] == pick)
    link = bc.explorer_link(r["tx_hash"])
    link_html = f'<a href="{link}" target="_blank">Buka di block explorer</a>' if link else "Tidak tersedia pada jaringan lokal"
    st.markdown(f'<div class="ev-card"><dl class="ev-kv"><dt>Transaction Hash</dt><dd>{hash_code(r["tx_hash"])}</dd>'
                f'<dt>Nomor blok</dt><dd>{r["block"]}</dd><dt>Jenis</dt><dd>{r["jenis"]}</dd><dt>Waktu</dt><dd>{r["waktu"]}</dd>'
                f'<dt>Wallet</dt><dd>{hash_code(r["wallet_full"]) if r["wallet_full"] else r["wallet_display"]}</dd>'
                f'<dt>Block explorer</dt><dd>{link_html}</dd></dl></div>', unsafe_allow_html=True)


def render():
    page_header("Riwayat Transaksi", "Aktivitas on-chain yang dibaca dari event smart contract.", "history")
    _body(False)


def render_admin():
    from components.admin_gate import require_admin
    require_admin("Riwayat Transaksi", "Seluruh aktivitas on-chain, termasuk alamat wallet (khusus Panitia).", "history")
    _body(True)
