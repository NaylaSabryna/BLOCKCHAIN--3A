# EVOTE - Decentralized Electronic Voting System

Aplikasi pemungutan suara digital berbasis blockchain (prototipe akademik). Mendukung banyak periode pemilihan,
kandidat dinamis dengan unggah foto, registrasi pemilih mandiri dengan verifikasi panitia, voting yang
ditandatangani langsung di MetaMask, hasil langsung, dan audit rantai hash.

Teknologi: Python, Streamlit, Solidity 0.8.28 (OpenZeppelin AccessControl), Hardhat, Web3.py, MetaMask, Plotly, SQLite, ikon Lucide.

## 1. Prasyarat

- Node.js 18 atau lebih baru dan npm (diuji Node 22)
- Python 3.10 atau lebih baru (diuji 3.12)
- Browser dengan ekstensi MetaMask
- Koneksi internet saat `npm install` dan compile pertama (Hardhat mengunduh kompiler Solidity 0.8.28)

## 2. Instalasi

```bash
npm install
py -3.12 -m pip install -r requirements.txt
npm run compile          # membuat artifacts/ (ABI) yang dibaca aplikasi
```

## 3. Menjalankan (tiga terminal)

```bash
# Terminal 1: blockchain lokal (biarkan berjalan)
npm run node

# Terminal 2: deploy kontrak, menulis deployment.json
npm run deploy

# Terminal 3: aplikasi (Windows PowerShell)
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
streamlit run app.py
```

Buka http://localhost:8501.

Setiap kali Terminal 1 dimulai ulang, seluruh data blockchain hilang. Jalankan `npm run deploy` lagi dan hapus
`data/evote.db` serta `data/uploads/` agar metadata off-chain tidak merujuk periode yang sudah tidak ada.

## 4. Konfigurasi MetaMask

1. Tambahkan jaringan: nama `Hardhat Localhost`, RPC `http://127.0.0.1:8545`, Chain ID `31337`, simbol `ETH`.
   (Atau klik "Pindah ke jaringan EVOTE" di aplikasi.)
