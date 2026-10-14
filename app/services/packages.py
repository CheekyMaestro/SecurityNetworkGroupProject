import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crypto.keys import derive_user_keys
from app.crypto.vault import decrypt_bytes, encrypt_bytes
from app.models import Claim, File, Package, User
from app.schemas import PackageCreate
from app.services.files import file_out
from app.timeutil import to_wib_iso

log = logging.getLogger("awan.packages")


def _meta(pkg: Package, aes_key: bytes) -> dict:
    return json.loads(decrypt_bytes("aes", aes_key, pkg.meta_iv, pkg.meta_ciphertext))


def _summary(pkg: Package, aes_key: bytes) -> dict:
    videos = [f for f in pkg.files if f.category == "video"]
    return {
        "id": pkg.id,
        **_meta(pkg, aes_key),
        "created_at": to_wib_iso(pkg.created_at),
        "video_file_id": max((f.id for f in videos), default=None),
        "document_count": sum(1 for f in pkg.files if f.category == "document"),
        "total_size_bytes": sum(f.size_bytes for f in pkg.files),
    }


def create_package(db: Session, user: User, body: PackageCreate) -> dict:
    aes_key = derive_user_keys(user.key_salt)["aes"]
    meta = {"item_name": body.item_name, "store": body.store, "order_no": body.order_no}
    iv, ct = encrypt_bytes("aes", aes_key, json.dumps(meta, ensure_ascii=False).encode())
    pkg = Package(user_id=user.id, meta_iv=iv, meta_ciphertext=ct)
    db.add(pkg)
    db.commit()
    db.refresh(pkg, ["files"])
    log.info("paket dibuat package_id=%s user_id=%s", pkg.id, user.id)
    return _summary(pkg, aes_key)


def list_packages(db: Session, user: User) -> list[dict]:
    aes_key = derive_user_keys(user.key_salt)["aes"]
    pkgs = db.scalars(
        select(Package).where(Package.user_id == user.id)
        .options(selectinload(Package.files)).order_by(Package.id.desc())
    )
    return [_summary(p, aes_key) for p in pkgs]


def get_package(db: Session, user: User, package_id: int) -> dict | None:
    pkg = db.get(Package, package_id)
    if pkg is None or pkg.user_id != user.id:
        return None
    aes_key = derive_user_keys(user.key_salt)["aes"]
    files = db.scalars(
        select(File).where(File.package_id == pkg.id)
        .options(selectinload(File.ciphertexts)).order_by(File.id)
    ).all()
    claim = db.scalar(
        select(Claim).where(Claim.package_id == pkg.id, Claim.buyer_id == user.id)
        .order_by(Claim.id.desc()).limit(1)
    )
    return {
        "id": pkg.id,
        **_meta(pkg, aes_key),
        "created_at": to_wib_iso(pkg.created_at),
        "files": [file_out(f, aes_key) for f in files],
        "claim": {"id": claim.id, "status": claim.status} if claim else None,
    }
