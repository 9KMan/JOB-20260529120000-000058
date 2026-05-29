import uuid
import pytest
from httpx import AsyncClient

from app.models.user import User
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_list_users_authenticated(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/users", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data


@pytest.mark.asyncio
async def test_list_users_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/users")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_user_admin(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "email": "newuser@example.com",
            "password": "newpassword123",
            "role": "member",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "member"


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.get(
        f"/api/v1/users/{test_user.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_get_nonexistent_user(client: AsyncClient, auth_headers: dict):
    response = await client.get(
        f"/api/v1/users/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, auth_headers: dict, test_user: User):
    response = await client.put(
        f"/api/v1/users/{test_user.id}",
        headers=auth_headers,
        json={"role": "member"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "member"


@pytest.mark.asyncio
async def test_delete_user_soft(client: AsyncClient, auth_headers: dict, db_session, test_tenant):
    # Create a user to delete
    password_hash = AuthService.hash_password("password123")
    from app.models.user import User
    user_to_delete = User(
        tenant_id=test_tenant.id,
        email="delete@example.com",
        password_hash=password_hash,
        role="member",
    )
    db_session.add(user_to_delete)
    await db_session.commit()
    await db_session.refresh(user_to_delete)

    response = await client.delete(
        f"/api/v1/users/{user_to_delete.id}",
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Verify soft delete
    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.id == user_to_delete.id))
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is not None
    assert deleted_user.is_active is False