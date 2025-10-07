import secrets
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.backend.crud.base import CRUDBase
from src.backend.models.user import APIKey, User
from src.backend.schemas.api_key import APIKeyCreate, APIKeyUpdate


class CRUDAPIKey(CRUDBase[APIKey, APIKeyCreate, APIKeyUpdate]):
    def generate_key_and_prefix(self):
        prefix = secrets.token_hex(4)
        secret = secrets.token_urlsafe(32)
        return f"{prefix}.{secret}", prefix, secret

    def hash_secret(self, secret: str) -> str:
        return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    async def create_with_owner(
        self, db: AsyncSession, *, obj_in: APIKeyCreate, owner: User
    ) -> tuple[APIKey, str]:
        key, prefix, secret = self.generate_key_and_prefix()
        hashed_secret = self.hash_secret(secret)

        expires_at = None
        if obj_in.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=obj_in.expires_in_days)

        db_obj = self.model(
            key_hash=hashed_secret,
            key_prefix=prefix,
            user_id=owner.id,
            organization_id=owner.organization_id,
            expires_at=expires_at,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj, key

    async def get_multi_by_user(
        self, db: AsyncSession, *, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[APIKey]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_prefix(self, db: AsyncSession, *, prefix: str) -> Optional[APIKey]:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.user))
            .filter(self.model.key_prefix == prefix)
        )
        return result.scalars().first()


api_key = CRUDAPIKey(APIKey)
