"""CBC + PKCS7 streaming, dipakai bersama oleh AES dan DES."""

from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


def _check_key(key: bytes, key_size: int, name: str) -> None:
    if len(key) != key_size:
        raise ValueError(f"Key {name} harus {key_size} byte")


class CbcEncryptor:
    def __init__(self, cipher_module, key: bytes, key_size: int, name: str):
        _check_key(key, key_size, name)
        self._bs = cipher_module.block_size
        self.iv = get_random_bytes(self._bs)
        self._cipher = cipher_module.new(key, cipher_module.MODE_CBC, iv=self.iv)
        self._buf = b""
        self._done = False

    def update(self, chunk: bytes) -> bytes:
        if self._done:
            raise ValueError("Encryptor sudah di-finalize")
        self._buf += chunk
        cut = len(self._buf) - len(self._buf) % self._bs
        if not cut:
            return b""
        out = self._cipher.encrypt(self._buf[:cut])
        self._buf = self._buf[cut:]
        return out

    def finalize(self) -> bytes:
        if self._done:
            raise ValueError("Encryptor sudah di-finalize")
        self._done = True
        out = self._cipher.encrypt(pad(self._buf, self._bs, style="pkcs7"))
        self._buf = b""
        return out


class CbcDecryptor:
    def __init__(self, cipher_module, key: bytes, iv: bytes, key_size: int, name: str):
        _check_key(key, key_size, name)
        self._bs = cipher_module.block_size
        if len(iv) != self._bs:
            raise ValueError(f"IV {name} harus {self._bs} byte")
        self._cipher = cipher_module.new(key, cipher_module.MODE_CBC, iv=iv)
        self._buf = b""
        self._done = False

    def update(self, chunk: bytes) -> bytes:
        if self._done:
            raise ValueError("Decryptor sudah di-finalize")
        self._buf += chunk
        # Tahan block terakhir: padding baru bisa dibuang di finalize.
        cut = len(self._buf) - len(self._buf) % self._bs
        if cut == len(self._buf):
            cut -= self._bs
        if cut <= 0:
            return b""
        out = self._cipher.decrypt(self._buf[:cut])
        self._buf = self._buf[cut:]
        return out

    def finalize(self) -> bytes:
        if self._done:
            raise ValueError("Decryptor sudah di-finalize")
        self._done = True
        if len(self._buf) != self._bs:
            raise ValueError("Panjang ciphertext tidak valid")
        last = self._cipher.decrypt(self._buf)
        self._buf = b""
        return unpad(last, self._bs, style="pkcs7")
