# BLOCKCHAIN tim A--3A

# 1. Konsep Utama: Kenapa E-Voting Pakai Blockchain?
Sistem pemilu tradisional sering dicurigai karena adanya risiko pengubahan data suara secara sepihak. Pada sistem ini:

Suara = Blok Data: Setiap suara yang masuk dibungkus dalam sebuah blok data yang berisi id pemilih, pilihan kandidat, lokasi, dan aktor pencatat.  


Permanen & Transparan: Begitu suara berhasil dicatat ke dalam blok, data tersebut tidak bisa dihapus atau diubah lagi.  


# 2. Bedah Struktur Kode (Garis Besar Logika)
block.py — Pembuat Cetakan Blok

__init__: Menentukan komponen penyusun blok, seperti nomor urut (index), waktu pencatatan (timestamp), isi suara/transaksi (data), dan identitas hash dari blok sebelumnya (previous_hash).  


calculate_hash(): Menggabungkan seluruh komponen di atas menjadi satu string teks, lalu mengacaknya menggunakan algoritma SHA-256.  


Prinsip: Ubah 1 karakter saja di dalam data (misal mengubah pilihan dari "Kandidat 01" jadi "Kandidat 02"), maka hasil karakter hash-nya akan berubah total (Avalanche Effect).  

blockchain.py — Pengelola Rantai & Validasi

create_genesis_block(): Membuat Blok 0 sebagai titik awal seluruh rantai suara karena belum ada blok sebelumnya.  


add_block(): Mengambil nilai hash dari blok paling akhir (chain[-1]), lalu memasukkannya ke kolom previous_hash milik blok baru. Mekanisme inilah yang membentuk rantai kriptografis (Hash Pointer).  


is_valid(): Fungsi pemeriksaan otomatis. Fungsi ini mengecek dua hal secara berurutan:  


Apakah isi data blok saat ini masih cocok dengan hasil kalkulasi ulang hash-nya?  


Apakah nilai previous_hash di blok saat ini sama persis dengan hash asli milik blok sebelumnya?  


main.py — Simulasi Eksekusi Transaksi Suara

Di sini kita mensimulasikan alur pemungutan suara nyata:  


Blok 0 (Genesis): Tanda pemilu dimulai.  


Blok 1 (Aktor 1 - Panitia KPU): Mendaftarkan dan memverifikasi identitas pemilih di TPS.  


Blok 2 (Aktor 2 - Pemilih): Pemilih memberikan suaranya untuk kandidat pilihan.  


Blok 3 (Aktor 3 - Saksi / Bawaslu): Pengawas independen mengesahkan bahwa suara telah masuk ke sistem secara sah.  


# 3. Mengapa Data Suara Tidak Bisa Dimanipulasi? (Tamper-Evident)
Bayangkan ada peretas yang masuk ke sistem dan mengubah isi suara pada Blok 2 agar kemenangan berpindah kandidat:  


Perubahan Terdeteksi: Begitu isi Blok 2 diubah, kalkulasi hash Blok 2 langsung berubah total.  


Koneksi Terputus: Blok 3 mencatat nilai previous_hash dari hash Blok 2 yang lama. Karena hash Blok 2 sudah berubah, sambungan rantai antara Blok 2 dan Blok 3 langsung terputus/rusak.  

Validasi Gagal: Saat fungsi is_valid() dijalankan, sistem langsung mengembalikan nilai False. Sistem otomatis menolak seluruh rantai yang telah dicurangi tersebut.  
