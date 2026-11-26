"""Koneksi Web3 dan utilitas kontrak. Tidak pernah menyimpan atau memakai private key:
transaksi hanya DISIAPKAN di sini dan ditandatangani oleh MetaMask di browser pengguna."""
import json
import re
import threading
import time

from web3 import Web3
from web3.logs import DISCARD

import config
from services.errors import ChainError

_lock = threading.Lock()
_state = {"mtime": None, "w3": None, "contract": None, "deployment": None, "errors": {}}
_block_ts: dict[int, int] = {}

ERROR_MESSAGES = {
    "ElectionNotFound": "Periode pemilihan tidak ditemukan.",
    "CandidateNotFound": "Kandidat tidak ditemukan atau sudah tidak aktif.",
    "InvalidTimeRange": "Waktu berakhir harus setelah waktu mulai.",
    "StartMustBeInFuture": "Waktu mulai harus berada di masa depan.",
    "ElectionAlreadyStarted": "Periode sudah dimulai sehingga data tidak dapat diubah.",
    "InvalidState": "Status periode tidak mengizinkan tindakan ini.",
    "NeedTwoCandidates": "Periode harus memiliki minimal dua kandidat aktif.",
    "DuplicateNomorUrut": "Nomor urut kandidat sudah dipakai pada periode ini.",
    "EmptyName": "Nama tidak boleh kosong.",
    "InvalidAddress": "Alamat wallet tidak valid.",
    "VoterNotEligible": "Wallet ini belum terverifikasi sebagai pemilih pada periode ini.",
    "AlreadyVoted": "Hak suara pada periode ini sudah digunakan.",
    "VotingNotOpen": "Pemungutan suara tidak sedang dibuka.",
    "CredentialAlreadyUsed": "Identitas pemilih ini sudah dipakai oleh wallet lain pada periode yang sama.",
    "AlreadyApproved": "Wallet ini sudah disetujui pada periode ini.",
    "ElectionNotEnded": "Periode belum berakhir.",
    "ElectionNotFinalized": "Periode harus difinalisasi terlebih dahulu.",
    "BatchIdExists": "Batch ID sudah digunakan atau memakai awalan yang dicadangkan (FINAL-).",
    "BatchNotFound": "Batch tidak ditemukan.",
    "EmptyBatchId": "Batch ID tidak boleh kosong.",
    "InvalidTransition": "Urutan status batch tidak valid.",
    "NoCheckpoints": "Belum ada checkpoint audit.",
    "AccessControlUnauthorizedAccount": "Wallet ini tidak memiliki hak Panitia pada smart contract.",
}

ELECTION_FIELDS = ["id", "name", "startTime", "endTime", "metadataHash", "state", "candidateCount",
                   "activeCandidates", "totalVotes", "approvedVoters", "createdAt"]
CANDIDATE_FIELDS = ["id", "nomorUrut", "name", "metadataHash", "active"]
BLOCK_FIELDS = ["index", "timestamp", "electionId", "batchId", "catatan", "totalVotes", "snapshotHash",
                "previousHash", "blockHash", "actor", "status"]


def _load():
    with _lock:
        if not config.DEPLOYMENT_PATH.exists() or not config.ARTIFACT_PATH.exists():
            raise ChainError("File deployment.json atau artifact kontrak tidak ditemukan. "
                             "Jalankan 'npm run compile' dan 'npm run deploy' terlebih dahulu.")
        mtime = (config.DEPLOYMENT_PATH.stat().st_mtime, config.ARTIFACT_PATH.stat().st_mtime)
        if _state["mtime"] == mtime and _state["w3"] is not None:
            return
        deployment = json.loads(config.DEPLOYMENT_PATH.read_text())
        abi = json.loads(config.ARTIFACT_PATH.read_text())["abi"]
        w3 = Web3(Web3.HTTPProvider(config.RPC_URL, request_kwargs={"timeout": 10}))
        contract = w3.eth.contract(address=Web3.to_checksum_address(deployment["address"]), abi=abi)
        errors = {}
        for item in abi:
            if item.get("type") == "error":
                sig = f"{item['name']}({','.join(i['type'] for i in item.get('inputs', []))})"
                errors[Web3.keccak(text=sig)[:4].hex().removeprefix("0x")] = item["name"]
        _state.update(mtime=mtime, w3=w3, contract=contract, deployment=deployment, errors=errors)
        _block_ts.clear()


def get_w3() -> Web3:
    _load()
    return _state["w3"]


def get_contract():
    _load()
    return _state["contract"]


