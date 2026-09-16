from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReservationCreate(BaseModel):
    table_id: UUID
    slot_start: datetime
    party_size: int = Field(ge=1, le=20)

    # Supplied by the client (e.g. a UUID generated once per "Book" button
    # click). If the same key is sent twice -- double click, retried
    # request after a network blip -- the API returns the original
    # reservation instead of creating a duplicate or throwing an error.
    idempotency_key: str = Field(min_length=8, max_length=100)


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    table_id: UUID
    slot_start: datetime
    party_size: int
    status: str
    created_at: datetime


class ReservationConflict(BaseModel):
    detail: str = "This table is already booked for the selected time slot."
