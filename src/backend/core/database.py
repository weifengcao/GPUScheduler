from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.backend.core.config import settings

# The base class for all our ORM models.
Base = declarative_base()

# Create an asynchronous engine for connecting to the database.
# The `echo=True` flag is useful for debugging as it logs all generated SQL.
async_engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Create a configured "AsyncSession" class.
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI dependency to get a DB session for a single request."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()