from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.backend.crud.base import CRUDBase
from src.backend.models.organization import Organization
from src.backend.schemas.organization import OrganizationCreate, OrganizationUpdate


class CRUDOrganization(CRUDBase[Organization, OrganizationCreate, OrganizationUpdate]):
    # You can add organization-specific CRUD methods here.
    # For example, a method to find an organization by name.
    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Organization]:
        result = await db.execute(select(self.model).filter(self.model.name == name))
        return result.scalars().first()


organization = CRUDOrganization(Organization)