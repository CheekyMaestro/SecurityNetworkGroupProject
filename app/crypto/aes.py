"""AES-256-CBC, IV acak 16 byte, PKCS7."""

from Crypto.Cipher import AES

from app.crypto._cbc import CbcDecryptor, CbcEncryptor

KEY_SIZE = 32
IV_SIZE = 16


class Encryptor(CbcEncryptor):
    def __init__(self, key: bytes):
        super().__init__(AES, key, KEY_SIZE, "AES")


class Decryptor(CbcDecryptor):
    def __init__(self, key: bytes, iv: bytes):
        super().__init__(AES, key, iv, KEY_SIZE, "AES")
