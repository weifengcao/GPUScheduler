
from typing import Any, Dict, Optional, Union, List
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.backend.core.security import get_password_hash
from src.backend.crud.base import CRUDBase
from src.backend.models.user import User
from src.backend.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            role=obj_in.role,
            organization_id=obj_in.organization_id,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password

        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        result = await db.execute(select(self.model).filter(self.model.email == email))
        return result.scalars().first()

    async def get_users_by_organization(
        self, db: AsyncSession, *, organization_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[User]:
        result = await db.execute(
            select(self.model)
            .where(self.model.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


user = CRUDUser(User)
