from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://loyalty:loyalty@postgres:5432/loyalty"
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "60"))
    cache_ttl_jitter_seconds: int = int(os.getenv("CACHE_TTL_JITTER_SECONDS", "15"))
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "lab-admin-key")


settings = Settings()
