"""Daily memory summarization: compress day's fact/entity/concept nodes into a summary_daily node."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services import store
from app.services.memory.graph_store import insert_node
from app.services.providers.base import ChatMessage, LLMRequest

logger = logging.getLogger(__name__)

EDGE_PROTECTION_THRESHOLD = 3  # nodes with >= this many edges are kept


def run_memory_daily_summary(
    llm_generate_fn,
    job_id: Optional[str] = None,
    params: Optional[dict] = None,
) -> Optional[str]:
    """Summarize today's fact/entity/concept nodes into a summary_daily node, then delete originals."""
    now = datetime.now(timezone.utc)
    day_start = (now - timedelta(days=1)).isoformat()
    day_end = now.isoformat()

    # Gather nodes created in the last 24 hours
    target_types = ["fact", "entity", "concept"]
    all_nodes = []
    for nt in target_types:
        nodes = store.get_memory_nodes_by_type_and_date(nt, before=day_end, after=day_start)
        all_nodes.extend(nodes)

    if len(all_nodes) < 3:
        logger.info("Memory daily summary: only %d nodes, skipping", len(all_nodes))
        return None

    # Build content for summarization
    content_lines = [f"- [{n['label']}] {n['content']}" for n in all_nodes]
    content_block = "\n".join(content_lines)

    req = LLMRequest(
        messages=[ChatMessage(role="user", content=content_block)],
        system_prompt=(
            "Summarize the following memory entries into a concise daily summary. "
            "Preserve key facts, entities, and relationships. "
            "Write in a compact format suitable for long-term memory retrieval."
        ),
        temperature=0.3,
        max_tokens=1024,
    )

    try:
        response = llm_generate_fn(req)
        summary_text = response.reply_text.strip()
    except Exception as e:
        logger.error("Memory daily summary LLM call failed: %s", e)
        return None

    # Create summary_daily node
    date_label = now.strftime("%Y-%m-%d")
    summary_node_id = insert_node(
        label=f"daily_summary_{date_label}",
        node_type="summary_daily",
        content=summary_text,
    )

    # Delete original nodes (protect well-connected entities)
    deletable = []
    protected = 0
    for n in all_nodes:
        edge_count = store.count_node_edges(n["id"])
        if edge_count >= EDGE_PROTECTION_THRESHOLD:
            protected += 1
        else:
            deletable.append(n["id"])

    deleted = store.delete_memory_nodes(deletable)

    # Create report
    report_id = store.insert_report(
        report_type="memory_daily_summary",
        title=f"Memory Daily Summary ({date_label})",
        content=summary_text,
        job_id=job_id,
        summary=f"Summarized {len(all_nodes)} nodes, deleted {deleted}, protected {protected}",
    )

    store.insert_event(
        event_type="report_ready",
        title=f"Memory Daily Summary ({date_label})",
        ref_id=report_id,
        ref_type="report",
    )

    logger.info(
        "Memory daily summary: %d nodes → 1 summary, deleted %d, protected %d",
        len(all_nodes), deleted, protected,
    )
    return report_id
