from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.backend.crud.base import CRUDBase
from src.backend.models.user import APIKey
from src.backend.schemas.api_key import APIKeyCreate, APIKeyUpdate


class CRUDAPIKey(CRUDBase[APIKey, APIKeyCreate, APIKeyUpdate]):
    async def get_by_prefix(self, db: AsyncSession, *, prefix: str) -> Optional[APIKey]:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.user))
            .filter(self.model.key_prefix == prefix)
        )
        return result.scalars().first()


api_key = CRUDAPIKey(APIKey)
