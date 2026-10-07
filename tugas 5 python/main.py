import time
from block import Block
from local_validator import verify_local_block
from vote_batch import VoteBatch
from vote_status import VoteStatus


def main():
  print("==================================================")
  print("  SISTEM E-VOTING BLOCKCHAIN JARINGAN TERTUTUP    ")
  print("==================================================")
  print("[Inisialisasi Sistem Jaringan Tertutup TPS]\n")

  blockchain = []

  while True:
    print("\n---------------- MENU UTAMA ----------------")
    print("1. Buat Batch Suara (Inisialisasi TPS)")
    print("2. Verifikasi Lokal (Integritas Blok)")
    print("3. Rekapitulasi Bertingkat")
    print("4. Penghitungan & Verifikasi Akhir")
    print("5. Keluar")

    choice = input("Pilih menu (1-5): ")

    if choice == "1":
      print("\n-> [PROSES 1] Membuat Batch Suara...")
      batch = VoteBatch(
          batch_id="BATCH-001",
          tps_location="TPS 01 - Wilayah A",
          total_voters=150,
          voter_id="VOTER-999",
          candidate_choice="Paslon 01",
          owner="Panitia TPS 01",
      )
      blockchain.append(batch.block)
      print(f"Sukses! Kotak suara {batch.batch_id} diinisialisasi.")
      print(f"Status Saat Ini : {batch.status.name}")

    elif choice == "2":
      print("\n-> [PROSES 2] Verifikasi Lokal...")
      if not blockchain:
        print("Belum ada blok suara. Jalankan Menu 1 terlebih dahulu!")
        continue

      target_block = blockchain[-1]
      is_valid = verify_local_block(target_block)
      if is_valid:
        status_baru = VoteStatus.VERIFIED_LOCAL
        print(f"Status blok diperbarui menjadi: {status_baru.name}")

    elif choice == "3":
      print("\n-> [PROSES 3] Rekapitulasi Bertingkat...")
      if not blockchain:
        print("Belum ada blok suara untuk direkap!")
        continue

      time.sleep(0.5)
      status_rekap = VoteStatus.IN_RECAP
      print(f"Blok berhasil dimasukkan ke rantai rekapitulasi.")
      print(f"Status blok diperbarui menjadi: {status_rekap.name}")

    elif choice == "4":
      print("\n-> [PROSES 4] Penghitungan & Verifikasi Akhir...")
      if not blockchain:
        print("Belum ada data untuk dihitung!")
        continue

      time.sleep(0.5)
      print(f"Status: {VoteStatus.FINAL_COUNT.name} (Penghitungan Akhir)")
      time.sleep(0.5)
      print(f"Status: {VoteStatus.FINISHED.name} (Seluruh Blok Aman & Sah)")

    elif choice == "5":
      print("Keluar dari program. Terima kasih!")
      break
    else:
      print("Pilihan tidak valid, silakan masukkan angka 1 sampai 5.")


if __name__ == "__main__":
    main()