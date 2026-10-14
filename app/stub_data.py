"""Contoh response sesuai kontrak, dipakai stub fase 1. Dihapus bertahap saat endpoint asli jadi."""

PROFILE = {
    "algorithm": "aes",
    "decrypt_ms": 0.42,
    "updated_at": "2026-10-14T10:12:00+07:00",
    "data": {
        "full_name": "Dzaky A.", "nik": "3578xxxxxxxxxxxx", "birth_date": "2004-05-12",
        "gender": "Laki-laki", "nationality": "WNI", "marital_status": "Belum kawin",
        "address": "Jl. Contoh No. 12, Surabaya", "phone": "0812xxxxxxxx",
        "bank_account": "BCA 1234xxxxxx", "religion": None, "health_notes": None,
    },
    "id_card_file_id": 7,
}

PROFILE_SAVED = {"updated_at": "2026-10-14T10:12:00+07:00", "enc_ms": {"aes": 0.31, "rc4": 0.12, "des": 0.55}}

PACKAGE = {
    "id": 3, "item_name": "Monitor 24 inci", "store": "Toko Elektra",
    "order_no": "INV/2026/10/0412", "created_at": "2026-10-11T16:45:00+07:00",
    "video_file_id": 12, "document_count": 2, "total_size_bytes": 190840112,
}

FILE_VIDEO = {
    "id": 12, "package_id": 3, "category": "video", "name": "unboxing-monitor.mp4",
    "mime_type": "video/mp4", "size_bytes": 190601216, "created_at": "2026-10-11T16:45:00+07:00",
    "algorithms": ["aes", "rc4", "des"],
}

FILE_INVOICE = {
    "id": 13, "package_id": 3, "category": "document", "name": "invoice-elektra.pdf",
    "mime_type": "application/pdf", "size_bytes": 2888, "created_at": "2026-10-11T16:46:00+07:00",
    "algorithms": ["aes", "rc4", "des"],
}

FILE_CHRONO = {
    "id": 14, "package_id": 3, "category": "document", "name": "kronologi.docx",
    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "size_bytes": 56552, "created_at": "2026-10-11T16:47:00+07:00",
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

PACKAGE_DETAIL = {
    **{k: PACKAGE[k] for k in ("id", "item_name", "store", "order_no", "created_at")},
    "files": [FILE_VIDEO, FILE_INVOICE, FILE_CHRONO],
    "claim": {"id": 5, "status": "ditinjau"},
}

STATS = {
    "per_algorithm": [
        {"algorithm": "aes", "avg_enc_ms_per_mb": 4.1, "avg_dec_ms_per_mb": 3.9, "total_cipher_bytes": 191004672},
        {"algorithm": "rc4", "avg_enc_ms_per_mb": 2.7, "avg_dec_ms_per_mb": 2.6, "total_cipher_bytes": 190601216},
        {"algorithm": "des", "avg_enc_ms_per_mb": 21.8, "avg_dec_ms_per_mb": 21.2, "total_cipher_bytes": 191004680},
    ],
    "per_category": [{"category": "video", "algorithm": "aes", "avg_enc_ms_per_mb": 4.0}],
}
