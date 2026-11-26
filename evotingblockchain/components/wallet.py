"""Jembatan MetaMask. Komponen JavaScript menjalankan connect, personal_sign, eth_sendTransaction, dan
pindah jaringan DI BROWSER; Python hanya menerima alamat, tanda tangan, dan hash transaksi.
Kunci privat tidak pernah menyentuh Python."""
import time
import uuid

import streamlit as st
import streamlit.components.v2 as components

import config
from services import auth_service as auth
from services import blockchain as bc
from services.errors import PermissionDenied, ValidationError

HTML = """
<div class="w">
  <button id="evote-connect" type="button"><span id="evote-label">Hubungkan Wallet</span></button>
  <div id="evote-info" class="info"></div>
</div>
"""

CSS = """
.w { font-family: Inter, system-ui, sans-serif; }
button { width:100%; padding:0.55rem 0.8rem; border-radius:8px; border:1px solid #2563EB; background:#2563EB;
  color:#fff; font-weight:600; font-size:0.85rem; cursor:pointer; }
button:hover { filter:brightness(1.08); }
button.on { background:transparent; border-color:rgba(255,255,255,0.25); color:#E2E8F0; cursor:default; }
.info { margin-top:8px; font-size:0.74rem; color:#94A3B8; overflow-wrap:anywhere; line-height:1.4; }
.info b { color:#E2E8F0; font-weight:600; }
"""

JS = r"""
const handled = (globalThis.__evoteHandled = globalThis.__evoteHandled || new Set());
// Penanda permintaan yang sudah dieksekusi juga disimpan di sessionStorage agar muat ulang halaman
// (atau sambungan Streamlit yang terputus lalu tersambung lagi) tidak mengirim ulang transaksi yang sama.
const seen = (id) => { try { return sessionStorage.getItem("evote_req_" + id) === "1"; } catch (e) { return false; } };
const mark = (id) => { handled.add(id); try { sessionStorage.setItem("evote_req_" + id, "1"); } catch (e) { /* abaikan */ } };

export default function (component) {
  const { parentElement, setStateValue, data } = component;
  const btn = parentElement.querySelector("#evote-connect");
  const label = parentElement.querySelector("#evote-label");
  const info = parentElement.querySelector("#evote-info");
  const eth = window.ethereum;
  let alive = true;

  const short = (a) => a.slice(0, 6) + "..." + a.slice(-4);
  const hex = (s) => "0x" + Array.from(new TextEncoder().encode(s)).map((b) => b.toString(16).padStart(2, "0")).join("");

  async function snapshot() {
    if (!eth) return { address: "", chainId: "", connected: false, hasProvider: false };
    const accounts = await eth.request({ method: "eth_accounts" });
    const chainId = await eth.request({ method: "eth_chainId" });
    return { address: accounts && accounts[0] ? accounts[0] : "", chainId, connected: !!(accounts && accounts[0]), hasProvider: true };
  }

  function paint(w) {
    if (!w.hasProvider) { label.textContent = "MetaMask tidak ditemukan"; btn.className = ""; info.textContent = "Pasang ekstensi MetaMask lalu muat ulang halaman."; return; }
    if (w.connected) {
      label.textContent = "Wallet Terhubung"; btn.className = "on";
      info.innerHTML = "<b>" + short(w.address) + "</b><br>Chain ID " + parseInt(w.chainId, 16);
    } else {
      label.textContent = "Hubungkan Wallet"; btn.className = ""; info.textContent = "Belum terhubung.";
    }
  }

  async function publish() {
    try { const w = await snapshot(); if (!alive) return; paint(w); setStateValue("wallet", w); }
    catch (e) { /* abaikan */ }
  }

  async function connect() {
    if (!eth) { paint({ hasProvider: false }); return; }
    try { await eth.request({ method: "eth_requestAccounts" }); } catch (e) { info.textContent = "Koneksi dibatalkan oleh pengguna."; }
    await publish();
  }

  async function execute(req) {
    const out = { id: req.id, type: req.type, ok: false };
    try {
      if (!eth) throw { message: "MetaMask tidak ditemukan." };
      if (req.type === "switch") {
        try { await eth.request({ method: "wallet_switchEthereumChain", params: [{ chainId: req.chain.chainId }] }); }
        catch (e) {
          if (e && e.code === 4902) await eth.request({ method: "wallet_addEthereumChain", params: [req.chain] });
          else throw e;
        }
        out.ok = true;
      } else {
        const accounts = await eth.request({ method: "eth_accounts" });
        const current = accounts && accounts[0] ? accounts[0].toLowerCase() : "";
        const expected = (req.address || (req.tx && req.tx.from) || "").toLowerCase();
        if (!current) throw { message: "Wallet belum terhubung." };
        if (expected && current !== expected) throw { message: "Akun MetaMask aktif berbeda dari akun yang diperlukan (" + short(expected) + ")." };
        if (req.type === "sign") {
          out.signature = await eth.request({ method: "personal_sign", params: [hex(req.message), current] });
          out.ok = true;
        } else if (req.type === "tx") {
          const tx = { ...req.tx };

          // Jangan menggunakan nonce lama dari aplikasi.
          // MetaMask akan mengelola nonce berdasarkan jaringan aktif.
          delete tx.nonce;

          // Pastikan akun pengirim sesuai dengan akun MetaMask.
          tx.from = current;

          out.txHash = await eth.request({
            method: "eth_sendTransaction",
            params: [tx]
          });

          out.ok = true;
        } else {
          throw { message: "Jenis permintaan tidak dikenal." };
        }
      }
    } catch (e) {
      out.rejected = !!(e && (e.code === 4001 || e.code === "ACTION_REJECTED"));
      out.error = (e && (e.message || e.reason)) ? String(e.message || e.reason).slice(0, 300) : "Permintaan gagal.";
    }
    setStateValue("response", out);
    publish();
  }

  btn.addEventListener("click", connect);
  const onAcc = () => publish();
  const onChain = () => publish();
  if (eth && eth.on) { eth.on("accountsChanged", onAcc); eth.on("chainChanged", onChain); }
  publish();

  const req = data && data.request;
  if (req && req.id && !handled.has(req.id) && !seen(req.id)) { mark(req.id); execute(req); }

  return () => {
    alive = false;
    btn.removeEventListener("click", connect);
    if (eth && eth.removeListener) { eth.removeListener("accountsChanged", onAcc); eth.removeListener("chainChanged", onChain); }
  };
}
"""

