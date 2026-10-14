import json
import logging
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto.keys import ALGORITHMS, Algorithm, derive_user_keys
from app.crypto.vault import decrypt_bytes, encrypt_bytes
from app.models import File, ProfileCiphertext, User
from app.schemas import ProfileData, ProfileDataOut
from app.timeutil import to_wib_iso, utcnow

log = logging.getLogger("awan.profile")


def _ms_since(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 3)


def latest_id_card_id(db: Session, user_id: int) -> int | None:
    return db.scalar(
        select(File.id)
        .where(File.user_id == user_id, File.category == "id_card")
        .order_by(File.id.desc())
        .limit(1)
    )


def save_profile(db: Session, user: User, data: ProfileData) -> dict:
    plaintext = json.dumps(data.model_dump(), ensure_ascii=False, separators=(",", ":")).encode()
    keys = derive_user_keys(user.key_salt)
    existing = {
        row.algorithm: row
        for row in db.scalars(select(ProfileCiphertext).where(ProfileCiphertext.user_id == user.id))
    }
    now = utcnow()
    enc_ms: dict[str, float] = {}
    for alg in ALGORITHMS:
        start = time.perf_counter()
        iv, ct = encrypt_bytes(alg, keys[alg], plaintext)
        enc_ms[alg] = _ms_since(start)
        row = existing.get(alg) or ProfileCiphertext(user_id=user.id, algorithm=alg)
        row.iv, row.ciphertext, row.enc_time_ms, row.updated_at = iv, ct, enc_ms[alg], now
        db.add(row)
    db.commit()
    log.info("profil disimpan user_id=%s plaintext_bytes=%d", user.id, len(plaintext))
    return {"updated_at": to_wib_iso(now), "enc_ms": enc_ms}


def read_profile(db: Session, user: User, alg: Algorithm) -> dict:
    row = db.scalar(
        select(ProfileCiphertext).where(
            ProfileCiphertext.user_id == user.id, ProfileCiphertext.algorithm == alg
        )
    )
    id_card = latest_id_card_id(db, user.id)
    if row is None:
        return {
            "algorithm": alg, "decrypt_ms": None, "updated_at": None,
            "data": ProfileDataOut().model_dump(), "id_card_file_id": id_card,
        }
    start = time.perf_counter()
    plaintext = decrypt_bytes(alg, derive_user_keys(user.key_salt)[alg], row.iv, row.ciphertext)
    decrypt_ms = _ms_since(start)
    data = ProfileDataOut.model_validate(json.loads(plaintext)).model_dump()
    return {
        "algorithm": alg,
        "decrypt_ms": decrypt_ms,
        "updated_at": to_wib_iso(row.updated_at),
        "data": data,
        "id_card_file_id": id_card,
    }
