"""Ikon Lucide (lisensi ISC) dimuat dari assets/icons sebagai SVG inline."""
import base64
import re
from functools import lru_cache

import config


@lru_cache(maxsize=None)
def _raw(name: str) -> str:
    path = config.ICON_DIR / f"{name}.svg"
    if not path.exists():
        path = config.ICON_DIR / "info.svg"
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    # Satu baris tanpa indentasi: Markdown Streamlit memotong HTML multibaris yang berindentasi.
    return re.sub(r"\s+", " ", text).replace("> <", "><").strip()


def svg(name: str, size: int = 18, cls: str = "") -> str:
    raw = _raw(name)
    raw = re.sub(r'\s(width|height|class)="[^"]*"', "", raw, count=3)
    return raw.replace("<svg", f'<svg width="{size}" height="{size}" class="{cls}" aria-hidden="true"', 1)


def mask_uri(name: str) -> str:
    raw = _raw(name).replace("currentColor", "black")
    return "data:image/svg+xml;base64," + base64.b64encode(raw.encode()).decode()


def nav_icon_css(mapping: dict[str, str]) -> str:
    """mapping: key tombol Streamlit -> nama ikon. Menghasilkan CSS ikon pada tombol navigasi."""
    return "\n".join(
        f'.st-key-{key} button {{ --ico: url("{mask_uri(icon)}"); }}' for key, icon in mapping.items())
