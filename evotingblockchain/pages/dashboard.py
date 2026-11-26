import streamlit as st

from components import charts, wallet as wl
from components.header import page_header
from components.metric_card import metric_row
from components.notifications import empty_state
from components.selectors import election_picker
from components.status_badge import status_badge
from services import blockchain as bc
from services import election_service as es
from services import transactions as txs


def recent_table(rows):
    import pandas as pd
    df = pd.DataFrame([{"Jenis": r["jenis"], "Periode": r["election_id"] or "-", "Blok": r["block"],
                        "Waktu": r["waktu"], "Wallet": r["wallet_display"], "Hash": r["tx_hash"][:14] + "..."} for r in rows])
    st.dataframe(df, hide_index=True, width="stretch")


def render():
    page_header("Dashboard", "Ringkasan pemilihan dan aktivitas blockchain secara langsung.", "layout-dashboard")
    e = election_picker()
    s = bc.status()
    if not e:
        metric_row([
            {"label": "Total Pemilih Terdaftar", "value": 0, "icon": "users"},
            {"label": "Total Kandidat", "value": 0, "icon": "user-check"},
            {"label": "Total Suara Masuk", "value": 0, "icon": "vote"},
            {"label": "Tinggi Blok", "value": f"#{s['block_number']}", "icon": "box"}])
        return
    part = round(e["total_votes"] * 100 / e["approved_voters"], 1) if e["approved_voters"] else 0.0
    tone = {"Sedang Berlangsung": "success", "Dibatalkan": "danger", "Draft": "warning"}.get(e["status"], "")
    metric_row([
        {"label": "Total Pemilih Terdaftar", "value": e["approved_voters"], "icon": "users", "hint": "Terverifikasi pada periode ini"},
        {"label": "Total Kandidat", "value": e["candidates"], "icon": "user-check", "hint": "Kandidat aktif"},
        {"label": "Total Suara Masuk", "value": e["total_votes"], "icon": "vote", "hint": "Transaksi terkonfirmasi"},
        {"label": "Partisipasi", "value": f"{part}%", "icon": "chart-column", "hint": "Suara masuk / pemilih terverifikasi"},
    ])
    metric_row([
        {"label": "Status Pemilihan", "value": e["status"], "icon": "info", "tone": tone, "small": True},
        {"label": "Periode Pemilihan", "value": e["name"], "icon": "calendar-range", "small": True, "hint": f"Periode #{e['id']}"},
        {"label": "Waktu Mulai", "value": es.fmt_time(e["start"]), "icon": "clock", "small": True},
        {"label": "Waktu Berakhir", "value": es.fmt_time(e["end"]), "icon": "clock", "small": True},
    ])
    metric_row([
        {"label": "Tinggi Blok Blockchain", "value": f"#{s['block_number']}", "icon": "box"},
        {"label": "Status Koneksi Blockchain", "value": "Terhubung" if s["contract_ok"] else "Terputus", "icon": "network",
         "tone": "success" if s["contract_ok"] else "danger", "small": True, "hint": f"Chain ID {s['chain_id']}"},
    ], per_row=4)
    series = txs.participation_series(e["id"])
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown('<p class="ev-card-title">Partisipasi pemilih (kumulatif)</p>', unsafe_allow_html=True)
            if series:
                st.plotly_chart(charts.participation_line(series), width="stretch", config=charts.CONFIG)
            else:
                empty_state("Belum ada suara masuk", "Grafik akan muncul setelah pemilih mengirim suara.", "chart-column")
    with c2:
        with st.container(border=True):
            st.markdown('<p class="ev-card-title">Aktivitas pemilihan per jam</p>', unsafe_allow_html=True)
            if series:
                st.plotly_chart(charts.activity_bar(series), width="stretch", config=charts.CONFIG)
            else:
                empty_state("Belum ada aktivitas", "Aktivitas suara per jam akan tampil di sini.", "history")
    w = wl.current()
    st.markdown('<p class="ev-card-title" style="margin-top:12px">Aktivitas transaksi terbaru</p>', unsafe_allow_html=True)
    rows = txs.recent(8, viewer=w["address"])
    if rows:
        recent_table(rows)
    else:
        empty_state("Belum ada transaksi", "Aktivitas on-chain akan tampil setelah ada transaksi.", "history")
