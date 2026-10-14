from pathlib import Path

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import ClaimKey, FileKey
from tests.conftest import create_user, login_client
from tests.test_files import content, upload
from tests.test_profile import NIK_PENANDA, sample

KB = 1024


class World:
    """Pembeli dengan profil, KTP, satu paket (video + 2 dokumen), dan dua toko."""

    def __init__(self):
        self.elektra_user = create_user("store", store_name="Toko Elektra")
        self.gadgetin_user = create_user("store", store_name="Toko Gadgetin")
        self.buyer = login_client(create_user("buyer"))
        self.elektra = login_client(self.elektra_user)
        self.gadgetin = login_client(self.gadgetin_user)

        self.buyer.put("/profile", json={"data": sample(full_name="Dzaky A.", phone="081299990000")})
        self.ktp = upload(self.buyer, "id_card", "ktp.png", content("png", 2 * KB)).json()
        self.pkg = self.buyer.post("/packages", json={
            "item_name": "Monitor 24 inci", "store": "Toko Elektra", "order_no": "INV/2026/10/0412",
        }).json()
        self.video_bytes = content("mp4", 200 * KB)
        self.video = upload(self.buyer, "video", "unboxing.mp4", self.video_bytes, package_id=self.pkg["id"]).json()
        self.invoice_bytes = content("pdf", 3 * KB)
        self.invoice = upload(self.buyer, "document", "invoice.pdf", self.invoice_bytes,
                              package_id=self.pkg["id"]).json()
        self.chrono = upload(self.buyer, "document", "kronologi.docx", content("docx", 2 * KB),
                             package_id=self.pkg["id"]).json()

    def claim(self, store_user=None, message="Layar bergaris setelah seminggu"):
        store_user = store_user or self.elektra_user
        return self.buyer.post("/claims", json={
            "package_id": self.pkg["id"], "store_user_id": store_user.id, "message": message,
        })

    def close(self):
        for c in (self.buyer, self.elektra, self.gadgetin):
            c.__exit__(None, None, None)


@pytest.fixture
def w():
    world = World()
    yield world
    world.close()


def _store_keys(file_id: int, user_id: int) -> list[str]:
    with SessionLocal() as db:
        return sorted(db.scalars(select(FileKey.algorithm).where(
            FileKey.file_id == file_id, FileKey.user_id == user_id)))


# --- Toko dan akses file ---

def test_daftar_toko(w):
    items = w.buyer.get("/stores").json()["items"]
    names = {s["store_name"]: s["id"] for s in items}
    assert names["Toko Elektra"] == w.elektra_user.id
    assert set(items[0]) == {"id", "store_name"}


def test_akses_file_sebelum_dan_sesudah_klaim(w):
    for alg in ("aes", "rc4", "des"):
        assert w.elektra.get(f"/files/{w.video['id']}/download", params={"alg": alg}).status_code == 404

    r = w.claim()
    assert r.status_code == 201
    assert set(r.json()) == {"id", "status"}
    assert r.json()["status"] == "diajukan"

    for alg in ("aes", "rc4", "des"):
        got = w.elektra.get(f"/files/{w.video['id']}/download", params={"alg": alg})
        assert got.status_code == 200
        assert got.content == w.video_bytes
        assert w.gadgetin.get(f"/files/{w.video['id']}/download", params={"alg": alg}).status_code == 404
    assert w.elektra.get(f"/files/{w.invoice['id']}/download").content == w.invoice_bytes


def test_file_keys_hanya_pemilik_dan_toko_tujuan(w):
    w.claim()
    with SessionLocal() as db:
        holders = set(db.scalars(select(FileKey.user_id).where(FileKey.file_id == w.video["id"])))
    assert holders == {w.buyer.get("/auth/me").json()["id"], w.elektra_user.id}
    assert _store_keys(w.video["id"], w.elektra_user.id) == ["aes", "des", "rc4"]
    assert _store_keys(w.video["id"], w.gadgetin_user.id) == []


def test_klaim_tidak_pernah_membagikan_id_card(w):
    # Paksa KTP masuk paket untuk memastikan filter di service, bukan hanya validasi upload.
    from app.models import File

    with SessionLocal() as db:
        db.get(File, w.ktp["id"]).package_id = w.pkg["id"]
        db.commit()
    claim_id = w.claim().json()["id"]
    assert _store_keys(w.ktp["id"], w.elektra_user.id) == []
    assert w.elektra.get(f"/files/{w.ktp['id']}/download").status_code == 404
    assert all(f["category"] != "id_card" for f in w.elektra.get(f"/claims/{claim_id}").json()["files"])


def test_toko_tidak_bisa_hapus_atau_lihat_daftar_file(w):
    w.claim()
    assert w.elektra.delete(f"/files/{w.video['id']}").status_code == 403
    assert w.elektra.get("/files").status_code == 403


