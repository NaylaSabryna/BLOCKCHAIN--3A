"""Konfigurasi pusat EVOTE. Semua nilai dapat dioverride lewat environment variable."""
import os
from datetime import timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

RPC_URL = os.environ.get("EVOTE_RPC_URL", "http://127.0.0.1:8545")
DEPLOYMENT_PATH = Path(os.environ.get("EVOTE_DEPLOYMENT", BASE_DIR / "deployment.json"))
ARTIFACT_PATH = Path(os.environ.get(
    "EVOTE_ARTIFACT",
    BASE_DIR / "artifacts" / "contracts" / "EVotingBlockchain.sol" / "EVotingBlockchain.json",
))
DB_PATH = Path(os.environ.get("EVOTE_DB", BASE_DIR / "data" / "evote.db"))
UPLOAD_DIR = Path(os.environ.get("EVOTE_UPLOADS", BASE_DIR / "data" / "uploads" / "candidates"))
ICON_DIR = BASE_DIR / "assets" / "icons"
CSS_PATH = BASE_DIR / "styles" / "main.css"

TZ = timezone(timedelta(hours=7))
TZ_LABEL = "WIB"

MAX_PHOTO_BYTES = 2 * 1024 * 1024
ALLOWED_PHOTO_EXT = {"jpg", "jpeg", "png"}
MAX_PHOTO_SIDE = 800

MIN_START_LEAD_SECONDS = 120          # waktu mulai minimal 2 menit dari sekarang
ADMIN_SESSION_SECONDS = 2 * 3600
MAX_REG_ATTEMPTS = 5

CHAIN_NAME = "Hardhat Localhost"
CURRENCY_SYMBOL = "ETH"
BLOCK_EXPLORER_URL = os.environ.get("EVOTE_EXPLORER", "")  # kosong pada jaringan lokal