2. Impor akun uji dari daftar akun yang dicetak `npm run node` (Account #0 sampai #19).
   Kunci tersebut publik dan hanya untuk jaringan lokal. Jangan pernah dipakai di jaringan sungguhan.
3. **Account #0 adalah Panitia pertama** (pengirim deploy mendapat role `PANITIA_ROLE` dan `DEFAULT_ADMIN_ROLE`).
   Gunakan akun #1, #2, dan seterusnya sebagai pemilih. Panitia tambahan dapat diberi role di menu Pengaturan Sistem.

## 5. Alur penggunaan

**Panitia** (pilih area "Panitia", hubungkan wallet, tanda tangani pesan login):

1. Manajemen Periode: buat periode (nama, deskripsi, jadwal WIB). Status awal Draft. Waktu mulai minimal 2 menit ke depan.
2. Manajemen Kandidat: tambah kandidat (nomor urut, nama, foto JPG/PNG maks 2 MB, deskripsi, visi, misi). Minimal 2 kandidat.
3. Manajemen Pemilih: impor DPT dari CSV (`custom_id,nama` dan opsional `kode_registrasi`). Kode sekali pakai
   dibuat otomatis bila kolom kode kosong dan **hanya ditampilkan satu kali**; bagikan ke pemilih secara aman.
4. Pengaturan Pemilihan: publikasikan periode.
5. Setelah pemilih mendaftar: Manajemen Pemilih, setujui (transaksi MetaMask mencatat hak memilih on-chain) atau tolak dengan alasan.
6. Setelah waktu berakhir: finalisasi hasil (checkpoint audit dibuat otomatis). Rekapitulasi Suara untuk checkpoint tambahan, Blockchain Audit untuk verifikasi.

**Pemilih**: Verifikasi Pemilih, tab Registrasi (Custom ID, kode, tanda tangan wallet), tunggu persetujuan, lalu Pemungutan Suara
saat periode berlangsung. Tombol voting hanya aktif bila seluruh syarat terpenuhi.

## 6. Verifikasi identitas

Custom ID yang diketik sendiri **tidak** membuktikan identitas. Verifikasi dilakukan dengan tiga lapis:

1. Custom ID dan kode registrasi harus cocok dengan DPT yang diimpor panitia (kode disimpan sebagai hash bergaram; 5 kali salah mengunci baris sampai panitia mengatur ulang kode).
2. Pemilih menandatangani permohonan dengan wallet (`personal_sign`) sebagai bukti kepemilikan wallet.
3. Panitia menyetujui, dan baru saat itu hak memilih tercatat di smart contract. Satu identitas hanya dapat dipakai satu wallet per periode (dijaga di database dan di kontrak lewat hash kredensial bergaram).

Kekuatan verifikasi identitas bergantung pada kualitas DPT dan cara kode dibagikan. Aplikasi ini tidak melakukan verifikasi dokumen/KTP.

## 7. Arsitektur singkat

- **Smart contract** `contracts/EVotingBlockchain.sol`: periode, kandidat, hak memilih, `vote`, tally, finalisasi, checkpoint audit (rantai hash), `AccessControl`.
- **Penandatanganan**: Python hanya menyiapkan transaksi (simulasi dahulu agar revert terdeteksi). MetaMask menandatangani dan mengirim di browser.
  Aplikasi menunggu receipt dan hanya menganggap sukses bila `status == 1`. Tidak ada kunci privat di kode.
- **Otorisasi Panitia**: wallet terhubung, tanda tangan `personal_sign` atas challenge acak (berlaku 5 menit), dan pemeriksaan `hasRole` di kontrak.
  Sesi hilang bila akun MetaMask berganti. Setiap fungsi admin di kontrak tetap dijaga `onlyRole`.
- **Basis data SQLite** (`data/evote.db`): DPT, registrasi dan riwayatnya, metadata kandidat, deskripsi periode, audit log. Hasil suara tidak pernah bersumber dari database.
  Hash metadata kandidat/periode disimpan on-chain sehingga perubahan diam-diam di database terdeteksi (peringatan di Manajemen Kandidat).
- **Foto kandidat**: divalidasi, dinormalisasi (metadata EXIF dibuang, maks 800 px), disimpan di `data/uploads/candidates/`.

### Fungsi audit lama yang dipertahankan

| Fungsi lama | Perilaku baru |
|---|---|
| `buatBatchSuara` | `buatBatchSuara(periode, batchId, catatan)`: checkpoint snapshot tally (hash dihitung on-chain), Batch ID unik global |
| `verifikasiLokal` | `verifikasiLokal(index)`: hanya Panitia, memeriksa blok mana pun beserta tautan ke blok sebelumnya, kegagalan tidak di-revert sehingga tercatat |
| `rekapitulasiBertingkat` / `penghitunganAkhir` | Per blok (bukan hanya blok terakhir) dengan urutan status yang divalidasi; penghitungan akhir mensyaratkan periode final |
| `getHistory`, `getBlockchainLength` | Tetap ada. Tambahan: `cekIntegritasRantai`, `getBlock`, `getBlockIndexByBatchId` |

NFT per batch tidak dipertahankan karena tidak relevan bagi voting individual. Hash memakai `abi.encode` (bukan `encodePacked`).

## 8. Privasi suara dan keterbatasan (PENTING)

**Ini adalah mode prototipe transparan, bukan secret ballot.**

- Transaksi `vote(periode, kandidat)` bersifat publik. Siapa pun dapat membaca calldata transaksi dari node dan mengetahui
  pilihan suatu alamat wallet. Aplikasi tidak menampilkannya, kontrak tidak menyimpan pemetaan wallet ke kandidat dan event `VoteCast` tidak memuat kandidat,
  tetapi ini tidak mengubah fakta bahwa calldata terbuka.
- Data identitas (Custom ID, nama) tidak pernah masuk blockchain. Hanya alamat wallet dan hash kredensial bergaram. Namun panitia yang memegang DPT dan registrasi dapat memetakan identitas ke wallet,
  sehingga dengan calldata publik, panitia (atau siapa pun yang mendapat DB) dapat menyimpulkan pilihan.
- Riwayat transaksi di aplikasi menyamarkan alamat pemilih bagi publik. Ini hanya pembatasan tampilan; data on-chain tetap terbuka.
- Untuk secret ballot sungguhan perlu anonymous credentials / zero-knowledge (misalnya Semaphore) atau tally terenkripsi dengan dekripsi ambang. Itu di luar cakupan prototipe ini.

Keterbatasan lain:

- Satu admin kunci tunggal pada jaringan lokal; tidak ada pemulihan jika wallet Panitia hilang.
- Tidak ada verifikasi dokumen identitas; kualitas DPT menentukan keabsahan pemilih.
- "Nonaktifkan kandidat" diimplementasikan sebagai Hapus (arsip) sebelum pemilihan dimulai; setelah mulai kandidat terkunci.
- Registrasi yang ditolak dapat diajukan ulang; kode dipulihkan agar pemilih tidak terkunci permanen.
- Riwayat transaksi hanya memuat transaksi berhasil (event kontrak); transaksi yang revert tidak menghasilkan event.
- Block explorer tidak tersedia di jaringan lokal (diatur lewat `EVOTE_EXPLORER` untuk jaringan lain).
- Font Inter dimuat dari Google Fonts dan memakai font sistem bila offline.
- Redeployment kontrak menghasilkan alamat dan state baru; data periode lama di node hilang bila node lokal dimulai ulang.

## 9. Pengujian

```bash
npm test                         # 17 uji smart contract (Hardhat/chai)
npm run node                     # terminal lain
pytest                           # layanan Python (deploy ke file sementara; tidak mengubah deployment.json Anda)
```

`pytest` memuat: otorisasi dan login tanda tangan, periode, kandidat dan foto, DPT, registrasi, voting, double voting,
privasi riwayat, finalisasi, audit, serta smoke test render seluruh 16 halaman dan larangan emoji.
Pada Windows jalankan `npx` melalui `npx.cmd` bila `pytest` gagal menemukan `npx`.

## 10. Struktur folder

```
app.py                  titik masuk Streamlit dan router
pages/                  halaman pemilih dan Panitia
components/             sidebar, wallet (MetaMask), tx_flow, kartu, badge, grafik, ikon
services/               blockchain, periode, kandidat, pemilih, voting, hasil, audit, transaksi
database/               schema.sql, db.py
styles/main.css         design system
assets/icons/           ikon Lucide (ISC)
contracts/ scripts/     Solidity dan deploy.js
tests/                  Hardhat (JS) dan pytest
data/                   evote.db dan foto (dibuat otomatis, tidak di-commit)
```

## 11. Pemecahan masalah

| Gejala | Penyebab dan solusi |
|---|---|
| Halaman "Blockchain tidak tersedia" | `npm run node` belum berjalan, atau belum `npm run deploy` |
| "Tidak ada kontrak pada alamat deployment" | Node dimulai ulang; jalankan `npm run deploy` lagi |
| Tombol wallet "MetaMask tidak ditemukan" | Ekstensi belum terpasang, atau buka lewat `localhost` pada browser dengan MetaMask aktif |
| Transaksi gagal di MetaMask | Reset akun pada Pengaturan, Lanjutan, Hapus data tab aktivitas setelah node dimulai ulang (nonce) |
| Tidak dapat membuat periode | Waktu mulai harus minimal 2 menit dari sekarang |
