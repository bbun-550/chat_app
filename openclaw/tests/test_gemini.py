from types import SimpleNamespace

import pytest

from app.services.llm_router import LLMRouter
from app.services.providers.base import ChatMessage, LLMRequest
from app.services.providers.gemini import DEFAULT_MODEL, GeminiProvider


class FakeModelAPI:
    def __init__(self):
        self.last_kwargs = None

    def generate_content(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(
            text="mock reply",
            usage_metadata=SimpleNamespace(
                prompt_token_count=12,
                candidates_token_count=34,
            ),
            to_dict=lambda: {"ok": True},
        )


class FakeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.models = FakeModelAPI()


def test_gemini_provider_generate(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.providers.gemini.genai.Client", FakeClient)

    provider = GeminiProvider()
    req = LLMRequest(
        messages=[
            ChatMessage(role="user", content="hello"),
            ChatMessage(role="assistant", content="hi"),
        ],
        system_prompt="You are helpful.",
        model=None,
        temperature=0.4,
        max_tokens=128,
    )
    res = provider.generate(req)

    assert res.reply_text == "mock reply"
    assert res.provider == "gemini"
    assert res.model == DEFAULT_MODEL
    assert res.input_tokens == 12
    assert res.output_tokens == 34
    assert res.raw == {"ok": True}


def test_router_unknown_provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.providers.gemini.genai.Client", FakeClient)
    router = LLMRouter()

    req = LLMRequest(messages=[ChatMessage(role="user", content="x")])
    with pytest.raises(ValueError):
        router.generate("unknown", req)
