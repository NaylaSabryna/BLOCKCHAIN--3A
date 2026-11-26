from database import db
from services import auth_service as auth
from services import blockchain as bc
from services import candidate_service as cs
from services import election_service as es
from services import voter_service as vs
from services.cache import clear_all
from services.errors import ValidationError
from services.flow import after, make_plan


def vote_gate(election_id: int | None, wallet: str | None, wallet_chain_id: int | None) -> dict:
    """Evaluasi seluruh syarat voting. Mengembalikan {'can_vote', 'reason', 'checks'}.
    Tombol voting aktif hanya bila semua syarat terpenuhi; kontrak tetap menjadi penjaga akhir."""
    checks = []

    def add(label, ok, detail=""):
        checks.append({"label": label, "ok": ok, "detail": detail})
        return ok

    ok = add("Wallet terhubung", bool(wallet), "Hubungkan MetaMask melalui panel samping." if not wallet else "")
    ok &= add("Jaringan sesuai", bool(wallet) and wallet_chain_id == bc.expected_chain_id(),
              f"Pindahkan MetaMask ke jaringan dengan Chain ID {bc.expected_chain_id()}.")
    e = es.get_election(election_id) if election_id else None
    ok &= add("Periode tersedia", e is not None, "Belum ada periode pemilihan.")
    cands = cs.list_candidates(election_id) if e else []
    ok &= add("Kandidat aktif tersedia", len(cands) > 0, "Periode ini belum memiliki kandidat aktif.")
    if e:
        if e["status"] == es.STATUS_RUNNING:
            add("Pemilihan sedang berlangsung", True)
        elif e["status"] == es.STATUS_UPCOMING:
            ok &= add("Pemilihan sedang berlangsung", False, f"Pemilihan belum dimulai ({es.fmt_time(e['start'])}).")
        elif e["status"] == es.STATUS_DRAFT:
            ok &= add("Pemilihan sedang berlangsung", False, "Periode masih berstatus Draft dan belum dipublikasikan.")
        else:
            ok &= add("Pemilihan sedang berlangsung", False, f"Periode berstatus {e['status']}.")
    st = vs.wallet_status(election_id, wallet) if (e and wallet) else None
    if st:
        reg_ok = st["registration"] != "Belum Terdaftar"
        ok &= add("Terdaftar sebagai pemilih", reg_ok, "Wallet ini belum terdaftar. Lakukan registrasi di menu Verifikasi Pemilih.")
        ok &= add("Terverifikasi panitia", st["eligible"],
                  "Permohonan registrasi masih menunggu verifikasi panitia." if st["registration"] == "Menunggu Verifikasi"
                  else "Wallet ini belum diverifikasi panitia.")
        ok &= add("Belum menggunakan hak suara", not st["voted"], "Hak suara pada periode ini sudah digunakan.")
    reason = next((c["detail"] for c in checks if not c["ok"]), "")
    return {"can_vote": bool(ok), "reason": reason, "checks": checks, "election": e, "candidates": cands, "status": st}


def prepare_vote(wallet: str, election_id: int, cid: int):
    wallet = auth.normalize_wallet(wallet)
    cand = cs.get_candidate(election_id, cid)
    if not cand or not cand["active"]:
        raise ValidationError("Kandidat tidak valid.")
    fn = bc.get_contract().functions.vote(election_id, cid)
    return make_plan("Pemungutan suara", bc.prepare_tx(fn, wallet), "vote_cast",
                     {"election_id": election_id}, "Suara Anda berhasil tercatat di blockchain.")


@after("vote_cast")
def _after_vote(payload, receipt, actor):
    # Sengaja tidak mencatat wallet maupun pilihan di database off-chain.
    clear_all()
