from fastapi import APIRouter, status

from app import stub_data
from app.schemas import Credentials, LoginRequest, OkOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: Credentials):
    return {**stub_data.USER_BUYER, "username": body.username}


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest):
    return stub_data.USER_BUYER


@router.post("/logout", response_model=OkOut)
def logout():
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me():
    return stub_data.USER_BUYER
