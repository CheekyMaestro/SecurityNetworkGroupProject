from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_buyer
from app.models import User
from app.schemas import Algorithm, ProfileOut, ProfileSaved, ProfileUpdate
from app.services import profile as service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(alg: Algorithm = "aes", user: User = Depends(require_buyer), db: Session = Depends(get_db)):
    return service.read_profile(db, user, alg)


@router.put("", response_model=ProfileSaved)
def put_profile(body: ProfileUpdate, user: User = Depends(require_buyer), db: Session = Depends(get_db)):
    return service.save_profile(db, user, body.data)
