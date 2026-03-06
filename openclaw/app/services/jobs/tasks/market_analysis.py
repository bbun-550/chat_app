import logging
from typing import Optional

from app.services import store
from app.services.providers.base import ChatMessage, LLMRequest

logger = logging.getLogger(__name__)


def run_market_analysis(
    llm_generate_fn,
    job_id: Optional[str] = None,
    params: Optional[dict] = None,
) -> Optional[str]:
    """Generate a market analysis report via LLM."""
    params = params or {}
    topics = params.get("topics", ["general AI market trends"])
    time_horizon = params.get("time_horizon", "weekly")

    prompt_text = (
        f"Provide a {time_horizon} market analysis covering these topics: "
        f"{', '.join(topics)}. "
        "Include key trends, notable developments, potential opportunities and risks. "
        "Structure the report with clear sections and bullet points."
    )

    req = LLMRequest(
        messages=[ChatMessage(role="user", content=prompt_text)],
        system_prompt=(
            "You are a market research analyst. Provide concise, actionable analysis. "
            "Use markdown formatting with headers and bullet points."
        ),
        temperature=0.4,
        max_tokens=2048,
    )

    try:
        response = llm_generate_fn(req)
        title = f"Market Analysis: {', '.join(topics[:3])}"
        summary = response.reply_text[:200].rsplit(" ", 1)[0] + "..."

        report_id = store.insert_report(
            report_type="market_analysis",
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
            title=f"Market analysis ready: {title}",
            ref_id=report_id,
            ref_type="report",
        )

        logger.info("Market analysis report generated: %s", report_id)
        return report_id
    except Exception as e:
        logger.error("Market analysis task failed: %s", e)
        store.insert_event(
            event_type="job_failed",
            title="Market analysis task failed",
            body=str(e),
            ref_id=job_id,
            ref_type="job",
        )
        return None
