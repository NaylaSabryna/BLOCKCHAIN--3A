"""Fixture pengujian layanan. Membutuhkan node Hardhat berjalan (npm run node).
Setiap sesi pengujian mendeploy kontrak BARU ke file deployment sementara, sehingga
deployment.json dan database proyek yang sedang dipakai tidak tersentuh."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_tmp = Path(tempfile.mkdtemp(prefix="evote_test_"))
os.environ["EVOTE_DB"] = str(_tmp / "test.db")
os.environ["EVOTE_UPLOADS"] = str(_tmp / "uploads")
os.environ["EVOTE_DEPLOYMENT"] = str(_tmp / "deployment.json")

# Kunci publik bawaan Hardhat (HANYA untuk pengujian lokal; aplikasi tidak memakai kunci privat apa pun).
HARDHAT_KEYS = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
    "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
]


@pytest.fixture(scope="session", autouse=True)
def deployed():
    cfg = os.environ.get("EVOTE_TEST_HARDHAT_CONFIG", "hardhat.config.js")
    env = {**os.environ, "DEPLOYMENT_FILE": os.environ["EVOTE_DEPLOYMENT"]}
    r = subprocess.run(["npx", "hardhat", "--config", cfg, "run", "scripts/deploy.js", "--network", "localhost"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        pytest.exit("Deploy gagal. Pastikan 'npm run node' berjalan.\n" + r.stdout + r.stderr)
    from database import db
    db.init_db()
    yield


@pytest.fixture(scope="session")
def w3(deployed):
    from services import blockchain as bc
    return bc.get_w3()


@pytest.fixture(scope="session")
def accounts(w3):
    return {"admin": w3.eth.accounts[0], "v1": w3.eth.accounts[1], "v2": w3.eth.accounts[2],
            "v3": w3.eth.accounts[3], "outsider": w3.eth.accounts[4]}


def sign_message(account_key_index: int, message: str) -> str:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    sig = Account.sign_message(encode_defunct(text=message), HARDHAT_KEYS[account_key_index]).signature.hex()
    return sig if sig.startswith("0x") else "0x" + sig


@pytest.fixture()
def send(w3):
    """Meniru MetaMask: kirim permintaan eth_sendTransaction dari akun, tunggu receipt, jalankan hook."""
    from services import blockchain as bc
    from services.flow import run_after

    def _send(plan, actor=None, run_hook=True):
        txh = w3.eth.send_transaction(plan["request"])
        receipt = bc.wait_receipt(txh.hex())
        assert receipt is not None and receipt["status"] == 1
        if run_hook:
            run_after(plan["after"], plan["payload"], receipt, actor or plan["request"]["from"])
        return receipt
    return _send


@pytest.fixture()
def advance(w3):
    def _adv(seconds):
        w3.provider.make_request("evm_increaseTime", [int(seconds)])
        w3.provider.make_request("evm_mine", [])
        from services.cache import clear_all
        clear_all()
    return _adv


@pytest.fixture(scope="module")
def seeded(deployed, w3):
    """Data uji untuk smoke test halaman (hanya di DB/kontrak sementara, bukan bagian aplikasi)."""
    import io
    from PIL import Image
    from services import blockchain as bc
    from services import candidate_service as cs
    from services import election_service as es
    from services import voter_service as vs
    from services import audit_service as audit
    from services.cache import clear_all
    from services.flow import run_after

    def send(plan):
        txh = w3.eth.send_transaction(plan["request"])
        rc = bc.wait_receipt(txh.hex())
        assert rc["status"] == 1
        run_after(plan["after"], plan["payload"], rc, plan["request"]["from"])

    admin = w3.eth.accounts[0]
    now = bc.chain_now()
    send(es.prepare_create(admin, "Periode Uji Antarmuka", "Data uji", now + 300, now + 3000))
    clear_all()
    eid = es.list_elections()[0]["id"]
    buf = io.BytesIO(); Image.new("RGB", (200, 160), (30, 90, 170)).save(buf, "PNG")
    for n, nama in ((1, "Calon Uji A"), (2, "Calon Uji B")):
        send(cs.prepare_add(admin, eid, {"nomor_urut": n, "nama": nama, "deskripsi": "d", "visi": "v", "misi": "m"},
                            (buf.getvalue(), "f.png") if n == 1 else None))
    send(es.prepare_publish(admin, eid))
    csv = b"custom_id,nama\nUJI001,Pemilih Uji\n"
    res = vs.import_roster(admin, eid, csv)
    code = res["imported"][0]["kode_registrasi"]
    w1 = w3.eth.accounts[1]
    vs.submit_registration(eid, "UJI001", code, w1, sign_message(1, vs.registration_message(eid, w1, "UJI001")))
    clear_all()
    yield eid
