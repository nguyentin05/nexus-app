from pydantic import BaseModel, EmailStr, Field


class ProfileResponse(BaseModel):
    user_id: str
    email: EmailStr
    display_name: str
    avatar_url: str | None = None


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
