import uuid
from typing import Any

from fastapi import HTTPException, status

from app.core.db import db_cursor
from app.core.security import hash_password, verify_password
from app.models import LoginRequest, RegisterRequest


def create_user(payload: RegisterRequest) -> dict[str, Any]:
    user_id = str(uuid.uuid4())
    with db_cursor() as cur:
        try:
            cur.execute(
                """
                insert into users (id, email, display_name, password_hash)
                values (%s, %s, %s, %s)
                returning id::text, email, display_name
                """,
                (user_id, payload.email.lower(), payload.display_name, hash_password(payload.password)),
            )
        except Exception as exc:
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc
            raise
        return cur.fetchone()


def authenticate_user(payload: LoginRequest) -> dict[str, Any] | None:
    with db_cursor() as cur:
        cur.execute(
            "select id::text, email, display_name, password_hash from users where email = %s",
            (payload.email.lower(),),
        )
        user = cur.fetchone()
    if not user or not verify_password(payload.password, user["password_hash"]):
        return None
    return user
