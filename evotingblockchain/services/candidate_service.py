import json

from web3 import Web3

from database import db
from services import blockchain as bc
from services import election_service as es
from services import storage_service as storage
from services.cache import clear_all
from services.errors import ValidationError
from services.flow import after, make_plan

FIELDS = ("deskripsi", "visi", "misi", "info_tambahan")
LIMITS = {"nama": 100, "deskripsi": 500, "visi": 2000, "misi": 3000, "info_tambahan": 1000}


def metadata_hash(election_id, nomor, form: dict, foto_sha: str | None) -> str:
    canon = json.dumps({
        "election_id": election_id, "nomor_urut": nomor, "nama": form["nama"],
        **{k: form.get(k, "") for k in FIELDS}, "foto_sha256": foto_sha or "",
    }, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "0x" + Web3.keccak(text=canon).hex().removeprefix("0x")


def validate_form(form: dict) -> dict:
    clean = {k: (form.get(k) or "").strip() for k in ("nama", *FIELDS)}
    if not clean["nama"]:
        raise ValidationError("Nama kandidat wajib diisi.")
    for k, lim in LIMITS.items():
        if len(clean[k]) > lim:
            raise ValidationError(f"Kolom {k.replace('_', ' ')} maksimal {lim} karakter.")
    try:
        nomor = int(form.get("nomor_urut"))
    except (TypeError, ValueError):
        raise ValidationError("Nomor urut harus berupa angka.")
    if nomor < 1 or nomor > 999:
        raise ValidationError("Nomor urut harus antara 1 dan 999.")
    clean["nomor_urut"] = nomor
    return clean


def _meta_rows(election_id):
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM candidates_meta WHERE election_id=?", (election_id,)).fetchall()
    return {r["chain_cid"]: dict(r) for r in rows}


def list_candidates(election_id: int, include_inactive=False) -> list[dict]:
    """Kandidat dari blockchain (otoritatif) digabung dengan metadata off-chain."""
    c = bc.get_contract()
    total = bc.read_election(election_id)["candidateCount"]
    meta = _meta_rows(election_id)
    out = []
    for cid in range(1, total + 1):
        ch = bc.read_candidate(election_id, cid)
        if not ch["active"] and not include_inactive:
            continue
        m = meta.get(cid)
        has = bool(m)
        out.append({
            "cid": cid, "nomor": ch["nomorUrut"], "nama": ch["name"], "active": ch["active"],
            "deskripsi": m["deskripsi"] if has else "", "visi": m["visi"] if has else "",
            "misi": m["misi"] if has else "", "info_tambahan": m["info_tambahan"] if has else "",
            "foto_path": m["foto_path"] if has else None, "foto_sha": m["foto_sha256"] if has else None,
            "has_meta": has, "meta_ok": has and m["metadata_hash"] == ch["metadataHash"],
            "chain_hash": ch["metadataHash"],
        })
    return sorted(out, key=lambda x: x["nomor"])


def get_candidate(election_id: int, cid: int) -> dict | None:
    return next((c for c in list_candidates(election_id, True) if c["cid"] == cid), None)


def _require_editable(election_id):
    e = es.get_election(election_id)
    if not e:
        raise ValidationError("Periode tidak ditemukan.")
    if not e["editable"]:
        raise ValidationError("Kandidat hanya dapat diubah sebelum pemilihan dimulai.")
    return e


def prepare_add(sender, election_id, form: dict, photo: tuple[bytes, str] | None):
    _require_editable(election_id)
    clean = validate_form(form)
    if any(c["nomor"] == clean["nomor_urut"] for c in list_candidates(election_id)):
        raise ValidationError("Nomor urut sudah dipakai kandidat lain pada periode ini.")
    foto_path = foto_sha = None
    if photo and photo[0]:
        foto_path, foto_sha = storage.save_candidate_photo(election_id, *photo)
    h = metadata_hash(election_id, clean["nomor_urut"], clean, foto_sha)
    fn = bc.get_contract().functions.addCandidate(election_id, clean["nomor_urut"], clean["nama"], h)
    payload = {"election_id": election_id, "form": clean, "foto_path": foto_path, "foto_sha": foto_sha, "hash": h}
    return make_plan("Penambahan kandidat", bc.prepare_tx(fn, sender), "candidate_added", payload,
                     f"Kandidat '{clean['nama']}' berhasil ditambahkan.")


def prepare_update(sender, election_id, cid, form: dict, photo: tuple[bytes, str] | None):
    _require_editable(election_id)
    cur = get_candidate(election_id, cid)
    if not cur or not cur["active"]:
        raise ValidationError("Kandidat tidak ditemukan.")
    clean = validate_form(form)
    if any(c["nomor"] == clean["nomor_urut"] and c["cid"] != cid for c in list_candidates(election_id)):
        raise ValidationError("Nomor urut sudah dipakai kandidat lain pada periode ini.")
    foto_path, foto_sha = cur["foto_path"], cur["foto_sha"]
    if photo and photo[0]:
        foto_path, foto_sha = storage.save_candidate_photo(election_id, *photo)
    h = metadata_hash(election_id, clean["nomor_urut"], clean, foto_sha)
    fn = bc.get_contract().functions.updateCandidate(election_id, cid, clean["nomor_urut"], clean["nama"], h)
    payload = {"election_id": election_id, "cid": cid, "form": clean, "foto_path": foto_path,
               "foto_sha": foto_sha, "hash": h}
    return make_plan("Pembaruan kandidat", bc.prepare_tx(fn, sender), "candidate_updated", payload,
                     f"Data kandidat '{clean['nama']}' berhasil diperbarui.")


def prepare_remove(sender, election_id, cid):
    _require_editable(election_id)
    fn = bc.get_contract().functions.removeCandidate(election_id, cid)
    return make_plan("Penghapusan kandidat", bc.prepare_tx(fn, sender), "candidate_removed",
                     {"election_id": election_id, "cid": cid},
                     "Kandidat dihapus dari periode dan disimpan sebagai arsip.")


def _upsert(election_id, cid, payload):
    f = payload["form"]
    es.ensure_meta(election_id)
    with db.connect() as conn:
        row = conn.execute("SELECT id FROM candidates_meta WHERE election_id=? AND chain_cid=?",
                           (election_id, cid)).fetchone()
        vals = (f["nomor_urut"], f["nama"], f["deskripsi"], f["visi"], f["misi"], f["info_tambahan"],
                payload["foto_path"], payload["foto_sha"], payload["hash"])
        if row:
            conn.execute("UPDATE candidates_meta SET nomor_urut=?, nama=?, deskripsi=?, visi=?, misi=?, "
                         "info_tambahan=?, foto_path=?, foto_sha256=?, metadata_hash=?, status='aktif', "
                         "updated_at=datetime('now') WHERE id=?", (*vals, row["id"]))
        else:
            conn.execute("INSERT INTO candidates_meta(election_id, chain_cid, nomor_urut, nama, deskripsi, visi, "
                         "misi, info_tambahan, foto_path, foto_sha256, metadata_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                         (election_id, cid, *vals))


@after("candidate_added")
def _after_added(payload, receipt, actor):
    ev = bc.process_receipt_event("CandidateAdded", receipt)
    cid = int(ev[0]["args"]["candidateId"])
    _upsert(payload["election_id"], cid, payload)
    db.audit(actor, "ADD_CANDIDATE", payload["election_id"], payload["form"]["nama"], receipt["transactionHash"].hex())
    clear_all()


@after("candidate_updated")
def _after_updated(payload, receipt, actor):
    _upsert(payload["election_id"], payload["cid"], payload)
    db.audit(actor, "UPDATE_CANDIDATE", payload["election_id"], payload["form"]["nama"], receipt["transactionHash"].hex())
    clear_all()


@after("candidate_removed")
def _after_removed(payload, receipt, actor):
    with db.connect() as conn:
        conn.execute("UPDATE candidates_meta SET status='dihapus', updated_at=datetime('now') "
                     "WHERE election_id=? AND chain_cid=?", (payload["election_id"], payload["cid"]))
    db.audit(actor, "REMOVE_CANDIDATE", payload["election_id"], f"cid={payload['cid']}", receipt["transactionHash"].hex())
    clear_all()
