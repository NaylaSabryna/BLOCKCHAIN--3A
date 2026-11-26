import pandas as pd
import streamlit as st

from components import charts
from components.header import page_header
from components.metric_card import metric_row
from components.notifications import alert, empty_state
from components.selectors import election_picker
from components.status_badge import status_badge
from services import election_service as es
from services import result_service as rs
import datetime as dt
import config


def results_body(election_id: int, admin: bool = False):
    r = rs.get_results(election_id)
    if not r:
        empty_state("Periode tidak ditemukan", "Pilih periode lain.", "calendar-range")
        return
    e = r["election"]
    if r["is_final"]:
        alert("success", "Periode telah difinalisasi. Angka di bawah adalah hasil final yang tercatat di blockchain.", "Hasil Final")
    elif e["state"] == es.STATE_CANCELLED:
        alert("danger", "Periode ini dibatalkan. Tidak ada hasil resmi.", "Dibatalkan")
    elif e["status"] == es.STATUS_DONE:
        alert("warning", "Pemungutan suara telah berakhir tetapi belum difinalisasi panitia. Angka masih berstatus sementara.", "Hasil Sementara")
    else:
        alert("warning", "Pemilihan belum final. Angka dapat berubah selama pemungutan suara berlangsung. "
                         "Hanya transaksi yang sudah terkonfirmasi yang dihitung.", "Hasil Sementara")
    leader = "-"
    if r["leaders"]:
        leader = " / ".join(f"No. {x['nomor']} {x['nama']}" for x in r["leaders"]) + (" (seri)" if r["tie"] else "")
    metric_row([
        {"label": "Total Suara Masuk", "value": r["total_votes"], "icon": "vote"},
        {"label": "Total Suara Sah", "value": r["valid_votes"], "icon": "circle-check", "tone": "success"},
        {"label": "Total Kandidat", "value": r["candidates"], "icon": "users"},
        {"label": "Partisipasi", "value": f"{r['participation']}%", "icon": "chart-column",
         "hint": f"{r['total_votes']} dari {r['registered']} pemilih terverifikasi"},
    ])
    metric_row([
        {"label": "Perolehan Tertinggi", "value": leader, "icon": "landmark", "small": True},
        {"label": "Status Periode", "value": e["status"], "icon": "info", "small": True},
        {"label": "Jenis Hasil", "value": r["label"], "icon": "shield-check", "small": True,
         "tone": "success" if r["is_final"] else "warning"},
        {"label": "Pembaruan Terakhir", "value": dt.datetime.fromtimestamp(r["updated_at"], config.TZ).strftime("%H:%M:%S") + " " + config.TZ_LABEL,
         "icon": "refresh-cw", "small": True, "hint": "Sinkron dengan blockchain"},
    ])
    if not r["rows"]:
        empty_state("Belum ada kandidat", "Hasil akan tampil setelah kandidat ditambahkan.", "users")
        return
    c1, c2 = st.columns([3, 2])
    with c1:
        with st.container(border=True):
            st.markdown('<p class="ev-card-title">Perolehan suara kandidat</p>', unsafe_allow_html=True)
            st.plotly_chart(charts.bar_votes(r["rows"]), width="stretch", config=charts.CONFIG, key=f"bar_{election_id}_{admin}")
    with c2:
        with st.container(border=True):
            st.markdown('<p class="ev-card-title">Persentase suara</p>', unsafe_allow_html=True)
            if r["total_votes"]:
                st.plotly_chart(charts.donut_votes(r["rows"]), width="stretch", config=charts.CONFIG, key=f"pie_{election_id}_{admin}")
            else:
                empty_state("Belum ada suara", "Diagram muncul setelah ada suara masuk.", "chart-column")
    with st.container(border=True):
        st.markdown('<p class="ev-card-title">Indikator partisipasi pemilih</p>', unsafe_allow_html=True)
        st.progress(min(r["participation"] / 100, 1.0), text=f"{r['participation']}% pemilih terverifikasi telah memilih")
    df = pd.DataFrame([{"No. Urut": x["nomor"], "Kandidat": x["nama"], "Suara": x["suara"], "Persentase": f"{x['persen']}%"} for x in r["rows"]])
    st.dataframe(df, hide_index=True, width="stretch")
    return df


def render():
    page_header("Hasil Pemilihan", "Perolehan suara dibaca langsung dari blockchain.", "chart-column")
    e = election_picker()
    if not e:
        return
    live = e["status"] == es.STATUS_RUNNING
    frag = st.fragment(run_every=5 if live else None)(lambda: results_body(e["id"]))
    frag()
    if live:
        st.caption("Pembaruan otomatis setiap 5 detik. Halaman tidak dimuat ulang seluruhnya.")
