from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_buyer
from app.models import User
from app.schemas import StoreList

router = APIRouter(prefix="/stores", tags=["stores"], dependencies=[Depends(require_buyer)])


@router.get("", response_model=StoreList)
def list_stores(db: Session = Depends(get_db)):
    stores = db.scalars(select(User).where(User.role == "store").order_by(User.store_name))
    return {"items": [{"id": s.id, "store_name": s.store_name} for s in stores]}
