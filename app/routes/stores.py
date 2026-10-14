from fastapi import APIRouter

from app import stub_data
from app.schemas import StoreList

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=StoreList)
def list_stores():
    return stub_data.STORES
