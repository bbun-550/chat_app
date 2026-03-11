"""Weekly memory summarization: compress week's summary_daily nodes into a summary_weekly node."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services import store
from app.services.memory.graph_store import insert_node
from app.services.providers.base import ChatMessage, LLMRequest

logger = logging.getLogger(__name__)


def run_memory_weekly_summary(
    llm_generate_fn,
    job_id: Optional[str] = None,
    params: Optional[dict] = None,
) -> Optional[str]:
    """Summarize this week's daily summary nodes into a summary_weekly node, then delete originals."""
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=7)).isoformat()
    week_end = now.isoformat()

    daily_nodes = store.get_memory_nodes_by_type_and_date(
        "summary_daily", before=week_end, after=week_start
    )

    if len(daily_nodes) < 2:
        logger.info("Memory weekly summary: only %d daily summaries, skipping", len(daily_nodes))
        return None

    content_block = "\n\n---\n\n".join(
        f"**{n['label']}**\n{n['content']}" for n in daily_nodes
    )

    req = LLMRequest(
        messages=[ChatMessage(role="user", content=content_block)],
        system_prompt=(
            "Synthesize the following daily memory summaries into a concise weekly summary. "
            "Merge overlapping topics, highlight recurring themes and key changes. "
            "Write in a compact format suitable for long-term memory retrieval."
        ),
        temperature=0.3,
        max_tokens=1024,
    )

    try:
        response = llm_generate_fn(req)
        summary_text = response.reply_text.strip()
    except Exception as e:
        logger.error("Memory weekly summary LLM call failed: %s", e)
        return None

    # Create summary_weekly node
    week_label = f"weekly_summary_{now.strftime('%Y-W%V')}"
    insert_node(
        label=week_label,
        node_type="summary_weekly",
        content=summary_text,
    )

    # Delete consumed daily summary nodes
    daily_ids = [n["id"] for n in daily_nodes]
    deleted = store.delete_memory_nodes(daily_ids)

    report_id = store.insert_report(
        report_type="memory_weekly_summary",
        title=f"Memory Weekly Summary ({week_label})",
        content=summary_text,
        job_id=job_id,
        summary=f"Merged {len(daily_nodes)} daily summaries, deleted {deleted}",
    )

    store.insert_event(
        event_type="report_ready",
        title=f"Memory Weekly Summary ({week_label})",
        ref_id=report_id,
        ref_type="report",
    )

    logger.info(
        "Memory weekly summary: %d daily summaries → 1 weekly, deleted %d",
        len(daily_nodes), deleted,
    )
    return report_id
