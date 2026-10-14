from fastapi import APIRouter, Depends, status

from app import stub_data
from app.deps import get_current_user, require_buyer, require_store
from app.schemas import (
    ClaimCreate, ClaimCreated, ClaimDetail, ClaimList, ClaimUpdate, ReplyCreate, ReplyOut,
)

router = APIRouter(prefix="/claims", dependencies=[Depends(get_current_user)], tags=["claims"])


@router.post("", response_model=ClaimCreated, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_buyer)])
def create_claim(body: ClaimCreate):
    return {"id": 5, "status": "diajukan"}


@router.get("", response_model=ClaimList)
def list_claims():
    return {"items": [stub_data.CLAIM]}


@router.get("/{claim_id}", response_model=ClaimDetail)
def get_claim(claim_id: int):
    return {**stub_data.CLAIM_DETAIL, "id": claim_id}


@router.patch("/{claim_id}", response_model=ClaimDetail, dependencies=[Depends(require_store)])
def update_claim(claim_id: int, body: ClaimUpdate):
    return {**stub_data.CLAIM_DETAIL, "id": claim_id, "status": body.status}


@router.post("/{claim_id}/replies", response_model=ReplyOut, status_code=status.HTTP_201_CREATED)
def add_reply(claim_id: int, body: ReplyCreate):
    return {**stub_data.REPLY, "body": body.body}
