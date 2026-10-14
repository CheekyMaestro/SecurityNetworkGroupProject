import os
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import File, FileCiphertext, FileKey
from app.services import files as files_service
from tests.conftest import create_user, login_client

KB = 1024
MB = 1024 * 1024

MAGIC = {
    "jpg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00",
    "png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
    "pdf": b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n",
    "doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00\x00\x00\x00",
    "docx": b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00",
    "xlsx": b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00",
    "mp4": b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00",
    "mov": b"\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00",
    "mkv": b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\xf7\x81",
}


def content(ext: str, size: int, marker: bytes = b"") -> bytes:
    head = MAGIC[ext] + marker
    if size <= len(head):
        return head[:size] if size >= 16 else head
    return head + os.urandom(size - len(head))


def upload(client, category, name, data, package_id=None, mime="application/octet-stream"):
    fields = {"category": category}
    if package_id is not None:
        fields["package_id"] = str(package_id)
    return client.post("/files", data=fields, files={"file": (name, data, mime)})


def storage_files() -> set[Path]:
    root = get_settings().storage_dir
    return {p for p in root.rglob("*") if p.is_file()} if root.exists() else set()


def me(client) -> int:
    return client.get("/auth/me").json()["id"]


@pytest.fixture
def other_buyer():
    c = login_client(create_user("buyer"))
    yield c
    c.__exit__(None, None, None)


# --- Upload menghasilkan 3 ciphertext + 3 kunci ---

def test_upload_tiga_ciphertext_tiga_file_tiga_kunci(buyer):
    before = storage_files()
    r = upload(buyer, "document", "invoice.pdf", content("pdf", 70 * KB))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "invoice.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["size_bytes"] == 70 * KB
    assert body["algorithms"] == ["aes", "rc4", "des"]
    assert body["created_at"].endswith("+07:00")

    with SessionLocal() as db:
        cts = db.scalars(select(FileCiphertext).where(FileCiphertext.file_id == body["id"])).all()
        keys = db.scalars(select(FileKey).where(FileKey.file_id == body["id"])).all()
        assert sorted(c.algorithm for c in cts) == ["aes", "des", "rc4"]
        assert all(c.enc_time_ms >= 0 for c in cts)
        assert len(keys) == 3
        assert {k.user_id for k in keys} == {me(buyer)}
        assert sorted(k.algorithm for k in keys) == ["aes", "des", "rc4"]
        f = db.get(File, body["id"])
        assert b"invoice" not in f.name_ciphertext

    new = storage_files() - before
    assert len(new) == 3
    assert sorted(p.name.rsplit("-", 1)[1] for p in new) == ["aes.bin", "des.bin", "rc4.bin"]
    sizes = {p.name.rsplit("-", 1)[1]: p.stat().st_size for p in new}
    assert sizes == {"aes.bin": 70 * KB + 16, "rc4.bin": 70 * KB, "des.bin": 70 * KB + 8}


@pytest.mark.parametrize("size", [1 * KB, 64 * KB, 64 * KB + 1, 1 * MB + 7])
@pytest.mark.parametrize("alg", ["aes", "rc4", "des"])
def test_unduh_tiap_algoritma_identik(buyer, alg, size):
    original = content("mp4", size)
    file_id = upload(buyer, "video", "unboxing.mp4", original).json()["id"]
    r = buyer.get(f"/files/{file_id}/download", params={"alg": alg})
    assert r.status_code == 200
    assert r.content == original
    assert r.headers["content-type"] == "video/mp4"
    assert r.headers["content-length"] == str(size)
    assert 'filename="unboxing.mp4"' in r.headers["content-disposition"]
    assert r.headers["cache-control"] == "no-store"


def test_unduh_default_aes_dan_alg_salah_400(buyer):
    file_id = upload(buyer, "id_card", "ktp.png", content("png", 2 * KB)).json()["id"]
    assert buyer.get(f"/files/{file_id}/download").status_code == 200
    assert buyer.get(f"/files/{file_id}/download", params={"alg": "3des"}).status_code == 400


