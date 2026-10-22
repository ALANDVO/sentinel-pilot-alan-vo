from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Sentinel Pilot"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./sentinel.db"

    # Security
    secret_key: str = "dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Keycloak / OIDC
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "sentinel"
    keycloak_client_id: str = "sentinel-pilot"
    keycloak_client_secret: str = ""
    keycloak_admin_user: str = "admin"
    keycloak_admin_password: str = "admin"

    # Demo mode (only for local development)
    demo_mode: bool = False

    # LLM (optional)
    llm_api_key: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()