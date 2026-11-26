"""Registrasi pemilih: DPT (CSV) -> permohonan -> verifikasi panitia -> hak memilih on-chain.
Identitas mentah hanya ada di SQLite; blockchain hanya menerima alamat wallet dan hash bergaram."""
import csv
import hashlib
import hmac
import io
import re
import secrets

from web3 import Web3

import config
from database import db
from services import auth_service as auth
from services import blockchain as bc
from services import election_service as es
from services.cache import clear_all
from services.errors import PermissionDenied, ValidationError
from services.flow import after, make_plan

REG_LABEL = {"menunggu": "Menunggu Verifikasi", "terverifikasi": "Terverifikasi", "ditolak": "Ditolak"}
ID_RE = re.compile(r"^[A-Za-z0-9._\-/]{1,64}$")


# -------------------------------------------------------------- kredensial
def credential_hash(election_id: int, custom_id: str) -> bytes:
    return Web3.keccak(text=f"{db.get_salt()}|{election_id}|{custom_id.strip()}")


def code_hash(election_id: int, code: str) -> str:
    norm = re.sub(r"[\s-]", "", code or "").upper()
    return hashlib.sha256(f"{db.get_salt()}|{election_id}|{norm}".encode()).hexdigest()


def generate_code() -> str:
    raw = secrets.token_hex(5).upper()
    return f"{raw[:5]}-{raw[5:]}"


def registration_message(election_id: int, wallet: str, custom_id: str) -> str:
    return ("EVOTE - Permohonan Registrasi Pemilih\n"
            f"Periode: {election_id}\n"
            f"Wallet: {wallet}\n"
            f"ID Pemilih: {custom_id.strip()}\n"
            "Tanda tangan ini hanya membuktikan kepemilikan wallet dan tidak dikenai biaya.")


# ------------------------------------------------------------------- DPT
def import_roster(admin_addr: str, election_id: int, csv_bytes: bytes) -> dict:
    auth.require_panitia(admin_addr)
    e = es.get_election(election_id)
    if not e:
        raise ValidationError("Periode tidak ditemukan.")
    if e["status"] in (es.STATUS_DONE, es.STATUS_CANCELLED):
        raise ValidationError("DPT tidak dapat diimpor ke periode yang sudah selesai atau dibatalkan.")
    if len(csv_bytes) > 2 * 1024 * 1024:
        raise ValidationError("Ukuran file CSV maksimal 2 MB.")
    try:
        text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("File CSV harus berenkode UTF-8.")
    sample = text[:2048]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    headers = {(h or "").strip().lower(): h for h in (reader.fieldnames or [])}
    if "custom_id" not in headers or "nama" not in headers:
        raise ValidationError("Header CSV wajib memuat kolom 'custom_id' dan 'nama' (opsional: 'kode_registrasi').")
    es.ensure_meta(election_id)
    imported, skipped, seen = [], [], set()
    with db.connect() as conn:
        for n, row in enumerate(reader, start=2):
            cid = (row.get(headers["custom_id"]) or "").strip()
            nama = (row.get(headers["nama"]) or "").strip()
            given = (row.get(headers.get("kode_registrasi", ""), "") or "").strip() if "kode_registrasi" in headers else ""
            if not cid and not nama:
                continue
            if not ID_RE.match(cid):
                skipped.append({"baris": n, "custom_id": cid, "alasan": "Custom ID kosong atau berisi karakter tidak valid"})
                continue
            if not nama or len(nama) > 120:
                skipped.append({"baris": n, "custom_id": cid, "alasan": "Nama kosong atau lebih dari 120 karakter"})
                continue
            if cid in seen or conn.execute("SELECT 1 FROM voter_roster WHERE election_id=? AND custom_id=?",
                                           (election_id, cid)).fetchone():
                skipped.append({"baris": n, "custom_id": cid, "alasan": "Custom ID duplikat"})
                continue
            seen.add(cid)
            code = given or generate_code()
            conn.execute("INSERT INTO voter_roster(election_id, custom_id, nama, kode_hash) VALUES(?,?,?,?)",
                         (election_id, cid, nama, code_hash(election_id, code)))
            imported.append({"custom_id": cid, "nama": nama, "kode_registrasi": code})
    db.audit(admin_addr, "IMPORT_ROSTER", election_id, f"{len(imported)} diimpor, {len(skipped)} dilewati")
    return {"imported": imported, "skipped": skipped}


