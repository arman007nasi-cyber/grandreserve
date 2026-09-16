from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    phone_number: str | None
    avatar_url: str | None
    preferred_language: str


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    avatar_url: str | None = None
    preferred_language: str | None = None
