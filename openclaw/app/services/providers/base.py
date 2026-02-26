from dataclasses import dataclass
from typing import Any, Optional, Protocol


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class LLMRequest:
    messages: list[ChatMessage]
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    metadata: Optional[dict[str, Any]] = None


@dataclass
class LLMResponse:
    reply_text: str
    provider: str
    model: str
    latency_ms: int
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    raw: Optional[dict[str, Any]] = None


class LLMProvider(Protocol):
    name: str

    def generate(self, req: LLMRequest) -> LLMResponse: ...
