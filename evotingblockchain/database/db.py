import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import config

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


@contextmanager
def connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    get_salt()


def get_setting(key, default=None):
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with connect() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value)))


def get_salt() -> str:
    """Garam rahasia server untuk hash kredensial. Dibuat acak sekali, tidak pernah di-hardcode."""
    salt = get_setting("credential_salt")
    if not salt:
        salt = secrets.token_hex(32)
        set_setting("credential_salt", salt)
    return salt


def audit(actor, action, election_id=None, detail=None, tx_hash=None):
    with connect() as conn:
        conn.execute(
            "INSERT INTO audit_log(actor, action, election_id, detail, tx_hash) VALUES(?,?,?,?,?)",
            (actor, action, election_id, detail, tx_hash))


def recent_audit(limit=100):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))]
