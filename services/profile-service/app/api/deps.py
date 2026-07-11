from typing import Any

from fastapi import Header, HTTPException, status

from app.core.security import verify_token


def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return verify_token(authorization.split(" ", 1)[1])
