from html import escape

from services import storage_service as storage


def candidate_card_html(c: dict) -> str:
    photo = storage.photo_uri(c.get("foto_path"), c["nama"])
    desc = c.get("deskripsi") or "Belum ada deskripsi."
    vision = (c.get("visi") or "").strip()
    short = (vision[:110] + "...") if len(vision) > 110 else vision
    vis_html = f'<p class="ev-cand-vision"><span>Visi:</span> {escape(short)}</p>' if short else ""
    return (f'<div class="ev-cand"><div class="ev-cand-photo"><img src="{photo}" alt="Foto {escape(c["nama"])}"/>'
            f'<span class="ev-cand-no">No. {c["nomor"]}</span></div><div class="ev-cand-body">'
            f'<p class="ev-cand-name">{escape(c["nama"])}</p><p class="ev-cand-desc">{escape(desc[:140])}</p>{vis_html}</div></div>')


def candidate_detail_html(c: dict) -> str:
    def block(title, text):
        return f'<h4 style="margin:14px 0 4px 0">{title}</h4><p style="white-space:pre-wrap;margin:0">{escape(text or "-")}</p>'
    photo = storage.photo_uri(c.get("foto_path"), c["nama"])
    extra = block("Informasi Tambahan", c["info_tambahan"]) if c.get("info_tambahan") else ""
    return (f'<img class="ev-detail-photo" src="{photo}" alt="Foto {escape(c["nama"])}"/>'
            f'<h3 style="margin:14px 0 2px 0;font-size:1.25rem">{escape(c["nama"])}</h3>'
            f'<span class="ev-badge info">Nomor Urut {c["nomor"]}</span>'
            f'{block("Deskripsi", c.get("deskripsi"))}{block("Visi", c.get("visi"))}{block("Misi", c.get("misi"))}{extra}')