_wallet_component = components.component("evote_metamask", html=HTML, css=CSS, js=JS)

EMPTY = {"address": "", "chainId": "", "connected": False, "hasProvider": False}


def mount():
    """Pasang komponen sekali per eksekusi skrip (di sidebar). Menyimpan keadaan wallet ke session_state."""
    req = st.session_state.get("wallet_request")
    res = _wallet_component(
        key="evote_wallet_cmp", data={"request": req},
        default={"wallet": EMPTY, "response": None},
        on_wallet_change=lambda: None, on_response_change=lambda: None,
    )
    incoming = res.wallet or EMPTY
    # Saat berpindah halaman komponen dipasang ulang dan sesaat melaporkan nilai default; abaikan nilai
    # default tersebut dan hanya terima laporan nyata dari browser (hasProvider = true).
    if incoming.get("hasProvider") or not st.session_state.get("wallet"):
        st.session_state["wallet"] = incoming
    resp = res.response
    if resp and req and resp.get("id") == req.get("id"):
        st.session_state["wallet_response"] = resp
        if req["type"] == "switch":
            st.session_state.pop("wallet_request", None)


def current() -> dict:
    w = st.session_state.get("wallet") or EMPTY
    try:
        chain_id = int(w["chainId"], 16) if w.get("chainId") else None
    except (TypeError, ValueError):
        chain_id = None
    addr = None
    if w.get("connected") and w.get("address"):
        try:
            addr = auth.normalize_wallet(w["address"])
        except ValidationError:
            addr = None
    try:
        expected = bc.expected_chain_id()
    except Exception:
        expected = None
    return {"address": addr, "chain_id": chain_id, "connected": bool(addr), "has_provider": bool(w.get("hasProvider")),
            "chain_ok": bool(addr) and chain_id == expected, "expected_chain": expected}


def _new_request(kind: str, **fields) -> str:
    rid = uuid.uuid4().hex
    st.session_state["wallet_request"] = {"id": rid, "type": kind, **fields}
    st.session_state.pop("wallet_response", None)
    return rid


def request_sign(message: str, address: str) -> str:
    return _new_request("sign", message=message, address=address)


def request_tx(tx: dict) -> str:
    return _new_request("tx", tx=tx, address=tx["from"])


def request_switch_network() -> str:
    cid = bc.expected_chain_id()
    return _new_request("switch", chain={
        "chainId": hex(cid), "chainName": config.CHAIN_NAME, "rpcUrls": [config.RPC_URL],
        "nativeCurrency": {"name": "Ether", "symbol": config.CURRENCY_SYMBOL, "decimals": 18}})


def take_response(request_id: str):
    """Ambil (sekali) respons untuk permintaan tertentu, atau None bila belum ada."""
    resp = st.session_state.get("wallet_response")
    if resp and resp.get("id") == request_id:
        st.session_state.pop("wallet_response", None)
        st.session_state.pop("wallet_request", None)
        return resp
    return None


# ------------------------------------------------------------- sesi panitia
def admin_address() -> str | None:
    """Alamat panitia yang telah membuktikan kepemilikan wallet (personal_sign) DAN memiliki role di kontrak."""
    s = st.session_state.get("admin_session")
    if not s:
        return None
    w = current()
    if time.time() > s["until"] or not w["connected"] or w["address"].lower() != s["address"].lower():
        st.session_state.pop("admin_session", None)
        return None
    return s["address"]


def admin_logout():
    st.session_state.pop("admin_session", None)
    st.session_state.pop("admin_challenge", None)


def poll_admin_login() -> str | None:
    """Memproses respons tanda tangan login panitia. Mengembalikan pesan kesalahan bila ada."""
    ch = st.session_state.get("admin_challenge")
    if not ch:
        return None
    resp = take_response(ch["request_id"])
    if not resp:
        return None
    st.session_state.pop("admin_challenge", None)
    if not resp["ok"]:
        return "Penandatanganan dibatalkan pengguna." if resp.get("rejected") else (resp.get("error") or "Gagal menandatangani.")
    try:
        addr = auth.verify_admin_login(ch, resp["signature"])
    except (PermissionDenied, ValidationError) as exc:
        return str(exc)
    st.session_state["admin_session"] = {"address": addr, "until": time.time() + config.ADMIN_SESSION_SECONDS}
    return None
