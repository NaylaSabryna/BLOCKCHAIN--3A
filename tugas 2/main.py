from blockchain import Blockchain

# Inisialisasi Blockchain E-Voting
evoting_chain = Blockchain()
# --- FILE main.py ---

# Aktor 1: Panitia / Admin Pemilu (Registrasi Pemilih / Inisialisasi)
evoting_chain.add_block({
    "election_id": "PILKADA-2026",
    "voter_id": "VOTER-101",
    "candidate_choice": "Kandidat 01",
    "actor": "Panitia KPU (Registrasi & Verifikasi Surat Suara)",
    "location": "TPS 01 - Cirebon"
})

# Aktor 2: Pemilih (Proses Pemungutan Suara Utama)
evoting_chain.add_block({
    "election_id": "PILKADA-2026",
    "voter_id": "VOTER-102",
    "candidate_choice": "Kandidat 02",
    "actor": "Pemilih Terverifikasi",
    "location": "TPS 01 - Cirebon"
})

# Aktor 3: Saksi / Pengawas Independen (Validasi & Audit Suara Sukses Masuk)
evoting_chain.add_block({
    "election_id": "PILKADA-2026",
    "voter_id": "VOTER-103",
    "candidate_choice": "Kandidat 01",
    "actor": "Saksi Bawaslu / Audit Independen",
    "location": "TPS 02 - Kuningan"
})

# Cetak isi seluruh rantai blok
for block in evoting_chain.chain:
    print("=" * 50)
    print("INDEX        :", block.index)
    print("TIMESTAMP    :", block.timestamp)
    print("DATA         :", block.data)
    print("PREV HASH    :", block.previous_hash)
    print("CURRENT HASH :", block.hash)


# Validasi Integritas Blockchain
print("\n" + "=" * 50)
print("Apakah Hasil E-Voting Valid & Bebas Manipulasi?:", evoting_chain.is_valid())
print("=" * 50)