def test_nama_file_unicode_kembali_utuh(buyer):
    name = "Invoice Toko «Elektra» 雲 #1.pdf"
    file_id = upload(buyer, "document", name, content("pdf", 100)).json()["id"]
    assert buyer.get("/files").json()["items"][0]["name"] == name
    cd = buyer.get(f"/files/{file_id}/download").headers["content-disposition"]
    assert "filename*=UTF-8''Invoice%20Toko%20%C2%ABElektra%C2%BB%20%E9%9B%B2%20%231.pdf" in cd


def test_nama_file_dengan_path_dibersihkan(buyer):
    r = upload(buyer, "document", "C:\\Users\\dzaky\\Desktop\\rekap.xlsx", content("xlsx", 100))
    assert r.json()["name"] == "rekap.xlsx"


def test_sesi_diperpanjang_juga_saat_unduh(buyer):
    file_id = upload(buyer, "document", "a.pdf", content("pdf", 100)).json()["id"]
    r = buyer.get(f"/files/{file_id}/download")
    assert any(h.startswith("session=") for h in r.headers.get_list("set-cookie"))


# --- Tidak ada plaintext tersimpan ---

def test_tidak_ada_plaintext_di_storage_maupun_database(buyer):
    marker = b"PENANDA-PLAINTEXT-7f3a9c"
    name_marker = "NamaFilePenanda9x"
    before = storage_files()
    upload(buyer, "document", f"{name_marker}.pdf", content("pdf", 200 * KB, marker) + marker * 50)
    for p in storage_files() - before:
        raw = p.read_bytes()
        assert marker not in raw
    db_raw = Path(get_settings().database_url.removeprefix("sqlite:///")).read_bytes()
    assert marker not in db_raw
    assert name_marker.encode() not in db_raw


# --- Validasi format dan ukuran ---

@pytest.mark.parametrize("category, name, data, mime", [
    ("video", "film.avi", content("mp4", 100), "video/x-msvideo"),
    ("document", "catatan.txt", b"hello world" * 10, "text/plain"),
    ("id_card", "ktp.gif", b"GIF89a" + bytes(100), "image/gif"),
    ("id_card", "ktp.pdf", content("pdf", 100), "application/pdf"),
    ("document", "virus.pdf", b"MZ\x90\x00" + bytes(200), "application/pdf"),
    ("video", "palsu.mp4", b"bukan video sama sekali" * 5, "video/mp4"),
    ("document", "invoice.pdf", content("pdf", 100), "image/png"),
    ("document", "tanpa_ekstensi", content("pdf", 100), "application/pdf"),
])
def test_format_salah_400_tanpa_sisa(buyer, category, name, data, mime):
    before = storage_files()
    r = upload(buyer, category, name, data, mime=mime)
    assert r.status_code == 400, r.text
    assert "Format" in r.json()["detail"] or "format" in r.json()["detail"]
    assert storage_files() == before


@pytest.mark.parametrize("category, ext, limit", [("id_card", "jpg", 5 * MB), ("document", "pdf", 20 * MB)])
def test_melebihi_batas_413_tanpa_file_parsial(buyer, category, ext, limit):
    before = storage_files()
    with SessionLocal() as db:
        rows_before = db.scalar(select(func.count(File.id)))
    r = upload(buyer, category, f"besar.{ext}", content(ext, limit + 1))
    assert r.status_code == 413
    assert "maksimal" in r.json()["detail"]
    assert storage_files() == before
    with SessionLocal() as db:
        assert db.scalar(select(func.count(File.id))) == rows_before


def test_tepat_di_batas_diterima(buyer):
    r = upload(buyer, "id_card", "ktp.jpg", content("jpg", 5 * MB))
    assert r.status_code == 201


