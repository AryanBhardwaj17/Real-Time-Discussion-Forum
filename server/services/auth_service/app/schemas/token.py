"""Auth schemas — token and admin-related schemas."""

from pydantic import BaseModel, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RoleUpdate(BaseModel):
    role: str = Field(pattern=r"^(admin|moderator|member)$", description="One of: admin, moderator, member")
