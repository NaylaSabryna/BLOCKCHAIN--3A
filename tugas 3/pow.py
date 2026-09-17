import hashlib
import time


def proof_of_work(block, difficulty):
  target = "0" * difficulty
  start_time = time.time()

  while not block.hash.startswith(target):
    block.nonce += 1
    block.hash = hashlib.sha256(
        f"{block.index}{block.data}{block.previous_hash}{block.nonce}".encode()
    ).hexdigest()

  end_time = time.time()
  print("Mining Suara Selesai!")
  print(f"Nonce Ditemukan: {block.nonce}")
  print(f"Waktu Proses   : {end_time - start_time:.4f} detik")