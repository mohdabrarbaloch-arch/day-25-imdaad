"""Application configuration — everything comes from the environment."""

import os
from functools import lru_cache


class Settings:
    """Typed access to environment configuration."""

    APP_NAME: str = "Imdaad"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./imdaad.db"
    )

    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")
        if o.strip()
    ]

    RATE_LIMIT_REGISTER: str = os.getenv("RATE_LIMIT_REGISTER", "5/minute")
    RATE_LIMIT_LOGIN: str = os.getenv("RATE_LIMIT_LOGIN", "10/minute")
    RATE_LIMIT_REQUESTS: str = os.getenv("RATE_LIMIT_REQUESTS", "20/minute")

    REQUEST_EXPIRY_HOURS: int = int(os.getenv("REQUEST_EXPIRY_HOURS", "72"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
