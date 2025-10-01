import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import bcrypt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.organization import Organization
from src.backend.models.user import User, APIKey

async def seed_database():
    """
    Seeds the database with an initial organization, user, and API key.
    """
    print("Starting database seeding...")
    db: AsyncSession = AsyncSessionLocal()

    try:
        # Create Organization
        organization = Organization(name="Default Organization", max_active_gpus=10)
        db.add(organization)
        await db.flush()

        # Create User
        user = User(
            email="admin@example.com",
            organization_id=organization.id,
            role="admin",
        )
        db.add(user)
        await db.flush()

        # Create API Key
        api_key_secret = uuid.uuid4().hex
        hashed_secret = bcrypt.hashpw(api_key_secret.encode("utf-8"), bcrypt.gensalt())
        key_prefix = "gpus_tst"

        api_key = APIKey(
            key_prefix=key_prefix,
            key_hash=hashed_secret.decode("utf-8"),
            user_id=user.id,
            organization_id=organization.id,
        )
        db.add(api_key)
        await db.commit()

        full_api_key = f"{key_prefix}.{api_key_secret}"
        print("\nDatabase seeded successfully!")
        print("========================================")
        print("Sample Organization, User, and API Key created.")
        print(f"  Organization: {organization.name}")
        print(f"  User Email: {user.email}")
        print("\nUse the following API key for authentication:")
        print(f"  Authorization: Bearer {full_api_key}")
        print("========================================")

    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(seed_database())