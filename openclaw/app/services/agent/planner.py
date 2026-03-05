import json
import logging
import uuid
from typing import Any

from app.schemas.agent import AgentStepSchema, ApprovalStatus, PlanResponse, RiskLevel
from app.services.agent.policy import evaluate_plan, overall_risk, requires_approval
from app.services.agent.tools.base import ToolRegistry
from app.services.providers.base import ChatMessage, LLMRequest

logger = logging.getLogger(__name__)

PLANNING_SYSTEM_PROMPT = """You are an agent planner. Given a user request, generate an execution plan.

Available tools and actions:
{tools_description}

Respond with a JSON object:
{{
  "intent": "brief description of what the user wants",
  "steps": [
    {{
      "tool_name": "filesystem",
      "action": "list_directory",
      "args": {{"path": "/Users/example/Desktop"}},
      "description": "List files on desktop to understand current state"
    }}
  ]
}}

Rules:
- Only use tools and actions from the available list
- Break complex requests into sequential steps
- Prefer read operations before write operations
- Be conservative: fewer steps is better
- Return ONLY valid JSON, no markdown fencing
"""


def generate_plan(
    user_message: str,
    registry: ToolRegistry,
    llm_generate_fn,
    conversation_id: str | None = None,
) -> PlanResponse:
    tools_desc = json.dumps(registry.list_all_actions(), indent=2)
    system_prompt = PLANNING_SYSTEM_PROMPT.format(tools_description=tools_desc)

    req = LLMRequest(
        messages=[ChatMessage(role="user", content=user_message)],
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=2048,
    )

    response = llm_generate_fn(req)
    plan_data = _parse_plan_json(response.reply_text)
    plan_id = str(uuid.uuid4())

    steps = []
    for i, step_data in enumerate(plan_data.get("steps", [])):
        steps.append(AgentStepSchema(
            step_index=i,
            tool_name=step_data.get("tool_name", "unknown"),
            args={"action": step_data.get("action", ""), **step_data.get("args", {})},
            risk_level=RiskLevel.LOW,
            approval=ApprovalStatus.PENDING,
            description=step_data.get("description", ""),
        ))

    steps = evaluate_plan(steps, registry)

    return PlanResponse(
        plan_id=plan_id,
        intent=plan_data.get("intent", user_message),
        steps=steps,
        overall_risk=overall_risk(steps),
        requires_approval=requires_approval(steps),
    )


def _parse_plan_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse plan JSON: %s", cleaned[:200])
        return {"intent": "unknown", "steps": []}
