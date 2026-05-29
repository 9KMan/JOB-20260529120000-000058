import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from app.kafka.producer import kafka_producer
from app.config import settings


class ProjectService:
    @staticmethod
    async def list_projects(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> ProjectListResponse:
        offset = (page - 1) * per_page

        count_result = await db.execute(
            select(func.count()).select_from(Project).where(Project.tenant_id == tenant_id)
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            select(Project)
            .where(Project.tenant_id == tenant_id)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        projects = result.scalars().all()

        return ProjectListResponse(
            data=[ProjectResponse.model_validate(p) for p in projects],
            total=total,
            page=page,
            per_page=per_page,
        )

    @staticmethod
    async def create_project(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        data: ProjectCreate,
    ) -> ProjectResponse:
        project = Project(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            status=data.status,
        )
        db.add(project)
        await db.flush()
        await db.refresh(project)

        # Publish Kafka event
        await kafka_producer.publish(
            topic=f"tenant.{tenant_id}.project.created",
            event={
                "event_id": str(uuid.uuid4()),
                "tenant_id": str(tenant_id),
                "entity": "project",
                "action": "created",
                "payload": {
                    "id": str(project.id),
                    "name": project.name,
                    "status": project.status,
                },
                "timestamp": project.created_at.isoformat(),
            },
        )

        return ProjectResponse.model_validate(project)

    @staticmethod
    async def get_project(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> ProjectResponse | None:
        result = await db.execute(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        project = result.scalar_one_or_none()
        if project is None:
            return None
        return ProjectResponse.model_validate(project)

    @staticmethod
    async def update_project(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ProjectUpdate,
    ) -> ProjectResponse | None:
        result = await db.execute(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        project = result.scalar_one_or_none()
        if project is None:
            return None

        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description
        if data.status is not None:
            project.status = data.status

        await db.flush()
        await db.refresh(project)

        # Publish Kafka event
        await kafka_producer.publish(
            topic=f"tenant.{tenant_id}.project.updated",
            event={
                "event_id": str(uuid.uuid4()),
                "tenant_id": str(tenant_id),
                "entity": "project",
                "action": "updated",
                "payload": {
                    "id": str(project.id),
                    "name": project.name,
                    "status": project.status,
                },
                "timestamp": project.created_at.isoformat(),
            },
        )

        return ProjectResponse.model_validate(project)

    @staticmethod
    async def delete_project(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> bool:
        result = await db.execute(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        project = result.scalar_one_or_none()
        if project is None:
            return False

        await db.delete(project)
        await db.flush()

        # Publish Kafka event
        await kafka_producer.publish(
            topic=f"tenant.{tenant_id}.project.deleted",
            event={
                "event_id": str(uuid.uuid4()),
                "tenant_id": str(tenant_id),
                "entity": "project",
                "action": "deleted",
                "payload": {"id": str(project_id)},
                "timestamp": "",
            },
        )

        return True
