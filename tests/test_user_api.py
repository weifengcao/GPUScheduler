
from httpx import AsyncClient
import pytest

from src.backend.models.user import User


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, db: AsyncSession):
    # This test will fail until we have a way to create an organization and an admin user
    pass
