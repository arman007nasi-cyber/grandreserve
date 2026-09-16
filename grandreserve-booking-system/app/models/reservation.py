import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReservationStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        # Final, database-enforced safety net: even if two requests somehow
        # both pass the application-level lock (e.g. a bug, or the app
        # running on multiple instances without shared Redis), Postgres
        # itself will reject a second CONFIRMED row for the same table
        # and time slot. This is what actually guarantees "no double
        # booking" no matter what -- locks reduce contention, the
        # constraint guarantees correctness.
        UniqueConstraint("table_id", "slot_start", name="uq_table_slot"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    table_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tables.id", ondelete="CASCADE"))

    slot_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, default=2)

    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"), default=ReservationStatus.CONFIRMED
    )

    # A client-supplied key so that a retried/double-clicked request never
    # creates two reservations -- the second attempt just returns the
    # original result instead of erroring or duplicating.
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()          # noqa: F821
    table: Mapped["Table"] = relationship()        # noqa: F821
