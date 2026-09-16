import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, reservations, restaurants, users, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For a quick demo/portfolio deployment we auto-create tables here.
    # In a real production setup this is replaced by `alembic upgrade
    # head` run as a separate release step, so schema changes are
    # versioned and reviewable.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    listener_task = asyncio.create_task(websocket.redis_listener())
    yield
    listener_task.cancel()


app = FastAPI(
    title="GrandReserve API",
    description=(
        "A concurrency-safe restaurant table booking system with live "
        f"seat availability over WebSockets. Support: {settings.support_email}"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Locked down to explicit origins in production; wide open here only to
# make the bundled demo frontend (served from a different port) work
# out of the box.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(restaurants.router)
app.include_router(reservations.router)
app.include_router(websocket.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
