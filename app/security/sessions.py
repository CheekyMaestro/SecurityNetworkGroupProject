"""JWT HS256 di cookie `session` (HttpOnly, SameSite=Lax)."""

from datetime import timedelta

import jwt
from starlette.responses import Response

from app.config import get_settings
from app.timeutil import utcnow

COOKIE_NAME = "session"
ALGORITHM = "HS256"


def create_token(user_id: int, role: str) -> str:
    settings = get_settings()
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.session_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def read_token(token: str) -> tuple[int, str] | None:
    """Return (user_id, role), atau None kalau token tidak valid/kedaluwarsa."""
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "role"]},
        )
        return int(payload["sub"]), str(payload["role"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=get_settings().session_minutes * 60,
        path="/",
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")


def response_sets_session(response: Response) -> bool:
    prefix = f"{COOKIE_NAME}=".encode()
    return any(k == b"set-cookie" and v.startswith(prefix) for k, v in response.headers.raw)
