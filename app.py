"""EVOTE - Decentralized Electronic Voting System. Titik masuk Streamlit."""
import streamlit as st

import config

st.set_page_config(page_title="EVOTE", page_icon=str(config.BASE_DIR / "assets" / "favicon.png"),
                   layout="wide", initial_sidebar_state="expanded")

from components import sidebar, tx_flow
from components.header import page_header
from components.notifications import alert, render_flash
from database import db
from pages import (admin_audit, admin_dashboard, admin_kandidat, admin_pemilih, admin_pengaturan, admin_periode,
                   admin_rekap, admin_sistem, candidates, dashboard, profile, results, transaction_history,
                   verification, voting)
from services import blockchain as bc

db.init_db()
st.markdown(f"<style>{config.CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
sidebar.inject_icon_css()

ROUTES = {
    "dashboard": dashboard.render, "candidates": candidates.render, "voting": voting.render,
    "results": results.render, "verification": verification.render, "transactions": transaction_history.render,
    "profile": profile.render,
    "admin_dashboard": admin_dashboard.render, "admin_periode": admin_periode.render,
    "admin_kandidat": admin_kandidat.render, "admin_pemilih": admin_pemilih.render,
    "admin_pengaturan": admin_pengaturan.render, "admin_rekap": admin_rekap.render,
    "admin_audit": admin_audit.render, "admin_transaksi": transaction_history.render_admin,
    "admin_sistem": admin_sistem.render,
}
TITLES = {k: t for k, t, _ in sidebar.VOTER_NAV + sidebar.ADMIN_NAV}
pages = {pid: st.Page(fn, title=TITLES[pid], url_path=pid, default=(pid == "dashboard")) for pid, fn in ROUTES.items()}
st.session_state["_pages"] = pages

pg = st.navigation(list(pages.values()), position="hidden")
current_id = pg.url_path or "dashboard"

admin_ids = {k for k, _, _ in sidebar.ADMIN_NAV}
mode = st.session_state.get("mode") or ("Panitia" if current_id in admin_ids else "Pemilih")
# Sinkronkan area dengan halaman: berpindah area membuka halaman pertama area tersebut.
if st.session_state.get("_last_mode") not in (None, mode):
    first = (sidebar.ADMIN_NAV if mode == "Panitia" else sidebar.VOTER_NAV)[0][0]
    st.session_state["_last_mode"] = mode
    if (current_id in admin_ids) != (mode == "Panitia"):
        st.switch_page(pages[first])
st.session_state["_last_mode"] = mode
if (current_id in admin_ids) and mode != "Panitia":
    mode = "Panitia"
    st.session_state["mode"] = "Panitia"

sidebar.render(current_id, pages, mode)

status = bc.status()
if not status["contract_ok"]:
    page_header("Blockchain tidak tersedia", "Aplikasi membutuhkan node Hardhat dan kontrak yang sudah dideploy.", "network")
    alert("danger", status["error"] or "Koneksi blockchain gagal.", "Tidak dapat terhubung")
    st.code("npm run node        # terminal 1\nnpm run deploy      # terminal 2\nstreamlit run app.py  # terminal 3", language="bash")
    st.stop()

render_flash()
tx_flow.render()
pg.run()
