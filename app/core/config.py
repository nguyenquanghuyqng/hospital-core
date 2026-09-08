from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Hospital Queue Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/hospital_db"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://postgres:password@localhost:5432/hospital_db"

    SECRET_KEY: str = "changeme-in-production"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 giờ

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
