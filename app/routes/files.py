from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from python_multipart.multipart import parse_options_header
from sqlalchemy.orm import Session

from app.crypto.keys import derive_user_keys
from app.db import get_db
from app.deps import get_current_user, require_buyer
from app.models import User
from app.schemas import Algorithm, Category, FileList, FileOut
from app.services import files as service
from app.services.files import MAX_UPLOAD, MB, UploadError

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DOC = {
    "requestBody": {
        "required": True,
        "content": {"multipart/form-data": {"schema": {
            "type": "object",
            "required": ["category", "file"],
            "properties": {
                "category": {"type": "string", "enum": ["id_card", "document", "video"]},
                "package_id": {"type": "integer"},
                "file": {"type": "string", "format": "binary"},
            },
        }}},
    },
}
# Toleransi overhead multipart di atas batas file terbesar.
MAX_BODY = MAX_UPLOAD + MB


def _content_disposition(name: str) -> str:
    fallback = "".join(c if c.isascii() and c.isprintable() and c not in '"\\' else "_" for c in name)
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(name, safe='')}"


@router.post(
    "", response_model=FileOut, status_code=status.HTTP_201_CREATED, openapi_extra=UPLOAD_DOC,
    summary="Upload file (multipart: category, package_id?, file; category dikirim sebelum file)",
)
async def upload_file(request: Request, user: User = Depends(require_buyer), db: Session = Depends(get_db)):
    ctype, opts = parse_options_header(request.headers.get("content-type", ""))
    boundary = opts.get(b"boundary")
    if ctype != b"multipart/form-data" or not boundary:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload harus multipart/form-data")
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BODY:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"Ukuran file maksimal {MAX_UPLOAD // MB} MB")

    upload = service.EncryptedUpload(db, user, boundary)
    stream = request.stream()
    try:
        async for chunk in stream:
            if chunk:
                await run_in_threadpool(upload.feed, chunk)
        stored = await run_in_threadpool(upload.finish)
        f = await run_in_threadpool(service.save_upload, db, user, stored)
    except UploadError as exc:
        upload.cleanup()
        db.rollback()
        # Habiskan sisa body (tanpa diproses) supaya browser menerima 400/413, bukan koneksi terputus.
        drained = 0
        async for chunk in stream:
            drained += len(chunk)
            if drained > MAX_BODY:
                break
        raise HTTPException(exc.status, exc.detail) from None
    except BaseException:
        upload.cleanup()
        db.rollback()
        raise
    return service.file_out(f, derive_user_keys(user.key_salt)["aes"])


@router.get("", response_model=FileList)
def list_files(category: Category | None = None, user: User = Depends(require_buyer), db: Session = Depends(get_db)):
    return {"items": service.list_files(db, user, category)}


@router.get("/{file_id}/download")
def download_file(
    file_id: int, alg: Algorithm = "aes", user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    dl = service.open_download(db, user, file_id, alg)
    if dl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File tidak ditemukan")
    return StreamingResponse(
        dl.chunks,
        media_type=dl.mime_type,
        headers={
            "Content-Disposition": _content_disposition(dl.name),
            "Content-Length": str(dl.size),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: int, user: User = Depends(require_buyer), db: Session = Depends(get_db)):
    if not service.delete_file(db, user, file_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File tidak ditemukan")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
