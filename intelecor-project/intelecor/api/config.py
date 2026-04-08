from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://intelecor:intelecor_dev@localhost:5432/intelecor"
    database_url_sync: str = "postgresql://intelecor:intelecor_dev@localhost:5432/intelecor"

    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    anthropic_api_key: str = ""
    llm_provider: str = "anthropic"
    ollama_base_url: str = "http://localhost:11434"

    resend_api_key: str = ""
    email_from: str = "reports@intelecor.com.au"

    gentu_api_base_url: str = ""
    gentu_api_key: str = ""
    gentu_tenant_id: str = ""

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
