import os
import time
from collections.abc import Iterator
from typing import Any

import ollama as ollama_lib

from app.services.providers.base import LLMRequest, LLMResponse, StreamChunk

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class OllamaProvider:
    name = "ollama"

    def __init__(self) -> None:
        self.client = ollama_lib.Client(host=OLLAMA_BASE_URL, timeout=300)

    def list_models(self) -> list[str]:
        response = self.client.list()
        return [m.model for m in response.models]

    def generate(self, req: LLMRequest) -> LLMResponse:
        model = req.model or DEFAULT_MODEL
        start = time.time()

        messages: list[dict[str, str]] = []
        if req.system_prompt:
            messages.append({"role": "system", "content": req.system_prompt})
        for msg in req.messages:
            messages.append({"role": msg.role, "content": msg.content})

        response = self.client.chat(
            model=model,
            messages=messages,
            options={
                "temperature": req.temperature,
                "num_predict": req.max_tokens,
            },
        )

        latency_ms = int((time.time() - start) * 1000)
        reply_text = response["message"]["content"]

        input_tokens = response.get("prompt_eval_count")
        output_tokens = response.get("eval_count")

        raw: Any = {k: v for k, v in response.model_dump().items() if k != "message"}

        return LLMResponse(
            reply_text=reply_text,
            provider=self.name,
            model=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw=raw,
        )

    def generate_stream(self, req: LLMRequest) -> Iterator[StreamChunk]:
        model = req.model or DEFAULT_MODEL

        messages: list[dict[str, str]] = []
        if req.system_prompt:
            messages.append({"role": "system", "content": req.system_prompt})
        for msg in req.messages:
            messages.append({"role": msg.role, "content": msg.content})

        stream = self.client.chat(
            model=model,
            messages=messages,
            options={
                "temperature": req.temperature,
                "num_predict": req.max_tokens,
            },
            stream=True,
        )

        for chunk in stream:
            done = chunk.get("done", False)
            delta = chunk.get("message", {}).get("content", "")
            input_tokens = chunk.get("prompt_eval_count") if done else None
            output_tokens = chunk.get("eval_count") if done else None
            yield StreamChunk(
                delta_text=delta,
                done=done,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
