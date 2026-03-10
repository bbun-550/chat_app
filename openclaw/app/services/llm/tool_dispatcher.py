"""Tool dispatcher for the router LLM.

Dispatches a classified intent to the appropriate external tool. Each tool
method is a stub that returns a plain-text response; actual library integrations
are guarded by ImportError so missing optional dependencies do not crash the server.
"""
from __future__ import annotations

import logging
from typing import Callable

from app.services.llm.intent_classifier import ClassifiedIntent, IntentType
from app.services.llm.router_config import OBSIDIAN_VAULT_PATH, ROUTER_THRESHOLD

logger = logging.getLogger(__name__)


class ToolDispatcher:
    """Dispatch a classified intent to the appropriate tool.

    If the intent is CHAT, or confidence is below *threshold*, returns None so
    the caller falls back to the standard LLM pipeline.
    """

    def __init__(self, threshold: float = ROUTER_THRESHOLD) -> None:
        self.threshold = threshold

    def dispatch(
        self,
        classified: ClassifiedIntent,
        message: str,
        llm_fn: Callable | None = None,
    ) -> str | None:
        """Return tool output string, or None to use the normal chat pipeline."""
        if classified.intent == IntentType.CHAT:
            return None
        if classified.confidence < self.threshold:
            logger.info(
                "Routing skipped: intent=%s confidence=%.2f below threshold=%.2f",
                classified.intent, classified.confidence, self.threshold,
            )
            return None

        logger.info("Routing to tool: intent=%s reason=%s", classified.intent, classified.reason)
        handler = {
            IntentType.BROWSE: self._browser_use,
            IntentType.RESEARCH: self._gpt_researcher,
            IntentType.EXECUTE: self._open_interpreter,
            IntentType.CODE: self._aider,
            IntentType.OBSIDIAN: self._obsidian_write,
        }.get(classified.intent)

        if handler is None:
            return None
        return handler(message)

    # ── Tool stubs ──────────────────────────────────────────────────────────

    def _browser_use(self, message: str) -> str:
        try:
            from browser_use import Agent as BrowserAgent  # noqa: F401
            # TODO: implement real browser-use integration
            return f"[browser-use] stub: would browse for — {message}"
        except ImportError:
            return (
                "[라우터 안내] 실시간 웹 검색이 필요한 질문입니다. "
                "서버에 `browser-use` 패키지가 설치되지 않아 일반 LLM으로 답변합니다.\n\n"
                "설치: pip install browser-use"
            )

    def _gpt_researcher(self, message: str) -> str:
        try:
            from gpt_researcher import GPTResearcher  # noqa: F401
            # TODO: implement real gpt-researcher integration
            return f"[gpt-researcher] stub: would research — {message}"
        except ImportError:
            return (
                "[라우터 안내] 심층 리서치가 필요한 질문입니다. "
                "서버에 `gpt-researcher` 패키지가 설치되지 않아 일반 LLM으로 답변합니다.\n\n"
                "설치: pip install gpt-researcher"
            )

    def _open_interpreter(self, message: str) -> str:
        try:
            import interpreter  # noqa: F401
            # TODO: implement real open-interpreter integration
            return f"[open-interpreter] stub: would execute — {message}"
        except ImportError:
            return (
                "[라우터 안내] 터미널/파일 실행이 필요한 요청입니다. "
                "서버에 `open-interpreter` 패키지가 설치되지 않아 일반 LLM으로 답변합니다.\n\n"
                "설치: pip install open-interpreter"
            )

    def _aider(self, message: str) -> str:
        try:
            from aider.coders import Coder  # noqa: F401
            # TODO: implement real aider integration
            return f"[aider] stub: would edit code for — {message}"
        except ImportError:
            return (
                "[라우터 안내] 코드 편집이 필요한 요청입니다. "
                "서버에 `aider-chat` 패키지가 설치되지 않아 일반 LLM으로 답변합니다.\n\n"
                "설치: pip install aider-chat"
            )

    def _obsidian_write(self, message: str) -> str:
        if not OBSIDIAN_VAULT_PATH:
            return (
                "[라우터 안내] Obsidian vault 경로가 설정되지 않았습니다. "
                "환경변수 OBSIDIAN_VAULT_PATH를 설정하세요."
            )
        try:
            import interpreter  # noqa: F401
            # TODO: implement real Obsidian vault write via open-interpreter
            return f"[obsidian] stub: would write note to {OBSIDIAN_VAULT_PATH} — {message}"
        except ImportError:
            return (
                "[라우터 안내] Obsidian 노트 작성이 필요한 요청입니다. "
                "서버에 `open-interpreter` 패키지가 설치되지 않아 일반 LLM으로 답변합니다.\n\n"
                "설치: pip install open-interpreter"
            )
