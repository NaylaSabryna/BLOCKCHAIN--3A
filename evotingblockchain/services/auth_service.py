"""Otorisasi: bukti kepemilikan wallet lewat personal_sign dan pemeriksaan role di smart contract."""
import secrets
import time

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

import config
from services import blockchain as bc
from services.errors import PermissionDenied, ValidationError


def normalize_wallet(address: str) -> str:
    if not address or not Web3.is_address(address):
        raise ValidationError("Alamat wallet tidak valid.")
    return Web3.to_checksum_address(address)


def admin_challenge(address: str) -> dict:
    address = normalize_wallet(address)
    nonce = secrets.token_hex(16)
    issued = int(time.time())
    message = (
        "EVOTE - Autentikasi Panitia\n"
        f"Wallet: {address}\n"
        f"Kontrak: {bc.contract_address()}\n"
        f"Chain ID: {bc.expected_chain_id()}\n"
        f"Nonce: {nonce}\n"
        f"Waktu: {issued}\n"
        "Tanda tangan ini tidak mengirim transaksi dan tidak dikenai biaya."
    )
    return {"address": address, "nonce": nonce, "issued_at": issued, "message": message}


def recover_signer(message: str, signature: str) -> str:
    try:
        return Account.recover_message(encode_defunct(text=message), signature=signature)
    except Exception as exc:
        raise ValidationError("Tanda tangan tidak valid.") from exc


def verify_signature(message: str, signature: str, address: str) -> bool:
    try:
        return recover_signer(message, signature).lower() == address.lower()
    except ValidationError:
        return False


def is_panitia(address: str) -> bool:
    try:
        return bool(bc.get_contract().functions.isPanitia(normalize_wallet(address)).call())
    except Exception:
        return False


def require_panitia(address: str | None):
    if not address or not is_panitia(address):
        raise PermissionDenied("Akses ditolak: wallet ini bukan Panitia terotorisasi di smart contract.")


def verify_admin_login(challenge: dict, signature: str) -> str:
    """Mengembalikan alamat panitia bila tanda tangan sah, challenge belum kedaluwarsa, dan role cocok."""
    if not challenge or time.time() - challenge["issued_at"] > 300:
        raise ValidationError("Permintaan tanda tangan kedaluwarsa. Ulangi autentikasi.")
    if not verify_signature(challenge["message"], signature, challenge["address"]):
        raise PermissionDenied("Tanda tangan tidak cocok dengan wallet yang terhubung.")
    require_panitia(challenge["address"])
    return challenge["address"]
