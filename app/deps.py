from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security.sessions import COOKIE_NAME, create_token, read_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Silakan masuk terlebih dahulu")
    claims = read_token(token)
    user = db.get(User, claims[0]) if claims else None
    if user is None or user.role != claims[1]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesi berakhir, silakan masuk lagi")
    # Sesi geser: middleware di main.py memasang cookie baru ini di respons apa pun.
    request.state.refreshed_session = create_token(user.id, user.role)
    return user


def require_buyer(user: User = Depends(get_current_user)) -> User:
    if user.role != "buyer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Fitur ini hanya untuk pembeli")
    return user


def require_store(user: User = Depends(get_current_user)) -> User:
    if user.role != "store":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Fitur ini hanya untuk admin toko")
    return user
