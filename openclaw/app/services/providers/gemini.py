import os
import time
from typing import Any

from google import genai
from google.genai import types

from app.services.providers.base import LLMRequest, LLMResponse

DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=api_key)

    def generate(self, req: LLMRequest) -> LLMResponse:
        model = req.model or DEFAULT_MODEL
        start = time.time()

        contents = []
        for msg in req.messages:
            role = "model" if msg.role == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))

        config = types.GenerateContentConfig(
            temperature=req.temperature,
            max_output_tokens=req.max_tokens,
        )
        if req.system_prompt:
            config.system_instruction = req.system_prompt

        response = self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        latency_ms = int((time.time() - start) * 1000)
        reply_text = getattr(response, "text", None) or str(response)

        input_tokens = None
        output_tokens = None
        usage = getattr(response, "usage_metadata", None)
        if usage:
            input_tokens = getattr(usage, "prompt_token_count", None)
            output_tokens = getattr(usage, "candidates_token_count", None)

        raw: Any = getattr(response, "to_dict", None)
        raw_json = raw() if callable(raw) else None

        return LLMResponse(
            reply_text=reply_text,
            provider=self.name,
            model=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw=raw_json,
        )
