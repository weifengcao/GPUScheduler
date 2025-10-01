from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Manages application settings using Pydantic.
    It automatically reads environment variables and can load from a .env file.
    """

    # Database URL for connecting to PostgreSQL.
    # Example: "postgresql+asyncpg://user:password@host:port/dbname"
    DATABASE_URL: str = "postgresql+asyncpg://gpuscheduler:password@localhost:5432/gpuscheduler_db"

    # Redis URL for Celery broker and caching.
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()