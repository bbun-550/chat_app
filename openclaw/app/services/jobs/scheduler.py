import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services import store
from app.services.jobs.worker import execute_job

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def _parse_cron(expr: str) -> CronTrigger:
    """Parse a 5-field cron expression into an APScheduler CronTrigger."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (need 5 fields): {expr}")
    minute, hour, day, month, day_of_week = parts
    return CronTrigger(
        minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week
    )


def schedule_job(job_id: str, cron_expression: str) -> None:
    """Add or replace a job in the APScheduler."""
    scheduler = get_scheduler()
    trigger = _parse_cron(cron_expression)
    scheduler.add_job(
        execute_job,
        trigger=trigger,
        args=[job_id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduled job %s with cron: %s", job_id, cron_expression)


def unschedule_job(job_id: str) -> None:
    """Remove a job from the scheduler."""
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(job_id)
        logger.info("Unscheduled job %s", job_id)
    except Exception:
        logger.debug("Job %s not found in scheduler (may not be scheduled)", job_id)


def load_jobs_from_db() -> int:
    """Load all enabled jobs from DB into the scheduler. Returns count loaded."""
    jobs = store.list_jobs(enabled_only=True)
    count = 0
    for job in jobs:
        try:
            schedule_job(job["id"], job["cron_expression"])
            count += 1
        except Exception as e:
            logger.error("Failed to schedule job %s: %s", job["id"], e)
    logger.info("Loaded %d jobs from database", count)
    return count


def start_scheduler() -> None:
    """Load jobs from DB and start the scheduler."""
    scheduler = get_scheduler()
    if scheduler.running:
        logger.warning("Scheduler already running")
        return
    load_jobs_from_db()
    scheduler.start()
    logger.info("Scheduler started")


def shutdown_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shut down")
