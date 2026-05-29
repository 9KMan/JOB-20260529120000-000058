import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_id, require_role
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.services.user_service import UserService

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_id)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> UserListResponse:
    """List all users for the current tenant (paginated)."""
    return await UserService.list_users(db, tenant_id, page, per_page)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_id)],
) -> UserResponse:
    """Create a new user (admin only)."""
    return await UserService.create_user(db, tenant_id, data)


@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_id)],
) -> UserResponse:
    """Get a user by ID."""
    user = await UserService.get_user(db, tenant_id, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.put("/{user_id}", status_code=status.HTTP_200_OK)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_id)],
) -> UserResponse:
    """Update a user (admin only)."""
    user = await UserService.update_user(db, tenant_id, user_id, data)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin"))],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_id)],
) -> None:
    """Soft-delete a user (admin only)."""
    success = await UserService.delete_user(db, tenant_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )