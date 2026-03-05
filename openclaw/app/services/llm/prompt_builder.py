import logging

from app.services import store
from app.services.memory.vector_store import search
from app.services.providers.base import ChatMessage, LLMRequest

logger = logging.getLogger(__name__)

STM_MESSAGE_LIMIT = 20  # recent messages to include


def build_prompt(
    conversation_id: str,
    user_message: str,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> LLMRequest:
    """Build an LLM request integrating STM, DSM, and LTM."""

    # 1. LTM — search vector memories by user message
    ltm_results = []
    try:
        ltm_results = search(query=user_message, limit=5, threshold=0.5)
    except Exception as e:
        logger.warning("LTM search failed: %s", e)

    # 2. DSM — get latest daily summary
    latest_summary = store.get_latest_daily_summary()

    # 3. STM — recent N messages
    all_messages = store.get_messages(conversation_id)
    recent_messages = all_messages[-STM_MESSAGE_LIMIT:]

    # 4. Build augmented system prompt
    parts = []
    if system_prompt:
        parts.append(system_prompt)

    if ltm_results:
        memory_lines = [m["content"] for m in ltm_results]
        parts.append("## Long-term Memory\n" + "\n".join(f"- {line}" for line in memory_lines))

    if latest_summary:
        parts.append("## Recent Summary\n" + latest_summary["summary_text"])

    augmented_system_prompt = "\n\n".join(parts) if parts else None

    # 5. Build message list from STM
    messages = [
        ChatMessage(role=m["role"], content=m["content"])
        for m in recent_messages
    ]

    return LLMRequest(
        messages=messages,
        system_prompt=augmented_system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
