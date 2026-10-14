"""Upload streaming terenkripsi, daftar, unduh, dan hapus file.

Upload dibaca langsung dari body request (bukan UploadFile, yang menyimpan plaintext ke file temporary).
Tiap potongan dienkripsi ke tiga file ciphertext sekaligus; plaintext tidak pernah menyentuh disk.
"""

import logging
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from python_multipart.multipart import MultipartParser, parse_options_header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto.keys import ALGORITHMS, Algorithm, derive_user_keys, new_file_keys
from app.crypto.vault import StreamDecryptor, StreamEncryptor, decrypt_bytes, encrypt_bytes, unwrap_key, wrap_key
from app.models import File, FileCiphertext, FileKey, Package, User
from app.timeutil import to_wib_iso

log = logging.getLogger("awan.files")

CHUNK = 64 * 1024
MB = 1024 * 1024
MAX_FIELD_BYTES = 64
MAX_NAME_CHARS = 200


class UploadError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class CategoryRule:
    label: str
    limit: int
    extensions: dict[str, str]  # ekstensi -> MIME kanonik


RULES: dict[str, CategoryRule] = {
    "id_card": CategoryRule("foto KTP", 5 * MB, {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}),
    "document": CategoryRule("dokumen", 20 * MB, {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }),
    "video": CategoryRule("video", 100 * MB, {"mp4": "video/mp4", "mkv": "video/x-matroska", "mov": "video/quicktime"}),
}
MAX_UPLOAD = max(r.limit for r in RULES.values())

# MIME dari browser tidak bisa dipercaya penuh; selain nilai ini, isi file juga dicek (magic bytes).
DECLARED_ALIASES = {
    "image/jpeg": {"image/jpg", "image/pjpeg"},
    "video/x-matroska": {"video/mkv", "video/webm", "application/x-matroska"},
}
GENERIC_MIMES = {"", "application/octet-stream"}

