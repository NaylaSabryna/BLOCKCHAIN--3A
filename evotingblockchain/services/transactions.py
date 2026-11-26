"""Riwayat transaksi dari event kontrak (sumber: blockchain). Tidak memuat pilihan kandidat."""
from collections import defaultdict
from datetime import datetime

import config
from services import blockchain as bc
from services.cache import ttl_cache

EVENTS = {
    "ElectionCreated": "Pembuatan Periode", "ElectionUpdated": "Pembaruan Periode",
    "ElectionPublished": "Publikasi Periode", "ElectionCancelled": "Pembatalan Periode",
    "ElectionFinalized": "Finalisasi Periode", "CandidateAdded": "Penambahan Kandidat",
    "CandidateUpdated": "Pembaruan Kandidat", "CandidateRemoved": "Penghapusan Kandidat",
    "VoterApproved": "Verifikasi Pemilih", "VoteCast": "Pemungutan Suara",
    "CheckpointCreated": "Checkpoint Audit", "StatusUpdated": "Pembaruan Status Batch",
    "LocalVerified": "Verifikasi Lokal",
}
VOTER_EVENTS = {"VoteCast", "VoterApproved"}


def _wallet_of(name, args):
    if name in VOTER_EVENTS:
        return args.get("voter")
    return args.get("actor")


@ttl_cache(3)
def _all_rows() -> list[dict]:
    rows = []
    for name, label in EVENTS.items():
        for ev in bc.get_events(name):
            a = ev["args"]
            rows.append({
                "tx_hash": ev["transactionHash"].hex(), "block": ev["blockNumber"], "log": ev["logIndex"],
                "event": name, "jenis": label, "election_id": a.get("electionId"),
                "timestamp": bc.block_timestamp(ev["blockNumber"]), "status": "Berhasil",
                "wallet": _wallet_of(name, a), "is_voter_wallet": name in VOTER_EVENTS,
            })
    rows.sort(key=lambda r: (r["block"], r["log"]), reverse=True)
    return rows


def mask(addr):
    return f"{addr[:6]}...{addr[-4:]}" if addr else "-"


def list_transactions(viewer: str | None = None, is_admin: bool = False, election_id=None,
                      status=None, query: str = "") -> list[dict]:
    """Aturan privasi: wallet pemilih hanya terlihat untuk panitia dan pemilik wallet itu sendiri."""
    out = []
    q = (query or "").strip().lower()
    for r in _all_rows():
        if election_id and r["election_id"] != election_id:
            continue
        if status and r["status"] != status:
            continue
        if q and q not in r["tx_hash"].lower():
            continue
        row = dict(r)
        w = row["wallet"]
        own = bool(viewer and w and w.lower() == viewer.lower())
        if row["is_voter_wallet"] and not (is_admin or own):
            row["wallet_display"] = "Disamarkan"
        else:
            row["wallet_display"] = mask(w) if w else "-"
        row["wallet_full"] = w if (is_admin or own or not row["is_voter_wallet"]) else None
        row["waktu"] = datetime.fromtimestamp(row["timestamp"], config.TZ).strftime("%d %b %Y %H:%M:%S")
        out.append(row)
    return out


def participation_series(election_id: int) -> list[dict]:
    """Kumulatif suara masuk per jam. Hanya jumlah, tanpa alamat atau pilihan."""
    buckets = defaultdict(int)
    for r in _all_rows():
        if r["event"] == "VoteCast" and r["election_id"] == election_id:
            buckets[r["timestamp"] // 3600 * 3600] += 1
    cum, series = 0, []
    for ts in sorted(buckets):
        cum += buckets[ts]
        series.append({"waktu": datetime.fromtimestamp(ts, config.TZ), "per_jam": buckets[ts], "kumulatif": cum})
    return series


def recent(limit=8, viewer=None, is_admin=False):
    return list_transactions(viewer, is_admin)[:limit]
