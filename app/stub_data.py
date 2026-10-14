"""Contoh response sesuai kontrak, dipakai stub fase 1. Dihapus bertahap saat endpoint asli jadi."""

FILE_VIDEO = {
    "id": 12, "package_id": 3, "category": "video", "name": "unboxing-monitor.mp4",
    "mime_type": "video/mp4", "size_bytes": 190601216, "created_at": "2026-10-11T16:45:00+07:00",
    "algorithms": ["aes", "rc4", "des"],
}

STORES = {"items": [{"id": 21, "store_name": "Toko Elektra"}, {"id": 22, "store_name": "Toko Gadgetin"}]}

CLAIM = {
    "id": 5, "package_id": 3, "item_name": "Monitor 24 inci", "order_no": "INV/2026/10/0412",
    "buyer_name": "Dzaky A.", "store_name": "Toko Elektra", "status": "ditinjau",
    "video_file_id": 12, "created_at": "2026-10-12T14:20:00+07:00",
}

REPLY = {
    "id": 1, "author_role": "store", "author_name": "Toko Elektra",
    "body": "Video sudah kami terima, kami cek ke kurir dulu.", "created_at": "2026-10-13T09:05:00+07:00",
}

CLAIM_DETAIL = {
    "id": 5, "status": "ditinjau", "message": "Layar retak di pojok kanan bawah",
    "created_at": "2026-10-12T14:20:00+07:00",
    "package": {"id": 3, "item_name": "Monitor 24 inci", "order_no": "INV/2026/10/0412"},
    "buyer": {"name": "Dzaky A.", "ktp_verified": True},
    "store": {"id": 21, "store_name": "Toko Elektra"},
    "files": [{k: FILE_VIDEO[k] for k in ("id", "category", "name", "mime_type", "size_bytes")}],
    "replies": [REPLY],
}

STATS = {
    "per_algorithm": [
        {"algorithm": "aes", "avg_enc_ms_per_mb": 4.1, "avg_dec_ms_per_mb": 3.9, "total_cipher_bytes": 191004672},
        {"algorithm": "rc4", "avg_enc_ms_per_mb": 2.7, "avg_dec_ms_per_mb": 2.6, "total_cipher_bytes": 190601216},
        {"algorithm": "des", "avg_enc_ms_per_mb": 21.8, "avg_dec_ms_per_mb": 21.2, "total_cipher_bytes": 191004680},
    ],
    "per_category": [{"category": "video", "algorithm": "aes", "avg_enc_ms_per_mb": 4.0}],
}
