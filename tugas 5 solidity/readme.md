# 🗳️ Sistem E-Voting Blockchain Jaringan Tertutup (Smart Contract)

Proyek ini merupakan implementasi *Smart Contract* untuk sistem **E-Voting Jaringan Tertutup (*Permissioned Blockchain*)** menggunakan bahasa pemrograman **Solidity**. Program ini dirancang untuk mensimulasikan alur pemungutan suara, verifikasi integritas data, rekapitulasi bertingkat, hingga penghitungan akhir secara aman dan transparan.

---

## 🛠️ Prasyarat
Untuk menjalankan *smart contract* ini, Anda tidak perlu menginstal environment khusus di komputer. Cukup gunakan browser dan akses **Remix IDE** (IDE berbasis web dari Ethereum).

---

## 🚀 Panduan Memulai & Pengujian di Remix IDE

### Langkah 1: Buka Remix IDE
1. Buka browser (Chrome, Firefox, atau Brave) dan kunjungi: [https://remix.ethereum.org](https://remix.ethereum.org).
2. Jika muncul tampilan awal atau pop-up selamat datang, klik **Accept** atau **Close**.

---

### Langkah 2: Buat File Smart Contract
1. Pada panel sebelah kiri (*File Explorer*), buka folder `contracts/`.
2. Klik ikon **New File** (kertas dengan tanda plus `+`).
3. Beri nama file: `EVotingBlockchain.sol` lalu tekan `Enter`.
4. Salin (*copy*) seluruh kode Solidity yang ada di repositori ini dan tempel (*paste*) ke dalam editor Remix.
5. Simpan file dengan menekan tombol `CTRL + S`.

---

### Langkah 3: Kompilasi Kode (*Compile*)
1. Klik menu **Solidity Compiler** di panel sebelah kiri (ikon berlogo Solidity `S`).
2. Pada opsi **Compiler**, pastikan menggunakan versi **`0.8.20`** (atau versi `0.8.x` lainnya).
3. Klik tombol biru **Compile EVotingBlockchain.sol**.
4. Jika kompilasi berhasil, akan muncul tanda centang hijau pada ikon menu sebelah kiri.

---

### Langkah 4: Deploy Contract ke Emulator
1. Klik menu **Deploy & Run Transactions** di panel sebelah kiri (ikon Ethereum dengan panah).
2. Pada bagian **Environment**, pilih **`Remix VM (Cancun)`** atau **`Remix VM (Shanghai)`** *(Emulator blockchain lokal berbasis browser)*.
3. Klik tombol oranye **Deploy**.
4. Pada panel **Deployed Contracts** di bagian bawah, klik panah kecil di samping nama `EVotingBlockchain` untuk membuka daftar fungsi interaktif.

---

## 🧪 Skenario Pengujian Fungsi (Menu 1 - 4)

> **Catatan:**
> * **Tombol Oranye:** Fungsi transaksi yang mengubah data di blockchain.
> * **Tombol Biru:** Fungsi *read-only* untuk membaca data tanpa biaya gas.

### 1. Inisialisasi TPS (`buatBatchSuara`)
* Buka formulir `buatBatchSuara` dengan mengklik panah kecil di samping tombolnya.
* Isi parameter berikut (pastikan kolom angka tidak dibiarkan kosong):
  * `_batchId`: `BATCH-001`
  * `_tpsLocation`: `TPS 01 - Wilayah A`
  * `_totalVoters`: `150`
  * `_voterId`: `VOTER-999`
  * `_candidateChoice`: `Paslon 01`
* Klik tombol **transact**.

### 2. Verifikasi Integritas Blok (`verifikasiLokal`)
* Klik tombol **verifikasiLokal**.
* Periksa log di bagian bawah Remix; sistem akan melakukan re-hashing data dan memancarkan *event* `LocalVerified`.

### 3. Rekapitulasi Bertingkat (`rekapitulasiBertingkat`)
* Klik tombol **rekapitulasiBertingkat**.
* Status blok pada rantai akan diperbarui menjadi `IN_RECAP` (Nilai Enum: `3`).

### 4. Penghitungan Akhir (`penghitunganAkhir`)
* Klik tombol **penghitunganAkhir**.
* Status blok akan bertransisi ke `FINAL_COUNT` lalu secara otomatis menjadi `FINISHED` (Nilai Enum: `5`).

---

## 🔍 Pemeriksaan Data (*Read-Only*)

* **Melihat Data Blok:** Klik tombol **`blockchain`**, masukkan angka `0` (indeks blok pertama), lalu klik **call**.
* **Melihat Track Record / History:** Klik tombol **`getHistory`**, masukkan ID Batch `"BATCH-001"`, lalu klik **call** untuk melihat seluruh catatan *log* perjalanan suara dari awal hingga selesai.
