"""Interface enkripsi yang dipakai backend.

encrypt_bytes / decrypt_bytes untuk data kecil (profil, metadata, nama file, pesan).
StreamEncryptor / StreamDecryptor untuk file, diumpankan per potongan.
wrap_key / unwrap_key membungkus kunci file dengan AES-256-GCM.
"""

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from app.crypto import aes, des, rc4
from app.crypto.keys import ALGORITHMS, Algorithm

_MODULES = {"aes": aes, "rc4": rc4, "des": des}

WRAP_NONCE_SIZE = 12
WRAP_TAG_SIZE = 16


def _module(alg: str):
    try:
        return _MODULES[alg]
    except KeyError:
        raise ValueError(f"Algoritma tidak dikenal: {alg!r}") from None


class StreamEncryptor:
    def __init__(self, alg: Algorithm, key: bytes):
        self.alg = alg
        self._impl = _module(alg).Encryptor(key)
        self.iv: bytes = self._impl.iv

    def update(self, chunk: bytes) -> bytes:
        return self._impl.update(chunk)

    def finalize(self) -> bytes:
        return self._impl.finalize()


class StreamDecryptor:
    def __init__(self, alg: Algorithm, key: bytes, iv: bytes):
        self.alg = alg
        self._impl = _module(alg).Decryptor(key, iv)

    def update(self, chunk: bytes) -> bytes:
        return self._impl.update(chunk)

    def finalize(self) -> bytes:
        return self._impl.finalize()


def encrypt_bytes(alg: Algorithm, key: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    enc = StreamEncryptor(alg, key)
    return enc.iv, enc.update(plaintext) + enc.finalize()


def decrypt_bytes(alg: Algorithm, key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    dec = StreamDecryptor(alg, key, iv)
    return dec.update(ciphertext) + dec.finalize()


def wrap_key(kek: bytes, key: bytes) -> tuple[bytes, bytes, bytes]:
    """Bungkus kunci file dengan key AES penerima. Return (nonce, wrapped, tag)."""
    if len(kek) != aes.KEY_SIZE:
        raise ValueError(f"KEK harus {aes.KEY_SIZE} byte")
    nonce = get_random_bytes(WRAP_NONCE_SIZE)
    cipher = AES.new(kek, AES.MODE_GCM, nonce=nonce, mac_len=WRAP_TAG_SIZE)
    wrapped, tag = cipher.encrypt_and_digest(key)
    return nonce, wrapped, tag


def unwrap_key(kek: bytes, nonce: bytes, wrapped: bytes, tag: bytes) -> bytes:
    """Raise ValueError kalau KEK salah atau data bungkus diubah."""
    if len(kek) != aes.KEY_SIZE:
        raise ValueError(f"KEK harus {aes.KEY_SIZE} byte")
    cipher = AES.new(kek, AES.MODE_GCM, nonce=nonce, mac_len=WRAP_TAG_SIZE)
    return cipher.decrypt_and_verify(wrapped, tag)


__all__ = [
    "ALGORITHMS", "Algorithm", "StreamEncryptor", "StreamDecryptor",
    "encrypt_bytes", "decrypt_bytes", "wrap_key", "unwrap_key",
]
