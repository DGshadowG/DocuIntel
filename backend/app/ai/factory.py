"""Provider selection from configuration (AI_PROVIDER env variable)."""
from functools import lru_cache

from app.ai.base import AIProvider
from app.core.config import get_settings


@lru_cache()
def get_provider() -> AIProvider:
    settings = get_settings()
    name = settings.AI_PROVIDER.strip().lower()
    if name == "openai":
        from app.ai.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if name == "ollama":
        from app.ai.ollama_provider import OllamaProvider
        return OllamaProvider()
    if name == "deterministic":
        from app.ai.deterministic import DeterministicProvider
        return DeterministicProvider()
    raise ValueError(
        f"AI_PROVIDER='{name}' no es valido. Use: deterministic | openai | ollama"
    )


def reset_provider_cache() -> None:
    """For tests: clear the cached provider after changing settings."""
    get_provider.cache_clear()
