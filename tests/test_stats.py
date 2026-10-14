import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import DecryptLog, File, User
from app.services import files as files_service
from app.services.stats import cipher_size
from tests.conftest import create_user, login_client
from tests.test_files import content, storage_files, upload

KB = 1024


def _logs(file_id: int) -> list[DecryptLog]:
    with SessionLocal() as db:
        return db.scalars(select(DecryptLog).where(DecryptLog.file_id == file_id)).all()


def test_stats_kosong(buyer):
    assert buyer.get("/stats").json() == {
        "per_algorithm": [
            {"algorithm": alg, "avg_enc_ms_per_mb": None, "avg_dec_ms_per_mb": None, "total_cipher_bytes": 0}
            for alg in ("aes", "rc4", "des")
        ],
        "per_category": [],
    }


@pytest.mark.parametrize("alg, size, expected", [
    ("aes", 0, 16), ("aes", 15, 16), ("aes", 16, 32), ("des", 8, 16), ("des", 9, 16), ("rc4", 77, 77),
])
def test_ukuran_ciphertext(alg, size, expected):
    assert cipher_size(alg, size) == expected


def test_total_cipher_bytes_sama_dengan_isi_disk(buyer):
    before = storage_files()
    upload(buyer, "video", "a.mp4", content("mp4", 300 * KB + 5))
    upload(buyer, "document", "b.pdf", content("pdf", 7 * KB + 3))
    new = storage_files() - before
    on_disk = {alg: sum(p.stat().st_size for p in new if p.name.endswith(f"-{alg}.bin")) for alg in ("aes", "rc4", "des")}
    stats = {s["algorithm"]: s for s in buyer.get("/stats").json()["per_algorithm"]}
    assert {alg: stats[alg]["total_cipher_bytes"] for alg in on_disk} == on_disk
    assert on_disk["rc4"] == 300 * KB + 5 + 7 * KB + 3


def test_waktu_enkripsi_terisi_dan_per_kategori(buyer):
    upload(buyer, "video", "a.mp4", content("mp4", 500 * KB))
    upload(buyer, "document", "b.pdf", content("pdf", 50 * KB))
    body = buyer.get("/stats").json()
    for s in body["per_algorithm"]:
        assert isinstance(s["avg_enc_ms_per_mb"], float) and s["avg_enc_ms_per_mb"] >= 0
        assert s["avg_dec_ms_per_mb"] is None
    assert [(c["category"], c["algorithm"]) for c in body["per_category"]] == [
        ("video", "aes"), ("video", "rc4"), ("video", "des"),
        ("document", "aes"), ("document", "rc4"), ("document", "des"),
    ]
    assert set(body["per_category"][0]) == {"category", "algorithm", "avg_enc_ms_per_mb"}


def test_waktu_dekripsi_setelah_unduh(buyer):
    file_id = upload(buyer, "video", "a.mp4", content("mp4", 400 * KB)).json()["id"]
    buyer.get(f"/files/{file_id}/download", params={"alg": "rc4"})
    stats = {s["algorithm"]: s for s in buyer.get("/stats").json()["per_algorithm"]}
    assert isinstance(stats["rc4"]["avg_dec_ms_per_mb"], float)
    assert stats["aes"]["avg_dec_ms_per_mb"] is None
    assert stats["des"]["avg_dec_ms_per_mb"] is None

    logs = _logs(file_id)
    assert len(logs) == 1
    assert (logs[0].algorithm, logs[0].size_bytes) == ("rc4", 400 * KB)
    assert logs[0].dec_time_ms >= 0


def test_unduhan_terputus_tidak_dicatat(buyer):
    file_id = upload(buyer, "video", "a.mp4", content("mp4", 300 * KB)).json()["id"]
    uid = buyer.get("/auth/me").json()["id"]
    with SessionLocal() as db:
        dl = files_service.open_download(db, db.get(User, uid), file_id, "aes")
    next(dl.chunks)
    dl.chunks.close()
    assert _logs(file_id) == []


def test_unduhan_toko_dicatat_di_statistik_pemilik(buyer):
    store_user = create_user("store", store_name="Toko S")
    store = login_client(store_user)
    try:
        pkg = buyer.post("/packages", json={"item_name": "A", "store": "S", "order_no": "1"}).json()
        file_id = upload(buyer, "video", "a.mp4", content("mp4", 100 * KB), package_id=pkg["id"]).json()["id"]
        buyer.post("/claims", json={"package_id": pkg["id"], "store_user_id": store_user.id, "message": "x"})
        assert store.get(f"/files/{file_id}/download", params={"alg": "des"}).status_code == 200
        stats = {s["algorithm"]: s for s in buyer.get("/stats").json()["per_algorithm"]}
        assert stats["des"]["avg_dec_ms_per_mb"] is not None
    finally:
        store.__exit__(None, None, None)


def test_statistik_hanya_file_sendiri(buyer):
    upload(buyer, "video", "a.mp4", content("mp4", 100 * KB))
    other = login_client(create_user())
    try:
        assert other.get("/stats").json()["per_algorithm"][0]["total_cipher_bytes"] == 0
    finally:
        other.__exit__(None, None, None)


def test_log_ikut_terhapus_bersama_file(buyer):
    file_id = upload(buyer, "document", "a.pdf", content("pdf", 10 * KB)).json()["id"]
    buyer.get(f"/files/{file_id}/download")
    assert len(_logs(file_id)) == 1
    buyer.delete(f"/files/{file_id}")
    assert _logs(file_id) == []
    with SessionLocal() as db:
        assert db.get(File, file_id) is None
    assert buyer.get("/stats").json()["per_algorithm"][0]["total_cipher_bytes"] == 0


def test_toko_403(store):
    assert store.get("/stats").status_code == 403