def deployment() -> dict:
    _load()
    return _state["deployment"]


def contract_address() -> str:
    return deployment()["address"]


def expected_chain_id() -> int:
    return int(deployment()["chainId"])


def status() -> dict:
    """Ringkasan koneksi untuk header dan dashboard. Tidak pernah melempar exception."""
    info = {"connected": False, "contract_ok": False, "chain_id": None, "block_number": 0,
            "address": None, "error": None, "rpc": config.RPC_URL}
    try:
        w3 = get_w3()
        if not w3.is_connected():
            info["error"] = "Node blockchain tidak dapat dihubungi. Jalankan 'npm run node'."
            return info
        info.update(connected=True, chain_id=w3.eth.chain_id, block_number=w3.eth.block_number,
                    address=contract_address())
        if w3.eth.get_code(Web3.to_checksum_address(contract_address())) in (b"", b"\x00"):
            info["error"] = "Tidak ada kontrak pada alamat deployment. Jalankan ulang 'npm run deploy'."
        elif info["chain_id"] != expected_chain_id():
            info["error"] = "Chain ID node berbeda dengan deployment.json."
        else:
            info["contract_ok"] = True
    except ChainError as exc:
        info["error"] = str(exc)
    except Exception as exc:  # koneksi gagal
        info["error"] = f"Koneksi blockchain gagal: {exc}"
    return info


def chain_now() -> int:
    w3 = get_w3()
    return int(max(time.time(), w3.eth.get_block("latest")["timestamp"]))


def block_timestamp(number: int) -> int:
    if number not in _block_ts:
        _block_ts[number] = int(get_w3().eth.get_block(number)["timestamp"])
    return _block_ts[number]


def _as_dict(fields, values):
    out = dict(zip(fields, values))
    for k, v in out.items():
        if isinstance(v, (bytes, bytearray)):
            out[k] = "0x" + bytes(v).hex()
    return out


def read_election(election_id: int) -> dict:
    return _as_dict(ELECTION_FIELDS, get_contract().functions.getElection(election_id).call())


def read_candidate(election_id: int, cid: int) -> dict:
    return _as_dict(CANDIDATE_FIELDS, get_contract().functions.getCandidate(election_id, cid).call())


def read_block(index: int) -> dict:
    return _as_dict(BLOCK_FIELDS, get_contract().functions.getBlock(index).call())


def decode_revert(exc: Exception) -> str:
    _load()
    data = getattr(exc, "data", None)
    if isinstance(data, dict):
        data = data.get("data")
    text = str(exc)
    if isinstance(data, str) and data.startswith("0x") and len(data) >= 10:
        name = _state["errors"].get(data[2:10])
        if name:
            return ERROR_MESSAGES.get(name, name)
    m = re.search(r"custom error '([A-Za-z0-9_]+)", text)
    if m:
        return ERROR_MESSAGES.get(m.group(1), m.group(1))
    return "Transaksi ditolak oleh smart contract: " + text[:160]


def prepare_tx(fn, sender: str) -> dict:
    """Simulasikan pemanggilan (mendeteksi revert lebih dulu) lalu siapkan permintaan eth_sendTransaction
    untuk ditandatangani MetaMask. Tidak ada kunci privat yang terlibat."""
    sender = Web3.to_checksum_address(sender)
    try:
        gas = fn.estimate_gas({"from": sender})
        data = fn.build_transaction({"from": sender, "gas": gas})["data"]
    except Exception as exc:
        raise ChainError(decode_revert(exc)) from exc
    return {"from": sender, "to": contract_address(), "data": data, "gas": hex(int(gas * 1.3) + 20000)}


def wait_receipt(tx_hash: str, timeout: int = 60):
    """Tunggu receipt. Mengembalikan receipt atau None bila waktu habis."""
    w3 = get_w3()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = w3.eth.get_transaction_receipt(tx_hash)
            if r is not None:
                return r
        except Exception:
            pass
        time.sleep(0.5)
    return None


def get_events(name: str, from_block=None):
    ev = getattr(get_contract().events, name)
    start = deployment().get("deployBlock", 0) if from_block is None else from_block
    return ev.get_logs(from_block=start)


def process_receipt_event(name: str, receipt):
    return getattr(get_contract().events, name)().process_receipt(receipt, errors=DISCARD)


def explorer_link(tx_hash: str):
    return f"{config.BLOCK_EXPLORER_URL.rstrip('/')}/tx/{tx_hash}" if config.BLOCK_EXPLORER_URL else None
