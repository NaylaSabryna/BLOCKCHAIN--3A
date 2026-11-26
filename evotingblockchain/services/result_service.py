import time

from services import blockchain as bc
from services import candidate_service as cs
from services import election_service as es


def get_results(election_id: int) -> dict | None:
    """Hasil dibaca langsung dari tally on-chain (hanya transaksi yang sudah terkonfirmasi)."""
    e = es.get_election(election_id)
    if not e:
        return None
    ids, nomor, active, votes = bc.get_contract().functions.getResults(election_id).call()
    meta = {c["cid"]: c for c in cs.list_candidates(election_id, include_inactive=True)}
    rows = []
    for cid, no, act, v in zip(ids, nomor, active, votes):
        if not act:
            continue
        rows.append({"cid": cid, "nomor": no, "nama": meta.get(cid, {}).get("nama", f"Kandidat {no}"), "suara": int(v)})
    rows.sort(key=lambda r: r["nomor"])
    total = sum(r["suara"] for r in rows)
    for r in rows:
        r["persen"] = round(r["suara"] * 100 / total, 2) if total else 0.0
    top = max((r["suara"] for r in rows), default=0)
    leaders = [r for r in rows if r["suara"] == top and top > 0]
    final = e["state"] == es.STATE_FINALIZED
    registered = e["approved_voters"]
    return {
        "election": e, "rows": rows, "total_votes": total, "valid_votes": total,
        "candidates": len(rows), "registered": registered,
        "participation": round(total * 100 / registered, 2) if registered else 0.0,
        "leaders": leaders, "is_final": final,
        "label": "Hasil Final" if final else "Hasil Sementara",
        "updated_at": int(time.time()),
        "tie": len(leaders) > 1,
    }
