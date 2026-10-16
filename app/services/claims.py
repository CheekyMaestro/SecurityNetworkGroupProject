"""Klaim ke toko.

Saat klaim dibuat, kunci file paket (kecuali id_card) dibuka dengan key pemilik lalu dibungkus ulang
untuk toko tujuan. Pesan, balasan, dan ringkasan klaim dienkripsi dengan kunci klaim acak yang dibungkus
untuk pembeli dan toko. Data profil tidak pernah dibungkus untuk toko.
"""

import json
import logging

from Crypto.Random import get_random_bytes
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto.keys import derive_user_keys
from app.crypto.vault import decrypt_bytes, encrypt_bytes, unwrap_key, wrap_key
from app.models import Claim, ClaimKey, ClaimReply, File, FileKey, Package, User
from app.services.files import file_name
from app.services.profile import read_profile
from app.timeutil import to_wib_iso, utcnow

log = logging.getLogger("awan.claims")

OPEN_STATUSES = ("diajukan", "ditinjau")


class ClaimError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _aes_key(user: User) -> bytes:
    return derive_user_keys(user.key_salt)["aes"]


def _wrap_claim_key(claim_key: bytes, user: User) -> ClaimKey:
    nonce, wrapped, tag = wrap_key(_aes_key(user), claim_key)
    return ClaimKey(user_id=user.id, wrap_nonce=nonce, wrapped_key=wrapped, wrap_tag=tag)


def share_file_with(db: Session, f: File, owner_aes: bytes, recipient: User) -> int:
    """Bungkus ulang kunci file untuk penerima. Return jumlah baris file_keys baru."""
    if f.category == "id_card":
        return 0
    existing = set(db.scalars(
        select(FileKey.algorithm).where(FileKey.file_id == f.id, FileKey.user_id == recipient.id)
    ))
    recipient_aes = _aes_key(recipient)
    added = 0
    for fk in db.scalars(select(FileKey).where(FileKey.file_id == f.id, FileKey.user_id == f.user_id)):
        if fk.algorithm in existing:
            continue
        file_key = unwrap_key(owner_aes, fk.wrap_nonce, fk.wrapped_key, fk.wrap_tag)
        nonce, wrapped, tag = wrap_key(recipient_aes, file_key)
        db.add(FileKey(file_id=f.id, user_id=recipient.id, algorithm=fk.algorithm,
                       wrap_nonce=nonce, wrapped_key=wrapped, wrap_tag=tag))
        added += 1
    return added


def share_new_file_with_open_claims(db: Session, f: File, owner: User) -> None:
    """File yang ditambahkan ke paket dengan klaim berjalan (mis. bukti tambahan) ikut dibagikan."""
    if f.package_id is None or f.category == "id_card":
        return
    claims = db.scalars(select(Claim).where(Claim.package_id == f.package_id, Claim.status.in_(OPEN_STATUSES)))
    owner_aes = _aes_key(owner)
    for claim in claims:
        share_file_with(db, f, owner_aes, db.get(User, claim.store_user_id))


def _buyer_name(db: Session, buyer: User) -> str:
    return read_profile(db, buyer, "aes")["data"]["full_name"] or buyer.username


def create_claim(db: Session, buyer: User, package_id: int, store_user_id: int, message: str) -> Claim:
    pkg = db.get(Package, package_id)
    if pkg is None or pkg.user_id != buyer.id:
        raise ClaimError(404, "Paket tidak ditemukan")
    store = db.get(User, store_user_id)
    if store is None or store.role != "store":
        raise ClaimError(404, "Toko tidak ditemukan")
    if db.scalar(select(Claim.id).where(Claim.package_id == pkg.id, Claim.status.in_(OPEN_STATUSES))):
        raise ClaimError(400, "Paket ini masih punya klaim yang berjalan")
    files = [f for f in pkg.files if f.category != "id_card"]
    if not files:
        raise ClaimError(400, "Tambahkan video atau dokumen ke paket sebelum mengajukan klaim")

    buyer_aes = _aes_key(buyer)
    meta = json.loads(decrypt_bytes("aes", buyer_aes, pkg.meta_iv, pkg.meta_ciphertext))
    summary = {"buyer_name": _buyer_name(db, buyer), "item_name": meta["item_name"], "order_no": meta["order_no"]}

    claim_key = get_random_bytes(32)
    message_iv, message_ct = encrypt_bytes("aes", claim_key, message.encode())
    summary_iv, summary_ct = encrypt_bytes("aes", claim_key, json.dumps(summary, ensure_ascii=False).encode())
    claim = Claim(
        package_id=pkg.id, buyer_id=buyer.id, store_user_id=store.id, status="diajukan",
        message_iv=message_iv, message_ciphertext=message_ct,
        summary_iv=summary_iv, summary_ciphertext=summary_ct,
    )
    claim.keys.extend([_wrap_claim_key(claim_key, buyer), _wrap_claim_key(claim_key, store)])
    db.add(claim)
    shared = sum(share_file_with(db, f, buyer_aes, store) for f in files)
    db.commit()
    log.info("klaim dibuat claim_id=%s package_id=%s store_id=%s file_keys_baru=%d",
             claim.id, pkg.id, store.id, shared)
    return claim


# --- Baca ---

