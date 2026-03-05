import json
import logging
import time

from app.schemas.agent import ExecuteResponse, StepApproval, StepResult
from app.services import store
from app.services.agent.tools.base import ToolRegistry
from app.services.providers.base import ChatMessage, LLMRequest

logger = logging.getLogger(__name__)


def execute_plan(
    plan_id: str,
    approvals: list[StepApproval],
    registry: ToolRegistry,
    llm_generate_fn=None,
) -> ExecuteResponse:
    agent_log = store.get_agent_log_by_plan_id(plan_id)
    if not agent_log:
        raise ValueError(f"No plan found with id: {plan_id}")

    steps_db = store.get_agent_steps(agent_log["id"])

    # Apply user approvals
    approval_map = {a.step_index: a.approved for a in approvals}
    for step in steps_db:
        idx = step["step_index"]
        if idx in approval_map:
            step["approval"] = "approved" if approval_map[idx] else "rejected"

    store.update_agent_log_status(plan_id, "executing")

    results: list[StepResult] = []
    all_success = True

    for step in steps_db:
        if step["approval"] not in ("auto_approved", "approved"):
            continue

        tool = registry.get(step["tool_name"])
        if tool is None:
            results.append(StepResult(
                step_index=step["step_index"], tool_name=step["tool_name"],
                success=False, error=f"Tool '{step['tool_name']}' not found",
            ))
            all_success = False
            continue

        args = json.loads(step["args_json"])
        action = args.pop("action", step["tool_name"])

        start = time.monotonic()
        tool_result = tool.execute(action, args)
        duration_ms = int((time.monotonic() - start) * 1000)

        store.update_agent_step_result(
            step_id=step["id"],
            success=tool_result.success,
            output_json=json.dumps(tool_result.output, ensure_ascii=False, default=str) if tool_result.output else None,
            error=tool_result.error,
            duration_ms=duration_ms,
        )

        results.append(StepResult(
            step_index=step["step_index"],
            tool_name=step["tool_name"],
            success=tool_result.success,
            output=tool_result.output,
            error=tool_result.error,
            duration_ms=duration_ms,
        ))

        if not tool_result.success:
            all_success = False
            break

    final_status = "completed" if all_success else "failed"
    if not results:
        final_status = "partial"
    store.update_agent_log_status(plan_id, final_status)

    summary = _generate_summary(results, llm_generate_fn)

    return ExecuteResponse(
        plan_id=plan_id,
        status=final_status,
        results=results,
        summary=summary,
    )


def _generate_summary(results: list[StepResult], llm_generate_fn=None) -> str:
    if not results:
        return "No steps were executed."
    if llm_generate_fn:
        try:
            results_text = "\n".join(
                f"Step {r.step_index}: {r.tool_name} - {'OK' if r.success else 'FAILED'}: {r.output or r.error}"
                for r in results
            )
            req = LLMRequest(
                messages=[ChatMessage(role="user", content=results_text)],
                system_prompt="Summarize these agent execution results in 1-2 sentences. Be concise.",
                temperature=0.3, max_tokens=256,
            )
            response = llm_generate_fn(req)
            return response.reply_text.strip()
        except Exception as e:
            logger.warning("Summary generation failed: %s", e)
    ok = sum(1 for r in results if r.success)
    return f"Executed {len(results)} steps: {ok} succeeded, {len(results) - ok} failed."
