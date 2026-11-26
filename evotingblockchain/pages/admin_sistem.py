import pandas as pd
import streamlit as st

from components.tabs import tab_select

import config
from components import tx_flow
from components.admin_gate import require_admin
from components.header import hash_code
from components.notifications import alert
from database import db
from services import blockchain as bc
from services import system_service as ss
from services.errors import EvoteError


def render():
    addr = require_admin("Pengaturan Sistem", "Informasi jaringan, kontrak, role Panitia, dan audit log aplikasi.", "landmark")
    s = bc.status()
    d = bc.deployment()
    labels = ["Jaringan dan Kontrak", "Role Panitia", "Audit Log Aplikasi"]
    sel = tab_select(labels, "tab_sistem")
    if sel == labels[0]:
        st.markdown(f'<div class="ev-card"><dl class="ev-kv"><dt>RPC URL</dt><dd>{hash_code(config.RPC_URL)}</dd>'
                    f'<dt>Chain ID</dt><dd>{s["chain_id"]}</dd><dt>Alamat kontrak</dt><dd>{hash_code(d["address"])}</dd>'
                    f'<dt>Deployer</dt><dd>{hash_code(d.get("deployer"))}</dd><dt>Blok deployment</dt><dd>{d.get("deployBlock", "-")}</dd>'
                    f'<dt>Waktu deployment</dt><dd>{d.get("deployedAt", "-")}</dd><dt>Basis data</dt><dd>{hash_code(str(config.DB_PATH))}</dd></dl></div>',
                    unsafe_allow_html=True)
        st.markdown('<p class="ev-card-title" style="margin-top:14px">Isi basis data off-chain</p>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{"Tabel": k, "Jumlah baris": v} for k, v in ss.db_counts().items()]), hide_index=True, width="stretch")
        alert("info", "Jika Hardhat node dimulai ulang, state blockchain hilang. Jalankan ulang 'npm run deploy' dan gunakan basis data baru "
                      "(hapus data/evote.db) agar metadata off-chain tidak merujuk periode yang sudah tidak ada.", "Catatan operasional")
    if sel == labels[1]:
        members = ss.panitia_members()
        st.dataframe(pd.DataFrame({"Wallet Panitia": members}), hide_index=True, width="stretch")
        if not ss.is_super_admin(addr):
            alert("warning", "Hanya wallet dengan DEFAULT_ADMIN_ROLE yang dapat menambah atau mencabut Panitia.")
        else:
            target = st.text_input("Alamat wallet", placeholder="0x...", key="role_target")
            a, b = st.columns(2)
            try:
                if a.button("Beri role Panitia", type="primary", key="grant", use_container_width=True):
                    tx_flow.start(ss.prepare_grant(addr, target))
                if b.button("Cabut role Panitia", key="revoke", use_container_width=True):
                    tx_flow.start(ss.prepare_revoke(addr, target))
            except EvoteError as exc:
                alert("danger", str(exc))
    if sel == labels[2]:
        rows = db.recent_audit(200)
        if rows:
            st.dataframe(pd.DataFrame([{"Waktu": r["at"], "Aktor": r["actor"], "Tindakan": r["action"], "Periode": r["election_id"],
                                        "Detail": r["detail"], "Tx": (r["tx_hash"] or "")[:14]} for r in rows]), hide_index=True, width="stretch")
        else:
            st.caption("Belum ada catatan.")
