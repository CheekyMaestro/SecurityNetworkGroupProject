import json

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.crypto.keys import derive_user_keys
from app.crypto.vault import decrypt_bytes
from app.db import SessionLocal
from app.models import ProfileCiphertext, User

FIELDS = ["full_name", "nik", "birth_date", "gender", "nationality", "marital_status",
          "address", "phone", "bank_account", "religion", "health_notes"]

NIK_PENANDA = "3578999988887777"


def sample(**override):
    data = {
        "full_name": "Dzaky A.", "nik": NIK_PENANDA, "birth_date": "2004-05-12",
        "gender": "Laki-laki", "nationality": "WNI", "marital_status": "Belum kawin",
        "address": "Jl. Contoh No. 12, Surabaya", "phone": "081234567890",
        "bank_account": "BCA 1234567890", "religion": None, "health_notes": None,
    }
    return {**data, **override}


def _rows(client):
    uid = client.get("/auth/me").json()["id"]
    with SessionLocal() as db:
        user = db.get(User, uid)
        rows = db.scalars(select(ProfileCiphertext).where(ProfileCiphertext.user_id == uid)).all()
        return user, {r.algorithm: r for r in rows}


def test_profil_kosong_semua_null(buyer):
    body = buyer.get("/profile").json()
    assert body == {
        "algorithm": "aes", "decrypt_ms": None, "updated_at": None,
        "data": {f: None for f in FIELDS}, "id_card_file_id": None,
    }


def test_put_response(buyer):
    r = buyer.put("/profile", json={"data": sample()})
    assert r.status_code == 200
    body = r.json()
    assert body["updated_at"].endswith("+07:00")
    assert set(body["enc_ms"]) == {"aes", "rc4", "des"}
    assert all(v >= 0 for v in body["enc_ms"].values())


@pytest.mark.parametrize("alg", ["aes", "rc4", "des"])
def test_get_tiap_algoritma_kembali_asli(buyer, alg):
    data = sample(religion="Islam", health_notes="Golongan darah O; alergi udang")
    updated_at = buyer.put("/profile", json={"data": data}).json()["updated_at"]
    body = buyer.get("/profile", params={"alg": alg}).json()
    assert body["algorithm"] == alg
    assert body["data"] == data
    assert body["updated_at"] == updated_at
    assert isinstance(body["decrypt_ms"], float) and body["decrypt_ms"] >= 0


def test_tersimpan_tiga_ciphertext_terpisah(buyer):
    data = sample(full_name="Nama Unik Penanda")
    buyer.put("/profile", json={"data": data})
    user, rows = _rows(buyer)
    assert set(rows) == {"aes", "rc4", "des"}
    assert len({r.ciphertext for r in rows.values()}) == 3
    assert {alg: len(r.iv) for alg, r in rows.items()} == {"aes": 16, "rc4": 16, "des": 8}
    for r in rows.values():
        assert NIK_PENANDA.encode() not in r.ciphertext
        assert b"Nama Unik Penanda" not in r.ciphertext
    # Tiap ciphertext bisa dibuka sendiri-sendiri dengan key user (bukan berlapis).
    keys = derive_user_keys(user.key_salt)
    for alg, r in rows.items():
        assert json.loads(decrypt_bytes(alg, keys[alg], r.iv, r.ciphertext)) == data


def test_simpan_ulang_menimpa_tetap_tiga_baris(buyer):
    buyer.put("/profile", json={"data": sample(address="Alamat lama")})
    _, before = _rows(buyer)
    buyer.put("/profile", json={"data": sample(address="Alamat baru")})
    _, after = _rows(buyer)
    assert len(after) == 3
    assert {a: r.id for a, r in after.items()} == {a: r.id for a, r in before.items()}
    assert all(after[a].iv != before[a].iv for a in after)
    for alg in ("aes", "rc4", "des"):
        assert buyer.get("/profile", params={"alg": alg}).json()["data"]["address"] == "Alamat baru"


def test_tidak_ada_plaintext_di_file_database(buyer):
    penanda = "PenandaRahasiaProfil_42"
    buyer.put("/profile", json={"data": sample(full_name=penanda, bank_account=f"BNI {penanda}")})
    db_path = get_settings().database_url.removeprefix("sqlite:///")
    with SessionLocal() as db:
        db.commit()  # pastikan tidak ada transaksi terbuka sebelum baca file
    raw = open(db_path, "rb").read()
    assert penanda.encode() not in raw
    assert penanda.encode("utf-16-le") not in raw


def test_profil_user_lain_tidak_terlihat(buyer):
    buyer.put("/profile", json={"data": sample()})
    from tests.conftest import create_user, login_client

    other = login_client(create_user())
    try:
        assert other.get("/profile").json()["data"] == {f: None for f in FIELDS}
    finally:
        other.__exit__(None, None, None)


def test_spasi_dibuang_dan_opsional_kosong_jadi_null(buyer):
    buyer.put("/profile", json={"data": sample(full_name="  Dzaky A.  ", religion="   ", health_notes="")})
    data = buyer.get("/profile").json()["data"]
    assert data["full_name"] == "Dzaky A."
    assert data["religion"] is None
    assert data["health_notes"] is None


def test_unicode_tersimpan_utuh(buyer):
    data = sample(full_name="Dzaky Ā. 'Ñ' — 雲", address="Jl. Kenanga №5 😀")
    buyer.put("/profile", json={"data": data})
    for alg in ("aes", "rc4", "des"):
        assert buyer.get("/profile", params={"alg": alg}).json()["data"] == data


@pytest.mark.parametrize("override, field", [
    ({"full_name": ""}, "Nama lengkap"),
    ({"nik": "   "}, "NIK"),
    ({"bank_account": None}, "rekening"),
    ({"birth_date": "12-05-2004"}, "Tanggal lahir"),
    ({"birth_date": "2004-02-30"}, "Tanggal lahir"),
    ({"birth_date": "2999-01-01"}, "Tanggal lahir"),
    ({"address": "x" * 501}, "Alamat"),
])
def test_validasi_field_400(buyer, override, field):
    r = buyer.put("/profile", json={"data": sample(**override)})
    assert r.status_code == 400
    assert field in r.json()["detail"]


def test_field_wajib_hilang_400(buyer):
    data = sample()
    del data["phone"]
    r = buyer.put("/profile", json={"data": data})
    assert r.status_code == 400
    assert "telepon" in r.json()["detail"]


def test_body_tanpa_bungkus_data_400(buyer):
    r = buyer.put("/profile", json=sample())
    assert r.status_code == 400
    assert r.json() == {"detail": "Data profil wajib dikirim dalam field data"}


def test_validasi_gagal_tidak_mengubah_profil(buyer):
    buyer.put("/profile", json={"data": sample(address="Tetap")})
    buyer.put("/profile", json={"data": sample(address="Baru", nik="")})
    assert buyer.get("/profile").json()["data"]["address"] == "Tetap"


def test_alg_default_aes_dan_tidak_valid_400(buyer):
    buyer.put("/profile", json={"data": sample()})
    assert buyer.get("/profile").json()["algorithm"] == "aes"
    r = buyer.get("/profile", params={"alg": "AES"})
    assert r.status_code == 400


def test_toko_tidak_bisa_akses_profil(store):
    assert store.get("/profile").status_code == 403
    assert store.put("/profile", json={"data": sample()}).status_code == 403
