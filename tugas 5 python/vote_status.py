from enum import Enum


class VoteStatus(Enum):
  CREATED = 1  # Kotak suara TPS dibuka
  VOTED = 2  # Pemilih telah memberikan suara
  VERIFIED_LOCAL = 3  # Suara divalidasi oleh Otoritas TPS (Jaringan Tertutup)
  IN_RECAP = 4  # Dalam proses rekapitulasi bertingkat
  FINAL_COUNT = 5  # Masuk ke penghitungan akhir
  FINISHED = 6  # Proses selesai & sah