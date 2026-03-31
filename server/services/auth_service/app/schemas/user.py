"""Auth schemas — user creation, login, profile update."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password_strength(password: str) -> str:
    """Require at least one uppercase, one lowercase, one digit, and one special character."""
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/~`]", password):
        raise ValueError("Password must contain at least one special character")
    return password


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=72)
    name: str | None = Field(None, max_length=100)

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v):
        return _validate_password_strength(v)


class UserLogin(BaseModel):
    login: str = Field(description="Email or username")
    password: str


class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)
    bio: str | None = Field(None, max_length=1000)

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url_scheme(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("Avatar URL must use http or https scheme")
        return v


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    name: str | None
    avatar_url: str | None
    bio: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PublicUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    name: str | None
    avatar_url: str | None
    bio: str | None
    role: str
    created_at: datetime
