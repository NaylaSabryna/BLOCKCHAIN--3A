from html import escape

from components.icons import svg

TONES = {
    # periode
    "Draft": "neutral", "Belum Dimulai": "info", "Sedang Berlangsung": "success",
    "Selesai": "neutral", "Dibatalkan": "danger",
    # pemilih
    "Belum Terdaftar": "neutral", "Menunggu Verifikasi": "warning", "Terverifikasi": "success",
    "Ditolak": "danger", "Wallet Belum Terhubung": "neutral", "Wallet Terhubung": "success",
    "Belum Memilih": "info", "Sudah Memilih": "success", "Tidak Memenuhi Syarat": "danger",
    "Memenuhi Syarat": "success",
    # transaksi / umum
    "Berhasil": "success", "Gagal": "danger", "Dibatalkan Pengguna": "warning",
    "Menunggu Persetujuan Wallet": "warning", "Transaksi Sedang Diproses": "info",
    "Menunggu Konfirmasi Blockchain": "info", "Valid": "success", "Tidak Valid": "danger",
    "Terhubung": "success", "Terputus": "danger", "Hasil Sementara": "warning", "Hasil Final": "success",
    "Dibuat": "info", "Terverifikasi Lokal": "success", "Dalam Rekapitulasi": "info",
    "Penghitungan Akhir": "info", "Aktif": "success", "Arsip": "neutral",
}
ICONS = {"success": "circle-check", "warning": "clock", "danger": "x", "info": "info", "neutral": "info"}


def status_badge(label: str, tone: str | None = None, icon: bool = False) -> str:
    tone = tone or TONES.get(label, "neutral")
    ico = svg(ICONS[tone], 13) if icon else ""
    return f'<span class="ev-badge {tone}">{ico}{escape(label)}</span>'
