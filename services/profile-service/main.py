from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, EmailStr, Field

try:
    import boto3
except ImportError:  # pragma: no cover - local scaffold without optional deps
    boto3 = None

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - local scaffold without optional deps
    psycopg = None
    dict_row = None

LOGGER = logging.getLogger("profile-service")

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
SQS_QUEUE_URL = os.getenv("USER_EVENTS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "nexus/avatars")

app = FastAPI(title="Nexus Profile Service", version="0.1.0")
_stop_consumer = threading.Event()


class ProfileResponse(BaseModel):
    user_id: str
    email: EmailStr
    display_name: str
    avatar_url: str | None = None


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)


def _unb64url(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def verify_token(token: str) -> dict[str, Any]:
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    expected = _b64url(hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    payload = json.loads(_unb64url(body))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return payload


def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return verify_token(authorization.split(" ", 1)[1])


@contextmanager
def db_cursor():
    if not DATABASE_URL or psycopg is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is not configured")
    with psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            yield cur
        conn.commit()


def init_schema() -> None:
    if not DATABASE_URL or psycopg is None:
        LOGGER.warning("database not configured; profile endpoints that need persistence will return 503")
        return
    with db_cursor() as cur:
        cur.execute(
            """
            create table if not exists profiles (
              user_id uuid primary key,
              email text unique not null,
              display_name text not null,
              avatar_url text,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now()
            )
            """
        )


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
    upsert_profile(user["sub"], user["email"], user.get("display_name") or user["email"])
    return {
        "user_id": user["sub"],
        "email": user["email"],
        "display_name": user.get("display_name") or user["email"],
        "avatar_url": None,
    }


def consume_user_events() -> None:
    if not SQS_QUEUE_URL or boto3 is None:
        LOGGER.info("SQS is not configured; profile event consumer disabled")
        return
    client = boto3.client("sqs", region_name=AWS_REGION)
    while not _stop_consumer.is_set():
        try:
            response = client.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=10,
                VisibilityTimeout=30,
            )
            for message in response.get("Messages", []):
                body = json.loads(message["Body"])
                if body.get("type") == "UserRegistered":
                    upsert_profile(body["user_id"], body["email"], body["display_name"])
                client.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=message["ReceiptHandle"])
        except Exception:
            LOGGER.exception("failed to consume user event")
            time.sleep(5)


def upload_to_cloudinary(file: UploadFile, contents: bytes) -> str:
    if not CLOUDINARY_CLOUD_NAME or not CLOUDINARY_API_KEY or not CLOUDINARY_API_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cloudinary is not configured")

    timestamp = str(int(time.time()))
    public_id = f"{uuid.uuid4().hex}-{file.filename or 'avatar'}"
    params = {
        "folder": CLOUDINARY_FOLDER,
        "public_id": public_id,
        "timestamp": timestamp,
    }
    signature_base = "&".join(f"{key}={params[key]}" for key in sorted(params)) + CLOUDINARY_API_SECRET
    signature = hashlib.sha1(signature_base.encode()).hexdigest()
    fields = {
        **params,
        "api_key": CLOUDINARY_API_KEY,
        "signature": signature,
    }

    boundary = uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="file"; filename="{file.filename or "avatar"}"\r\n'.encode()
    )
    body.extend(f"Content-Type: {file.content_type or 'application/octet-stream'}\r\n\r\n".encode())
    body.extend(contents)
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    request = urllib.request.Request(
        f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Cloudinary upload failed: {detail}") from exc
    return payload["secure_url"]


@app.on_event("startup")
def startup() -> None:
    try:
        init_schema()
    except Exception:
        LOGGER.exception("database schema initialization failed; continuing startup")
    threading.Thread(target=consume_user_events, daemon=True).start()


@app.on_event("shutdown")
def shutdown() -> None:
    _stop_consumer.set()


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "profile-service", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/me", response_model=ProfileResponse)
def me(user: dict[str, Any] = Depends(current_user)) -> ProfileResponse:
    return ProfileResponse(**get_profile(user))


@app.patch("/me", response_model=ProfileResponse)
def update_me(payload: UpdateProfileRequest, user: dict[str, Any] = Depends(current_user)) -> ProfileResponse:
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
        updated = cur.fetchone()
    return ProfileResponse(**updated)


@app.post("/avatar", response_model=ProfileResponse)
async def upload_avatar(file: UploadFile = File(...), user: dict[str, Any] = Depends(current_user)) -> ProfileResponse:
    profile = get_profile(user)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Avatar must be <= 5 MiB")
    avatar_url = upload_to_cloudinary(file, contents)
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
        updated = cur.fetchone()
    return ProfileResponse(**updated)
