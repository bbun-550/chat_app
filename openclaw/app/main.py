from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import agent, chat, conversations, events, export, jobs, reports, system_prompts

load_dotenv()

app = FastAPI(title="OpenClaw")

from app.middleware.auth import AuthMiddleware

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations.router)
app.include_router(system_prompts.router)
app.include_router(chat.router)
app.include_router(export.router)
app.include_router(agent.router)
app.include_router(jobs.router)
app.include_router(reports.router)
app.include_router(events.router)


@app.on_event("startup")
def on_startup():
    from app.services.jobs.scheduler import start_scheduler
    from app.services.db import engine
    import sqlalchemy
    with engine.connect() as conn:
        try:
            conn.execute(sqlalchemy.text(
                "ALTER TABLE messages ADD COLUMN is_bookmarked INTEGER NOT NULL DEFAULT 0"
            ))
            conn.commit()
        except Exception:
            pass  # Column already exists
    # Migrate embedding dimension (384 → 1024) if needed
    try:
        from app.services.memory.migrate_embeddings import migrate_embedding_dimension
        migrate_embedding_dimension()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Embedding migration skipped: %s", e)

    start_scheduler()

    # Register system memory summarization jobs (idempotent)
    try:
        from app.services import store as _store
        from app.services.jobs.scheduler import schedule_job
        _MEMORY_JOBS = [
            {"name": "Memory Daily Summary", "task_type": "memory_daily_summary", "cron": "0 2 * * *"},
            {"name": "Memory Weekly Summary", "task_type": "memory_weekly_summary", "cron": "0 3 * * 1"},
            {"name": "Memory Monthly Summary", "task_type": "memory_monthly_summary", "cron": "0 4 1 * *"},
        ]
        existing_types = {j["task_type"] for j in _store.list_jobs()}
        for spec in _MEMORY_JOBS:
            if spec["task_type"] not in existing_types:
                created = _store.create_job(
                    name=spec["name"], task_type=spec["task_type"],
                    cron_expression=spec["cron"],
                )
                schedule_job(created["id"], spec["cron"])
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to register memory jobs: %s", e)


@app.on_event("shutdown")
def on_shutdown():
    from app.services.jobs.scheduler import shutdown_scheduler
    shutdown_scheduler()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
