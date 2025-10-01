import uuid
from typing import Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.backend.crud.base import CRUDBase
from src.backend.models.gpu import GPU, GpuStatus
from src.backend.models.organization import Organization
from src.backend.schemas.organization import OrganizationCreate, OrganizationUpdate


class CRUDOrganization(CRUDBase[Organization, OrganizationCreate, OrganizationUpdate]):
    # You can add organization-specific CRUD methods here.
    # For example, a method to find an organization by name.
    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Organization]:
        result = await db.execute(select(self.model).filter(self.model.name == name))
        return result.scalars().first()

    async def get_active_gpu_count(self, db: AsyncSession, *, organization_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count(GPU.id)).where(
                GPU.organization_id == organization_id,
                GPU.status.in_([GpuStatus.PROVISIONING, GpuStatus.AVAILABLE, GpuStatus.BUSY])
            )
        )
        return result.scalar_one()


organization = CRUDOrganization(Organization)
