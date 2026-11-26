import pandas as pd
import streamlit as st

from components import tx_flow
from components.admin_gate import require_admin
from components.notifications import alert, empty_state
from components.selectors import election_picker
from pages.results import results_body
from services import audit_service as audit
from services import election_service as es
from services.errors import EvoteError


def render():
    addr = require_admin("Rekapitulasi Suara", "Rekap perolehan suara dan pembuatan checkpoint audit.", "clipboard-list")
    e = election_picker()
    if not e:
        return
    df = results_body(e["id"], admin=True)
    if df is not None and len(df):
        st.download_button("Ekspor rekap (CSV)", df.to_csv(index=False), f"rekap_periode_{e['id']}.csv", "text/csv")
    st.markdown('<p class="ev-card-title" style="margin-top:18px">Checkpoint audit periode ini</p>', unsafe_allow_html=True)
    blocks = [b for b in audit.list_blocks() if b["electionId"] == e["id"]]
    if blocks:
        st.dataframe(pd.DataFrame([{"Blok": b["index"], "Batch ID": b["batchId"], "Waktu": es.fmt_time(b["timestamp"]),
                                    "Total Suara": b["totalVotes"], "Status": b["status_label"]} for b in blocks]), hide_index=True, width="stretch")
    else:
        empty_state("Belum ada checkpoint", "Buat checkpoint untuk mengunci snapshot perolehan suara pada rantai hash.", "shield-check")
    if e["state"] in (es.STATE_PUBLISHED, es.STATE_FINALIZED):
        c1, c2 = st.columns([1, 2])
        bid = c1.text_input("Batch ID", value=f"BATCH-{e['id']}-{len(blocks) + 1}", key=f"bid_{e['id']}")
        note = c2.text_input("Catatan", max_chars=200, key=f"bnote_{e['id']}")
        if st.button("Buat checkpoint audit", type="primary", key=f"mk_{e['id']}"):
            try:
                tx_flow.start(audit.prepare_create(addr, e["id"], bid, note))
            except EvoteError as exc:
                alert("danger", str(exc))
    else:
        st.caption("Checkpoint dapat dibuat setelah periode dipublikasikan.")
