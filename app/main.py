from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, projects, users
from app.config import settings
from app.kafka.producer import kafka_producer
from app.kafka.consumer import kafka_consumer
from app.ws.client_manager import ws_client_manager


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

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}