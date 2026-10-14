import os

import pytest

from app.crypto import keys
from app.crypto.vault import (
    ALGORITHMS,
    StreamDecryptor,
    StreamEncryptor,
    decrypt_bytes,
    encrypt_bytes,
    unwrap_key,
    wrap_key,
)

KB = 1024
SIZES = [0, 1, 15, 16, 17, 64 * KB, 64 * KB + 1, 1024 * KB]
IV_SIZES = {"aes": 16, "rc4": 16, "des": 8}


@pytest.fixture(scope="module")
def payloads():
    return {n: os.urandom(n) for n in SIZES}


def _stream_encrypt(alg, key, data, chunk):
    enc = StreamEncryptor(alg, key)
    out = b"".join(enc.update(data[i : i + chunk]) for i in range(0, len(data), chunk))
    return enc.iv, out + enc.finalize()


def _stream_decrypt(alg, key, iv, data, chunk):
    dec = StreamDecryptor(alg, key, iv)
    out = b"".join(dec.update(data[i : i + chunk]) for i in range(0, len(data), chunk))
    return out + dec.finalize()


@pytest.mark.parametrize("alg", ALGORITHMS)
@pytest.mark.parametrize("size", SIZES)
def test_roundtrip_bytes(alg, size, payloads):
    key = keys.new_file_keys()[alg]
    data = payloads[size]
    iv, ct = encrypt_bytes(alg, key, data)
    assert len(iv) == IV_SIZES[alg]
    assert decrypt_bytes(alg, key, iv, ct) == data


@pytest.mark.parametrize("alg", ALGORITHMS)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("chunk", [1000, 64 * KB])
def test_roundtrip_streaming(alg, size, chunk, payloads):
    if size > 64 * KB + 1 and chunk == 1000:
        chunk = 7777  # tetap potongan ganjil, tapi tidak terlalu lambat
    key = keys.new_file_keys()[alg]
    data = payloads[size]
    iv, ct = _stream_encrypt(alg, key, data, chunk)
    assert _stream_decrypt(alg, key, iv, ct, chunk) == data
    # Format stream dan sekali jalan identik, jadi bisa saling dekripsi.
    assert decrypt_bytes(alg, key, iv, ct) == data


@pytest.mark.parametrize("alg", ALGORITHMS)
def test_streaming_chunk_satu_byte(alg, payloads):
    key = keys.new_file_keys()[alg]
    data = payloads[17]
    iv, ct = _stream_encrypt(alg, key, data, 1)
    assert _stream_decrypt(alg, key, iv, ct, 1) == data


@pytest.mark.parametrize("alg", ALGORITHMS)
@pytest.mark.parametrize("size", [n for n in SIZES if n])
def test_ciphertext_beda_dari_plaintext(alg, size, payloads):
    key = keys.new_file_keys()[alg]
    data = payloads[size]
    _, ct = encrypt_bytes(alg, key, data)
    assert ct != data
    if size >= 16:
        assert data[:16] not in ct


@pytest.mark.parametrize("alg", ALGORITHMS)
def test_dua_enkripsi_data_sama_hasil_beda(alg):
    key = keys.new_file_keys()[alg]
    data = b"Data yang sama persis" * 10
    iv1, ct1 = encrypt_bytes(alg, key, data)
    iv2, ct2 = encrypt_bytes(alg, key, data)
    assert iv1 != iv2
    assert ct1 != ct2


@pytest.mark.parametrize("alg, size, expected", [
    ("aes", 0, 16), ("aes", 15, 16), ("aes", 16, 32), ("aes", 17, 32),
    ("des", 0, 8), ("des", 7, 8), ("des", 8, 16),
    ("rc4", 0, 0), ("rc4", 17, 17),
])
def test_panjang_ciphertext(alg, size, expected):
    _, ct = encrypt_bytes(alg, keys.new_file_keys()[alg], b"a" * size)
    assert len(ct) == expected


def test_rc4_nonce_beda_keystream_beda():
    key = keys.new_file_keys()["rc4"]
    zeros = bytes(64)
    _, ks1 = encrypt_bytes("rc4", key, zeros)
    _, ks2 = encrypt_bytes("rc4", key, zeros)
    assert ks1 != ks2


