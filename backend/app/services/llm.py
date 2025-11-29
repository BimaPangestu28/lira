"""LLM service supporting OpenAI and Azure OpenAI providers."""

from functools import lru_cache

from langchain_openai import AzureChatOpenAI, ChatOpenAI

from app.core.config import LLMProvider, get_settings


@lru_cache
def get_llm_client():
    """
    Get the configured LLM client based on provider settings.

    @returns ChatOpenAI or AzureChatOpenAI instance
    @raises ValueError - When provider is not configured properly
    """
    settings = get_settings()

    if settings.llm_provider == LLMProvider.AZURE_OPENAI:
        if not all([
            settings.azure_openai_api_key,
            settings.azure_openai_endpoint,
            settings.azure_openai_deployment_name,
        ]):
            raise ValueError(
                "Azure OpenAI requires AZURE_OPENAI_API_KEY, "
                "AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT_NAME"
            )

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment_name,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            temperature=0.7,
            streaming=True,
        )

    # Default: OpenAI
    if not settings.openai_api_key:
        raise ValueError("OpenAI requires OPENAI_API_KEY")

    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
        streaming=True,
    )
