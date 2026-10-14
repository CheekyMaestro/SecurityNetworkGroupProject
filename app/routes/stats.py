from fastapi import APIRouter, Depends

from app import stub_data
from app.deps import require_buyer
from app.schemas import StatsOut

router = APIRouter(prefix="/stats", dependencies=[Depends(require_buyer)], tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats():
    return stub_data.STATS
