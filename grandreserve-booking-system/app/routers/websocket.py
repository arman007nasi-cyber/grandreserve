import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.redis_client import TABLE_STATUS_CHANNEL, redis_client

router = APIRouter()


class ConnectionManager:
    """Tracks every open WebSocket connection for the live floor-plan view."""

    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: str):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def redis_listener():
    """
    Background task: subscribes once to Redis and fans out every
    table-status event (published by reservation_service.py) to all
    currently-connected WebSocket clients. Using Redis pub/sub instead of
    an in-process list means this still works correctly if the API is
    ever scaled to multiple replicas -- a booking made on instance A is
    broadcast to a browser connected to instance B.
    """
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(TABLE_STATUS_CHANNEL)
    async for message in pubsub.listen():
        if message["type"] == "message":
            await manager.broadcast(message["data"])


@router.websocket("/ws/tables")
async def table_status_socket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't need anything FROM the client on this channel;
            # just keep the connection alive and detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