def test_file_kosong_400(buyer):
    before = storage_files()
    r = buyer.post("/files", data={"category": "document"}, files={"file": ("a.pdf", b"", "application/pdf")})
    assert r.status_code == 400
    assert storage_files() == before


def test_tanpa_file_400(buyer):
    r = buyer.post("/files", data={"category": "document"}, files={"lain": ("x.txt", b"x")})
    assert r.status_code == 400


def test_kategori_tidak_valid_400(buyer):
    r = upload(buyer, "foto", "a.png", content("png", 100))
    assert r.status_code == 400


def test_category_harus_sebelum_file(buyer):
    boundary = "batasAwan"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.pdf\"\r\n"
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + content("pdf", 100) + (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"category\"\r\n\r\ndocument\r\n--{boundary}--\r\n"
    ).encode()
    r = buyer.post("/files", content=body, headers={"content-type": f"multipart/form-data; boundary={boundary}"})
    assert r.status_code == 400
    assert "category" in r.json()["detail"]


def test_bukan_multipart_400(buyer):
    r = buyer.post("/files", json={"category": "document"})
    assert r.status_code == 400


def test_gagal_di_tengah_rollback_dan_bersih(buyer, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("DB mati")

    monkeypatch.setattr(files_service, "save_upload", boom)
    before = storage_files()
    with SessionLocal() as db:
        rows_before = db.scalar(select(func.count(File.id)))
    with pytest.raises(RuntimeError):
        upload(buyer, "document", "a.pdf", content("pdf", 200 * KB))
    assert storage_files() == before
    with SessionLocal() as db:
        assert db.scalar(select(func.count(File.id))) == rows_before


# --- Kepemilikan: selalu 404 ---

def test_user_lain_tidak_bisa_akses_file(buyer, other_buyer):
    file_id = upload(buyer, "document", "rahasia.pdf", content("pdf", 100)).json()["id"]
    for alg in ("aes", "rc4", "des"):
        assert other_buyer.get(f"/files/{file_id}/download", params={"alg": alg}).status_code == 404
    assert other_buyer.delete(f"/files/{file_id}").status_code == 404
    assert all(f["id"] != file_id for f in other_buyer.get("/files").json()["items"])
    assert buyer.get(f"/files/{file_id}/download").status_code == 200


def test_toko_tanpa_klaim_404(buyer, store):
    file_id = upload(buyer, "video", "v.mp4", content("mp4", 1000)).json()["id"]
    for alg in ("aes", "rc4", "des"):
        assert store.get(f"/files/{file_id}/download", params={"alg": alg}).status_code == 404


def test_file_tidak_ada_404(buyer):
    assert buyer.get("/files/999999/download").status_code == 404
    assert buyer.delete("/files/999999").status_code == 404


# --- Hapus ---

def test_hapus_file_menghapus_baris_dan_disk(buyer):
    before = storage_files()
    file_id = upload(buyer, "document", "hapus.pdf", content("pdf", 100 * KB)).json()["id"]
    assert len(storage_files() - before) == 3
    r = buyer.delete(f"/files/{file_id}")
    assert r.status_code == 204
    assert r.content == b""
    assert storage_files() == before
    with SessionLocal() as db:
        assert db.get(File, file_id) is None
        assert not db.scalars(select(FileCiphertext).where(FileCiphertext.file_id == file_id)).all()
        assert not db.scalars(select(FileKey).where(FileKey.file_id == file_id)).all()
    assert buyer.get(f"/files/{file_id}/download").status_code == 404


# --- Daftar file ---

def test_daftar_file_dengan_filter_kategori(buyer):
    upload(buyer, "video", "v.mov", content("mov", 100))
    upload(buyer, "document", "d.docx", content("docx", 100))
    upload(buyer, "id_card", "k.jpeg", content("jpg", 100), mime="image/jpeg")
    all_items = buyer.get("/files").json()["items"]
    assert len(all_items) == 3
    videos = buyer.get("/files", params={"category": "video"}).json()["items"]
    assert [f["name"] for f in videos] == ["v.mov"]
    assert videos[0]["mime_type"] == "video/quicktime"
    assert set(videos[0]) == {"id", "package_id", "category", "name", "mime_type",
                              "size_bytes", "created_at", "algorithms"}


def test_mkv_dan_doc_lama_diterima(buyer):
    assert upload(buyer, "video", "a.mkv", content("mkv", 100), mime="video/x-matroska").status_code == 201
    assert upload(buyer, "document", "b.doc", content("doc", 100), mime="application/msword").status_code == 201


def test_ktp_muncul_di_profil(buyer):
    file_id = upload(buyer, "id_card", "ktp.png", content("png", 100), mime="image/png").json()["id"]
    assert buyer.get("/profile").json()["id_card_file_id"] == file_id


# --- Paket ---

def test_paket_lengkap(buyer):
    r = buyer.post("/packages", json={"item_name": " Monitor 24 inci ", "store": "Toko Elektra",
                                      "order_no": "INV/2026/10/0412"})
    assert r.status_code == 201
    pkg = r.json()
    assert pkg["item_name"] == "Monitor 24 inci"
    assert (pkg["video_file_id"], pkg["document_count"], pkg["total_size_bytes"]) == (None, 0, 0)

    video = upload(buyer, "video", "unboxing.mp4", content("mp4", 300 * KB), package_id=pkg["id"]).json()
    upload(buyer, "document", "invoice.pdf", content("pdf", 10 * KB), package_id=pkg["id"])
    upload(buyer, "document", "kronologi.docx", content("docx", 5 * KB), package_id=pkg["id"])
    upload(buyer, "document", "lepas.pdf", content("pdf", 1 * KB))

    item = buyer.get("/packages").json()["items"][0]
    assert item == {
        "id": pkg["id"], "item_name": "Monitor 24 inci", "store": "Toko Elektra",
        "order_no": "INV/2026/10/0412", "created_at": pkg["created_at"],
        "video_file_id": video["id"], "document_count": 2,
        "total_size_bytes": 300 * KB + 10 * KB + 5 * KB,
    }

    detail = buyer.get(f"/packages/{pkg['id']}").json()
    assert set(detail) == {"id", "item_name", "store", "order_no", "created_at", "files", "claim"}
    assert [f["name"] for f in detail["files"]] == ["unboxing.mp4", "invoice.pdf", "kronologi.docx"]
    assert detail["claim"] is None


def test_metadata_paket_terenkripsi(buyer):
    penanda = "BarangPenandaRahasia77"
    buyer.post("/packages", json={"item_name": penanda, "store": "Toko X", "order_no": "INV-1"})
    db_raw = Path(get_settings().database_url.removeprefix("sqlite:///")).read_bytes()
    assert penanda.encode() not in db_raw


def test_paket_user_lain_404(buyer, other_buyer):
    pkg_id = buyer.post("/packages", json={"item_name": "A", "store": "B", "order_no": "C"}).json()["id"]
    assert other_buyer.get(f"/packages/{pkg_id}").status_code == 404
    assert other_buyer.get("/packages").json()["items"] == []
    before = storage_files()
    r = upload(other_buyer, "document", "a.pdf", content("pdf", 100), package_id=pkg_id)
    assert r.status_code == 404
    assert storage_files() == before


def test_paket_validasi(buyer):
    assert buyer.post("/packages", json={"item_name": "", "store": "B", "order_no": "C"}).status_code == 400
    assert buyer.post("/packages", json={"item_name": "A", "store": "B"}).status_code == 400
    assert buyer.get("/packages/999999").status_code == 404


def test_ktp_tidak_boleh_masuk_paket(buyer):
    pkg_id = buyer.post("/packages", json={"item_name": "A", "store": "B", "order_no": "C"}).json()["id"]
    r = upload(buyer, "id_card", "ktp.png", content("png", 100), package_id=pkg_id)
    assert r.status_code == 400
