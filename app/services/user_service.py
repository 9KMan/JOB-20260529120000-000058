import uuid
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.services.auth_service import AuthService


class UserService:
    @staticmethod
    async def list_users(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> UserListResponse:
        offset = (page - 1) * per_page

        # Count total
        count_result = await db.execute(
            select(func.count()).select_from(User).where(User.tenant_id == tenant_id)
        )
        total = count_result.scalar() or 0

        # Fetch page
        result = await db.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        users = result.scalars().all()

        return UserListResponse(
            data=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            per_page=per_page,
        )

    @staticmethod
    async def create_user(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        data: UserCreate,
    ) -> UserResponse:
        password_hash = AuthService.hash_password(data.password)
        user = User(
            tenant_id=tenant_id,
            email=data.email,
            password_hash=password_hash,
            role=data.role,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return UserResponse.model_validate(user)

    @staticmethod
    async def get_user(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> UserResponse | None:
        result = await db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return UserResponse.model_validate(user)

    @staticmethod
    async def update_user(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        data: UserUpdate,
    ) -> UserResponse | None:
        result = await db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None

        if data.email is not None:
            user.email = data.email
        if data.password is not None:
            user.password_hash = AuthService.hash_password(data.password)
        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active

        await db.flush()
        await db.refresh(user)
        return UserResponse.model_validate(user)

    @staticmethod
    async def delete_user(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        result = await db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return False

        # Soft delete
        user.is_active = False
        await db.flush()
        return True