def roster_stats(election_id: int) -> dict:
    with db.connect() as conn:
        r = conn.execute("SELECT COUNT(*) t, COALESCE(SUM(kode_terpakai),0) p FROM voter_roster WHERE election_id=?",
                         (election_id,)).fetchone()
        regs = {row["status"]: row["n"] for row in conn.execute(
            "SELECT status, COUNT(*) n FROM registrations WHERE election_id=? GROUP BY status", (election_id,))}
    return {"dpt": r["t"], "kode_terpakai": r["p"], "menunggu": regs.get("menunggu", 0),
            "terverifikasi": regs.get("terverifikasi", 0), "ditolak": regs.get("ditolak", 0)}


def reset_code(admin_addr: str, roster_id: int) -> str:
    auth.require_panitia(admin_addr)
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM voter_roster WHERE id=?", (roster_id,)).fetchone()
        if not row:
            raise ValidationError("Data DPT tidak ditemukan.")
        if conn.execute("SELECT 1 FROM registrations WHERE roster_id=? AND status IN ('menunggu','terverifikasi')",
                        (roster_id,)).fetchone():
            raise ValidationError("Identitas ini sudah memiliki registrasi aktif; kode tidak dapat diatur ulang.")
        code = generate_code()
        conn.execute("UPDATE voter_roster SET kode_hash=?, kode_terpakai=0, gagal_verifikasi=0 WHERE id=?",
                     (code_hash(row["election_id"], code), roster_id))
    db.audit(admin_addr, "RESET_CODE", row["election_id"], f"roster={roster_id}")
    return code


# ------------------------------------------------------------ registrasi
def submit_registration(election_id: int, custom_id: str, code: str, wallet: str, signature: str) -> int:
    wallet = auth.normalize_wallet(wallet)
    custom_id = (custom_id or "").strip()
    if not ID_RE.match(custom_id):
        raise ValidationError("Custom ID tidak valid.")
    e = es.get_election(election_id)
    if not e:
        raise ValidationError("Periode tidak ditemukan.")
    if e["state"] not in (es.STATE_DRAFT, es.STATE_PUBLISHED) or bc.chain_now() > e["end"]:
        raise ValidationError("Registrasi untuk periode ini sudah ditutup.")
    if not auth.verify_signature(registration_message(election_id, wallet, custom_id), signature, wallet):
        raise PermissionDenied("Tanda tangan wallet tidak valid. Registrasi memerlukan bukti kepemilikan wallet.")
    generic = "Custom ID atau kode registrasi tidak sesuai dengan Daftar Pemilih Tetap."
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM voter_roster WHERE election_id=? AND custom_id=?",
                           (election_id, custom_id)).fetchone()
        if not row:
            raise ValidationError(generic)
        if row["gagal_verifikasi"] >= config.MAX_REG_ATTEMPTS:
            raise PermissionDenied("Terlalu banyak percobaan gagal. Hubungi panitia untuk mengatur ulang kode registrasi.")
        if not hmac.compare_digest(row["kode_hash"], code_hash(election_id, code)):
            conn.execute("UPDATE voter_roster SET gagal_verifikasi = gagal_verifikasi + 1 WHERE id=?", (row["id"],))
            conn.commit()
            raise ValidationError(generic)
        if conn.execute("SELECT 1 FROM registrations WHERE election_id=? AND roster_id=? AND status IN ('menunggu','terverifikasi')",
                        (election_id, row["id"])).fetchone():
            raise ValidationError("Identitas ini sudah memiliki registrasi aktif pada periode ini.")
        if conn.execute("SELECT 1 FROM registrations WHERE election_id=? AND wallet=? AND status IN ('menunggu','terverifikasi')",
                        (election_id, wallet)).fetchone():
            raise ValidationError("Wallet ini sudah didaftarkan pada periode ini.")
        if bc.get_contract().functions.isEligible(election_id, wallet).call():
            raise ValidationError("Wallet ini sudah memiliki hak memilih pada periode ini.")
        cur = conn.execute("INSERT INTO registrations(election_id, roster_id, wallet, status, signature) "
                           "VALUES(?,?,?,?,?)", (election_id, row["id"], wallet, "menunggu", signature))
        reg_id = cur.lastrowid
        conn.execute("INSERT INTO registration_history(registration_id, status, actor, note) VALUES(?,?,?,?)",
                     (reg_id, "menunggu", wallet, "Permohonan dikirim pemilih"))
        conn.execute("UPDATE voter_roster SET kode_terpakai=1, gagal_verifikasi=0 WHERE id=?", (row["id"],))
    return reg_id


