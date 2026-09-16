import json
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reservation import Reservation, ReservationStatus
from app.models.restaurant import Table
from app.schemas.reservation import ReservationCreate
from app.services.redis_client import TableLock, redis_client

TABLE_STATUS_CHANNEL = "table_status_updates"


async def create_reservation(db: AsyncSession, user_id: UUID, payload: ReservationCreate) -> Reservation:
    slot_key = payload.slot_start.isoformat()

    # 1) Idempotency check first: if this exact request was already
    #    processed (e.g. the client retried after a timed-out response),
    #    hand back the original reservation instead of erroring or
    #    creating a duplicate booking.
    existing = await db.scalar(
        select(Reservation).where(Reservation.idempotency_key == payload.idempotency_key)
    )
    if existing:
        return existing

    # 2) Fast-fail lock: only one concurrent request per (table, slot)
    #    gets past this point. This is what keeps 99 out of 100
    #    simultaneous requests from ever reaching the database.
    async with TableLock(str(payload.table_id), slot_key) as acquired:
        if not acquired:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Someone else is booking this table right now. Please try another table or time.",
            )

        table = await db.get(Table, payload.table_id)
        if table is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Table not found.")

        # 3) Re-check inside the transaction (belt-and-suspenders: the
        #    Redis lock could theoretically have expired under extreme
        #    load before we get here).
        conflict = await db.scalar(
            select(Reservation).where(
                Reservation.table_id == payload.table_id,
                Reservation.slot_start == payload.slot_start,
                Reservation.status == ReservationStatus.CONFIRMED,
            )
        )
        if conflict:
            raise HTTPException(status.HTTP_409_CONFLICT, "This table is already booked for that time slot.")

        reservation = Reservation(
            user_id=user_id,
            table_id=payload.table_id,
            slot_start=payload.slot_start,
            party_size=payload.party_size,
            idempotency_key=payload.idempotency_key,
            status=ReservationStatus.CONFIRMED,
        )
        db.add(reservation)

        try:
            await db.commit()
        except IntegrityError:
            # 4) Final, database-level safety net: the UNIQUE constraint on
            #    (table_id, slot_start) rejects a genuine race that slipped
            #    past the lock (e.g. lock TTL expiry, multi-region Redis).
            await db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, "This table is already booked for that time slot."
            )

        await db.refresh(reservation)

    # 5) Tell every connected client (the live floor-plan view) that this
    #    table just became unavailable for this slot.
    await redis_client.publish(
        TABLE_STATUS_CHANNEL,
        json.dumps(
            {
                "table_id": str(payload.table_id),
                "slot_start": slot_key,
                "status": "booked",
            }
        ),
    )
    return reservation


async def cancel_reservation(db: AsyncSession, user_id: UUID, reservation_id: UUID) -> None:
    reservation = await db.get(Reservation, reservation_id)
    if reservation is None or reservation.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found.")

    reservation.status = ReservationStatus.CANCELLED
    await db.commit()

    await redis_client.publish(
        TABLE_STATUS_CHANNEL,
        json.dumps(
            {
                "table_id": str(reservation.table_id),
                "slot_start": reservation.slot_start.isoformat(),
                "status": "available",
            }
        ),
    )
