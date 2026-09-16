from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    seats: int


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str
    opens_at: str
    closes_at: str
    tables: list[TableOut] = []
