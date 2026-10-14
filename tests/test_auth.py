import logging
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models import User
from app.security.sessions import COOKIE_NAME, read_token
from app.timeutil import utcnow
from tests.conftest import PASSWORD, create_user, unique_name

PROTECTED = [
    ("post", "/auth/logout"), ("get", "/auth/me"),
    ("get", "/profile"), ("put", "/profile"),
    ("post", "/packages"), ("get", "/packages"), ("get", "/packages/1"),
    ("post", "/files"), ("get", "/files"), ("get", "/files/1/download"), ("delete", "/files/1"),
    ("get", "/stats"), ("get", "/stores"),
    ("post", "/claims"), ("get", "/claims"), ("get", "/claims/1"),
    ("patch", "/claims/1"), ("post", "/claims/1/replies"),
]
BUYER_ONLY = [
    ("get", "/profile"), ("put", "/profile"), ("post", "/packages"), ("get", "/packages"),
    ("get", "/packages/1"), ("post", "/files"), ("get", "/files"), ("delete", "/files/1"),
    ("get", "/stats"), ("get", "/stores"), ("post", "/claims"),
]


def _session_cookie_header(resp) -> str:
    headers = [h for h in resp.headers.get_list("set-cookie") if h.startswith(f"{COOKIE_NAME}=")]
    assert len(headers) == 1, headers
    return headers[0]


def _token(user_id: int, role: str, minutes: int = 60, secret: str | None = None) -> str:
    now = utcnow()
    return jwt.encode(
        {"sub": str(user_id), "role": role, "iat": now, "exp": now + timedelta(minutes=minutes)},
        secret or get_settings().jwt_secret,
        algorithm="HS256",
    )


# --- Register ---

def test_register_berhasil_dan_langsung_masuk(client):
    name = unique_name("baru")
    r = client.post("/auth/register", json={"username": name, "password": "password-ok"})
    assert r.status_code == 201
    body = r.json()
    assert body == {"id": body["id"], "username": name, "role": "buyer", "store_name": None}
    assert client.get("/auth/me").json()["username"] == name

    with SessionLocal() as db:
        user = db.get(User, body["id"])
        assert user.password_hash.startswith("$2b$")
        assert "password-ok" not in user.password_hash
        assert len(user.key_salt) == 16


def test_register_cookie_aman(client):
    r = client.post("/auth/register", json={"username": unique_name(), "password": "password-ok"})
    cookie = _session_cookie_header(r).lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert f"max-age={get_settings().session_minutes * 60}" in cookie


def test_register_key_salt_unik(client):
    ids = [
        client.post("/auth/register", json={"username": unique_name(), "password": "password-ok"}).json()["id"]
        for _ in range(2)
    ]
    with SessionLocal() as db:
        salts = {db.get(User, i).key_salt for i in ids}
    assert len(salts) == 2


def test_register_username_dipakai_400(client):
    name = unique_name("Kembar")
    assert client.post("/auth/register", json={"username": name, "password": "password-ok"}).status_code == 201
    for variant in (name, name.lower(), name.upper()):
        r = client.post("/auth/register", json={"username": variant, "password": "password-ok"})
        assert r.status_code == 400
        assert r.json() == {"detail": "Username sudah dipakai"}


@pytest.mark.parametrize("username, password", [
    ("ab", "password-ok"),
    ("a" * 33, "password-ok"),
    ("pakai spasi", "password-ok"),
    ("titik.titik", "password-ok"),
    ("valid_user", "pendek"),
])
def test_register_format_salah_400(client, username, password):
    r = client.post("/auth/register", json={"username": username, "password": password})
    assert r.status_code == 400
    assert isinstance(r.json()["detail"], str)


# --- Login ---

