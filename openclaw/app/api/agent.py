import json
import logging

from fastapi import APIRouter, HTTPException

from app.schemas.agent import ExecuteRequest, ExecuteResponse, PlanRequest, PlanResponse
from app.services import store
from app.services.agent.planner import generate_plan
from app.services.agent.executor import execute_plan
from app.services.agent.tools.base import ToolRegistry
from app.services.agent.tools.filesystem import FilesystemTool
from app.services.agent.tools.shell import ShellTool
from app.services.agent.tools.external_ai import ExternalAITool
from app.services.llm_router import LLMRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

_llm_router: LLMRouter | None = None
_tool_registry: ToolRegistry | None = None


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        _tool_registry.register(FilesystemTool())
        _tool_registry.register(ShellTool())
        _tool_registry.register(ExternalAITool())
    return _tool_registry


@router.post("/plan", response_model=PlanResponse)
def create_plan(req: PlanRequest):
    conversation = store.get_conversation(req.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    llm_router = get_llm_router()
    provider = req.provider
    model = req.model

    def llm_fn(llm_req):
        if model:
            llm_req.model = model
        return llm_router.generate(provider, llm_req)

    try:
        plan = generate_plan(
            user_message=req.message,
            registry=get_tool_registry(),
            llm_generate_fn=llm_fn,
            conversation_id=req.conversation_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Planning failed: {exc}") from exc

    log_id = store.insert_agent_log(
        plan_id=plan.plan_id,
        conversation_id=req.conversation_id,
        intent=plan.intent,
        plan_json=plan.model_dump_json(),
        overall_risk=plan.overall_risk.value,
        provider=provider,
        model=model,
    )
    for step in plan.steps:
        store.insert_agent_step(
            agent_log_id=log_id,
            step_index=step.step_index,
            tool_name=step.tool_name,
            args_json=json.dumps(step.args, ensure_ascii=False),
            risk_level=step.risk_level.value,
            approval=step.approval.value,
            description=step.description,
        )

    return plan


@router.post("/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest):
    agent_log = store.get_agent_log_by_plan_id(req.plan_id)
    if not agent_log:
        raise HTTPException(status_code=404, detail="Plan not found")

    llm_router = get_llm_router()
    provider = agent_log.get("provider", "gemini")

    def llm_fn(llm_req):
        return llm_router.generate(provider, llm_req)

    try:
        result = execute_plan(
            plan_id=req.plan_id,
            approvals=req.approvals,
            registry=get_tool_registry(),
            llm_generate_fn=llm_fn,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Execution failed: {exc}") from exc

    return result


@router.get("/logs")
def list_logs(conversation_id: str | None = None, limit: int = 50):
    return store.list_agent_logs(conversation_id=conversation_id, limit=limit)
