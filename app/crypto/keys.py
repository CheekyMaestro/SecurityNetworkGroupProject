"""Penurunan key user (HKDF) dan pembuatan kunci file acak. Key tidak pernah disimpan."""

from typing import Literal

from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF
from Crypto.Random import get_random_bytes

from app.crypto import aes, des, rc4

Algorithm = Literal["aes", "rc4", "des"]
ALGORITHMS: tuple[Algorithm, ...] = ("aes", "rc4", "des")

KEY_SALT_SIZE = 16
HKDF_INFO = b"awan-user-v1"
KEY_SIZES: dict[Algorithm, int] = {"aes": aes.KEY_SIZE, "rc4": rc4.KEY_SIZE, "des": des.KEY_SIZE}


def new_key_salt() -> bytes:
    return get_random_bytes(KEY_SALT_SIZE)


def derive_user_keys(key_salt: bytes, master_secret: bytes | None = None) -> dict[Algorithm, bytes]:
    """HKDF-SHA256(MASTER_SECRET, salt=key_salt) 56 byte -> AES 32 | RC4 16 | DES 8."""
    if len(key_salt) != KEY_SALT_SIZE:
        raise ValueError(f"key_salt harus {KEY_SALT_SIZE} byte")
    if master_secret is None:
        from app.config import get_settings

        master_secret = get_settings().master_secret_bytes
    okm = HKDF(master_secret, sum(KEY_SIZES.values()), key_salt, SHA256, context=HKDF_INFO)
    out: dict[Algorithm, bytes] = {}
    pos = 0
    for alg in ALGORITHMS:
        out[alg] = okm[pos : pos + KEY_SIZES[alg]]
        pos += KEY_SIZES[alg]
    return out


def new_file_keys() -> dict[Algorithm, bytes]:
    return {alg: get_random_bytes(KEY_SIZES[alg]) for alg in ALGORITHMS}
