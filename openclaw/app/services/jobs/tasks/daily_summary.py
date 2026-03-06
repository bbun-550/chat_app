import logging
from typing import Optional

from app.services import store
from app.services.memory.summarizer import generate_daily_summary

logger = logging.getLogger(__name__)


def run_daily_summary(
    llm_generate_fn,
    job_id: Optional[str] = None,
    params: Optional[dict] = None,
) -> Optional[str]:
    """Run daily summary across recent conversations, leveraging existing summarizer."""
    params = params or {}
    conversation_id = params.get("conversation_id")

    if conversation_id:
        conversation_ids = [conversation_id]
    else:
        conversations = store.list_conversations()
        conversation_ids = [c["id"] for c in conversations[:10]]

    summaries = []
    for conv_id in conversation_ids:
        summary_id = generate_daily_summary(conv_id, llm_generate_fn)
        if summary_id:
            summaries.append(conv_id)

    if not summaries:
        logger.info("Daily summary: no conversations needed summarization")
        return None

    title = f"Daily Summary ({len(summaries)} conversations)"
    recent = store.get_daily_summaries(limit=len(summaries))
    content = "\n\n---\n\n".join(
        f"**Conversation:** {s['conversation_id']}\n{s['summary_text']}"
        for s in recent
    )

    report_id = store.insert_report(
        report_type="daily_summary",
        title=title,
        content=content,
        job_id=job_id,
        summary=f"Summarized {len(summaries)} conversations",
        params=params,
    )

    store.insert_event(
        event_type="report_ready",
        title=title,
        ref_id=report_id,
        ref_type="report",
    )

    logger.info("Daily summary complete: %d conversations", len(summaries))
    return report_id
