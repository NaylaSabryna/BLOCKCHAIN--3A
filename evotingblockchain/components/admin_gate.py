import streamlit as st

from components import wallet as wl
from components.header import page_header
from components.icons import svg
from components.notifications import alert
from services import auth_service as auth


def require_admin(title: str, subtitle: str, icon: str) -> str:
    """Mengembalikan alamat panitia terautentikasi, atau menampilkan gerbang akses lalu menghentikan halaman.
    Autentikasi = wallet terhubung + tanda tangan personal_sign + role PANITIA di smart contract."""
    err = wl.poll_admin_login()
    addr = wl.admin_address()
    if addr:
        page_header(title, subtitle, icon)
        return addr
    page_header("Akses Panitia", "Area ini hanya untuk wallet Panitia yang terotorisasi di smart contract.", "lock")
    if err:
        alert("danger", err, "Autentikasi gagal")
    w = wl.current()
    with st.container(border=True):
        st.markdown(f'<p class="ev-card-title">{svg("key-round", 18)} Autentikasi Panitia</p>', unsafe_allow_html=True)
        if not w["has_provider"]:
            alert("warning", "MetaMask tidak terdeteksi di browser ini. Pasang ekstensi MetaMask lalu muat ulang halaman.")
        elif not w["connected"]:
            alert("info", "Hubungkan wallet Panitia melalui tombol 'Hubungkan Wallet' pada panel samping.")
        elif not w["chain_ok"]:
            alert("warning", f"MetaMask berada pada jaringan yang salah. Gunakan Chain ID {w['expected_chain']}.")
            if st.button("Pindah ke jaringan EVOTE", key="gate_switch"):
                wl.request_switch_network()
                st.rerun()
        elif not auth.is_panitia(w["address"]):
            alert("danger", f"Wallet {w['address'][:6]}...{w['address'][-4:]} tidak memiliki role Panitia di smart contract. "
                  "Pindah ke akun Panitia di MetaMask.", "Akses ditolak")
        else:
            st.write("Wallet Panitia terdeteksi. Tanda tangani pesan untuk membuktikan kepemilikan wallet. "
                     "Tindakan ini gratis dan tidak mengirim transaksi.")
            ch = st.session_state.get("admin_challenge")
            if ch:
                alert("info", "Menunggu tanda tangan di MetaMask...")
                if st.button("Batalkan", key="gate_cancel"):
                    st.session_state.pop("admin_challenge", None)
                    st.session_state.pop("wallet_request", None)
                    st.rerun()
            elif st.button("Tanda tangani untuk masuk", type="primary", key="gate_sign"):
                ch = auth.admin_challenge(w["address"])
                ch["request_id"] = wl.request_sign(ch["message"], w["address"])
                st.session_state["admin_challenge"] = ch
                st.rerun()
    st.stop()