def test_bukti_tambahan_setelah_klaim_ikut_dibagikan(w):
    claim_id = w.claim().json()["id"]
    w.elektra.patch(f"/claims/{claim_id}", json={"status": "ditinjau", "reply": "Mohon foto label paket"})
    extra = upload(w.buyer, "document", "label.pdf", content("pdf", 1 * KB), package_id=w.pkg["id"]).json()
    assert w.elektra.get(f"/files/{extra['id']}/download").status_code == 200
    assert w.gadgetin.get(f"/files/{extra['id']}/download").status_code == 404
    names = [f["name"] for f in w.elektra.get(f"/claims/{claim_id}").json()["files"]]
    assert "label.pdf" in names


def test_file_di_luar_paket_tidak_dibagikan(w):
    lepas = upload(w.buyer, "document", "lain.pdf", content("pdf", 100)).json()
    w.claim()
    assert w.elektra.get(f"/files/{lepas['id']}/download").status_code == 404


# --- Isi klaim untuk tiap pihak ---

def test_daftar_klaim_pembeli_dan_toko(w):
    claim_id = w.claim().json()["id"]
    expected = {
        "id": claim_id, "package_id": w.pkg["id"], "item_name": "Monitor 24 inci",
        "order_no": "INV/2026/10/0412", "buyer_name": "Dzaky A.", "store_name": "Toko Elektra",
        "status": "diajukan", "video_file_id": w.video["id"],
    }
    for client in (w.buyer, w.elektra):
        items = client.get("/claims").json()["items"]
        assert len(items) == 1
        item = items[0]
        assert item["created_at"].endswith("+07:00")
        del item["created_at"]
        assert item == expected
    assert w.gadgetin.get("/claims").json()["items"] == []


def test_detail_klaim_bentuk_kontrak(w):
    claim_id = w.claim().json()["id"]
    d = w.elektra.get(f"/claims/{claim_id}").json()
    assert set(d) == {"id", "status", "message", "created_at", "package", "buyer", "store", "files", "replies"}
    assert d["message"] == "Layar bergaris setelah seminggu"
    assert d["package"] == {"id": w.pkg["id"], "item_name": "Monitor 24 inci", "order_no": "INV/2026/10/0412"}
    assert d["buyer"] == {"name": "Dzaky A.", "ktp_verified": True}
    assert d["store"] == {"id": w.elektra_user.id, "store_name": "Toko Elektra"}
    assert [f["name"] for f in d["files"]] == ["unboxing.mp4", "invoice.pdf", "kronologi.docx"]
    assert set(d["files"][0]) == {"id", "category", "name", "mime_type", "size_bytes"}
    assert d["replies"] == []
    assert w.buyer.get(f"/claims/{claim_id}").json() == d


def test_toko_tidak_menerima_data_profil_sensitif(w):
    claim_id = w.claim().json()["id"]
    raw = (w.elektra.get(f"/claims/{claim_id}").text + w.elektra.get("/claims").text)
    for secret in (NIK_PENANDA, "081299990000", "BCA 1234567890", "Jl. Contoh"):
        assert secret not in raw


def test_ktp_belum_ada_tidak_terverifikasi(w):
    w.buyer.delete(f"/files/{w.ktp['id']}")
    claim_id = w.claim().json()["id"]
    assert w.elektra.get(f"/claims/{claim_id}").json()["buyer"]["ktp_verified"] is False


def test_nama_pembeli_dari_username_kalau_profil_kosong():
    store_user = create_user("store", store_name="Toko Z")
    buyer_user = create_user("buyer")
    buyer = login_client(buyer_user)
    try:
        pkg = buyer.post("/packages", json={"item_name": "A", "store": "Z", "order_no": "1"}).json()
        upload(buyer, "document", "a.pdf", content("pdf", 100), package_id=pkg["id"])
        claim_id = buyer.post("/claims", json={"package_id": pkg["id"], "store_user_id": store_user.id,
                                               "message": "rusak"}).json()["id"]
        assert buyer.get(f"/claims/{claim_id}").json()["buyer"]["name"] == buyer_user.username
    finally:
        buyer.__exit__(None, None, None)


def test_paket_menampilkan_status_klaim(w):
    claim_id = w.claim().json()["id"]
    assert w.buyer.get(f"/packages/{w.pkg['id']}").json()["claim"] == {"id": claim_id, "status": "diajukan"}
    w.elektra.patch(f"/claims/{claim_id}", json={"status": "diterima"})
    assert w.buyer.get(f"/packages/{w.pkg['id']}").json()["claim"] == {"id": claim_id, "status": "diterima"}


# --- Status dan balasan ---

