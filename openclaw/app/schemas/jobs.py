from typing import Any, Optional

from pydantic import BaseModel


# -- Job schemas --


class CreateJobRequest(BaseModel):
    name: str
    task_type: str
    cron_expression: str
    params: Optional[dict[str, Any]] = None


class JobResponse(BaseModel):
    id: str
    name: str
    task_type: str
    cron_expression: str
    params_json: str
    enabled: int
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    created_at: str
    updated_at: str


class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    enabled: Optional[int] = None


# -- Report schemas --


class ReportResponse(BaseModel):
    id: str
    job_id: Optional[str] = None
    report_type: str
    title: str
    content: str
    summary: Optional[str] = None
    params_json: str
    provider: Optional[str] = None
    model: Optional[str] = None
    latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    status: str
    created_at: str


class ReportListItem(BaseModel):
    id: str
    job_id: Optional[str] = None
    report_type: str
    title: str
    summary: Optional[str] = None
    status: str
    created_at: str


# -- Event schemas --


class EventResponse(BaseModel):
    id: str
    event_type: str
    title: str
    body: Optional[str] = None
    ref_id: Optional[str] = None
    ref_type: Optional[str] = None
    is_read: int
    created_at: str
