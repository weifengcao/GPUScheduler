import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.crud.api_key import api_key as api_key_crud
from src.backend.models.user import User

api_key_scheme = APIKeyHeader(name="Authorization")

async def get_current_user(
    api_key: str = Depends(api_key_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    if not api_key.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = api_key.split(" ")[1]
    try:
        prefix, secret = token.split(".")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        )

    db_api_key = await api_key_crud.get_by_prefix(db, prefix=prefix)
    if db_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    if not bcrypt.checkpw(secret.encode("utf-8"), db_api_key.key_hash.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    # TODO: Check for key expiration.

    return db_api_key.user
