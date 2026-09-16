from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationConflict, ReservationCreate, ReservationOut
from app.services.reservation_service import cancel_reservation, create_reservation

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post(
    "",
    response_model=ReservationOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ReservationConflict}},
)
async def book_table(
    payload: ReservationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_reservation(db, current_user.id, payload)


@router.get("/me", response_model=list[ReservationOut])
async def my_reservations(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.scalars(
        select(Reservation)
        .where(Reservation.user_id == current_user.id)
        .order_by(Reservation.slot_start.desc())
    )
    return result.all()


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel(
    reservation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await cancel_reservation(db, current_user.id, reservation_id)
