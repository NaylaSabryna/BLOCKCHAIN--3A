import streamlit as st


def goto(page_id: str):
    page = st.session_state.get("_pages", {}).get(page_id)
    if page is not None:
        st.switch_page(page)
