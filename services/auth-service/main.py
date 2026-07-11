from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
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

LOGGER = logging.getLogger("auth-service")

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
SQS_QUEUE_URL = os.getenv("USER_EVENTS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))

app = FastAPI(title="Nexus Auth Service", version="0.1.0")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or uuid.uuid4().hex
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, expected = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    actual = hash_password(password, salt).split("$", 2)[2]
    return hmac.compare_digest(actual, expected)


def issue_token(user: dict[str, Any]) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "display_name": user["display_name"],
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64url(signature)}"


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
        LOGGER.warning("database not configured; auth endpoints that need persistence will return 503")
        return
    with db_cursor() as cur:
        cur.execute(
            """
            create table if not exists users (
              id uuid primary key,
              email text unique not null,
              display_name text not null,
              password_hash text not null,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now()
            )
            """
        )


def publish_user_registered(user: dict[str, Any]) -> None:
    if not SQS_QUEUE_URL or boto3 is None:
        LOGGER.info("SQS is not configured; skipping UserRegistered event")
        return
    client = boto3.client("sqs", region_name=AWS_REGION)
    client.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=json.dumps(
            {
                "type": "UserRegistered",
                "user_id": str(user["id"]),
                "email": user["email"],
                "display_name": user["display_name"],
            }
        ),
    )


@app.on_event("startup")
def startup() -> None:
    try:
        init_schema()
    except Exception:
        LOGGER.exception("database schema initialization failed; continuing startup")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "auth-service", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> UserResponse:
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
        user = cur.fetchone()
    publish_user_registered(user)
    return UserResponse(**user)


@app.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    with db_cursor() as cur:
        cur.execute(
            "select id::text, email, display_name, password_hash from users where email = %s",
            (payload.email.lower(),),
        )
        user = cur.fetchone()
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=issue_token(user), expires_in=TOKEN_TTL_SECONDS)


@app.post("/logout")
def logout(_: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    return {"status": "ok"}


@app.get("/me", response_model=UserResponse)
def me(user: dict[str, Any] = Depends(current_user)) -> UserResponse:
    return UserResponse(id=user["sub"], email=user["email"], display_name=user["display_name"])
