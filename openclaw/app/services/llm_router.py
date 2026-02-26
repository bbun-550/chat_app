from app.services.providers.base import LLMProvider, LLMRequest, LLMResponse
from app.services.providers.gemini import GeminiProvider


class LLMRouter:
    def __init__(self) -> None:
        self.providers: dict[str, LLMProvider] = {
            "gemini": GeminiProvider(),
        }

    def list_providers(self) -> list[str]:
        return list(self.providers.keys())

    def generate(self, provider_name: str, req: LLMRequest) -> LLMResponse:
        provider = self.providers.get(provider_name)
        if provider is None:
            raise ValueError(
                f"Unknown provider: {provider_name}. Available providers: {self.list_providers()}"
            )
        return provider.generate(req)