_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP = b"PK\x03\x04"
_QT_ATOMS = {b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip", b"pnot"}


def _magic_ok(ext: str, head: bytes) -> bool:
    if ext in ("jpg", "jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == "png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == "pdf":
        return head.startswith(b"%PDF-")
    if ext in ("doc", "xls"):
        return head.startswith(_OLE)
    if ext in ("docx", "xlsx"):
        return head.startswith(_ZIP)
    if ext == "mp4":
        return head[4:8] == b"ftyp"
    if ext == "mov":
        return head[4:8] in _QT_ATOMS
    if ext == "mkv":
        return head.startswith(b"\x1a\x45\xdf\xa3")
    return False


def format_hint(category: str) -> str:
    rule = RULES[category]
    exts = ", ".join(sorted({e for e in rule.extensions if e != "jpeg"}))
    return f"Format {rule.label} yang diterima: {exts}"


def size_hint(category: str) -> str:
    rule = RULES[category]
    return f"Ukuran {rule.label} maksimal {rule.limit // MB} MB"


def clean_filename(raw: bytes) -> str:
    name = raw.decode("utf-8", errors="replace").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if ch.isprintable()).strip().strip(".")
    if len(name) > MAX_NAME_CHARS:
        stem, dot, ext = name.rpartition(".")
        name = (stem[: MAX_NAME_CHARS - len(ext) - 1] + dot + ext) if dot else name[:MAX_NAME_CHARS]
    return name or "file"


def storage_root() -> Path:
    return get_settings().storage_dir


def _abs(rel: str) -> Path:
    root = storage_root().resolve()
    path = (root / rel).resolve()
    if root not in path.parents:
        raise ValueError("Path penyimpanan tidak valid")
    return path


# --- Upload ---

@dataclass
class _Writer:
    alg: Algorithm
    enc: StreamEncryptor
    rel_path: str
    fh: BinaryIO
    enc_seconds: float = 0.0
    cipher_bytes: int = 0


@dataclass
class _StoredFile:
    name: str
    category: str
    ext: str
    mime_type: str
    size: int
    package_id: int | None
    file_keys: dict[Algorithm, bytes]
    writers: list[_Writer] = field(default_factory=list)


class EncryptedUpload:
    """Parser multipart streaming. Field `category` (dan `package_id`) harus dikirim sebelum `file`."""

    def __init__(self, db: Session, user: User, boundary: bytes):
        self.db = db
        self.user = user
        self.fields: dict[str, str] = {}
        self.stored: _StoredFile | None = None
        self.paths: list[Path] = []
        self._part_name: str | None = None
        self._part_is_file = False
        self._field_buf = b""
        self._pending = b""
        self._head = b""
        self._magic_checked = False
        self._file_done = False
        self._headers: dict[bytes, bytes] = {}
        self._hname: list[bytes] = []
        self._hvalue: list[bytes] = []
        self._parser = MultipartParser(boundary, {
            "on_part_begin": self._on_part_begin,
            "on_header_field": lambda d, s, e: self._hname.append(d[s:e]),
            "on_header_value": lambda d, s, e: self._hvalue.append(d[s:e]),
            "on_header_end": self._on_header_end,
            "on_headers_finished": self._on_headers_finished,
            "on_part_data": self._on_part_data,
            "on_part_end": self._on_part_end,
        })

    # Dipanggil dari threadpool, satu potongan body per panggilan.
    def feed(self, chunk: bytes) -> None:
        self._parser.write(chunk)

    def finish(self) -> _StoredFile:
        self._parser.finalize()
        if self.stored is None:
            raise UploadError(400, "File wajib dipilih")
        if not self._file_done:
            raise UploadError(400, "Upload tidak lengkap, coba lagi")
        if self.stored.size == 0:
            raise UploadError(400, "File kosong")
        return self.stored

    def cleanup(self) -> None:
        if self.stored:
            for w in self.stored.writers:
                try:
                    w.fh.close()
                except OSError:
                    pass
        for p in self.paths:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                log.warning("gagal hapus ciphertext parsial %s", p.name)

    # --- callback parser ---

    def _on_part_begin(self) -> None:
        self._headers = {}

    def _on_header_end(self) -> None:
        self._headers[b"".join(self._hname).lower()] = b"".join(self._hvalue)
        self._hname.clear()
        self._hvalue.clear()

    def _on_headers_finished(self) -> None:
        _, opts = parse_options_header(self._headers.get(b"content-disposition", b""))
        name = opts.get(b"name", b"").decode("utf-8", errors="replace")
        self._part_name = name
        self._field_buf = b""
        self._part_is_file = name == "file"
        if self._part_is_file:
            self._start_file(opts.get(b"filename", b""), self._headers.get(b"content-type", b""))
        elif name not in ("category", "package_id"):
            raise UploadError(400, f"Field tidak dikenal: {name[:30]}")

    def _on_part_data(self, data: bytes, start: int, end: int) -> None:
        piece = data[start:end]
        if not self._part_is_file:
            self._field_buf += piece
            if len(self._field_buf) > MAX_FIELD_BYTES:
                raise UploadError(400, "Input tidak valid")
            return
        stored = self.stored
        stored.size += len(piece)
        if stored.size > RULES[stored.category].limit:
            raise UploadError(413, size_hint(stored.category))
        if not self._magic_checked:
            self._head += piece[: 16 - len(self._head)]
            if len(self._head) >= 16:
                self._check_magic()
        self._pending += piece
        if len(self._pending) >= CHUNK:
            cut = len(self._pending) - len(self._pending) % CHUNK
            self._encrypt(self._pending[:cut])
            self._pending = self._pending[cut:]

    def _on_part_end(self) -> None:
        if not self._part_is_file:
            self.fields[self._part_name] = self._field_buf.decode("utf-8", errors="replace").strip()
            return
        if self.stored.size and not self._magic_checked:
            self._check_magic()
        if self._pending:
            self._encrypt(self._pending)
            self._pending = b""
        for w in self.stored.writers:
            start = time.perf_counter()
            tail = w.enc.finalize()
            w.enc_seconds += time.perf_counter() - start
            w.fh.write(tail)
            w.cipher_bytes += len(tail)
            w.fh.close()
        self._part_is_file = False
        self._file_done = True

    # --- file ---

    def _start_file(self, raw_name: bytes, declared: bytes) -> None:
        if self.stored is not None:
            raise UploadError(400, "Hanya satu file per upload")
        category = self.fields.get("category")
        if category is None:
            raise UploadError(400, "Field category harus dikirim sebelum file")
        if category not in RULES:
            raise UploadError(400, "Kategori harus id_card, document, atau video")
        package_id = self._package_id(category)

        name = clean_filename(raw_name)
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        rule = RULES[category]
        if ext not in rule.extensions:
            raise UploadError(400, format_hint(category))
        canonical = rule.extensions[ext]
        declared_mime = declared.decode("latin-1").split(";")[0].strip().lower()
        if declared_mime not in GENERIC_MIMES | {canonical} | DECLARED_ALIASES.get(canonical, set()):
            raise UploadError(400, format_hint(category))

        self.stored = _StoredFile(name, category, ext, canonical, 0, package_id, new_file_keys())
        base = uuid.uuid4().hex
        folder = storage_root() / base[:2]
        folder.mkdir(parents=True, exist_ok=True)
        for alg in ALGORITHMS:
            rel = f"{base[:2]}/{base}-{alg}.bin"
            path = folder / f"{base}-{alg}.bin"
            self.paths.append(path)
            fh = open(path, "xb")
            self.stored.writers.append(_Writer(alg, StreamEncryptor(alg, self.stored.file_keys[alg]), rel, fh))

    def _package_id(self, category: str) -> int | None:
        raw = self.fields.get("package_id", "")
        if not raw:
            return None
        if category == "id_card":
            raise UploadError(400, "Foto KTP tidak dikaitkan ke paket")
        try:
            package_id = int(raw)
        except ValueError:
            raise UploadError(400, "package_id harus angka") from None
        pkg = self.db.get(Package, package_id)
        if pkg is None or pkg.user_id != self.user.id:
            raise UploadError(404, "Paket tidak ditemukan")
        return package_id

    def _check_magic(self) -> None:
        self._magic_checked = True
        if not _magic_ok(self.stored.ext, self._head):
            raise UploadError(400, f"Isi file tidak sesuai format .{self.stored.ext}. {format_hint(self.stored.category)}")

    def _encrypt(self, data: bytes) -> None:
        for w in self.stored.writers:
            start = time.perf_counter()
            ct = w.enc.update(data)
            w.enc_seconds += time.perf_counter() - start
            w.fh.write(ct)
            w.cipher_bytes += len(ct)


def save_upload(db: Session, user: User, stored: _StoredFile) -> File:
    aes_key = derive_user_keys(user.key_salt)["aes"]
    name_iv, name_ct = encrypt_bytes("aes", aes_key, stored.name.encode())
    f = File(
        user_id=user.id, package_id=stored.package_id, category=stored.category,
        name_iv=name_iv, name_ciphertext=name_ct, mime_type=stored.mime_type, size_bytes=stored.size,
    )
    for w in stored.writers:
        f.ciphertexts.append(FileCiphertext(
            algorithm=w.alg, iv=w.enc.iv, storage_path=w.rel_path, enc_time_ms=round(w.enc_seconds * 1000, 3),
        ))
        nonce, wrapped, tag = wrap_key(aes_key, stored.file_keys[w.alg])
        f.keys.append(FileKey(user_id=user.id, algorithm=w.alg, wrap_nonce=nonce, wrapped_key=wrapped, wrap_tag=tag))
    db.add(f)
    db.flush()
    from app.services.claims import share_new_file_with_open_claims

    share_new_file_with_open_claims(db, f, user)
    db.commit()
    log.info("upload file_id=%s user_id=%s category=%s size=%d", f.id, user.id, f.category, f.size_bytes)
    return f


# --- Baca ---

def file_name(f: File, owner_aes_key: bytes) -> str:
    return decrypt_bytes("aes", owner_aes_key, f.name_iv, f.name_ciphertext).decode("utf-8", errors="replace")


def file_out(f: File, owner_aes_key: bytes) -> dict:
    order = {alg: i for i, alg in enumerate(ALGORITHMS)}
    return {
        "id": f.id,
        "package_id": f.package_id,
        "category": f.category,
        "name": file_name(f, owner_aes_key),
        "mime_type": f.mime_type,
        "size_bytes": f.size_bytes,
        "created_at": to_wib_iso(f.created_at),
        "algorithms": sorted((c.algorithm for c in f.ciphertexts), key=order.__getitem__),
    }


def list_files(db: Session, user: User, category: str | None) -> list[dict]:
    q = select(File).where(File.user_id == user.id)
    if category:
        q = q.where(File.category == category)
    aes_key = derive_user_keys(user.key_salt)["aes"]
    return [file_out(f, aes_key) for f in db.scalars(q.order_by(File.id.desc()))]


@dataclass
class Download:
    name: str
    mime_type: str
    size: int
    chunks: Iterator[bytes]


def open_download(db: Session, user: User, file_id: int, alg: Algorithm) -> Download | None:
    """None = tidak ada kunci untuk user ini (bukan pemilik dan tidak dibagikan) -> 404."""
    fk = db.scalar(select(FileKey).where(
        FileKey.file_id == file_id, FileKey.user_id == user.id, FileKey.algorithm == alg,
    ))
    if fk is None:
        return None
    f = db.get(File, file_id)
    ct = db.scalar(select(FileCiphertext).where(FileCiphertext.file_id == file_id, FileCiphertext.algorithm == alg))
    if f is None or ct is None:
        return None
    path = _abs(ct.storage_path)
    if not path.is_file():
        log.error("ciphertext hilang file_id=%s alg=%s", file_id, alg)
        return None
    file_key = unwrap_key(derive_user_keys(user.key_salt)["aes"], fk.wrap_nonce, fk.wrapped_key, fk.wrap_tag)
    owner = user if f.user_id == user.id else db.get(User, f.user_id)
    name = file_name(f, derive_user_keys(owner.key_salt)["aes"])
    log.info("download file_id=%s user_id=%s alg=%s", file_id, user.id, alg)
    return Download(name, f.mime_type, f.size_bytes, _decrypt_stream(path, alg, file_key, ct.iv))


def _decrypt_stream(path: Path, alg: Algorithm, key: bytes, iv: bytes) -> Iterator[bytes]:
    dec = StreamDecryptor(alg, key, iv)
    with open(path, "rb") as fh:
        while chunk := fh.read(CHUNK):
            out = dec.update(chunk)
            if out:
                yield out
    tail = dec.finalize()
    if tail:
        yield tail


# --- Hapus ---

def delete_file(db: Session, user: User, file_id: int) -> bool:
    f = db.get(File, file_id)
    if f is None or f.user_id != user.id:
        return False
    paths = [_abs(c.storage_path) for c in f.ciphertexts]
    db.delete(f)
    db.commit()
    for p in paths:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            log.warning("gagal hapus ciphertext file_id=%s", file_id)
    log.info("hapus file_id=%s user_id=%s", file_id, user.id)
    return True
