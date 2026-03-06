from app.services.jobs.tasks.daily_summary import run_daily_summary
from app.services.jobs.tasks.market_analysis import run_market_analysis
from app.services.jobs.tasks.research_report import run_research_report

TASK_REGISTRY: dict[str, callable] = {
    "market_analysis": run_market_analysis,
    "research_report": run_research_report,
    "daily_summary": run_daily_summary,
}
