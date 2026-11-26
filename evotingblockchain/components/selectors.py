import streamlit as st

from components.notifications import empty_state
from services import election_service as es


def election_picker(key: str = "sel_election", label: str = "Periode pemilihan", only=None):
    """Pilihan periode yang konsisten antarhalaman. Mengembalikan dict periode atau None."""
    items = es.list_elections()
    if only:
        items = [e for e in items if only(e)]
    if not items:
        empty_state("Belum ada periode pemilihan", "Panitia perlu membuat periode pemilihan terlebih dahulu.", "calendar-range")
        return None
    ids = [e["id"] for e in items]
    if st.session_state.get(key) not in ids:
        st.session_state[key] = (es.default_election(items) or items[0])["id"]
    by_id = {e["id"]: e for e in items}
    chosen = st.selectbox(label, ids, key=key,
                          format_func=lambda i: f"{by_id[i]['name']}  (Periode #{i}, {by_id[i]['status']})")
    return by_id[chosen]
