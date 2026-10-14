"""DES-CBC, IV acak 8 byte, PKCS7. Tidak aman untuk sistem nyata; dipakai karena syarat tugas."""

from Crypto.Cipher import DES

from app.crypto._cbc import CbcDecryptor, CbcEncryptor

KEY_SIZE = 8
IV_SIZE = 8


class Encryptor(CbcEncryptor):
    def __init__(self, key: bytes):
        super().__init__(DES, key, KEY_SIZE, "DES")


class Decryptor(CbcDecryptor):
    def __init__(self, key: bytes, iv: bytes):
        super().__init__(DES, key, iv, KEY_SIZE, "DES")
