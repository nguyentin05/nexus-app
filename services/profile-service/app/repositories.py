from typing import Any

from app.core.db import db_cursor
from app.models import UpdateProfileRequest


def upsert_profile(user_id: str, email: str, display_name: str) -> None:
    with db_cursor() as cur:
        cur.execute(
            """
            insert into profiles (user_id, email, display_name)
            values (%s, %s, %s)
            on conflict (user_id) do update set
              email = excluded.email,
              display_name = excluded.display_name,
              updated_at = now()
            """,
            (user_id, email.lower(), display_name),
        )


def get_profile(user: dict[str, Any]) -> dict[str, Any]:
    with db_cursor() as cur:
        cur.execute(
            "select user_id::text, email, display_name, avatar_url from profiles where user_id = %s",
            (user["sub"],),
        )
        profile = cur.fetchone()
    if profile:
        return profile
    display_name = user.get("display_name") or user["email"]
    upsert_profile(user["sub"], user["email"], display_name)
    return {
        "user_id": user["sub"],
        "email": user["email"],
        "display_name": display_name,
        "avatar_url": None,
    }


def update_profile(
    user: dict[str, Any], payload: UpdateProfileRequest
) -> dict[str, Any]:
    profile = get_profile(user)
    with db_cursor() as cur:
        cur.execute(
            """
            update profiles
            set display_name = %s, updated_at = now()
            where user_id = %s
            returning user_id::text, email, display_name, avatar_url
            """,
            (payload.display_name, profile["user_id"]),
        )
        return cur.fetchone()


def update_avatar_url(user: dict[str, Any], avatar_url: str) -> dict[str, Any]:
    profile = get_profile(user)
    with db_cursor() as cur:
        cur.execute(
            """
            update profiles
            set avatar_url = %s, updated_at = now()
            where user_id = %s
            returning user_id::text, email, display_name, avatar_url
            """,
            (avatar_url, profile["user_id"]),
        )
        return cur.fetchone()
