from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import current_user
from app.cloudinary import upload_to_cloudinary
from app.models import ProfileResponse, UpdateProfileRequest
from app.repositories import get_profile, update_avatar_url, update_profile

router = APIRouter(tags=["profile"])


@router.get("/me", response_model=ProfileResponse)
def me(user: dict[str, Any] = Depends(current_user)) -> ProfileResponse:
    return ProfileResponse(**get_profile(user))


@router.patch("/me", response_model=ProfileResponse)
def update_me(
    payload: UpdateProfileRequest, user: dict[str, Any] = Depends(current_user)
) -> ProfileResponse:
    return ProfileResponse(**update_profile(user, payload))


@router.post("/avatar", response_model=ProfileResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(current_user),
) -> ProfileResponse:
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Avatar must be <= 5 MiB",
        )
    avatar_url = upload_to_cloudinary(file, contents)
    return ProfileResponse(**update_avatar_url(user, avatar_url))
