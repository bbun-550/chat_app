import logging
from typing import Optional

from app.services import store
from app.services.providers.base import ChatMessage, LLMRequest

logger = logging.getLogger(__name__)


def run_research_report(
    llm_generate_fn,
    job_id: Optional[str] = None,
    params: Optional[dict] = None,
) -> Optional[str]:
    """Generate a deep research report on a given topic."""
    params = params or {}
    topic = params.get("topic", "Emerging AI applications")
    depth = params.get("depth", "comprehensive")

    prompt_text = (
        f"Write a {depth} research report on: {topic}. "
        "Include: executive summary, background, current state, key findings, "
        "challenges, future outlook, and recommendations. "
        "Use markdown formatting with headers."
    )

    req = LLMRequest(
        messages=[ChatMessage(role="user", content=prompt_text)],
        system_prompt=(
            "You are a senior research analyst. Produce well-structured, "
            "evidence-based reports with clear sections and actionable insights."
        ),
        temperature=0.3,
        max_tokens=4096,
    )

    try:
        response = llm_generate_fn(req)
        title = f"Research Report: {topic}"
        summary = response.reply_text[:200].rsplit(" ", 1)[0] + "..."

        report_id = store.insert_report(
            report_type="research_report",
            title=title,
            content=response.reply_text,
            job_id=job_id,
            summary=summary,
            params=params,
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

        store.insert_event(
            event_type="report_ready",
            title=f"Research report ready: {topic}",
            ref_id=report_id,
            ref_type="report",
        )

        logger.info("Research report generated: %s", report_id)
        return report_id
    except Exception as e:
        logger.error("Research report task failed: %s", e)
        store.insert_event(
            event_type="job_failed",
            title="Research report task failed",
            body=str(e),
            ref_id=job_id,
            ref_type="job",
        )
        return None
