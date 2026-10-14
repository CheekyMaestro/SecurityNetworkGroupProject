from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_buyer
from app.models import User
from app.schemas import PackageCreate, PackageDetail, PackageList, PackageOut
from app.services import packages as service

router = APIRouter(prefix="/packages", tags=["packages"])


@router.post("", response_model=PackageOut, status_code=status.HTTP_201_CREATED)
def create_package(body: PackageCreate, user: User = Depends(require_buyer), db: Session = Depends(get_db)):
    return service.create_package(db, user, body)


@router.get("", response_model=PackageList)
def list_packages(user: User = Depends(require_buyer), db: Session = Depends(get_db)):
    return {"items": service.list_packages(db, user)}


@router.get("/{package_id}", response_model=PackageDetail)
def get_package(package_id: int, user: User = Depends(require_buyer), db: Session = Depends(get_db)):
    pkg = service.get_package(db, user, package_id)
    if pkg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paket tidak ditemukan")
    return pkg
