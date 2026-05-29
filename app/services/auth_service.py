import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import TokenResponse, RefreshResponse

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role,
            "exp": expire,
            "type": "access",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def create_refresh_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "exp": expire,
            "type": "refresh",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    async def register_tenant(
        db: AsyncSession,
        tenant_name: str,
        tenant_slug: str,
        admin_email: str,
        admin_password: str,
        plan: str = "starter",
    ) -> TokenResponse:
        # Check if tenant slug already exists
        result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        if result.scalar_one_or_none() is not None:
            raise ValueError(f"Tenant slug '{tenant_slug}' already exists")

        # Create tenant
        tenant = Tenant(name=tenant_name, slug=tenant_slug, plan=plan)
        db.add(tenant)
        await db.flush()

        # Create admin user
        password_hash = AuthService.hash_password(admin_password)
        admin_user = User(
            tenant_id=tenant.id,
            email=admin_email,
            password_hash=password_hash,
            role="admin",
        )
        db.add(admin_user)
        await db.flush()
        await db.refresh(tenant)
        await db.refresh(admin_user)

        # Generate tokens
        access_token = AuthService.create_access_token(admin_user.id, tenant.id, admin_user.role)
        refresh_token = AuthService.create_refresh_token(admin_user.id, tenant.id)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    @staticmethod
    async def login(db: AsyncSession, email: str, password: str) -> TokenResponse | None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            return None
        if not AuthService.verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None

        access_token = AuthService.create_access_token(user.id, user.tenant_id, user.role)
        refresh_token = AuthService.create_refresh_token(user.id, user.tenant_id)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_token: str) -> RefreshResponse | None:
        try:
            payload = jwt.decode(
                refresh_token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "refresh":
                return None
            user_id = uuid.UUID(payload["sub"])
            tenant_id = uuid.UUID(payload["tenant_id"])
        except (jwt.JWTError, KeyError, ValueError):
            return None

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None

        access_token = AuthService.create_access_token(user.id, user.tenant_id, user.role)
        return RefreshResponse(access_token=access_token)

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
