from fastapi import APIRouter, Depends

from app import stub_data
from app.deps import require_buyer
from app.schemas import Algorithm, ProfileOut, ProfileSaved, ProfileUpdate

router = APIRouter(prefix="/profile", dependencies=[Depends(require_buyer)], tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(alg: Algorithm = "aes"):
    return {**stub_data.PROFILE, "algorithm": alg}


@router.put("", response_model=ProfileSaved)
def put_profile(body: ProfileUpdate):
    return stub_data.PROFILE_SAVED