def _claim_key_for(db: Session, claim: Claim, user: User) -> bytes | None:
    ck = db.scalar(select(ClaimKey).where(ClaimKey.claim_id == claim.id, ClaimKey.user_id == user.id))
    if ck is None:
        return None
    return unwrap_key(_aes_key(user), ck.wrap_nonce, ck.wrapped_key, ck.wrap_tag)


def _visible_files(db: Session, claim: Claim, viewer: User) -> list[File]:
    """File paket yang kuncinya dimiliki viewer. id_card tidak pernah termasuk."""
    return list(db.scalars(
        select(File)
        .where(File.package_id == claim.package_id, File.category != "id_card",
               File.id.in_(select(FileKey.file_id).where(FileKey.user_id == viewer.id)))
        .order_by(File.id)
    ))


def _summary(claim: Claim, claim_key: bytes) -> dict:
    return json.loads(decrypt_bytes("aes", claim_key, claim.summary_iv, claim.summary_ciphertext))


def _item(db: Session, claim: Claim, viewer: User, claim_key: bytes) -> dict:
    summary = _summary(claim, claim_key)
    videos = [f.id for f in _visible_files(db, claim, viewer) if f.category == "video"]
    return {
        "id": claim.id,
        "package_id": claim.package_id,
        "item_name": summary["item_name"],
        "order_no": summary["order_no"],
        "buyer_name": summary["buyer_name"],
        "store_name": db.get(User, claim.store_user_id).store_name,
        "status": claim.status,
        "video_file_id": max(videos, default=None),
        "created_at": to_wib_iso(claim.created_at),
    }


def list_claims(db: Session, viewer: User) -> list[dict]:
    column = Claim.store_user_id if viewer.role == "store" else Claim.buyer_id
    items = []
    for claim in db.scalars(select(Claim).where(column == viewer.id).order_by(Claim.id.desc())):
        key = _claim_key_for(db, claim, viewer)
        if key is not None:
            items.append(_item(db, claim, viewer, key))
    return items


def _get_for(db: Session, claim_id: int, viewer: User) -> tuple[Claim, bytes]:
    claim = db.get(Claim, claim_id)
    if claim is None or viewer.id not in (claim.buyer_id, claim.store_user_id):
        raise ClaimError(404, "Klaim tidak ditemukan")
    key = _claim_key_for(db, claim, viewer)
    if key is None:
        raise ClaimError(404, "Klaim tidak ditemukan")
    return claim, key


def _reply_out(db: Session, reply: ClaimReply, claim: Claim, claim_key: bytes, summary: dict) -> dict:
    author = db.get(User, reply.author_id)
    return {
        "id": reply.id,
        "author_role": author.role,
        "author_name": author.store_name if author.role == "store" else summary["buyer_name"],
        "body": decrypt_bytes("aes", claim_key, reply.body_iv, reply.body_ciphertext).decode(),
        "created_at": to_wib_iso(reply.created_at),
    }


def claim_detail(db: Session, claim_id: int, viewer: User) -> dict:
    claim, key = _get_for(db, claim_id, viewer)
    summary = _summary(claim, key)
    buyer = db.get(User, claim.buyer_id)
    store = db.get(User, claim.store_user_id)
    buyer_aes = _aes_key(buyer)
    ktp = db.scalar(select(File.id).where(File.user_id == buyer.id, File.category == "id_card").limit(1))
    return {
        "id": claim.id,
        "status": claim.status,
        "message": decrypt_bytes("aes", key, claim.message_iv, claim.message_ciphertext).decode(),
        "created_at": to_wib_iso(claim.created_at),
        "package": {"id": claim.package_id, "item_name": summary["item_name"], "order_no": summary["order_no"]},
        "buyer": {"name": summary["buyer_name"], "ktp_verified": ktp is not None},
        "store": {"id": store.id, "store_name": store.store_name},
        "files": [
            {"id": f.id, "category": f.category, "name": file_name(f, buyer_aes),
             "mime_type": f.mime_type, "size_bytes": f.size_bytes}
            for f in _visible_files(db, claim, viewer)
        ],
        "replies": [_reply_out(db, r, claim, key, summary) for r in claim.replies],
    }


# --- Ubah ---

def _add_reply(db: Session, claim: Claim, claim_key: bytes, author: User, body: str) -> ClaimReply:
    iv, ct = encrypt_bytes("aes", claim_key, body.encode())
    reply = ClaimReply(claim_id=claim.id, author_id=author.id, body_iv=iv, body_ciphertext=ct)
    db.add(reply)
    claim.updated_at = utcnow()
    return reply


def update_status(db: Session, claim_id: int, store: User, status: str, reply: str | None) -> dict:
    claim, key = _get_for(db, claim_id, store)
    if claim.store_user_id != store.id:
        raise ClaimError(404, "Klaim tidak ditemukan")
    claim.status = status
    claim.updated_at = utcnow()
    if reply and reply.strip():
        _add_reply(db, claim, key, store, reply.strip())
    db.commit()
    db.expire_all()
    log.info("status klaim claim_id=%s status=%s", claim.id, status)
    return claim_detail(db, claim.id, store)


def add_reply(db: Session, claim_id: int, author: User, body: str) -> dict:
    claim, key = _get_for(db, claim_id, author)
    reply = _add_reply(db, claim, key, author, body)
    db.commit()
    log.info("balasan klaim claim_id=%s author_id=%s", claim.id, author.id)
    return _reply_out(db, reply, claim, key, _summary(claim, key))
