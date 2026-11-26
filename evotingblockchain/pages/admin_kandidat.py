import streamlit as st

from components.tabs import tab_select

from components import tx_flow
from components.admin_gate import require_admin
from components.candidate_card import candidate_card_html
from components.notifications import alert, empty_state
from components.selectors import election_picker
from services import candidate_service as cs
from services.errors import EvoteError


def _photo(label, key):
    f = st.file_uploader(label, type=["jpg", "jpeg", "png"], key=key, help="Format JPG, JPEG, atau PNG. Maksimal 2 MB.")
    if f is not None:
        st.image(f.getvalue(), caption="Pratinjau foto", width=180)
        return (f.getvalue(), f.name)
    return None


def _fields(prefix, cur=None):
    cur = cur or {}
    a, b = st.columns([1, 3])
    nomor = a.number_input("Nomor urut", 1, 999, int(cur.get("nomor", 1)), key=f"{prefix}_no")
    nama = b.text_input("Nama kandidat", cur.get("nama", ""), max_chars=100, key=f"{prefix}_nm")
    desk = st.text_area("Deskripsi singkat", cur.get("deskripsi", ""), max_chars=500, key=f"{prefix}_ds")
    visi = st.text_area("Visi", cur.get("visi", ""), max_chars=2000, key=f"{prefix}_vi")
    misi = st.text_area("Misi", cur.get("misi", ""), max_chars=3000, key=f"{prefix}_mi")
    info = st.text_area("Informasi tambahan (opsional)", cur.get("info_tambahan", ""), max_chars=1000, key=f"{prefix}_in")
    return {"nomor_urut": nomor, "nama": nama, "deskripsi": desk, "visi": visi, "misi": misi, "info_tambahan": info}


def render():
    addr = require_admin("Manajemen Kandidat", "Tambah, edit, dan hapus kandidat per periode. Foto diunggah langsung dari sini.", "users")
    e = election_picker()
    if not e:
        return
    if not e["editable"]:
        alert("warning", "Kandidat terkunci karena periode sudah dimulai, selesai, atau dibatalkan. Data hanya dapat dilihat.", "Kandidat terkunci")
    cands = cs.list_candidates(e["id"])
    labels = ["Daftar Kandidat", "Tambah Kandidat", "Edit atau Hapus"]
    sel = tab_select(labels, "tab_kandidat")
    if sel == labels[0]:
        if not cands:
            empty_state("Belum ada kandidat", "Tambahkan kandidat pada tab 'Tambah Kandidat'.", "users")
        for i in range(0, len(cands), 3):
            cols = st.columns(3)
            for col, c in zip(cols, cands[i:i + 3]):
                with col:
                    st.markdown(candidate_card_html(c), unsafe_allow_html=True)
                    if not c["has_meta"]:
                        st.caption("Metadata off-chain tidak ditemukan untuk kandidat ini.")
                    elif not c["meta_ok"]:
                        st.caption("Peringatan: hash metadata tidak cocok dengan blockchain.")
                    st.write("")
    if sel == labels[1]:
        if not e["editable"]:
            empty_state("Penambahan dikunci", "Periode sudah dimulai atau selesai.", "lock")
        else:
            v = len(cands)  # kunci widget berubah setelah penambahan sehingga formulir kembali bersih
            photo = _photo("Foto kandidat", f"add_photo_{e['id']}_{v}")
            form = _fields(f"add_{e['id']}_{v}", {"nomor": max([c["nomor"] for c in cands], default=0) + 1})
            if st.button("Tambah kandidat", type="primary", key=f"btn_add_{e['id']}"):
                try:
                    tx_flow.start(cs.prepare_add(addr, e["id"], form, photo))
                except EvoteError as exc:
                    alert("danger", str(exc), "Tidak dapat menambah kandidat")
    if sel == labels[2]:
        if not cands:
            empty_state("Belum ada kandidat", "Tidak ada data untuk diedit.", "users")
        elif not e["editable"]:
            empty_state("Edit dikunci", "Kandidat tidak dapat diubah setelah pemilihan dimulai.", "lock")
        else:
            by = {c["cid"]: c for c in cands}
            cid = st.selectbox("Pilih kandidat", list(by), format_func=lambda i: f"No. {by[i]['nomor']} - {by[i]['nama']}", key=f"edit_c_{e['id']}")
            cur = by[cid]
            st.markdown(candidate_card_html(cur), unsafe_allow_html=True)
            st.write("")
            photo = _photo("Ganti foto (kosongkan untuk mempertahankan foto saat ini)", f"ed_photo_{e['id']}_{cid}")
            form = _fields(f"edit_{e['id']}_{cid}", cur)
            if st.button("Simpan perubahan", type="primary", key=f"btn_upd_{e['id']}_{cid}"):
                try:
                    tx_flow.start(cs.prepare_update(addr, e["id"], cid, form, photo))
                except EvoteError as exc:
                    alert("danger", str(exc), "Tidak dapat menyimpan")
            st.divider()
            ok = st.checkbox("Saya yakin ingin menghapus kandidat ini dari periode", key=f"del_ok_{e['id']}_{cid}")
            if st.button("Hapus kandidat", disabled=not ok, key=f"btn_del_{e['id']}_{cid}"):
                try:
                    tx_flow.start(cs.prepare_remove(addr, e["id"], cid))
                except EvoteError as exc:
                    alert("danger", str(exc), "Tidak dapat menghapus")
