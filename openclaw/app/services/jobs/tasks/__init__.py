from app.services.jobs.tasks.daily_summary import run_daily_summary
from app.services.jobs.tasks.market_analysis import run_market_analysis
from app.services.jobs.tasks.research_report import run_research_report
from app.services.jobs.tasks.memory_daily_summary import run_memory_daily_summary
from app.services.jobs.tasks.memory_weekly_summary import run_memory_weekly_summary
from app.services.jobs.tasks.memory_monthly_summary import run_memory_monthly_summary

TASK_REGISTRY: dict[str, callable] = {
    "market_analysis": run_market_analysis,
    "research_report": run_research_report,
    "daily_summary": run_daily_summary,
    "memory_daily_summary": run_memory_daily_summary,
    "memory_weekly_summary": run_memory_weekly_summary,
    "memory_monthly_summary": run_memory_monthly_summary,
}
