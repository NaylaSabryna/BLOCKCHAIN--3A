"""Smoke test render seluruh halaman memakai AppTest (tanpa browser/MetaMask).
Wallet dan sesi Panitia disimulasikan lewat session_state; eksekusi transaksi diuji di test_services.py."""
import importlib
import os
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PAGES = {
    "dashboard": ("dashboard", "render"), "candidates": ("candidates", "render"), "voting": ("voting", "render"),
    "results": ("results", "render"), "verification": ("verification", "render"),
    "transactions": ("transaction_history", "render"), "profile": ("profile", "render"),
    "admin_dashboard": ("admin_dashboard", "render"), "admin_periode": ("admin_periode", "render"),
    "admin_kandidat": ("admin_kandidat", "render"), "admin_pemilih": ("admin_pemilih", "render"),
    "admin_pengaturan": ("admin_pengaturan", "render"), "admin_rekap": ("admin_rekap", "render"),
    "admin_audit": ("admin_audit", "render"), "admin_transaksi": ("transaction_history", "render_admin"),
    "admin_sistem": ("admin_sistem", "render"),
}

SCRIPT = '''
import sys, time
sys.path.insert(0, r"{root}")
import streamlit as st
import config
st.markdown(f"<style>{{config.CSS_PATH.read_text()}}</style>", unsafe_allow_html=True)
from database import db
db.init_db()
from components import tx_flow
from components.notifications import render_flash
st.session_state["wallet"] = {{"address": "{wallet}", "chainId": "0x7a69", "connected": True, "hasProvider": True}}
if {admin}:
    st.session_state["admin_session"] = {{"address": "{wallet}", "until": time.time() + 3600}}
import importlib
mod = importlib.import_module("pages.{module}")
render_flash(); tx_flow.render()
getattr(mod, "{fn}")()
'''


def run_page(pid, wallet, admin=True):
    module, fn = PAGES[pid]
    at = AppTest.from_string(SCRIPT.format(root=ROOT, wallet=wallet, admin=admin, module=module, fn=fn), default_timeout=90)
    at.run()
    return at


@pytest.fixture(scope="module")
def admin_wallet(deployed, w3):
    return w3.eth.accounts[0]


@pytest.mark.parametrize("pid", list(PAGES))
def test_halaman_kondisi_kosong(pid, admin_wallet):
    at = run_page(pid, admin_wallet)
    assert not at.exception, [e.value for e in at.exception]


def test_gerbang_admin_menolak_tanpa_sesi(admin_wallet):
    at = run_page("admin_dashboard", admin_wallet, admin=False)
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "Akses Panitia" in html and "Total Periode" not in html
    # wallet non-panitia: pesan akses ditolak
    from web3 import Web3
    at2 = run_page("admin_kandidat", Web3(Web3.HTTPProvider("http://127.0.0.1:8545")).eth.accounts[7], admin=False)
    assert "tidak memiliki role Panitia" in " ".join(m.value for m in at2.markdown)


@pytest.mark.parametrize("pid", list(PAGES))
def test_halaman_dengan_data(pid, admin_wallet, seeded):
    at = run_page(pid, admin_wallet)
    assert not at.exception, [e.value for e in at.exception]
    if pid in ("candidates", "voting"):
        assert "ev-cand" in " ".join(m.value for m in at.markdown)


def test_tidak_ada_emoji_di_antarmuka():
    import re
    emoji = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2705\u274C]")
    offenders = []
    for folder in ("pages", "components", "styles"):
        for p in (ROOT / folder).glob("*"):
            if p.suffix in (".py", ".css") and emoji.search(p.read_text(encoding="utf-8")):
                offenders.append(p.name)
    for p in [ROOT / "app.py"]:
        if emoji.search(p.read_text(encoding="utf-8")):
            offenders.append(p.name)
    assert not offenders, offenders
