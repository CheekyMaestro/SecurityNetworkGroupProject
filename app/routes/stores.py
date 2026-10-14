from fastapi import APIRouter, Depends

from app import stub_data
from app.deps import require_buyer
from app.schemas import StoreList

router = APIRouter(prefix="/stores", dependencies=[Depends(require_buyer)], tags=["stores"])


@router.get("", response_model=StoreList)
def list_stores():
    return stub_data.STORES
