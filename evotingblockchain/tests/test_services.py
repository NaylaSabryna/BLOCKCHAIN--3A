import io

import pytest
from PIL import Image

from conftest import sign_message
from services import auth_service as auth
from services import audit_service as audit
from services import blockchain as bc
from services import candidate_service as cs
from services import election_service as es
from services import result_service as rs
from services import storage_service as storage
from services import transactions as txs
from services import voter_service as vs
from services import voting_service as vt
from services.cache import clear_all
from services.errors import PermissionDenied, ValidationError


def png_bytes(size=(120, 90), color=(10, 80, 160)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def ctx():
    return {}


def test_status_terkoneksi(deployed):
    s = bc.status()
    assert s["connected"] and s["contract_ok"]


def test_otorisasi_panitia(accounts):
    assert auth.is_panitia(accounts["admin"])
    assert not auth.is_panitia(accounts["outsider"])
    with pytest.raises(PermissionDenied):
        auth.require_panitia(accounts["outsider"])


def test_login_admin_dengan_tanda_tangan(accounts):
    ch = auth.admin_challenge(accounts["admin"])
    sig = sign_message(0, ch["message"])
    assert auth.verify_admin_login(ch, sig) == accounts["admin"]
    # tanda tangan wallet lain ditolak
    with pytest.raises(PermissionDenied):
        auth.verify_admin_login(ch, sign_message(1, ch["message"]))
    # wallet sah tetapi bukan panitia ditolak
    ch2 = auth.admin_challenge(accounts["outsider"])
    with pytest.raises(PermissionDenied):
        auth.verify_admin_login(ch2, sign_message(1, ch2["message"]))  # kunci milik v1, bukan outsider
    # wallet non-panitia dengan tanda tangan benar tetap ditolak oleh pengecekan role
    ch3 = auth.admin_challenge(accounts["v1"])
    with pytest.raises(PermissionDenied):
        auth.verify_admin_login(ch3, sign_message(1, ch3["message"]))


def test_periode_validasi_dan_pembuatan(ctx, accounts, send):
    now = bc.chain_now()
    with pytest.raises(ValidationError):
        es.prepare_create(accounts["admin"], "", "x", now + 500, now + 900)
    with pytest.raises(ValidationError):
        es.prepare_create(accounts["admin"], "Uji", "x", now + 10, now + 900)  # terlalu dekat
    with pytest.raises(ValidationError):
        es.prepare_create(accounts["admin"], "Uji", "x", now + 900, now + 500)
    # non-panitia ditolak di tahap simulasi kontrak
    with pytest.raises(Exception) as exc:
        es.prepare_create(accounts["outsider"], "Uji", "x", now + 500, now + 900)
    assert "Panitia" in str(exc.value)
    ctx["start"], ctx["end"] = now + 600, now + 1800
    plan = es.prepare_create(accounts["admin"], "Pemilihan Ketua Uji", "Deskripsi uji", ctx["start"], ctx["end"])
    send(plan)
    clear_all()
    e = es.list_elections()[0]
    ctx["eid"] = e["id"]
    assert e["name"] == "Pemilihan Ketua Uji" and e["status"] == es.STATUS_DRAFT
    assert e["description"] == "Deskripsi uji" and e["meta_ok"]


def test_kandidat_dinamis_dan_foto(ctx, accounts, send):
    eid = ctx["eid"]
    # validasi foto
    with pytest.raises(ValidationError):
        storage.save_candidate_photo(eid, b"bukan gambar", "x.png")
    with pytest.raises(ValidationError):
        storage.save_candidate_photo(eid, png_bytes(), "x.gif")
    with pytest.raises(ValidationError):
        storage.save_candidate_photo(eid, b"\x00" * (3 * 1024 * 1024), "x.png")
    form = lambda n, nama: {"nomor_urut": n, "nama": nama, "deskripsi": "Ringkas", "visi": "Visi", "misi": "Misi"}
    send(cs.prepare_add(accounts["admin"], eid, form(1, "Calon Satu"), (png_bytes(), "foto.png")))
    send(cs.prepare_add(accounts["admin"], eid, form(2, "Calon Dua"), None))
    with pytest.raises(ValidationError):
        cs.prepare_add(accounts["admin"], eid, form(1, "Duplikat"), None)
    c = cs.list_candidates(eid)
    assert [x["nomor"] for x in c] == [1, 2]
    assert c[0]["foto_path"] and c[0]["meta_ok"] and c[1]["foto_path"] is None
    assert storage.photo_uri(c[0]["foto_path"], c[0]["nama"]).startswith("data:image/jpeg")
    assert storage.photo_uri(None, "Calon Dua").startswith("data:image/svg+xml")
    # edit
    send(cs.prepare_update(accounts["admin"], eid, c[1]["cid"], form(3, "Calon Dua Revisi"), None))
    c = cs.list_candidates(eid)
    assert [x["nomor"] for x in c] == [1, 3] and c[1]["nama"] == "Calon Dua Revisi" and c[1]["meta_ok"]
    # hapus + nomor bebas kembali
    send(cs.prepare_add(accounts["admin"], eid, form(4, "Sementara"), None))
    tmp = [x for x in cs.list_candidates(eid) if x["nama"] == "Sementara"][0]
    send(cs.prepare_remove(accounts["admin"], eid, tmp["cid"]))
    assert all(x["nama"] != "Sementara" for x in cs.list_candidates(eid))
    send(cs.prepare_add(accounts["admin"], eid, form(4, "Pengganti"), None))
    assert len(cs.list_candidates(eid)) == 3
    send(cs.prepare_remove(accounts["admin"], eid, [x for x in cs.list_candidates(eid) if x["nama"] == "Pengganti"][0]["cid"]))
    assert len(cs.list_candidates(eid)) == 2


def test_periode_lain_tidak_tercampur(ctx, accounts, send):
    now = bc.chain_now()
    send(es.prepare_create(accounts["admin"], "Periode Kedua", "", now + 5000, now + 9000))
    clear_all()
    other = es.list_elections()[0]["id"]
    assert other != ctx["eid"]
    assert cs.list_candidates(other) == []
    assert len(cs.list_candidates(ctx["eid"])) == 2


CSV = (b"custom_id,nama\nNIM001,Pemilih Satu\nNIM002,Pemilih Dua\nNIM003,Pemilih Tiga\n"
       b"NIM001,Duplikat\n,Tanpa ID\n")


def test_impor_dpt(ctx, accounts):
    eid = ctx["eid"]
    with pytest.raises(PermissionDenied):
        vs.import_roster(accounts["outsider"], eid, CSV)
    with pytest.raises(ValidationError):
        vs.import_roster(accounts["admin"], eid, b"a,b\n1,2\n")
    res = vs.import_roster(accounts["admin"], eid, CSV)
    assert len(res["imported"]) == 3 and len(res["skipped"]) == 2  # duplikat dan baris tanpa ID dilewati
    ctx["codes"] = {r["custom_id"]: r["kode_registrasi"] for r in res["imported"]}
    assert vs.roster_stats(eid)["dpt"] == 3
    # impor ulang file yang sama tidak membuat duplikat
    again = vs.import_roster(accounts["admin"], eid, CSV)
    assert len(again["imported"]) == 0


def test_registrasi_dan_verifikasi(ctx, accounts, send):
    eid = ctx["eid"]
    w1, w2 = accounts["v1"], accounts["v2"]
    msg = lambda w, i: vs.registration_message(eid, w, i)
    # tanda tangan salah (wallet lain)
    with pytest.raises(PermissionDenied):
        vs.submit_registration(eid, "NIM001", ctx["codes"]["NIM001"], w1, sign_message(2, msg(w1, "NIM001")))
    # kode salah
    with pytest.raises(ValidationError):
        vs.submit_registration(eid, "NIM001", "SALAH-KODE0", w1, sign_message(1, msg(w1, "NIM001")))
    # custom id tidak ada di DPT
    with pytest.raises(ValidationError):
        vs.submit_registration(eid, "NIM999", "XXXXX-XXXXX", w1, sign_message(1, msg(w1, "NIM999")))
    r1 = vs.submit_registration(eid, "NIM001", ctx["codes"]["NIM001"], w1, sign_message(1, msg(w1, "NIM001")))
    assert vs.wallet_status(eid, w1)["registration"] == "Menunggu Verifikasi"
    # identitas sama / wallet sama tidak boleh daftar lagi
    with pytest.raises(ValidationError):
        vs.submit_registration(eid, "NIM001", ctx["codes"]["NIM001"], w2, sign_message(2, msg(w2, "NIM001")))
    with pytest.raises(ValidationError):
        vs.submit_registration(eid, "NIM002", ctx["codes"]["NIM002"], w1, sign_message(1, msg(w1, "NIM002")))
    # v2 mendaftar lalu ditolak, lalu dapat mendaftar ulang
    r2 = vs.submit_registration(eid, "NIM002", ctx["codes"]["NIM002"], w2, sign_message(2, msg(w2, "NIM002")))
    with pytest.raises(PermissionDenied):
        vs.reject_registration(accounts["outsider"], r2, "x")
    with pytest.raises(ValidationError):
        vs.reject_registration(accounts["admin"], r2, "  ")
    vs.reject_registration(accounts["admin"], r2, "Data tidak sesuai")
    assert vs.wallet_status(eid, w2)["registration"] == "Ditolak"
    r2b = vs.submit_registration(eid, "NIM002", ctx["codes"]["NIM002"], w2, sign_message(2, msg(w2, "NIM002")))
    # persetujuan hanya oleh panitia, tercatat on-chain
    with pytest.raises(PermissionDenied):
        vs.prepare_approve(accounts["outsider"], r1)
    send(vs.prepare_approve(accounts["admin"], r1))
    send(vs.prepare_approve(accounts["admin"], r2b))
    assert vs.wallet_status(eid, w1)["registration"] == "Terverifikasi" and vs.wallet_status(eid, w1)["eligible"]
    hist = vs.registration_history(r1)
    assert [h["status"] for h in hist] == ["menunggu", "terverifikasi"]
    with pytest.raises(ValidationError):
        vs.prepare_approve(accounts["admin"], r1)  # sudah diproses


def test_kunci_percobaan_gagal(ctx, accounts):
    eid, w3_ = ctx["eid"], accounts["v3"]
    msg = vs.registration_message(eid, w3_, "NIM003")
    sig = sign_message(3, msg)
    for _ in range(5):
        with pytest.raises(ValidationError):
            vs.submit_registration(eid, "NIM003", "SALAH-SALAH", w3_, sig)
    with pytest.raises(PermissionDenied):  # kode benar pun terkunci
        vs.submit_registration(eid, "NIM003", ctx["codes"]["NIM003"], w3_, sig)
    new = vs.reset_code(accounts["admin"], [r for r in _roster(eid) if r["custom_id"] == "NIM003"][0]["id"])
    ctx["codes"]["NIM003"] = new
    vs.submit_registration(eid, "NIM003", new, w3_, sig)


def _roster(eid):
    from database import db
    with db.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM voter_roster WHERE election_id=?", (eid,))]


def test_voting_alur_lengkap(ctx, accounts, send, advance):
    eid = ctx["eid"]
    w1, w2 = accounts["v1"], accounts["v2"]
    chain = bc.expected_chain_id()
    # sebelum publikasi: tidak dapat memilih
    g = vt.vote_gate(eid, w1, chain)
    assert not g["can_vote"]
    # panitia dapat mempublikasikan (>= 2 kandidat tersedia)
    send(es.prepare_publish(accounts["admin"], eid))
    clear_all()
    assert es.get_election(eid)["status"] == es.STATUS_UPCOMING
    g = vt.vote_gate(eid, w1, chain)
    assert not g["can_vote"] and "belum dimulai" in g["reason"]
    advance(700)
    g = vt.vote_gate(eid, w1, chain)
    assert g["can_vote"], g["checks"]
    # kondisi tombol lain
    assert not vt.vote_gate(eid, None, None)["can_vote"]
    assert not vt.vote_gate(eid, w1, 1)["can_vote"]
    assert not vt.vote_gate(eid, accounts["outsider"], chain)["can_vote"]
    # kandidat terkunci setelah dimulai
    with pytest.raises(ValidationError):
        cs.prepare_add(accounts["admin"], eid, {"nomor_urut": 9, "nama": "Terlambat"}, None)
    with pytest.raises(ValidationError):
        es.prepare_update(accounts["admin"], eid, "Ganti", "", bc.chain_now() + 500, bc.chain_now() + 900)
    c = cs.list_candidates(eid)
    send(vt.prepare_vote(w1, eid, c[0]["cid"]))
    send(vt.prepare_vote(w2, eid, c[0]["cid"]))
    clear_all()
    assert not vt.vote_gate(eid, w1, chain)["can_vote"]
    with pytest.raises(Exception) as exc:
        vt.prepare_vote(w1, eid, c[1]["cid"])  # double voting ditolak pada simulasi kontrak
    assert "sudah digunakan" in str(exc.value)
    res = rs.get_results(eid)
    assert res["total_votes"] == 2 and res["rows"][0]["suara"] == 2 and res["rows"][0]["persen"] == 100.0
    assert res["label"] == "Hasil Sementara" and res["participation"] == 100.0
    ctx["voted"] = True


def test_riwayat_dan_privasi(ctx, accounts):
    eid = ctx["eid"]
    rows = txs.list_transactions(viewer=None, is_admin=False, election_id=eid)
    votes = [r for r in rows if r["event"] == "VoteCast"]
    assert len(votes) == 2
    assert all(r["wallet_display"] == "Disamarkan" and r["wallet_full"] is None for r in votes)
    own = txs.list_transactions(viewer=accounts["v1"], election_id=eid)
    assert any(r["event"] == "VoteCast" and r["wallet_full"] == accounts["v1"] for r in own)
    admin_rows = txs.list_transactions(is_admin=True, election_id=eid)
    assert all(r["wallet_full"] for r in admin_rows if r["event"] == "VoteCast")
    assert txs.list_transactions(query=votes[0]["tx_hash"][:12])[0]["tx_hash"] == votes[0]["tx_hash"]
    ser = txs.participation_series(eid)
    assert ser and ser[-1]["kumulatif"] == 2
    # tidak ada kolom pilihan kandidat pada riwayat publik
    assert not any("kandidat" in k or "candidate" in k for k in votes[0])


def test_finalisasi_dan_audit(ctx, accounts, send, advance):
    eid = ctx["eid"]
    with pytest.raises(Exception) as exc:
        es.prepare_finalize(accounts["admin"], eid)
    assert "belum berakhir" in str(exc.value)
    send(audit.prepare_create(accounts["admin"], eid, "BATCH-A", "Snapshot saat voting"))
    with pytest.raises(ValidationError):
        audit.prepare_create(accounts["admin"], eid, "FINAL-1", "x")
    with pytest.raises(Exception):
        audit.prepare_create(accounts["admin"], eid, "BATCH-A", "dup")
    advance(2500)
    assert es.get_election(eid)["status"] == es.STATUS_DONE
    assert es.get_election(eid)["needs_finalize"]
    send(es.prepare_finalize(accounts["admin"], eid))
    clear_all()
    res = rs.get_results(eid)
    assert res["is_final"] and res["label"] == "Hasil Final"
    blocks = audit.list_blocks()
    assert len(blocks) == 2 and blocks[1]["batchId"] == f"FINAL-{eid}"
    assert audit.chain_integrity()["valid"]
    send(audit.prepare_verify(accounts["admin"], 1))
    send(audit.prepare_recap(accounts["admin"], 1))
    send(audit.prepare_final(accounts["admin"], 1))
    found = audit.search_batch("BATCH-A")
    assert found["block"]["status_name"] == "FINISHED"
    assert [h["event"] for h in found["history"]] == ["VOTE_BATCH_CREATED", "VERIFIED_LOCAL", "IN_RECAP", "FINISHED"]
    assert audit.search_batch("TIDAK-ADA") is None
    txh, blk = audit.tx_for_batch("BATCH-A", "")
    assert txh and blk
    # setelah selesai, pemilihan tidak dapat dibuka kembali / dibatalkan
    with pytest.raises(Exception):
        es.prepare_cancel(accounts["admin"], eid)
    with pytest.raises(ValidationError):
        cs.prepare_add(accounts["admin"], eid, {"nomor_urut": 8, "nama": "Pasca"}, None)


def test_audit_log_tersimpan(ctx):
    from database import db
    actions = {a["action"] for a in db.recent_audit(200)}
    assert {"CREATE_ELECTION", "ADD_CANDIDATE", "APPROVE_VOTER", "FINALIZE_ELECTION", "IMPORT_ROSTER"} <= actions


def test_tidak_ada_private_key_di_kode():
    from pathlib import Path
    import re
    root = Path(__file__).resolve().parents[1]
    pat = re.compile(r"0x[0-9a-fA-F]{64}")
    offenders = []
    for p in list(root.glob("*.py")) + list((root / "services").glob("*.py")) + list((root / "pages").glob("*.py")) \
            + list((root / "components").glob("*.py")) + list((root / "database").glob("*.py")):
        if pat.search(p.read_text()):
            offenders.append(p.name)
    assert not offenders, f"Kemungkinan private key pada: {offenders}"
