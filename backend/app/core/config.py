"""Application configuration using pydantic-settings."""

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "LIRA"
    debug: bool = False
    port: int = 8011

    # LiveKit
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # Deepgram
    deepgram_api_key: str = ""

    # LLM Provider Selection
    llm_provider: LLMProvider = LLMProvider.OPENAI
    llm_model: str = "gpt-4o-mini"  # Fast model for low latency

    # OpenAI
    openai_api_key: str = ""

    # Azure OpenAI
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_deployment_name: str = ""

    # Redis (optional)
    redis_url: str = "redis://localhost:6379"

    # Session
    session_ttl_seconds: int = 3600  # 1 hour


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
