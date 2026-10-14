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

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def tmp_root() -> Path:
    return _TMP