@pytest.mark.parametrize("alg", ["aes", "des"])
def test_cbc_ciphertext_terpotong_ditolak(alg):
    key = keys.new_file_keys()[alg]
    iv, ct = encrypt_bytes(alg, key, b"x" * 40)
    with pytest.raises(ValueError):
        decrypt_bytes(alg, key, iv, ct[:-1])
    with pytest.raises(ValueError):
        decrypt_bytes(alg, key, iv, b"")


@pytest.mark.parametrize("alg, bad_len", [("aes", 16), ("rc4", 32), ("des", 16)])
def test_panjang_key_salah_ditolak(alg, bad_len):
    with pytest.raises(ValueError):
        encrypt_bytes(alg, os.urandom(bad_len), b"data")


def test_algoritma_tidak_dikenal():
    with pytest.raises(ValueError):
        encrypt_bytes("blowfish", os.urandom(16), b"data")


def test_finalize_dua_kali_ditolak():
    enc = StreamEncryptor("aes", keys.new_file_keys()["aes"])
    enc.finalize()
    with pytest.raises(ValueError):
        enc.finalize()
    with pytest.raises(ValueError):
        enc.update(b"x")


# --- Key user (HKDF) ---

def test_derive_user_keys_panjang_dan_deterministik():
    salt = keys.new_key_salt()
    a = keys.derive_user_keys(salt)
    b = keys.derive_user_keys(salt)
    assert a == b
    assert {k: len(v) for k, v in a.items()} == {"aes": 32, "rc4": 16, "des": 8}
    assert len({a["aes"][:8], a["rc4"][:8], a["des"]}) == 3


def test_derive_user_keys_beda_salt_beda_key():
    assert keys.derive_user_keys(keys.new_key_salt()) != keys.derive_user_keys(keys.new_key_salt())


def test_derive_user_keys_beda_master_beda_key():
    salt = keys.new_key_salt()
    assert keys.derive_user_keys(salt, os.urandom(32)) != keys.derive_user_keys(salt, os.urandom(32))


def test_derive_user_keys_salt_salah_ditolak():
    with pytest.raises(ValueError):
        keys.derive_user_keys(b"pendek")


def test_new_file_keys_acak():
    a, b = keys.new_file_keys(), keys.new_file_keys()
    assert {k: len(v) for k, v in a.items()} == {"aes": 32, "rc4": 16, "des": 8}
    assert all(a[alg] != b[alg] for alg in ALGORITHMS)


# --- Wrap kunci file ---

@pytest.mark.parametrize("alg", ALGORITHMS)
def test_wrap_unwrap_roundtrip(alg):
    kek = keys.derive_user_keys(keys.new_key_salt())["aes"]
    file_key = keys.new_file_keys()[alg]
    nonce, wrapped, tag = wrap_key(kek, file_key)
    assert (len(nonce), len(tag)) == (12, 16)
    assert wrapped != file_key
    assert unwrap_key(kek, nonce, wrapped, tag) == file_key


def test_unwrap_dengan_kek_lain_gagal():
    owner = keys.derive_user_keys(keys.new_key_salt())["aes"]
    other = keys.derive_user_keys(keys.new_key_salt())["aes"]
    nonce, wrapped, tag = wrap_key(owner, keys.new_file_keys()["aes"])
    with pytest.raises(ValueError):
        unwrap_key(other, nonce, wrapped, tag)


def test_unwrap_data_diubah_gagal():
    kek = keys.new_file_keys()["aes"]
    nonce, wrapped, tag = wrap_key(kek, keys.new_file_keys()["aes"])
    tampered = bytes([wrapped[0] ^ 1]) + wrapped[1:]
    with pytest.raises(ValueError):
        unwrap_key(kek, nonce, tampered, tag)


def test_rewrap_untuk_toko():
    """Alur klaim: buka dengan key pemilik, bungkus ulang dengan key toko."""
    owner = keys.derive_user_keys(keys.new_key_salt())["aes"]
    store = keys.derive_user_keys(keys.new_key_salt())["aes"]
    file_key = keys.new_file_keys()["des"]
    for_owner = wrap_key(owner, file_key)
    for_store = wrap_key(store, unwrap_key(owner, *for_owner))
    assert unwrap_key(store, *for_store) == file_key
