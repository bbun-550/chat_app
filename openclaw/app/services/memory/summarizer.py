import logging

from app.services import store
from app.services.memory.vector_store import store_memory
from app.services.providers.base import ChatMessage, LLMRequest

logger = logging.getLogger(__name__)

AUTO_SUMMARY_THRESHOLD = 20  # messages since last summary


def generate_daily_summary(
    conversation_id: str,
    llm_generate_fn,
) -> str | None:
    """Summarize conversation messages using LLM and store as daily summary."""
    messages = store.get_messages(conversation_id)
    if not messages:
        return None

    conversation_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in messages
    )

    req = LLMRequest(
        messages=[ChatMessage(role="user", content=conversation_text)],
        system_prompt=(
            "Summarize this conversation concisely. "
            "Focus on key topics discussed, decisions made, and important information shared. "
            "Include the number of distinct facts or topics covered."
        ),
        temperature=0.3,
        max_tokens=512,
    )

    try:
        response = llm_generate_fn(req)
        summary_text = response.reply_text.strip()

        # Estimate fact count from summary (rough heuristic)
        sentences = [s.strip() for s in summary_text.replace("\n", ". ").split(".") if s.strip()]
        fact_count = len(sentences)

        summary_id = store.insert_daily_summary(
            conversation_id=conversation_id,
            summary_text=summary_text,
            fact_count=fact_count,
        )

        # Also store summary as vector memory for LTM retrieval
        store_memory(
            content=summary_text,
            memory_type="summary",
            source_conversation_id=conversation_id,
        )

        logger.info(
            "Generated daily summary for conversation %s (facts=%d)",
            conversation_id, fact_count,
        )
        return summary_id
    except Exception as e:
        logger.error("Failed to generate daily summary: %s", e)
        return None


def auto_summarize_if_needed(
    conversation_id: str,
    llm_generate_fn,
) -> str | None:
    """Auto-summarize if message count exceeds threshold since last summary."""
    messages = store.get_messages(conversation_id)
    if len(messages) < AUTO_SUMMARY_THRESHOLD:
        return None

    latest = store.get_latest_daily_summary()
    if latest and latest.get("conversation_id") == conversation_id:
        # Count messages after last summary
        summary_time = latest["created_at"]
        new_messages = [m for m in messages if m["created_at"] > summary_time]
        if len(new_messages) < AUTO_SUMMARY_THRESHOLD:
            return None

    return generate_daily_summary(conversation_id, llm_generate_fn)
