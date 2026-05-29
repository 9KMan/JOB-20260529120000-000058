import pytest
from httpx import AsyncClient

from app.models.tenant import Tenant
from app.models.user import User


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={
            "tenant_name": "New Tenant",
            "tenant_slug": "new-tenant",
            "admin_email": "admin@newtenant.com",
            "admin_password": "securepassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_slug(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={
            "tenant_name": "Tenant A",
            "tenant_slug": "duplicate",
            "admin_email": "a@tenant.com",
            "admin_password": "password123",
        },
    )
    response = await client.post(
        "/auth/register",
        json={
            "tenant_name": "Tenant B",
            "tenant_slug": "duplicate",
            "admin_email": "b@tenant.com",
            "admin_password": "password123",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    response = await client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: User):
    response = await client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    response = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "password123"},
    )
    assert response.status_code == 401