from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.reservation import Reservation, ReservationStatus
from app.models.restaurant import Restaurant, Table
from app.schemas.restaurant import RestaurantOut, TableOut

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("", response_model=list[RestaurantOut])
async def list_restaurants(db: AsyncSession = Depends(get_db)):
    result = await db.scalars(select(Restaurant).options(selectinload(Restaurant.tables)))
    return result.all()


@router.get("/{restaurant_id}", response_model=RestaurantOut)
async def get_restaurant(restaurant_id: UUID, db: AsyncSession = Depends(get_db)):
    restaurant = await db.get(Restaurant, restaurant_id, options=[selectinload(Restaurant.tables)])
    if restaurant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restaurant not found.")
    return restaurant


@router.get("/{restaurant_id}/availability", response_model=list[TableOut])
async def available_tables(restaurant_id: UUID, slot_start: datetime, db: AsyncSession = Depends(get_db)):
    """Tables at this restaurant that are NOT already confirmed-booked for the given slot."""
    booked_subq = (
        select(Reservation.table_id)
        .where(Reservation.slot_start == slot_start, Reservation.status == ReservationStatus.CONFIRMED)
    )
    result = await db.scalars(
        select(Table).where(Table.restaurant_id == restaurant_id, Table.id.not_in(booked_subq))
    )
    return result.all()
