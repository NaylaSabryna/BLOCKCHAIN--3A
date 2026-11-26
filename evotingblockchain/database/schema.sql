-- Skema SQLite EVOTE (data off-chain). Sumber kebenaran suara tetap blockchain.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Metadata periode (nama, waktu, status ada di blockchain; deskripsi ada di sini)
CREATE TABLE IF NOT EXISTS elections_meta (
    election_id  INTEGER PRIMARY KEY,
    description  TEXT NOT NULL DEFAULT '',
    created_by   TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Metadata kandidat. Kunci logis: (election_id, nomor_urut) selama status = 'aktif'.
CREATE TABLE IF NOT EXISTS candidates_meta (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id     INTEGER NOT NULL REFERENCES elections_meta(election_id) ON DELETE CASCADE,
    chain_cid       INTEGER NOT NULL,
    nomor_urut      INTEGER NOT NULL CHECK (nomor_urut > 0),
    nama            TEXT NOT NULL CHECK (length(trim(nama)) > 0),
    deskripsi       TEXT NOT NULL DEFAULT '',
    visi            TEXT NOT NULL DEFAULT '',
    misi            TEXT NOT NULL DEFAULT '',
    info_tambahan   TEXT NOT NULL DEFAULT '',
    foto_path       TEXT,
    foto_sha256     TEXT,
    metadata_hash   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'aktif' CHECK (status IN ('aktif','dihapus')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_cand_nomor_aktif
    ON candidates_meta(election_id, nomor_urut) WHERE status = 'aktif';
CREATE UNIQUE INDEX IF NOT EXISTS ux_cand_chain
    ON candidates_meta(election_id, chain_cid);

-- Daftar pemilih tetap (DPT) hasil impor CSV oleh panitia
CREATE TABLE IF NOT EXISTS voter_roster (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id   INTEGER NOT NULL REFERENCES elections_meta(election_id) ON DELETE CASCADE,
    custom_id     TEXT NOT NULL,
    nama          TEXT NOT NULL,
    kode_hash     TEXT NOT NULL,
    kode_terpakai INTEGER NOT NULL DEFAULT 0 CHECK (kode_terpakai IN (0,1)),
    gagal_verifikasi INTEGER NOT NULL DEFAULT 0,
    imported_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (election_id, custom_id)
);

CREATE TABLE IF NOT EXISTS registrations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id      INTEGER NOT NULL REFERENCES elections_meta(election_id) ON DELETE CASCADE,
    roster_id        INTEGER NOT NULL REFERENCES voter_roster(id),
    wallet           TEXT NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('menunggu','terverifikasi','ditolak')),
    signature        TEXT NOT NULL,
    submitted_at     TEXT NOT NULL DEFAULT (datetime('now')),
    decided_at       TEXT,
    decided_by       TEXT,
    alasan           TEXT,
    approve_tx_hash  TEXT
);
-- Satu wallet dan satu identitas hanya boleh punya satu registrasi aktif per periode
CREATE UNIQUE INDEX IF NOT EXISTS ux_reg_wallet_aktif
    ON registrations(election_id, wallet) WHERE status IN ('menunggu','terverifikasi');
CREATE UNIQUE INDEX IF NOT EXISTS ux_reg_roster_aktif
    ON registrations(election_id, roster_id) WHERE status IN ('menunggu','terverifikasi');

CREATE TABLE IF NOT EXISTS registration_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_id INTEGER NOT NULL REFERENCES registrations(id) ON DELETE CASCADE,
    status          TEXT NOT NULL,
    actor           TEXT,
    note            TEXT,
    at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    at          TEXT NOT NULL DEFAULT (datetime('now')),
    actor       TEXT,
    action      TEXT NOT NULL,
    election_id INTEGER,
    detail      TEXT,
    tx_hash     TEXT
);
