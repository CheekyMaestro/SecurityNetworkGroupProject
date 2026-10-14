from fastapi import APIRouter, status

from app import stub_data
from app.schemas import PackageCreate, PackageDetail, PackageList, PackageOut

router = APIRouter(prefix="/packages", tags=["packages"])


@router.post("", response_model=PackageOut, status_code=status.HTTP_201_CREATED)
def create_package(body: PackageCreate):
    return {**stub_data.PACKAGE, **body.model_dump(), "video_file_id": None,
            "document_count": 0, "total_size_bytes": 0}


@router.get("", response_model=PackageList)
def list_packages():
    return {"items": [stub_data.PACKAGE]}


@router.get("/{package_id}", response_model=PackageDetail)
def get_package(package_id: int):
    return {**stub_data.PACKAGE_DETAIL, "id": package_id}
