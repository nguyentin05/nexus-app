from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import current_user
from app.core.config import settings
from app.core.security import issue_token
from app.events import publish_user_registered
from app.models import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.repositories import authenticate_user, create_user

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> UserResponse:
    user = create_user(payload)
    publish_user_registered(user)
    return UserResponse(**user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = authenticate_user(payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=issue_token(user), expires_in=settings.TOKEN_TTL_SECONDS)


@router.post("/logout")
def logout(_: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
def me(user: dict[str, Any] = Depends(current_user)) -> UserResponse:
    return UserResponse(id=user["sub"], email=user["email"], display_name=user["display_name"])
