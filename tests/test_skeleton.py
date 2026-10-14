import base64

import pytest
from sqlalchemy import inspect

from app.config import ConfigError, Settings, validate_settings
from app.db import engine

GOOD_SECRET = base64.b64encode(b"\x01" * 32).decode()


def _settings(**kw):
    base = {"master_secret": GOOD_SECRET, "jwt_secret": "jwt-rahasia-yang-cukup-panjang-untuk-hs256", "_env_file": None}
    return Settings(**{**base, **kw})


@pytest.mark.parametrize(
    "kw, pesan",
    [
        ({"master_secret": ""}, "MASTER_SECRET kosong"),
        ({"jwt_secret": "  "}, "JWT_SECRET kosong"),
        ({"jwt_secret": "pendek"}, "minimal 32"),
        ({"master_secret": "bukan-base64!!"}, "base64"),
        ({"master_secret": base64.b64encode(b"x" * 16).decode()}, "32 byte"),
    ],
)
def test_config_gagal_dengan_pesan_jelas(kw, pesan):
    with pytest.raises(ConfigError, match=pesan):
        validate_settings(_settings(**kw))


def test_config_valid():
    assert len(validate_settings(_settings()).master_secret_bytes) == 32


def test_secret_tidak_muncul_di_repr():
    assert GOOD_SECRET not in repr(_settings())


def test_tabel_dibuat(client):
    tables = set(inspect(engine).get_table_names())
    assert {
        "users", "profile_ciphertexts", "packages", "files",
        "file_ciphertexts", "file_keys", "claims", "claim_replies",
    } <= tables


def test_openapi_memuat_semua_endpoint(client):
    paths = client.get("/openapi.json").json()["paths"]
    expected = {
        ("/auth/register", "post"), ("/auth/login", "post"), ("/auth/logout", "post"), ("/auth/me", "get"),
        ("/profile", "get"), ("/profile", "put"),
        ("/packages", "post"), ("/packages", "get"), ("/packages/{package_id}", "get"),
        ("/files", "post"), ("/files", "get"), ("/files/{file_id}/download", "get"),
        ("/files/{file_id}", "delete"), ("/stats", "get"), ("/stores", "get"),
        ("/claims", "post"), ("/claims", "get"), ("/claims/{claim_id}", "get"),
        ("/claims/{claim_id}", "patch"), ("/claims/{claim_id}/replies", "post"),
    }
    actual = {(p, m) for p, ops in paths.items() for m in ops}
    assert expected <= actual


def test_stats_bentuk_kontrak(buyer):
    stats = buyer.get("/stats").json()
    assert [s["algorithm"] for s in stats["per_algorithm"]] == ["aes", "rc4", "des"]


def test_bentuk_kontrak_prd_tim(buyer):
    """Bentuk dari docs/PRD.md tim; mock FE dibuat persis seperti ini."""
    me = buyer.get("/auth/me").json()
    assert set(me) == {"id", "username", "role", "store_name"}


@pytest.mark.parametrize("path", ["/profile?alg=blowfish", "/files/1/download?alg=AES2"])
def test_alg_tidak_valid_400(buyer, path):
    r = buyer.get(path)
    assert r.status_code == 400
    assert r.json() == {"detail": "Algoritma harus aes, rc4, atau des"}


def test_validasi_selalu_400_dengan_detail_string(client):
    r = client.post("/auth/register", json={"username": "a", "password": "12345678"})
    assert r.status_code == 400
    assert isinstance(r.json()["detail"], str)


def test_404_format_kontrak(client):
    r = client.get("/tidak-ada")
    assert r.status_code == 404
    assert r.json() == {"detail": "Tidak ditemukan"}
