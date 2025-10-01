from typing import List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.backend.crud.base import CRUDBase
from src.backend.models.gpu import GPU, GpuStatus
from src.backend.schemas.gpu import GPUCreate, GPUUpdate


class CRUDGpu(CRUDBase[GPU, GPUCreate, GPUUpdate]):
    async def get_multi_by_owner(
        self, db: AsyncSession, *, organization_id: uuid.UUID, status: Optional[GpuStatus] = None
    ) -> List[GPU]:
        query = select(self.model).filter(self.model.organization_id == organization_id)
        if status:
            query = query.filter(self.model.status == status)
        result = await db.execute(query)
        return result.scalars().all()


gpu = CRUDGpu(GPU)
