from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_buyer
from app.models import User
from app.schemas import StatsOut
from app.services import stats as service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(user: User = Depends(require_buyer), db: Session = Depends(get_db)):
    return service.get_stats(db, user)
