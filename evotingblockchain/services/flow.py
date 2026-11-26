"""Rencana transaksi (plan) dan hook pasca-konfirmasi. Plan dibuat oleh layanan, ditandatangani
oleh MetaMask di browser, lalu hook dijalankan HANYA setelah receipt berstatus sukses."""
import importlib

HANDLERS = {}
_MODULES = ["services.election_service", "services.candidate_service", "services.voter_service",
            "services.voting_service", "services.audit_service"]


def after(name):
    
    def deco(fn):
        HANDLERS[name] = fn
        return fn
    return deco


def make_plan(label, request, after_name, payload=None, success=None):
    return {"label": label, "request": request, "after": after_name,
            "payload": payload or {}, "success": success or f"{label} berhasil dicatat di blockchain."}


def run_after(name, payload, receipt, actor):
    for m in _MODULES:
        importlib.import_module(m)
    fn = HANDLERS.get(name)
    if fn is None:
        raise KeyError(f"Hook pasca-transaksi tidak dikenal: {name}")
    return fn(payload, receipt, actor)
