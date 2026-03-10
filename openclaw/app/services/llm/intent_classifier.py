"""Intent classifier for the router LLM.

Uses a lightweight LLM call (temp=0.1) to classify user messages into one of
the supported intent types. The LLM is asked to return a JSON object so the
result is deterministic and easy to parse.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from app.services.providers.base import ChatMessage, LLMRequest

logger = logging.getLogger(__name__)

_CLASSIFICATION_SYSTEM_PROMPT = """You are an intent classifier. Given a user message, classify it into exactly one of the following intent types:

- chat: General conversation, Q&A, writing assistance, explanations
- browse: Needs real-time web browsing (news, stock prices, current events, live data)
- research: Deep research requiring multiple sources and a structured report
- execute: Terminal commands, file system operations, shell scripts
- code: Code editing, refactoring, or pair-programming with file changes
- obsidian: Writing notes or structured documents to an Obsidian vault

Respond ONLY with valid JSON in the format:
{"intent": "<type>", "confidence": <0.0–1.0>, "reason": "<one sentence>"}

Do not include any other text."""


class IntentType(str, Enum):
    CHAT = "chat"
    BROWSE = "browse"
    RESEARCH = "research"
    EXECUTE = "execute"
    CODE = "code"
    OBSIDIAN = "obsidian"


@dataclass
class ClassifiedIntent:
    intent: IntentType
    confidence: float
    reason: str


def classify_intent(
    message: str,
    llm_fn: Callable[[LLMRequest], object],
) -> ClassifiedIntent:
    """Classify the intent of *message* using the provided LLM function.

    Falls back to IntentType.CHAT on any error so the pipeline never blocks.
    """
    req = LLMRequest(
        messages=[ChatMessage(role="user", content=message)],
        system_prompt=_CLASSIFICATION_SYSTEM_PROMPT,
        model="gemini-3-flash-preview",
        temperature=0.1,
        max_tokens=128,
    )
    try:
        response = llm_fn(req)
        raw = response.reply_text.strip()  # type: ignore[attr-defined]
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)
        intent_str = data.get("intent", "chat").lower()
        try:
            intent = IntentType(intent_str)
        except ValueError:
            intent = IntentType.CHAT
        return ClassifiedIntent(
            intent=intent,
            confidence=float(data.get("confidence", 1.0)),
            reason=data.get("reason", ""),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Intent classification failed, defaulting to chat: %s", exc)
        return ClassifiedIntent(
            intent=IntentType.CHAT,
            confidence=1.0,
            reason="classification error – fallback to chat",
        )
