from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.crud.base import CRUDBase
from src.backend.models.organization import Organization
from src.backend.schemas.organization import OrganizationCreate, OrganizationUpdate


class CRUDOrganization(CRUDBase[Organization, OrganizationCreate, OrganizationUpdate]):
    async def get_by_name(
        self, db: AsyncSession, *, name: str
    ) -> Optional[Organization]:
        """
        Get an organization by its name.
        """
        statement = select(self.model).filter(self.model.name == name)
        result = await db.execute(statement)
        return result.scalars().first()


organization = CRUDOrganization(Organization)