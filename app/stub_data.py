"""Contoh response sesuai kontrak, dipakai stub fase 1. Dihapus bertahap saat endpoint asli jadi."""

STATS = {
    "per_algorithm": [
        {"algorithm": "aes", "avg_enc_ms_per_mb": 4.1, "avg_dec_ms_per_mb": 3.9, "total_cipher_bytes": 191004672},
        {"algorithm": "rc4", "avg_enc_ms_per_mb": 2.7, "avg_dec_ms_per_mb": 2.6, "total_cipher_bytes": 190601216},
        {"algorithm": "des", "avg_enc_ms_per_mb": 21.8, "avg_dec_ms_per_mb": 21.2, "total_cipher_bytes": 191004680},
    ],
    "per_category": [{"category": "video", "algorithm": "aes", "avg_enc_ms_per_mb": 4.0}],
}
