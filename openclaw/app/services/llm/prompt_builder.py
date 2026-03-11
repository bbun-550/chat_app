import logging

from app.services import store
from app.services.memory.graph_store import hybrid_search
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
    """Build an LLM request integrating STM, DSM (graph summaries), and LTM (hybrid search)."""

    # 1. LTM — hybrid vector + graph search
    ltm_results = []
    try:
        ltm_results = hybrid_search(query=user_message, limit=5, threshold=0.5, graph_depth=2)
    except Exception as e:
        logger.warning("LTM hybrid search failed: %s", e)

    # 2. DSM — hierarchical summary nodes (monthly > weekly > daily), fallback to daily_summaries
    summary_node = None
    try:
        summary_node = store.get_latest_summary_node()
    except Exception as e:
        logger.warning("Graph summary lookup failed: %s", e)

    if not summary_node:
        latest_summary = store.get_latest_daily_summary()
    else:
        latest_summary = None

    # 3. STM — recent N messages
    all_messages = store.get_messages(conversation_id)
    recent_messages = all_messages[-STM_MESSAGE_LIMIT:]

    # 4. Build augmented system prompt
    parts = []
    if system_prompt:
        parts.append(system_prompt)

    if ltm_results:
        memory_lines = []
        for m in ltm_results:
            label = m.get("label", "")
            content = m.get("content", "")
            edge = m.get("edge")
            if edge:
                rel = edge.get("relation_type", "related_to")
                line = f"- [{label}] ({rel}) {content}"
            elif label and label != content:
                line = f"- [{label}] {content}"
            else:
                line = f"- {content}"
            memory_lines.append(line)
        parts.append("## Long-term Memory\n" + "\n".join(memory_lines))

    if summary_node:
        level = summary_node["node_type"].replace("summary_", "")
        parts.append(f"## Recent Summary ({level})\n" + summary_node["content"])
    elif latest_summary:
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
