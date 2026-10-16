import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crypto.keys import new_key_salt
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import Credentials, LoginRequest, OkOut, UserOut
from app.security.passwords import hash_password, verify_password
from app.security.sessions import clear_session_cookie, create_token, set_session_cookie

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("awan.auth")

LOGIN_FAILED = "Username atau password salah"


def _find_user(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.username) == username.lower()))


def _user_out(user: User) -> dict:
    return {"id": user.id, "username": user.username, "role": user.role, "store_name": user.store_name}


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: Credentials, response: Response, db: Session = Depends(get_db)):
    if _find_user(db, body.username):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username sudah dipakai")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        key_salt=new_key_salt(),
        role="buyer",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username sudah dipakai") from None
    log.info("register user_id=%s", user.id)
    set_session_cookie(response, create_token(user.id, user.role))
    return _user_out(user)


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = _find_user(db, body.username)
    if not verify_password(body.password, user.password_hash if user else None):
        log.info("login gagal")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, LOGIN_FAILED)
    log.info("login user_id=%s", user.id)
    set_session_cookie(response, create_token(user.id, user.role))
    return _user_out(user)


@router.post("/logout", response_model=OkOut)
def logout(response: Response, user: User = Depends(get_current_user)):
    clear_session_cookie(response)
    log.info("logout user_id=%s", user.id)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)
