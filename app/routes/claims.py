from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_buyer, require_store
from app.models import User
from app.schemas import (
    ClaimCreate, ClaimCreated, ClaimDetail, ClaimList, ClaimUpdate, ReplyCreate, ReplyOut,
)
from app.services import claims as service
from app.services.claims import ClaimError

router = APIRouter(prefix="/claims", tags=["claims"])


def _run(fn, *args):
    try:
        return fn(*args)
    except ClaimError as exc:
        raise HTTPException(exc.status, exc.detail) from None


@router.post("", response_model=ClaimCreated, status_code=status.HTTP_201_CREATED)
def create_claim(body: ClaimCreate, user: User = Depends(require_buyer), db: Session = Depends(get_db)):
    claim = _run(service.create_claim, db, user, body.package_id, body.store_user_id, body.message)
    return {"id": claim.id, "status": claim.status}


@router.get("", response_model=ClaimList)
def list_claims(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": service.list_claims(db, user)}


@router.get("/{claim_id}", response_model=ClaimDetail)
def get_claim(claim_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _run(service.claim_detail, db, claim_id, user)


@router.patch("/{claim_id}", response_model=ClaimDetail)
def update_claim(claim_id: int, body: ClaimUpdate, user: User = Depends(require_store), db: Session = Depends(get_db)):
    return _run(service.update_status, db, claim_id, user, body.status, body.reply)


@router.post("/{claim_id}/replies", response_model=ReplyOut, status_code=status.HTTP_201_CREATED)
def add_reply(claim_id: int, body: ReplyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _run(service.add_reply, db, claim_id, user, body.body)
