Untuk mengisi kotak-kotak input (*form deployment* dan parameter fungsi) pada **Deployed Contract** dari smart contract `EVotingBlockchain` di atas (misalnya melalui Remix IDE), berikut adalah panduan lengkap berdasarkan tipe data dan alur fungsi yang tersedia:

---

### 1. Saat Deploy Contract (`constructor`)

Ketika Anda menekan tombol **Deploy** di Remix, kontrak ini **tidak memerlukan parameter tambahan** pada constructor karena nilai `name` dan `symbol` NFT sudah di-hardcode di dalam kontrak (`"EVotingBatchToken", "EVOTE"`).

* **Kotak Parameter Constructor:** Kosongkan atau abaikan, langsung klik **Deploy**.

---

### 2. Fungsi Utama (`buatBatchSuara`)

Fungsi ini digunakan oleh panitia (`contractOwner`) untuk membuat batch suara sekaligus melakukan *minting* NFT. Fungsi ini menerima **6 parameter** berurutan:

| Parameter | Tipe Data | Contoh Nilai / Cara Mengisi | Keterangan |
| --- | --- | --- | --- |
| `_batchId` | `string` | `"BATCH-TPS-001"` | ID unik untuk kelompok/batch suara. |
| `_tpsLocation` | `string` | `"TPS 01 Jakarta Selatan"` | Lokasi Tempat Pemungutan Suara. |
| `_totalVoters` | `uint256` | `150` | Total jumlah pemilih di TPS tersebut (angka bulat tanpa tanda kutip). |
| `_voterId` | `string` | `"VOTER-X992"` | ID pemilih atau representasi data pemilih. |
| `_candidateChoice` | `string` | `"Paslon 01"` | Pilihan kandidat atau suara yang dimasukkan. |
| `_metadataURI` | `string` | `"ipfs://QmYourMetadataHashHere"` | Link URI metadata NFT (misalnya dari IPFS / JSON metadata). |

---

### 3. Fungsi View / Query Riwayat (`getHistory`)

Jika Anda ingin melihat riwayat (*history logs*) dari suatu batch suara yang sudah dibuat, fungsi ini memerlukan 1 parameter:

| Parameter | Tipe Data | Contoh Nilai / Cara Mengisi |
| --- | --- | --- |
| `_batchId` | `string` | `"BATCH-TPS-001"` (harus sama persis dengan yang diinput saat `buatBatchSuara`) |

---

### 4. Fungsi Pengecekan Pemilik NFT (`getBatchOwner`)

Untuk mengecek alamat dompet pemilik NFT berdasarkan ID tokennya:

| Parameter | Tipe Data | Contoh Nilai / Cara Mengisi |
| --- | --- | --- |
| `_tokenId` | `uint256` | `1` (karena token ID pertama dimulai dari angka `1`, lalu `2`, dst.) |

---

### 5. Fungsi Tanpa Parameter (Eksekusi Langsung)

Fungsi-fungsi berikut **tidak memerlukan input parameter apa pun**, sehingga Anda bisa langsung mengkliknya di antarmuka Remix:

* **`verifikasiLokal()`**: Mengecek integritas blok suara terakhir di blockchain.
* **`rekapitulasiBertingkat()`**: Mengubah status blok terakhir ke tahap rekapitulasi.
* **`penghitunganAkhir()`**: Menyelesaikan proses hitung akhir dan mengubah status menjadi sah (`FINISHED`).
* **`getBlockchainLength()`**: Melihat total jumlah blok yang sudah tercatat di blockchain.

---

### 💡 Tips Alur Pengujian di Remix IDE:

1. Pastikan Anda menggunakan akun Ethereum pertama (sebagai `contractOwner` / Panitia).
2. Panggil fungsi **`buatBatchSuara`** terlebih dahulu dengan mengisi data-data di atas.
3. Setelah berhasil, jalankan **`verifikasiLokal`** $\rightarrow$ **`rekapitulasiBertingkat`** $\rightarrow$ **`penghitunganAkhir`** secara berurutan untuk mensimulasikan siklus hidup e-voting.
