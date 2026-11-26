import streamlit as st

from components import wallet as wl
from components.icons import nav_icon_css, svg
from services import blockchain as bc

VOTER_NAV = [
    ("dashboard", "Dashboard", "layout-dashboard"), ("candidates", "Daftar Kandidat", "users"),
    ("voting", "Pemungutan Suara", "vote"), ("results", "Hasil Pemilihan", "chart-column"),
    ("verification", "Verifikasi Pemilih", "user-check"), ("transactions", "Riwayat Transaksi", "history"),
    ("profile", "Profil / Wallet", "wallet"),
]
ADMIN_NAV = [
    ("admin_dashboard", "Dashboard Admin", "layout-dashboard"), ("admin_periode", "Manajemen Periode", "calendar-range"),
    ("admin_kandidat", "Manajemen Kandidat", "users"), ("admin_pemilih", "Manajemen Pemilih", "user-check"),
    ("admin_pengaturan", "Pengaturan Pemilihan", "settings-2"), ("admin_rekap", "Rekapitulasi Suara", "clipboard-list"),
    ("admin_audit", "Blockchain Audit", "shield-check"), ("admin_transaksi", "Riwayat Transaksi", "history"),
    ("admin_sistem", "Pengaturan Sistem", "landmark"),
]
MODES = ["Pemilih", "Panitia"]


def inject_icon_css():
    mapping = {f"nav_{k}": ico for k, _, ico in VOTER_NAV + ADMIN_NAV}
    st.markdown(f"<style>{nav_icon_css(mapping)}</style>", unsafe_allow_html=True)


def render(current_id: str, pages: dict, mode: str):
    with st.sidebar:
        st.markdown(f'<div class="ev-brand"><div class="ev-brand-mark">{svg("vote", 22)}</div><div>'
                    f'<div class="ev-brand-name">EVOTE</div><div class="ev-brand-sub">Decentralized Electronic<br>Voting System</div>'
                    f'</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="ev-side-label">AREA</div>', unsafe_allow_html=True)
        st.segmented_control("Area", MODES, key="mode", label_visibility="collapsed", default="Pemilih")
        st.markdown('<div class="ev-side-label">MENU</div>', unsafe_allow_html=True)
        for pid, label, _ in (ADMIN_NAV if mode == "Panitia" else VOTER_NAV):
            if st.button(label, key=f"nav_{pid}", type="primary" if pid == current_id else "secondary",
                         use_container_width=True):
                st.switch_page(pages[pid])
        st.markdown('<div class="ev-side-label">DOMPET DIGITAL</div>', unsafe_allow_html=True)
        wl.mount()
        w = wl.current()
        if w["connected"] and not w["chain_ok"]:
            st.markdown('<div class="ev-side-card"><span class="ev-dot bad"></span><b>Jaringan tidak sesuai</b><br>'
                        f'Gunakan Chain ID {w["expected_chain"]}.</div>', unsafe_allow_html=True)
            if st.button("Pindah jaringan", key="side_switch", use_container_width=True):
                wl.request_switch_network()
                st.rerun()
        if mode == "Panitia" and wl.admin_address():
            st.markdown('<div class="ev-side-card" style="margin-top:8px"><span class="ev-dot ok"></span><b>Sesi Panitia aktif</b></div>',
                        unsafe_allow_html=True)
            if st.button("Keluar dari sesi Panitia", key="side_logout", use_container_width=True):
                wl.admin_logout()
                st.rerun()
        s = bc.status()
        dot = "ok" if s["contract_ok"] else "bad"
        txt = "Terhubung" if s["contract_ok"] else "Terputus"
        st.markdown(f'<div class="ev-side-label">JARINGAN</div><div class="ev-side-card"><span class="ev-dot {dot}"></span>'
                    f'<b>{txt}</b><br>Blok #{s["block_number"]} | Chain {s["chain_id"] or "-"}</div>', unsafe_allow_html=True)
