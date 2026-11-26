"""Penyimpanan foto kandidat di server (bukan di smart contract)."""
import base64
import hashlib
import io
from functools import lru_cache

from PIL import Image, UnidentifiedImageError

import config
from services.errors import ValidationError


def save_candidate_photo(election_id: int, data: bytes, filename: str) -> tuple[str, str]:
    """Validasi, normalisasi (hapus metadata EXIF, ubah ukuran), lalu simpan. Mengembalikan (path_relatif, sha256)."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in config.ALLOWED_PHOTO_EXT:
        raise ValidationError("Format foto harus JPG, JPEG, atau PNG.")
    if len(data) > config.MAX_PHOTO_BYTES:
        raise ValidationError(f"Ukuran foto maksimal {config.MAX_PHOTO_BYTES // (1024 * 1024)} MB.")
    if not data:
        raise ValidationError("File foto kosong.")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        if img.format not in ("JPEG", "PNG"):
            raise ValidationError("Isi file bukan gambar JPG atau PNG yang valid.")
        img = img.convert("RGB")
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValidationError("File tidak dapat dibaca sebagai gambar yang valid.") from exc
    img.thumbnail((config.MAX_PHOTO_SIDE, config.MAX_PHOTO_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    out = buf.getvalue()
    digest = hashlib.sha256(out).hexdigest()
    folder = config.UPLOAD_DIR / str(election_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{digest[:20]}.jpg"
    path.write_bytes(out)
    return f"{election_id}/{path.name}", digest


@lru_cache(maxsize=256)
def _read_uri(rel: str, mtime: float) -> str:
    raw = (config.UPLOAD_DIR / rel).read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()


def photo_uri(rel: str | None, name: str = "") -> str:
    """Data URI foto bila ada dan valid; jika tidak, placeholder SVG berinisial."""
    if rel:
        p = (config.UPLOAD_DIR / rel).resolve()
        if config.UPLOAD_DIR.resolve() in p.parents and p.exists():
            return _read_uri(rel, p.stat().st_mtime)
    return placeholder_uri(name)


def placeholder_uri(name: str) -> str:
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 400'>"
        "<rect width='400' height='400' fill='#E2E8F0'/>"
        "<circle cx='200' cy='160' r='70' fill='#94A3B8'/>"
        "<path d='M60 400c0-86 62-150 140-150s140 64 140 150z' fill='#94A3B8'/>"
        "</svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
