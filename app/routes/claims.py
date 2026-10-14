from fastapi import APIRouter, status

from app import stub_data
from app.schemas import (
    ClaimCreate, ClaimCreated, ClaimDetail, ClaimList, ClaimUpdate, ReplyCreate, ReplyOut,
)

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("", response_model=ClaimCreated, status_code=status.HTTP_201_CREATED)
def create_claim(body: ClaimCreate):
    return {"id": 5, "status": "diajukan"}


@router.get("", response_model=ClaimList)
def list_claims():
    return {"items": [stub_data.CLAIM]}


@router.get("/{claim_id}", response_model=ClaimDetail)
def get_claim(claim_id: int):
    return {**stub_data.CLAIM_DETAIL, "id": claim_id}


@router.patch("/{claim_id}", response_model=ClaimDetail)
def update_claim(claim_id: int, body: ClaimUpdate):
    return {**stub_data.CLAIM_DETAIL, "id": claim_id, "status": body.status}


@router.post("/{claim_id}/replies", response_model=ReplyOut, status_code=status.HTTP_201_CREATED)
def add_reply(claim_id: int, body: ReplyCreate):
    return {**stub_data.REPLY, "body": body.body}
