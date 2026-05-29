import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RefreshResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Register a new tenant with an admin user."""
    try:
        result = await AuthService.register_tenant(
            db=db,
            tenant_name=data.tenant_name,
            tenant_slug=data.tenant_slug,
            admin_email=data.admin_email,
            admin_password=data.admin_password,
            plan=data.plan,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    data: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Login and receive JWT tokens."""
    result = await AuthService.login(
        db=db,
        email=data.email,
        password=data.password,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return result


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RefreshResponse:
    """Refresh the access token using the refresh token from cookie."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    result = await AuthService.refresh_access_token(db, refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return result