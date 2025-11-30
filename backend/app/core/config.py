"""Application configuration using pydantic-settings."""

from enum import Enum
from functools import lru_cache

from pydantic import model_validator
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
    log_level: str = "INFO"

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

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @model_validator(mode="after")
    def validate_required_settings(self):
        """Validate required settings are present."""
        errors = []

        # LiveKit is required
        if not self.livekit_url:
            errors.append("LIVEKIT_URL is required")
        if not self.livekit_api_key:
            errors.append("LIVEKIT_API_KEY is required")
        if not self.livekit_api_secret:
            errors.append("LIVEKIT_API_SECRET is required")

        # Deepgram is required
        if not self.deepgram_api_key:
            errors.append("DEEPGRAM_API_KEY is required")

        # LLM provider validation
        if self.llm_provider == LLMProvider.OPENAI:
            if not self.openai_api_key:
                errors.append("OPENAI_API_KEY is required when using OpenAI provider")
        elif self.llm_provider == LLMProvider.AZURE_OPENAI:
            if not self.azure_openai_api_key:
                errors.append("AZURE_OPENAI_API_KEY is required when using Azure OpenAI")
            if not self.azure_openai_endpoint:
                errors.append("AZURE_OPENAI_ENDPOINT is required when using Azure OpenAI")
            if not self.azure_openai_deployment_name:
                errors.append("AZURE_OPENAI_DEPLOYMENT_NAME is required when using Azure OpenAI")

        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")

        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
