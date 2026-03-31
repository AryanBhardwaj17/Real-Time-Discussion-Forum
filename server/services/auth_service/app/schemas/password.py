"""Auth schemas — password change."""

from pydantic import BaseModel, Field, field_validator

from app.schemas.user import _validate_password_strength


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def check_password_strength(cls, v):
        return _validate_password_strength(v)