def test_login_berhasil(client):
    user = create_user()
    r = client.post("/auth/login", json={"username": user.username, "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["id"] == user.id
    _session_cookie_header(r)


def test_login_username_tidak_peka_huruf_besar(client):
    user = create_user()
    r = client.post("/auth/login", json={"username": user.username.upper(), "password": PASSWORD})
    assert r.status_code == 200


@pytest.mark.parametrize("case", ["password_salah", "username_tidak_ada"])
def test_login_salah_401_pesan_generik(client, case):
    user = create_user()
    body = (
        {"username": user.username, "password": "salah-total"}
        if case == "password_salah"
        else {"username": "tidak_ada_orangnya", "password": PASSWORD}
    )
    r = client.post("/auth/login", json=body)
    assert r.status_code == 401
    assert r.json() == {"detail": "Username atau password salah"}
    assert not r.headers.get_list("set-cookie")


def test_password_tidak_masuk_log(client, caplog):
    caplog.set_level(logging.DEBUG)
    name = unique_name()
    client.post("/auth/register", json={"username": name, "password": "penanda-rahasia-xyz"})
    client.post("/auth/login", json={"username": name, "password": "penanda-rahasia-xyz"})
    client.post("/auth/login", json={"username": name, "password": "penanda-salah-xyz"})
    assert "penanda" not in caplog.text


# --- Logout ---

def test_logout_menghapus_cookie(buyer):
    r = buyer.post("/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    cookie = _session_cookie_header(r).lower()
    assert "max-age=0" in cookie or "expires=thu, 01 jan 1970" in cookie
    assert buyer.get("/auth/me").status_code == 401


# --- Tanpa sesi / sesi rusak ---

@pytest.mark.parametrize("method, path", PROTECTED)
def test_endpoint_tanpa_cookie_401(client, method, path):
    r = client.request(method, path)
    assert r.status_code == 401
    assert isinstance(r.json()["detail"], str)


@pytest.mark.parametrize("make_token", [
    lambda u: _token(u.id, u.role, minutes=-1),
    lambda u: _token(u.id, u.role, secret="secret-lain"),
    lambda u: _token(u.id, "store"),
    lambda u: _token(999999, "buyer"),
    lambda u: "bukan.jwt.sama_sekali",
], ids=["kedaluwarsa", "secret_lain", "role_dipalsukan", "user_tidak_ada", "sampah"])
def test_token_tidak_valid_401(make_token):
    user = create_user()
    with TestClient(app, cookies={COOKIE_NAME: make_token(user)}) as c:
        r = c.get("/auth/me")
    assert r.status_code == 401
    assert r.json() == {"detail": "Sesi berakhir, silakan masuk lagi"}


# --- Peran ---

@pytest.mark.parametrize("method, path", BUYER_ONLY)
def test_toko_di_endpoint_pembeli_403(store, method, path):
    assert store.request(method, path).status_code == 403


def test_pembeli_di_endpoint_toko_403(buyer):
    r = buyer.patch("/claims/1", json={"status": "diterima"})
    assert r.status_code == 403
    assert r.json() == {"detail": "Fitur ini hanya untuk admin toko"}


def test_me_toko(store):
    me = store.get("/auth/me").json()
    assert me["role"] == "store"
    assert me["store_name"]


# --- Sesi geser ---

def test_sesi_diperpanjang_setiap_request():
    user = create_user()
    almost_expired = _token(user.id, user.role, minutes=1)
    with TestClient(app, cookies={COOKIE_NAME: almost_expired}) as c:
        r = c.get("/auth/me")
    assert r.status_code == 200
    new_token = _session_cookie_header(r).split(";")[0].split("=", 1)[1]
    exp = jwt.decode(new_token, get_settings().jwt_secret, algorithms=["HS256"])["exp"]
    remaining = exp - utcnow().timestamp()
    assert remaining > (get_settings().session_minutes - 1) * 60
    assert read_token(new_token) == (user.id, user.role)


def test_sesi_diperpanjang_juga_di_response_langsung(buyer):
    # Download mengembalikan Response sendiri; cookie tetap harus diperbarui.
    r = buyer.get("/files/1/download")
    assert r.status_code == 200
    _session_cookie_header(r)


def test_tidak_ada_cookie_baru_kalau_gagal_auth(client):
    r = client.get("/auth/me")
    assert r.status_code == 401
    assert not r.headers.get_list("set-cookie")
