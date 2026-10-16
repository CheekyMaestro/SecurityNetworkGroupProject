from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Dipakai saat username tidak ada, supaya waktu respons login sama dan username tidak bisa ditebak.
_DUMMY_HASH = _ctx.hash("awan-dummy-password")


def hash_password(password: str) -> str:
    return _ctx.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _ctx.verify(password, _DUMMY_HASH)
        return False
    try:
        return _ctx.verify(password, password_hash)
    except ValueError:
        return False
