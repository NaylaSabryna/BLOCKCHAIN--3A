import streamlit as st


def tab_select(labels: list[str], key: str) -> str:
    """Pengganti st.tabs yang statusnya disimpan di server (tidak reset saat tata letak halaman berubah)
    dan hanya merender isi tab yang dipilih."""
    if st.session_state.get(key) not in labels:
        st.session_state[key] = labels[0]
    chosen = st.segmented_control("Bagian", labels, key=key, label_visibility="collapsed", default=labels[0])
    return chosen or labels[0]