def test_toko_ubah_status_dan_balas(w):
    claim_id = w.claim().json()["id"]
    r = w.elektra.patch(f"/claims/{claim_id}", json={"status": "ditinjau", "reply": "  Kami cek ke kurir dulu.  "})
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ditinjau"
    assert len(d["replies"]) == 1
    reply = d["replies"][0]
    assert reply["author_role"] == "store"
    assert reply["author_name"] == "Toko Elektra"
    assert reply["body"] == "Kami cek ke kurir dulu."
    assert set(reply) == {"id", "author_role", "author_name", "body", "created_at"}

    r = w.elektra.patch(f"/claims/{claim_id}", json={"status": "diterima"})
    assert r.json()["status"] == "diterima"
    assert len(r.json()["replies"]) == 1


def test_balasan_dua_arah(w):
    claim_id = w.claim().json()["id"]
    r = w.buyer.post(f"/claims/{claim_id}/replies", json={"body": "Ini nomor resinya JNE123"})
    assert r.status_code == 201
    assert r.json()["author_role"] == "buyer"
    assert r.json()["author_name"] == "Dzaky A."
    w.elektra.post(f"/claims/{claim_id}/replies", json={"body": "Terima kasih"})
    bodies = [x["body"] for x in w.buyer.get(f"/claims/{claim_id}").json()["replies"]]
    assert bodies == ["Ini nomor resinya JNE123", "Terima kasih"]


def test_isi_klaim_terenkripsi_di_database(w):
    marker_msg = "PesanKlaimPenanda55"
    marker_reply = "BalasanPenanda66"
    claim_id = w.claim(message=marker_msg).json()["id"]
    w.elektra.post(f"/claims/{claim_id}/replies", json={"body": marker_reply})
    raw = Path(get_settings().database_url.removeprefix("sqlite:///")).read_bytes()
    for marker in (marker_msg, marker_reply, "Monitor 24 inci", "INV/2026/10/0412"):
        assert marker.encode() not in raw
    with SessionLocal() as db:
        holders = set(db.scalars(select(ClaimKey.user_id).where(ClaimKey.claim_id == claim_id)))
    assert holders == {w.buyer.get("/auth/me").json()["id"], w.elektra_user.id}


# --- Akses yang ditolak ---

def test_toko_lain_dan_pembeli_lain_404(w):
    claim_id = w.claim().json()["id"]
    other = login_client(create_user("buyer"))
    try:
        for client in (w.gadgetin, other):
            assert client.get(f"/claims/{claim_id}").status_code == 404
            assert client.post(f"/claims/{claim_id}/replies", json={"body": "halo"}).status_code == 404
        assert w.gadgetin.patch(f"/claims/{claim_id}", json={"status": "diterima"}).status_code == 404
        assert other.get("/claims").json()["items"] == []
    finally:
        other.__exit__(None, None, None)


def test_pembeli_tidak_bisa_ubah_status(w):
    claim_id = w.claim().json()["id"]
    assert w.buyer.patch(f"/claims/{claim_id}", json={"status": "diterima"}).status_code == 403


def test_klaim_paket_orang_lain_404(w):
    other = login_client(create_user("buyer"))
    try:
        r = other.post("/claims", json={"package_id": w.pkg["id"], "store_user_id": w.elektra_user.id,
                                        "message": "x"})
        assert r.status_code == 404
    finally:
        other.__exit__(None, None, None)


def test_klaim_ke_bukan_toko_404(w):
    buyer_id = w.buyer.get("/auth/me").json()["id"]
    r = w.buyer.post("/claims", json={"package_id": w.pkg["id"], "store_user_id": buyer_id, "message": "x"})
    assert r.status_code == 404
    assert w.buyer.post("/claims", json={"package_id": w.pkg["id"], "store_user_id": 999999,
                                         "message": "x"}).status_code == 404


def test_klaim_ganda_ditolak_sampai_selesai(w):
    claim_id = w.claim().json()["id"]
    assert w.claim(store_user=w.gadgetin_user).status_code == 400
    w.elektra.patch(f"/claims/{claim_id}", json={"status": "ditolak"})
    assert w.claim(store_user=w.gadgetin_user).status_code == 201


def test_paket_kosong_tidak_bisa_diklaim(w):
    pkg = w.buyer.post("/packages", json={"item_name": "A", "store": "B", "order_no": "C"}).json()
    r = w.buyer.post("/claims", json={"package_id": pkg["id"], "store_user_id": w.elektra_user.id,
                                      "message": "x"})
    assert r.status_code == 400


def test_validasi_klaim(w):
    r = w.buyer.post("/claims", json={"package_id": w.pkg["id"], "store_user_id": w.elektra_user.id,
                                      "message": "   "})
    assert r.status_code == 400
    claim_id = w.claim().json()["id"]
    assert w.elektra.patch(f"/claims/{claim_id}", json={"status": "selesai"}).status_code == 400
    assert w.buyer.post(f"/claims/{claim_id}/replies", json={"body": ""}).status_code == 400
