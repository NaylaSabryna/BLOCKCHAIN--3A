# Sistem E-Voting Blockchain berbasis Smart Contract & Tokenisasi (ERC-721)

Proyek ini merupakan implementasi *smart contract* E-Voting Jaringan Tertutup yang dikembangkan menggunakan bahasa pemrograman **Solidity (v0.8.20)**. Sistem ini mengintegrasikan fungsi pencatatan blok suara terenkripsi dengan standar token **ERC-721 (NFT)** dari OpenZeppelin sebagai sertifikat digital bukti kepemilikan kotak suara/batch TPS secara *on-chain*.

---

## 🏗️ Fitur Utama

- **Pencatatan Blok Suara (*On-Chain*)**: Menyimpan data pemungutan suara, lokasi TPS, ID pemilih, serta pilihan kandidat secara aman.
- **Integritas Data via Hashing**: Menggunakan algoritma cryptographic hash `keccak256` untuk memastikan setiap blok suara terhubung dan tidak dapat dimanipulasi.
- **Tokenisasi Batch TPS (ERC-721)**: Menggenerasi NFT otomatis untuk setiap batch suara TPS yang dibuat sebagai bukti digital hak akses/keabsahan panitia.
- **Verifikasi & Rekapitulasi Bertingkat**: Mendukung alur kerja pemilu mulai dari verifikasi lokal TPS, rekapitulasi bertingkat, hingga penghitungan akhir.
- **Audit Trail & Logging History**: Mencatat seluruh riwayat perubahan status batch suara yang dapat dilacak secara transparan (*read-only*).

---

## 🛠️ Prasyarat & Teknologi

- **Solidity Compiler**: `^0.8.20`
- **Pustaka OpenZeppelin**: `@openzeppelin/contracts` (Modul ERC721 & ERC721URIStorage)
- **Lingkungan Pengujian**: [Remix IDE](https://remix.ethereum.org/)

---

## 🚀 Panduan Penggunaan di Remix IDE

### 1. Kompilasi Kontrak (*Compile*)
1. Buka [Remix IDE](https://remix.ethereum.org/).
2. Buat file baru bernama `EVotingBlockchain.sol` di dalam folder `contracts/`.
3. Tempelkan seluruh kode *smart contract* ke dalam file tersebut.
4. Buka tab **Solidity Compiler** di panel sebelah kiri.
5. Pilih versi **0.8.20** atau yang lebih baru, lalu klik **Compile EVotingBlockchain.sol**.

### 2. Penyebaran Kontrak (*Deploy*)
1. Masuk ke tab **Deploy & Run Transactions**.
2. Pilih **ENVIRONMENT** (misalnya *Remix VM (Cancun)*).
3. Pilih kontrak `EVotingBlockchain`.
4. Langsung klik tombol **Deploy** (tanpa mengisi parameter awal).

---

## 📑 Panduan Pengisian Parameter Fungsi

Setelah berhasil di-*deploy*, buka opsi fungsi di panel **Deployed Contracts**:

### 1. `buatBatchSuara` (Mencetak Blok Suara & Mint NFT)
Fungsi ini digunakan oleh panitia untuk membuka kotak suara TPS baru dan mencetak NFT batch.

| Nama Parameter | Tipe Data | Contoh Isian di Remix | Keterangan |
| :--- | :--- | :--- | :--- |
| `_batchId` | `string` | `"BATCH-TPS01"` | ID Unik untuk batch suara |
| `_tpsLocation` | `string` | `"TPS 01 Desa Sukamaju"` | Lokasi atau alamat TPS |
| `_
