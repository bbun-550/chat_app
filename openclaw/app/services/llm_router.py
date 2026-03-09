import logging
from collections.abc import Iterator

from app.services.providers.base import LLMProvider, LLMRequest, LLMResponse, StreamChunk
from app.services.providers.gemini import GeminiProvider

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self) -> None:
        self.providers: dict[str, LLMProvider] = {}
        try:
            self.providers["gemini"] = GeminiProvider()
        except Exception as e:
            logger.warning("Gemini provider unavailable: %s", e)
        try:
            from app.services.providers.ollama import OllamaProvider
            self.providers["ollama"] = OllamaProvider()
        except Exception as e:
            logger.warning("Ollama provider unavailable: %s", e)

    def list_providers(self) -> list[str]:
        return list(self.providers.keys())

    GEMINI_MODELS = [
        "gemini-3-flash-preview",
        "gemini-3.1-pro-preview",
    ]

    def list_models(self, provider_name: str) -> list[str]:
        provider = self.providers.get(provider_name)
        if provider is None:
            raise ValueError(f"Unknown provider: {provider_name}")
        if hasattr(provider, "list_models"):
            return provider.list_models()
        if provider_name == "gemini":
            return self.GEMINI_MODELS
        return []

    def generate(self, provider_name: str, req: LLMRequest) -> LLMResponse:
        provider = self.providers.get(provider_name)
        if provider is None:
            raise ValueError(
                f"Unknown provider: {provider_name}. Available providers: {self.list_providers()}"
            )
        return provider.generate(req)

    def generate_stream(self, provider_name: str, req: LLMRequest) -> Iterator[StreamChunk]:
        provider = self.providers.get(provider_name)
        if provider is None:
            raise ValueError(
                f"Unknown provider: {provider_name}. Available providers: {self.list_providers()}"
            )
        yield from provider.generate_stream(req)
