"""
Run once after the stack is up to create a demo restaurant with tables:

    docker compose exec api python -m scripts.seed_demo_data

Prints the restaurant_id and the "hot" table_id that the load test
(load_test/locustfile.py) hammers with 100 concurrent booking attempts.
"""

import asyncio

from app.database import AsyncSessionLocal, Base, engine
from app.models.restaurant import Restaurant, Table


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        restaurant = Restaurant(
            name="GrandReserve Demo",
            address="123 Portfolio Ave, Demo City",
            opens_at="10:00",
            closes_at="23:00",
        )
        db.add(restaurant)
        await db.flush()  # get restaurant.id without committing yet

        tables = [Table(restaurant_id=restaurant.id, label=f"T-{i}", seats=2 + (i % 3) * 2) for i in range(1, 11)]
        db.add_all(tables)
        await db.commit()

        print(f"restaurant_id = {restaurant.id}")
        print(f"hot_table_id  = {tables[0].id}   <-- use this for the load test")
        for t in tables:
            print(f"  table {t.label}: {t.id}")


if __name__ == "__main__":
    asyncio.run(main())
