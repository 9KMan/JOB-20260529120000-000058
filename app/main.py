import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError

from app.api import auth, projects, users
from app.config import settings
from app.kafka.producer import kafka_producer
from app.kafka.consumer import kafka_consumer
from app.ws.client_manager import ws_client_manager
from app.middleware.tenant import TenantMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await kafka_producer.start()
    await kafka_consumer.start()
    yield
    await kafka_producer.stop()
    await kafka_consumer.stop()


app = FastAPI(
    title="Multi-Tenant SaaS Backend",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantMiddleware)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.websocket("/ws/v1")
async def websocket_endpoint(websocket: WebSocket, token: str | None = Query(None)) -> None:
    """WebSocket endpoint with JWT auth via query param or first frame."""
    # Try to get token from query param first
    if token is None:
        # Try to get from first frame
        try:
            data = await websocket.receive_json()
            token = data.get("token")
        except Exception:
            pass

    if token is None:
        await websocket.close(code=4001, reason="Missing token")
        return

    # Validate token
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token type")
            return
        tenant_id = uuid.UUID(payload["tenant_id"])
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Connect with tenant context
    await ws_client_manager.connect(websocket, tenant_id)

    try:
        # Subscribe to Redis for cross-worker fan-out
        await ws_client_manager.subscribe_redis(tenant_id, "projects")
        await ws_client_manager.subscribe_redis(tenant_id, "users")

        while True:
            data = await websocket.receive_text()
            # Echo back with channel prefix for client routing
            await ws_client_manager.broadcast_to_tenant(
                tenant_id,
                "events",
                {"user_id": str(user_id), "data": data},
            )
    except WebSocketDisconnect:
        ws_client_manager.disconnect(websocket, tenant_id)