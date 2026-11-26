import pandas as pd
import streamlit as st

from components import nav
from components.admin_gate import require_admin
from components.metric_card import metric_row
from components.notifications import empty_state
from services import blockchain as bc
from services import election_service as es
from services import transactions as txs
from services import voter_service as vs
from database import db


def render():
    addr = require_admin("Dashboard Admin", "Ringkasan operasional pemilihan dan aktivitas blockchain.", "layout-dashboard")
    items = es.list_elections()
    s = bc.status()
    running = [e for e in items if e["status"] == es.STATUS_RUNNING]
    votes = sum(e["total_votes"] for e in items)
    voters = sum(e["approved_voters"] for e in items)
    part = round(votes * 100 / voters, 1) if voters else 0.0
    pending = 0
    with db.connect() as conn:
        pending = conn.execute("SELECT COUNT(*) n FROM registrations WHERE status='menunggu'").fetchone()["n"]
    metric_row([
        {"label": "Total Periode", "value": len(items), "icon": "calendar-range"},
        {"label": "Periode Aktif", "value": len(running), "icon": "clock", "tone": "success" if running else ""},
        {"label": "Total Kandidat Aktif", "value": sum(e["candidates"] for e in items), "icon": "users"},
        {"label": "Total Pemilih Terverifikasi", "value": voters, "icon": "user-check"},
        {"label": "Total Suara Masuk", "value": votes, "icon": "vote"},
        {"label": "Partisipasi", "value": f"{part}%", "icon": "chart-column"},
        {"label": "Registrasi Menunggu", "value": pending, "icon": "clipboard-list", "tone": "warning" if pending else ""},
        {"label": "Status Jaringan", "value": "Terhubung" if s["contract_ok"] else "Terputus", "icon": "network",
         "tone": "success" if s["contract_ok"] else "danger", "small": True, "hint": f"Blok #{s['block_number']}"},
    ])
    st.markdown('<p class="ev-card-title">Pintasan</p>', unsafe_allow_html=True)
    cols = st.columns(5)
    for col, (pid, label) in zip(cols, [("admin_periode", "Manajemen Periode"), ("admin_kandidat", "Manajemen Kandidat"),
                                        ("admin_pemilih", "Manajemen Pemilih"), ("admin_pengaturan", "Pengaturan Pemilihan"),
                                        ("admin_audit", "Blockchain Audit")]):
        if col.button(label, key=f"sc_{pid}", use_container_width=True):
            nav.goto(pid)
    left, right = st.columns(2)
    with left:
        st.markdown('<p class="ev-card-title" style="margin-top:14px">Permohonan registrasi terbaru</p>', unsafe_allow_html=True)
        regs = []
        for e in items[:5]:
            regs += [dict(r, periode=e["name"]) for r in vs.list_registrations(addr, e["id"])[:5]]
        regs.sort(key=lambda r: r["submitted_at"], reverse=True)
        if regs:
            st.dataframe(pd.DataFrame([{"Waktu": r["submitted_at"], "Periode": r["periode"], "Custom ID": r["custom_id"],
                                        "Status": vs.REG_LABEL[r["status"]]} for r in regs[:8]]), hide_index=True, width="stretch")
        else:
            empty_state("Belum ada permohonan", "Permohonan registrasi pemilih akan tampil di sini.", "clipboard-list")
    with right:
        st.markdown('<p class="ev-card-title" style="margin-top:14px">Aktivitas blockchain terbaru</p>', unsafe_allow_html=True)
        rows = txs.recent(8, viewer=addr, is_admin=True)
        if rows:
            st.dataframe(pd.DataFrame([{"Jenis": r["jenis"], "Blok": r["block"], "Waktu": r["waktu"], "Wallet": r["wallet_display"]} for r in rows]),
                         hide_index=True, width="stretch")
        else:
            empty_state("Belum ada aktivitas", "Transaksi akan tampil setelah ada aktivitas on-chain.", "history")
