"""
Remembench — Application Configuration

Centralized settings using pydantic-settings. All values can be
overridden via environment variables or a .env file.

CORS_ORIGINS accepts a comma-separated string for easy Docker deployment:
    CORS_ORIGINS=https://my-domain.com,http://localhost:3000
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Remembench platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "Remembench"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # --- CORS ---
    cors_origins: str | list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Accept comma-separated string or list from env var."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/remembench"
    )

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- External API Keys ---
    noaa_cdo_token: str = ""
    abstract_api_key: str = ""

    # --- Web Search (historical article lookup) ---
    exa_api_key: str = ""
    tavily_api_key: str = ""

    # --- Billing / Stripe ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # --- API Key (for write endpoints) ---
    api_key: str = ""  # Set REMEMBENCH_API_KEY env var to enable auth

    # --- Open-Meteo (no key needed) ---
    open_meteo_base_url: str = "https://archive-api.open-meteo.com/v1/archive"

    # --- GDELT ---
    gdelt_base_url: str = "https://api.gdeltproject.org/api/v2"

    # --- LLM / Classification ---
    llm_provider: str = "openai"  # openai | gemini | anthropic
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"

    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_persist_dir: str = "./data/chromadb"

    # --- Logging ---
    log_level: str = "INFO"


settings = Settings()
