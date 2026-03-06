from fastapi import APIRouter, HTTPException

from app.schemas.jobs import ReportListItem, ReportResponse
from app.services import store

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportListItem])
def list_reports(report_type: str | None = None, limit: int = 50):
    reports = store.list_reports(report_type=report_type, limit=limit)
    return [
        {
            "id": r["id"], "job_id": r["job_id"], "report_type": r["report_type"],
            "title": r["title"], "summary": r["summary"],
            "status": r["status"], "created_at": r["created_at"],
        }
        for r in reports
    ]


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: str):
    report = store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
