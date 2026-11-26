from database import db
from services import auth_service as auth
from services import blockchain as bc
from services.errors import ValidationError
from services.flow import make_plan

ZERO32 = b"\x00" * 32


def is_super_admin(addr: str) -> bool:
    return bool(bc.get_contract().functions.hasRole(ZERO32, auth.normalize_wallet(addr)).call())


def _role():
    return bc.get_contract().functions.PANITIA_ROLE().call()


def prepare_grant(sender, target):
    target = auth.normalize_wallet(target)
    if auth.is_panitia(target):
        raise ValidationError("Wallet tersebut sudah menjadi Panitia.")
    fn = bc.get_contract().functions.grantRole(_role(), target)
    return make_plan("Pemberian role Panitia", bc.prepare_tx(fn, sender), "audit_only",
                     {"action": "GRANT_PANITIA", "detail": target}, "Role Panitia diberikan.")


def prepare_revoke(sender, target):
    target = auth.normalize_wallet(target)
    if target.lower() == sender.lower():
        raise ValidationError("Anda tidak dapat mencabut role Panitia milik sendiri dari halaman ini.")
    if not auth.is_panitia(target):
        raise ValidationError("Wallet tersebut bukan Panitia.")
    fn = bc.get_contract().functions.revokeRole(_role(), target)
    return make_plan("Pencabutan role Panitia", bc.prepare_tx(fn, sender), "audit_only",
                     {"action": "REVOKE_PANITIA", "detail": target}, "Role Panitia dicabut.")


def panitia_members() -> list[str]:
    role = _role()
    granted = {e["args"]["account"] for e in bc.get_events("RoleGranted") if e["args"]["role"] == role}
    revoked = {e["args"]["account"] for e in bc.get_events("RoleRevoked") if e["args"]["role"] == role}
    return sorted(a for a in granted if a not in revoked or auth.is_panitia(a))


def db_counts() -> dict:
    with db.connect() as conn:
        return {t: conn.execute(f"SELECT COUNT(*) n FROM {t}").fetchone()["n"]
                for t in ("elections_meta", "candidates_meta", "voter_roster", "registrations", "audit_log")}
