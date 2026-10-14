from fastapi import APIRouter

from app import stub_data
from app.schemas import StatsOut

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats():
    return stub_data.STATS
