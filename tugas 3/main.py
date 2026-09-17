from block import Block
from pos import proof_of_stake
from pow import proof_of_work

print("=== SIMULASI PROOF OF WORK (PoW) PADA E-VOTING ===")
# Data suara dari pemilih yang akan dimasukkan ke dalam blok
vote_data = {"voter_id": "ID_PEMILIH_001", "candidate_choice": "Kandidat 02"}
block_vote = Block(index=1, data=vote_data, previous_hash="0")

difficulty = 5
print(f"\nData Suara Masuk  : {block_vote.data}")
print(f"Target Difficulty : {difficulty}")

proof_of_work(block_vote, difficulty)
print(f"Nonce             : {block_vote.nonce}")
print(f"Hash Blok Suara   : {block_vote.hash}")

print("\n" + "=" * 50 + "\n")

print("=== SIMULASI PROOF OF STAKE (PoS) PEMILIHAN VALIDATOR TPS ===")
# Representasi bobot stake saksi/panitia pemilu terdesentralisasi
validators = {
    "Panitia_Pusat": 70,
    "Saksi_Kandidat_1": 10,
    "Saksi_Kandidat_2": 10,
    "Node_Independent_KPU": 10,
}

print("\nDaftar Node Validator & Stake:")
for validator, stake in validators.items():
  print(f"- {validator}: {stake} Stake")

selected = proof_of_stake(validators)
print(f"\nValidator Terpilih untuk Memvalidasi Blok Suara: {selected}")