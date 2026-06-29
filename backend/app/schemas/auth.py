from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(
        ...,
        description="User email address.",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password.",
    )
    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Optional display name.",
    )


class LoginRequest(BaseModel):
    email: EmailStr = Field(
        ...,
        description="User email address.",
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User password.",
    )


class AuthUserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str | None = None
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserResponse