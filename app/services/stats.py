"""Statistik waktu dan ukuran per algoritma untuk file milik pembeli.

Rata-rata per MB dihitung tertimbang (total ms / total MB), supaya file kecil dengan overhead tetap
tidak mendominasi angka.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crypto.keys import ALGORITHMS
from app.models import DecryptLog, File, FileCiphertext, User

MB = 1024 * 1024
CATEGORY_ORDER = ("video", "document", "id_card")
BLOCK = {"aes": 16, "des": 8}


def cipher_size(alg: str, size: int) -> int:
    """Ukuran ciphertext di disk: CBC + PKCS7 selalu menambah 1..block byte, RC4 sama dengan aslinya."""
    block = BLOCK.get(alg)
    return size if block is None else (size // block + 1) * block


def _per_mb(ms: float | None, size: int | None) -> float | None:
    if ms is None or not size:
        return None
    return round(ms / (size / MB), 3)


def get_stats(db: Session, user: User) -> dict:
    enc_rows = db.execute(
        select(File.category, FileCiphertext.algorithm, File.size_bytes, FileCiphertext.enc_time_ms)
        .join(FileCiphertext, FileCiphertext.file_id == File.id)
        .where(File.user_id == user.id)
    ).all()
    dec_rows = dict(
        (alg, (ms, size)) for alg, ms, size in db.execute(
            select(DecryptLog.algorithm, func.sum(DecryptLog.dec_time_ms), func.sum(DecryptLog.size_bytes))
            .join(File, File.id == DecryptLog.file_id)
            .where(File.user_id == user.id)
            .group_by(DecryptLog.algorithm)
        ).all()
    )

    enc_total: dict[str, list[float]] = {alg: [0.0, 0, 0] for alg in ALGORITHMS}  # ms, size, cipher
    by_cat: dict[tuple[str, str], list[float]] = {}
    for category, alg, size, ms in enc_rows:
        t = enc_total[alg]
        t[0] += ms
        t[1] += size
        t[2] += cipher_size(alg, size)
        c = by_cat.setdefault((category, alg), [0.0, 0])
        c[0] += ms
        c[1] += size

    per_algorithm = []
    for alg in ALGORITHMS:
        ms, size, cipher = enc_total[alg]
        dec_ms, dec_size = dec_rows.get(alg, (None, None))
        per_algorithm.append({
            "algorithm": alg,
            "avg_enc_ms_per_mb": _per_mb(ms, size),
            "avg_dec_ms_per_mb": _per_mb(dec_ms, dec_size),
            "total_cipher_bytes": int(cipher),
        })

    per_category = [
        {"category": cat, "algorithm": alg, "avg_enc_ms_per_mb": _per_mb(*by_cat[(cat, alg)])}
        for cat in CATEGORY_ORDER for alg in ALGORITHMS if (cat, alg) in by_cat
    ]
    return {"per_algorithm": per_algorithm, "per_category": per_category}
