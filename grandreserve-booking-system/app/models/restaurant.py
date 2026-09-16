import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    opens_at: Mapped[str] = mapped_column(String(5), default="10:00")   # "HH:MM"
    closes_at: Mapped[str] = mapped_column(String(5), default="23:00")

    tables: Mapped[list["Table"]] = relationship(back_populates="restaurant")


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("restaurants.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(30), nullable=False)      # e.g. "T-12"
    seats: Mapped[int] = mapped_column(Integer, default=2)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="tables")
