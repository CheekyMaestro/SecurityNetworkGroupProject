"""RC4 (ARC4) dengan nonce acak 16 byte. Tidak aman untuk sistem nyata; dipakai karena syarat tugas.

RC4 tidak punya IV, jadi key per ciphertext = 16 byte pertama HMAC-SHA256(key, nonce).
Dengan begitu keystream tidak pernah dipakai ulang walau key dasarnya sama.
"""

import hashlib
import hmac

from Crypto.Cipher import ARC4
from Crypto.Random import get_random_bytes

KEY_SIZE = 16
NONCE_SIZE = 16


def _session_key(key: bytes, nonce: bytes) -> bytes:
    if len(key) != KEY_SIZE:
        raise ValueError(f"Key RC4 harus {KEY_SIZE} byte")
    if len(nonce) != NONCE_SIZE:
        raise ValueError(f"Nonce RC4 harus {NONCE_SIZE} byte")
    return hmac.new(key, nonce, hashlib.sha256).digest()[:KEY_SIZE]


class _Stream:
    def __init__(self, key: bytes, nonce: bytes):
        self._cipher = ARC4.new(_session_key(key, nonce))
        self._done = False

    def update(self, chunk: bytes) -> bytes:
        if self._done:
            raise ValueError("Stream sudah di-finalize")
        return self._cipher.encrypt(chunk)

    def finalize(self) -> bytes:
        if self._done:
            raise ValueError("Stream sudah di-finalize")
        self._done = True
        return b""


class Encryptor(_Stream):
    def __init__(self, key: bytes):
        self.iv = get_random_bytes(NONCE_SIZE)
        super().__init__(key, self.iv)


class Decryptor(_Stream):
    def __init__(self, key: bytes, iv: bytes):
        super().__init__(key, iv)
