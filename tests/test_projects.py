import uuid
import pytest
from httpx import AsyncClient

from app.models.project import Project


@pytest.mark.asyncio
async def test_list_projects_authenticated(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/projects", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_projects_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/projects")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={
            "name": "New Project",
            "description": "A new project",
            "status": "active",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Project"
    assert data["description"] == "A new project"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_project_by_id(client: AsyncClient, auth_headers: dict, test_project: Project):
    response = await client.get(
        f"/api/v1/projects/{test_project.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_project.id)
    assert data["name"] == test_project.name


@pytest.mark.asyncio
async def test_get_nonexistent_project(client: AsyncClient, auth_headers: dict):
    response = await client.get(
        f"/api/v1/projects/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, auth_headers: dict, test_project: Project):
    response = await client.put(
        f"/api/v1/projects/{test_project.id}",
        headers=auth_headers,
        json={"name": "Updated Project", "status": "inactive"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Project"
    assert data["status"] == "inactive"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, auth_headers: dict, db_session, test_tenant):
    # Create a project to delete
    project = Project(
        tenant_id=test_tenant.id,
        name="To Delete",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    response = await client.delete(
        f"/api/v1/projects/{project.id}",
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Verify deletion
    from sqlalchemy import select
    result = await db_session.execute(select(Project).where(Project.id == project.id))
    deleted = result.scalar_one_or_none()
    assert deleted is None