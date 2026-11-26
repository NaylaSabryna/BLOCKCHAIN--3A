import re

from services import auth_service as auth
from services import blockchain as bc
from services.cache import clear_all
from services.errors import ValidationError
from services.flow import after, make_plan
from database import db

STATUS_NAMES = ["CREATED", "VERIFIED_LOCAL", "IN_RECAP", "FINAL_COUNT", "FINISHED"]
STATUS_LABEL = {"CREATED": "Dibuat", "VERIFIED_LOCAL": "Terverifikasi Lokal", "IN_RECAP": "Dalam Rekapitulasi",
                "FINAL_COUNT": "Penghitungan Akhir", "FINISHED": "Selesai"}
BATCH_RE = re.compile(r"^[A-Za-z0-9._\-]{3,64}$")


def list_blocks() -> list[dict]:
    n = bc.get_contract().functions.getBlockchainLength().call()
    blocks = []
    for i in range(1, n + 1):
        b = bc.read_block(i)
        b["status_name"] = STATUS_NAMES[b["status"]]
        b["status_label"] = STATUS_LABEL[b["status_name"]]
        blocks.append(b)
    return blocks


def chain_integrity() -> dict:
    valid, first = bc.get_contract().functions.cekIntegritasRantai().call()
    return {"valid": bool(valid), "first_invalid": int(first)}


def search_batch(batch_id: str) -> dict | None:
    batch_id = (batch_id or "").strip()
    if not batch_id:
        return None
    c = bc.get_contract()
    idx = c.functions.getBlockIndexByBatchId(batch_id).call()
    if idx == 0:
        return None
    b = bc.read_block(idx)
    b["status_name"] = STATUS_NAMES[b["status"]]
    b["status_label"] = STATUS_LABEL[b["status_name"]]
    hist = c.functions.getHistory(batch_id).call()
    history = [{"timestamp": h[0], "event": h[1], "actor": h[2], "status": STATUS_LABEL[STATUS_NAMES[h[3]]], "detail": h[4]}
               for h in hist]
    return {"block": b, "history": history}


def tx_for_batch(batch_id: str, block_hash: str):
    """Cari transaction hash pembuatan checkpoint dari event CheckpointCreated."""
    for ev in bc.get_events("CheckpointCreated"):
        if ev["args"]["batchId"] == batch_id:
            return ev["transactionHash"].hex(), ev["blockNumber"]
    return None, None


def prepare_create(sender, election_id, batch_id, catatan):
    batch_id = (batch_id or "").strip()
    if not BATCH_RE.match(batch_id):
        raise ValidationError("Batch ID harus 3-64 karakter: huruf, angka, titik, garis bawah, atau tanda hubung.")
    if batch_id.upper().startswith("FINAL-"):
        raise ValidationError("Awalan FINAL- dicadangkan untuk finalisasi otomatis.")
    fn = bc.get_contract().functions.buatBatchSuara(election_id, batch_id, (catatan or "").strip()[:200])
    return make_plan("Pembuatan checkpoint audit", bc.prepare_tx(fn, sender), "audit_only",
                     {"action": "CREATE_CHECKPOINT", "election_id": election_id, "detail": batch_id},
                     "Checkpoint audit tercatat di rantai hash.")


def prepare_verify(sender, index):
    fn = bc.get_contract().functions.verifikasiLokal(index)
    return make_plan("Verifikasi lokal", bc.prepare_tx(fn, sender), "verify_local", {"index": index},
                     "Transaksi verifikasi lokal dikirim.")


def prepare_recap(sender, index):
    fn = bc.get_contract().functions.rekapitulasiBertingkat(index)
    return make_plan("Rekapitulasi bertingkat", bc.prepare_tx(fn, sender), "audit_only",
                     {"action": "RECAP", "detail": f"blok={index}"}, "Blok masuk rekapitulasi bertingkat.")


def prepare_final(sender, index):
    fn = bc.get_contract().functions.penghitunganAkhir(index)
    return make_plan("Penghitungan akhir", bc.prepare_tx(fn, sender), "audit_only",
                     {"action": "FINAL_COUNT", "detail": f"blok={index}"}, "Penghitungan akhir selesai untuk blok ini.")


@after("verify_local")
def _after_verify(payload, receipt, actor):
    ev = bc.process_receipt_event("LocalVerified", receipt)
    ok = bool(ev[0]["args"]["isValid"]) if ev else False
    db.audit(actor, "VERIFY_LOCAL" if ok else "VERIFY_LOCAL_FAILED", None, f"blok={payload['index']}",
             receipt["transactionHash"].hex())
    clear_all()
    if not ok:
        raise ValidationError("Verifikasi GAGAL: hash blok tidak cocok. Kegagalan tercatat di blockchain.")
