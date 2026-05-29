import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.database import engine


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Injects tenant_id into PostgreSQL session settings for RLS.
    Called after JWT auth populates request.state.tenant_id.
    """

    async def dispatch(self, request: Request, call_next):
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id is not None:
            # Set PostgreSQL session variable for RLS
            async with engine.connect() as conn:
                await conn.execute(
                    f"SET LOCAL app.tenant_id = '{tenant_id}'"
                )

        response = await call_next(request)
        return response