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

    # AWS Settings
    AWS_REGION: str = "us-east-1"
    AWS_AMI_ID: str = "ami-0c55b159cbfafe1f0"  # Example: Amazon Linux 2 AMI
    AWS_INSTANCE_TYPE: str = "g4dn.xlarge"
    AWS_SECURITY_GROUP_ID: str
    AWS_KEY_PAIR_NAME: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()