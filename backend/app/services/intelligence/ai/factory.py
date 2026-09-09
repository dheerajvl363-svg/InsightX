import logging
from typing import Dict, Optional, Type

from app.config import AI_MODEL_NAME, AI_PROVIDER
from app.services.intelligence.ai.base import BaseAIProvider
from app.services.intelligence.ai.mock import MockAIProvider
from app.services.intelligence.ai.openai import OpenAIProvider

logger = logging.getLogger(__name__)

# Registry for AI Provider classes
_PROVIDER_REGISTRY: Dict[str, Type[BaseAIProvider]] = {
    "mock": MockAIProvider,
    "noop": MockAIProvider,
    "openai": OpenAIProvider,
}

_provider_instances: Dict[str, BaseAIProvider] = {}


def register_ai_provider(name: str, provider_cls: Type[BaseAIProvider]) -> None:
    """
    Registers a new AI provider adapter implementation (e.g. OpenAIProvider, AnthropicProvider).
    """
    _PROVIDER_REGISTRY[name.lower()] = provider_cls
    logger.info(f"Registered AI provider adapter '{name}' ({provider_cls.__name__})")


def get_ai_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseAIProvider:
    """
    Factory function instantiating or retrieving a singleton AI provider instance.
    
    Defaults to configuration setting `AI_PROVIDER` (default 'mock').
    Fallbacks gracefully to MockAIProvider if named provider is not registered or unavailable.
    """
    selected_name = (provider_name or AI_PROVIDER or "mock").lower()
    selected_model = model_name or AI_MODEL_NAME or "insightx-mock-ai-v1"

    cache_key = f"{selected_name}:{selected_model}"
    if cache_key in _provider_instances:
        return _provider_instances[cache_key]

    provider_cls = _PROVIDER_REGISTRY.get(selected_name)
    if provider_cls is None:
        logger.warning(
            f"AI Provider '{selected_name}' requested but not registered. "
            "Falling back to MockAIProvider."
        )
        provider_cls = MockAIProvider

    if issubclass(provider_cls, (MockAIProvider, OpenAIProvider)):
        instance = provider_cls(model_name=selected_model)
    else:
        instance = provider_cls()

    if not instance.is_available():
        logger.warning(
            f"AI Provider '{instance.provider_name}' is not available (e.g. missing API keys). "
            "Falling back to MockAIProvider."
        )
        instance = MockAIProvider(model_name=selected_model)

    _provider_instances[cache_key] = instance
    return instance
