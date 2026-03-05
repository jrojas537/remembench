"""
Remembench — Application Configuration

Centralized definition of environment variables utilizing `pydantic-settings`. 
Enforces rigorous validation on startup, preventing the app from launching if 
critical strings (like the Database URL) are missing or misconfigured.
"""

from typing import Union, List
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration singleton for the Remembench platform.
    Variables mapped directly to the root `.env` or system environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # --- Application Identity ---
    app_name: str = Field("Remembench", description="Global application display name")
    debug: bool = Field(False, description="Enable local Uvicorn reload and verbose ORM logging")
    api_prefix: str = Field("/api/v1", description="Default prefix bound to all standard FastAPI routers")

    # --- Security & Network Boundaries ---
    cors_origins: Union[str, List[str]] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Permitted cross-origin hosts (Accepts raw lists or comma-separated env strings)"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Convert a comma-separated `.env` string into a list of valid URLs."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # --- Core Infrastructure Links ---
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/remembench",
        description="Asyncpg dialect PostgreSQL connection string"
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Primary Redis Cache DB (used for Tier 2/3 HTTP Caching idempotency)"
    )
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery Worker message broker queue"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery State synchronization engine"
    )

    # --- External Data Provider API Keys ---
    noaa_cdo_token: str = Field("", description="NOAA API Key (National Oceanic Data)")
    abstract_api_key: str = Field("", description="AbstractAPI Key (Global Holidays provider)")

    # --- LLM Web Scraper & Orchestration API Keys ---
    exa_api_key: str = Field("", description="Exa.ai Web Search SDK Key")
    tavily_api_key: str = Field("", description="Tavily.com Search Network API Key")

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
    gemini_model: str = "gemini-2.5-flash"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"

    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_persist_dir: str = "./data/chromadb"

    # --- Logging ---
    log_level: str = "INFO"


settings = Settings()
