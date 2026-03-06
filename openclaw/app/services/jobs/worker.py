import json
import logging
from typing import Optional

from app.services import store
from app.services.jobs.tasks import TASK_REGISTRY
from app.services.llm_router import LLMRouter

logger = logging.getLogger(__name__)

_llm_router: LLMRouter | None = None


def _get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router


def execute_job(job_id: str) -> Optional[str]:
    """Execute a job by ID. Returns report_id or None."""
    job = store.get_job(job_id)
    if not job:
        logger.error("Job not found: %s", job_id)
        return None

    task_type = job["task_type"]
    task_fn = TASK_REGISTRY.get(task_type)
    if not task_fn:
        logger.error("Unknown task type: %s", task_type)
        return None

    params = json.loads(job["params_json"]) if job["params_json"] else {}
    provider = params.pop("provider", "gemini")

    router = _get_llm_router()

    def llm_generate_fn(req):
        return router.generate(provider, req)

    store.insert_event(
        event_type="job_started",
        title=f"Job started: {job['name']}",
        ref_id=job_id,
        ref_type="job",
    )

    try:
        report_id = task_fn(
            llm_generate_fn=llm_generate_fn,
            job_id=job_id,
            params=params,
        )
        store.update_job_last_run(job_id)

        store.insert_event(
            event_type="job_completed",
            title=f"Job completed: {job['name']}",
            ref_id=job_id,
            ref_type="job",
        )

        return report_id
    except Exception as e:
        logger.error("Job execution failed for %s: %s", job_id, e)
        store.insert_event(
            event_type="job_failed",
            title=f"Job failed: {job['name']}",
            body=str(e),
            ref_id=job_id,
            ref_type="job",
        )
        return None


def execute_task_directly(
    task_type: str, params: Optional[dict] = None
) -> Optional[str]:
    """Execute a task without a Job record (for ad-hoc runs)."""
    task_fn = TASK_REGISTRY.get(task_type)
    if not task_fn:
        raise ValueError(f"Unknown task type: {task_type}")

    params = dict(params) if params else {}
    provider = params.pop("provider", "gemini")
    router = _get_llm_router()

    def llm_generate_fn(req):
        return router.generate(provider, req)

    return task_fn(llm_generate_fn=llm_generate_fn, params=params)
