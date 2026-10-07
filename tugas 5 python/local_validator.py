import time
from block import Block


def verify_local_block(block: Block) -> bool:
  print("[Jaringan Tertutup] Memverifikasi integritas blok suara...")
  time.sleep(0.4)

  current_hash = block.calculate_hash()
  if block.hash == current_hash:
    print("✓ Verifikasi Lokal Sukses! Blok suara sah dan tidak berubah.")
    return True
  else:
    print("✗ Verifikasi Gagal! Terdeteksi perubahan data pada blok.")
    return False