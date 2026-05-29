import uuid
import logging
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class WSClientManager:
    def __init__(self) -> None:
        # In-memory store: tenant_id -> set of websocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._redis_client: redis.Redis | None = None

    async def connect(self, websocket: WebSocket, tenant_id: uuid.UUID) -> None:
        await websocket.accept()
        tid = str(tenant_id)
        if tid not in self._connections:
            self._connections[tid] = set()
        self._connections[tid].add(websocket)
        logger.info(f"WebSocket connected for tenant {tid}. Total: {len(self._connections[tid])}")

    def disconnect(self, websocket: WebSocket, tenant_id: uuid.UUID) -> None:
        tid = str(tenant_id)
        if tid in self._connections:
            self._connections[tid].discard(websocket)
            if not self._connections[tid]:
                del self._connections[tid]
        logger.info(f"WebSocket disconnected for tenant {tid}")

    async def broadcast_to_tenant(self, tenant_id: uuid.UUID, channel: str, message: dict) -> None:
        tid = str(tenant_id)
        if tid in self._connections:
            payload = f"CHANNEL:{channel}|MESSAGE:{message}"
            for ws in self._connections[tid]:
                try:
                    await ws.send_text(payload)
                except Exception as e:
                    logger.warning(f"Failed to send WS message: {e}")

    async def publish_redis(self, tenant_id: uuid.UUID, channel: str, message: dict) -> None:
        """Publish to Redis for multi-worker fan-out."""
        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                return

        try:
            await self._redis_client.publish(
                f"tenant:{tenant_id}:{channel}",
                str(message),
            )
        except Exception as e:
            logger.warning(f"Redis publish failed: {e}")

    async def subscribe_redis(self, tenant_id: uuid.UUID, channel: str) -> None:
        """Subscribe to Redis channel for fan-out from other workers."""
        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                return

        pubsub = self._redis_client.pubsub()
        await pubsub.subscribe(f"tenant:{tenant_id}:{channel}")
        logger.info(f"Subscribed to Redis channel tenant:{tenant_id}:{channel}")


ws_client_manager = WSClientManager()