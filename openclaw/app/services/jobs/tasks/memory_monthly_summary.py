"""Monthly memory summarization: compress month's summary_weekly nodes into a summary_monthly node."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services import store
from app.services.memory.graph_store import insert_node
from app.services.providers.base import ChatMessage, LLMRequest

logger = logging.getLogger(__name__)


def run_memory_monthly_summary(
    llm_generate_fn,
    job_id: Optional[str] = None,
    params: Optional[dict] = None,
) -> Optional[str]:
    """Summarize this month's weekly summary nodes into a summary_monthly node, then delete originals."""
    now = datetime.now(timezone.utc)
    month_start = (now - timedelta(days=30)).isoformat()
    month_end = now.isoformat()

    weekly_nodes = store.get_memory_nodes_by_type_and_date(
        "summary_weekly", before=month_end, after=month_start
    )

    if len(weekly_nodes) < 2:
        logger.info("Memory monthly summary: only %d weekly summaries, skipping", len(weekly_nodes))
        return None

    content_block = "\n\n---\n\n".join(
        f"**{n['label']}**\n{n['content']}" for n in weekly_nodes
    )

    req = LLMRequest(
        messages=[ChatMessage(role="user", content=content_block)],
        system_prompt=(
            "Synthesize the following weekly memory summaries into a concise monthly summary. "
            "Identify long-term patterns, stable preferences, and major developments. "
            "Write in a compact format suitable for permanent long-term memory."
        ),
        temperature=0.3,
        max_tokens=1024,
    )

    try:
        response = llm_generate_fn(req)
        summary_text = response.reply_text.strip()
    except Exception as e:
        logger.error("Memory monthly summary LLM call failed: %s", e)
        return None

    # Create summary_monthly node
    month_label = f"monthly_summary_{now.strftime('%Y-%m')}"
    insert_node(
        label=month_label,
        node_type="summary_monthly",
        content=summary_text,
    )

    # Delete consumed weekly summary nodes
    weekly_ids = [n["id"] for n in weekly_nodes]
    deleted = store.delete_memory_nodes(weekly_ids)

    report_id = store.insert_report(
        report_type="memory_monthly_summary",
        title=f"Memory Monthly Summary ({month_label})",
        content=summary_text,
        job_id=job_id,
        summary=f"Merged {len(weekly_nodes)} weekly summaries, deleted {deleted}",
    )

    store.insert_event(
        event_type="report_ready",
        title=f"Memory Monthly Summary ({month_label})",
        ref_id=report_id,
        ref_type="report",
    )

    logger.info(
        "Memory monthly summary: %d weekly summaries → 1 monthly, deleted %d",
        len(weekly_nodes), deleted,
    )
    return report_id
