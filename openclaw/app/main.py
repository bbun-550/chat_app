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
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    from app.services.jobs.scheduler import shutdown_scheduler
    shutdown_scheduler()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
