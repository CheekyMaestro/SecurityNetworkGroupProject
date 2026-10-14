import base64
import os
import tempfile
from pathlib import Path

import pytest

# Env harus siap sebelum modul app diimpor (settings dan engine dibuat saat import).
_TMP = Path(tempfile.mkdtemp(prefix="awan-test-"))
os.environ["MASTER_SECRET"] = base64.b64encode(os.urandom(32)).decode()
os.environ["JWT_SECRET"] = base64.urlsafe_b64encode(os.urandom(32)).decode()
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["STORAGE_DIR"] = str(_TMP / "storage")
os.environ["SESSION_MINUTES"] = "60"

import itertools  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.crypto.keys import new_key_salt  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402

PASSWORD = "rahasia-123"
_seq = itertools.count(1)


def unique_name(prefix: str = "user") -> str:
    return f"{prefix}{next(_seq)}"


def create_user(role: str = "buyer", store_name: str | None = None) -> User:
    with SessionLocal() as db:
        user = User(
            username=unique_name(role),
            password_hash=hash_password(PASSWORD),
            key_salt=new_key_salt(),
            role=role,
            store_name=store_name,
        )
        db.add(user)
        db.commit()
        return user


def login_client(user: User) -> TestClient:
    c = TestClient(app)
    c.__enter__()
    r = c.post("/auth/login", json={"username": user.username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def buyer():
    c = login_client(create_user("buyer"))
    yield c
    c.__exit__(None, None, None)


@pytest.fixture
def store():
    c = login_client(create_user("store", store_name=unique_name("Toko ")))
    yield c
    c.__exit__(None, None, None)


@pytest.fixture
def tmp_root() -> Path:
    return _TMP
