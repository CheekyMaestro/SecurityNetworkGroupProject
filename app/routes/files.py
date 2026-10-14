from fastapi import APIRouter, Depends, Form, Response, UploadFile, status

from app import stub_data
from app.deps import get_current_user, require_buyer
from app.schemas import Algorithm, Category, FileList, FileOut

router = APIRouter(prefix="/files", dependencies=[Depends(get_current_user)], tags=["files"])


@router.post("", response_model=FileOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_buyer)])
def upload_file(file: UploadFile, category: Category = Form(), package_id: int | None = Form(None)):
    return {**stub_data.FILE_VIDEO, "category": category, "package_id": package_id,
            "name": file.filename or "file", "mime_type": file.content_type or "application/octet-stream"}


@router.get("", response_model=FileList, dependencies=[Depends(require_buyer)])
def list_files(category: Category | None = None):
    items = [stub_data.FILE_VIDEO, stub_data.FILE_INVOICE, stub_data.FILE_CHRONO]
    return {"items": [f for f in items if category is None or f["category"] == category]}


@router.get("/{file_id}/download")
def download_file(file_id: int, alg: Algorithm = "aes"):
    return Response(
        content=f"stub file {file_id} ({alg})\n".encode(),
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="stub.txt"'},
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_buyer)])
def delete_file(file_id: int):
    return Response(status_code=status.HTTP_204_NO_CONTENT)
