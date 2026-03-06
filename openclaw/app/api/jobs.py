import json

from fastapi import APIRouter, HTTPException

from app.schemas.jobs import CreateJobRequest, JobResponse, UpdateJobRequest
from app.services import store
from app.services.jobs.scheduler import schedule_job, unschedule_job
from app.services.jobs.worker import execute_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=201)
def create_job(req: CreateJobRequest):
    if req.task_type not in ("market_analysis", "research_report", "daily_summary"):
        raise HTTPException(status_code=400, detail="Invalid task_type")
    try:
        job = store.create_job(
            name=req.name,
            task_type=req.task_type,
            cron_expression=req.cron_expression,
            params=req.params,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        schedule_job(job["id"], req.cron_expression)
    except ValueError as exc:
        store.delete_job(job["id"])
        raise HTTPException(status_code=400, detail=f"Invalid cron expression: {exc}")
    return job


@router.get("")
def list_jobs(enabled_only: bool = False):
    return store.list_jobs(enabled_only=enabled_only)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(job_id: str, req: UpdateJobRequest):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    updates: dict = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.cron_expression is not None:
        updates["cron_expression"] = req.cron_expression
    if req.params is not None:
        updates["params_json"] = json.dumps(req.params, ensure_ascii=False)
    if req.enabled is not None:
        updates["enabled"] = req.enabled
    if not updates:
        return job
    updated = store.update_job(job_id, **updates)
    if updated["enabled"]:
        schedule_job(job_id, updated["cron_expression"])
    else:
        unschedule_job(job_id)
    return updated


@router.delete("/{job_id}")
def delete_job(job_id: str):
    unschedule_job(job_id)
    deleted = store.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"deleted": True}


@router.post("/{job_id}/run")
def trigger_job(job_id: str):
    """Manually trigger a job execution (outside of cron schedule)."""
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    report_id = execute_job(job_id)
    return {"job_id": job_id, "report_id": report_id}
