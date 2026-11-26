from datetime import datetime

from web3 import Web3

import config
from database import db
from services import blockchain as bc
from services.cache import ttl_cache, clear_all
from services.errors import ValidationError
from services.flow import after, make_plan

STATE_DRAFT, STATE_PUBLISHED, STATE_CANCELLED, STATE_FINALIZED = 0, 1, 2, 3

STATUS_DRAFT = "Draft"
STATUS_UPCOMING = "Belum Dimulai"
STATUS_RUNNING = "Sedang Berlangsung"
STATUS_DONE = "Selesai"
STATUS_CANCELLED = "Dibatalkan"


def derive_status(state: int, start: int, end: int, now: int) -> str:
    if state == STATE_CANCELLED:
        return STATUS_CANCELLED
    if state == STATE_FINALIZED:
        return STATUS_DONE
    if state == STATE_DRAFT:
        return STATUS_DRAFT
    if now < start:
        return STATUS_UPCOMING
    if now <= end:
        return STATUS_RUNNING
    return STATUS_DONE


def to_unix(d, t) -> int:
    return int(datetime(d.year, d.month, d.day, t.hour, t.minute, tzinfo=config.TZ).timestamp())


def fmt_time(ts: int | None) -> str:
    if not ts:
        return "-"
    return datetime.fromtimestamp(int(ts), config.TZ).strftime("%d %b %Y, %H:%M") + f" {config.TZ_LABEL}"


def description_hash(description: str) -> str:
    return "0x" + Web3.keccak(text=description.strip()).hex().removeprefix("0x")


def ensure_meta(election_id: int, description: str = "", created_by: str | None = None):
    with db.connect() as conn:
        conn.execute("INSERT OR IGNORE INTO elections_meta(election_id, description, created_by) VALUES(?,?,?)",
                     (election_id, description, created_by))


def _description(election_id: int) -> str:
    with db.connect() as conn:
        row = conn.execute("SELECT description FROM elections_meta WHERE election_id=?", (election_id,)).fetchone()
    return row["description"] if row else ""


def enrich(raw: dict, now: int) -> dict:
    status = derive_status(raw["state"], raw["startTime"], raw["endTime"], now)
    return {
        "id": raw["id"], "name": raw["name"], "start": raw["startTime"], "end": raw["endTime"],
        "state": raw["state"], "status": status, "description": _description(raw["id"]),
        "candidates": raw["activeCandidates"], "total_votes": raw["totalVotes"],
        "approved_voters": raw["approvedVoters"], "metadata_hash": raw["metadataHash"],
        "created_at": raw["createdAt"],
        "editable": raw["state"] in (STATE_DRAFT, STATE_PUBLISHED) and now < raw["startTime"],
        "is_open": status == STATUS_RUNNING,
        "needs_finalize": raw["state"] == STATE_PUBLISHED and now > raw["endTime"],
        "meta_ok": raw["metadataHash"] == "0x" + "00" * 32 or
                   raw["metadataHash"] == description_hash(_description(raw["id"])),
    }


@ttl_cache(2)
def list_elections() -> list[dict]:
    c = bc.get_contract()
    now = bc.chain_now()
    count = c.functions.electionCount().call()
    items = [enrich(bc.read_election(i), now) for i in range(1, count + 1)]
    return sorted(items, key=lambda e: e["id"], reverse=True)


def get_election(election_id: int) -> dict | None:
    return next((e for e in list_elections() if e["id"] == election_id), None)


def default_election(items: list[dict] | None = None) -> dict | None:
    items = list_elections() if items is None else items
    if not items:
        return None
    running = [e for e in items if e["status"] == STATUS_RUNNING]
    if running:
        return min(running, key=lambda e: e["end"])
    upcoming = [e for e in items if e["status"] == STATUS_UPCOMING]
    if upcoming:
        return min(upcoming, key=lambda e: e["start"])
    return max(items, key=lambda e: e["start"])


def _validate(name: str, description: str, start: int, end: int):
    name = (name or "").strip()
    if not name:
        raise ValidationError("Nama pemilihan wajib diisi.")
    if len(name) > 120:
        raise ValidationError("Nama pemilihan maksimal 120 karakter.")
    if len(description or "") > 2000:
        raise ValidationError("Deskripsi maksimal 2000 karakter.")
    if end <= start:
        raise ValidationError("Waktu berakhir harus setelah waktu mulai.")
    if start < bc.chain_now() + config.MIN_START_LEAD_SECONDS:
        raise ValidationError("Waktu mulai minimal 2 menit dari sekarang agar transaksi sempat dikonfirmasi.")
    return name, (description or "").strip()


def prepare_create(sender, name, description, start, end):
    name, description = _validate(name, description, start, end)
    fn = bc.get_contract().functions.createElection(name, start, end, description_hash(description))
    return make_plan("Pembuatan periode pemilihan", bc.prepare_tx(fn, sender), "election_created",
                     {"name": name, "description": description}, f"Periode '{name}' berhasil dibuat sebagai Draft.")


def prepare_update(sender, election_id, name, description, start, end):
    e = get_election(election_id)
    if not e or not e["editable"]:
        raise ValidationError("Periode hanya dapat diedit sebelum waktu mulai.")
    name, description = _validate(name, description, start, end)
    fn = bc.get_contract().functions.updateElection(election_id, name, start, end, description_hash(description))
    return make_plan("Pembaruan periode pemilihan", bc.prepare_tx(fn, sender), "election_updated",
                     {"election_id": election_id, "description": description, "name": name})


def prepare_publish(sender, election_id):
    fn = bc.get_contract().functions.publishElection(election_id)
    return make_plan("Publikasi periode", bc.prepare_tx(fn, sender), "audit_only",
                     {"action": "PUBLISH_ELECTION", "election_id": election_id},
                     "Periode dipublikasikan. Kandidat dan jadwal kini terkunci menurut jadwal pemilihan.")


def prepare_cancel(sender, election_id):
    fn = bc.get_contract().functions.cancelElection(election_id)
    return make_plan("Pembatalan periode", bc.prepare_tx(fn, sender), "audit_only",
                     {"action": "CANCEL_ELECTION", "election_id": election_id}, "Periode dibatalkan.")


def prepare_finalize(sender, election_id):
    fn = bc.get_contract().functions.finalizeElection(election_id)
    return make_plan("Finalisasi hasil", bc.prepare_tx(fn, sender), "audit_only",
                     {"action": "FINALIZE_ELECTION", "election_id": election_id},
                     "Hasil periode difinalisasi dan checkpoint audit otomatis dibuat.")


@after("election_created")
def _after_created(payload, receipt, actor):
    ev = bc.process_receipt_event("ElectionCreated", receipt)
    eid = int(ev[0]["args"]["electionId"])
    ensure_meta(eid, payload["description"], actor)
    db.audit(actor, "CREATE_ELECTION", eid, payload["name"], receipt["transactionHash"].hex())
    clear_all()


@after("election_updated")
def _after_updated(payload, receipt, actor):
    ensure_meta(payload["election_id"])
    with db.connect() as conn:
        conn.execute("UPDATE elections_meta SET description=? WHERE election_id=?",
                     (payload["description"], payload["election_id"]))
    db.audit(actor, "UPDATE_ELECTION", payload["election_id"], payload["name"], receipt["transactionHash"].hex())
    clear_all()


@after("audit_only")
def _after_audit_only(payload, receipt, actor):
    db.audit(actor, payload["action"], payload.get("election_id"), payload.get("detail"),
             receipt["transactionHash"].hex())
    clear_all()