def list_registrations(admin_addr: str, election_id: int, status: str | None = None, search: str = "") -> list[dict]:
    auth.require_panitia(admin_addr)
    q = ("SELECT r.id, r.election_id, r.wallet, r.status, r.submitted_at, r.decided_at, r.decided_by, r.alasan, "
         "r.approve_tx_hash, v.custom_id, v.nama FROM registrations r JOIN voter_roster v ON v.id = r.roster_id "
         "WHERE r.election_id=?")
    args: list = [election_id]
    if status:
        q += " AND r.status=?"
        args.append(status)
    if search.strip():
        q += " AND (lower(v.custom_id) LIKE ? OR lower(r.wallet) LIKE ?)"
        like = f"%{search.strip().lower()}%"
        args += [like, like]
    q += " ORDER BY r.id DESC"
    with db.connect() as conn:
        return [dict(r) for r in conn.execute(q, args)]


def registration_history(registration_id: int) -> list[dict]:
    with db.connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT status, actor, note, at FROM registration_history WHERE registration_id=? ORDER BY id",
            (registration_id,))]


def prepare_approve(sender: str, registration_id: int):
    auth.require_panitia(sender)
    with db.connect() as conn:
        reg = conn.execute("SELECT r.*, v.custom_id FROM registrations r JOIN voter_roster v ON v.id=r.roster_id "
                           "WHERE r.id=?", (registration_id,)).fetchone()
    if not reg or reg["status"] != "menunggu":
        raise ValidationError("Hanya permohonan berstatus 'Menunggu Verifikasi' yang dapat disetujui.")
    fn = bc.get_contract().functions.approveVoter(
        reg["election_id"], Web3.to_checksum_address(reg["wallet"]), credential_hash(reg["election_id"], reg["custom_id"]))
    return make_plan("Verifikasi pemilih", bc.prepare_tx(fn, sender), "registration_approved",
                     {"registration_id": registration_id, "election_id": reg["election_id"]},
                     "Pemilih diverifikasi dan hak memilih tercatat di blockchain.")


@after("registration_approved")
def _after_approved(payload, receipt, actor):
    txh = receipt["transactionHash"].hex()
    with db.connect() as conn:
        conn.execute("UPDATE registrations SET status='terverifikasi', decided_at=datetime('now'), decided_by=?, "
                     "approve_tx_hash=? WHERE id=?", (actor, txh, payload["registration_id"]))
        conn.execute("INSERT INTO registration_history(registration_id, status, actor, note) VALUES(?,?,?,?)",
                     (payload["registration_id"], "terverifikasi", actor, "Disetujui panitia"))
    db.audit(actor, "APPROVE_VOTER", payload["election_id"], f"registrasi={payload['registration_id']}", txh)
    clear_all()


def reject_registration(admin_addr: str, registration_id: int, alasan: str):
    auth.require_panitia(admin_addr)
    alasan = (alasan or "").strip()
    if not alasan:
        raise ValidationError("Alasan penolakan wajib diisi.")
    with db.connect() as conn:
        reg = conn.execute("SELECT * FROM registrations WHERE id=?", (registration_id,)).fetchone()
        if not reg or reg["status"] != "menunggu":
            raise ValidationError("Hanya permohonan berstatus 'Menunggu Verifikasi' yang dapat ditolak.")
        conn.execute("UPDATE registrations SET status='ditolak', decided_at=datetime('now'), decided_by=?, alasan=? "
                     "WHERE id=?", (admin_addr, alasan, registration_id))
        conn.execute("UPDATE voter_roster SET kode_terpakai=0 WHERE id=?", (reg["roster_id"],))
        conn.execute("INSERT INTO registration_history(registration_id, status, actor, note) VALUES(?,?,?,?)",
                     (registration_id, "ditolak", admin_addr, alasan))
    db.audit(admin_addr, "REJECT_VOTER", reg["election_id"], f"registrasi={registration_id}")


def wallet_status(election_id: int, wallet: str | None) -> dict:
    """Status pemilih untuk satu wallet pada satu periode (registrasi dari DB, hak memilih dari blockchain)."""
    res = {"registration": "Belum Terdaftar", "eligible": False, "voted": False, "history": [], "alasan": None}
    if not wallet:
        return res
    wallet = auth.normalize_wallet(wallet)
    c = bc.get_contract()
    res["eligible"] = bool(c.functions.isEligible(election_id, wallet).call())
    res["voted"] = bool(c.functions.hasVoted(election_id, wallet).call())
    with db.connect() as conn:
        reg = conn.execute("SELECT id, status, alasan FROM registrations WHERE election_id=? AND wallet=? "
                           "ORDER BY id DESC LIMIT 1", (election_id, wallet)).fetchone()
    if reg:
        res["registration"] = REG_LABEL[reg["status"]]
        res["alasan"] = reg["alasan"]
        res["history"] = registration_history(reg["id"])
    if res["eligible"]:
        res["registration"] = "Terverifikasi"
    return res
