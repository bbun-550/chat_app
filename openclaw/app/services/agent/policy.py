from app.schemas.agent import AgentStepSchema, ApprovalStatus, RiskLevel
from app.services.agent.tools.base import ToolRegistry


def evaluate_plan(steps: list[AgentStepSchema], registry: ToolRegistry) -> list[AgentStepSchema]:
    """Evaluate risk for each step and set approval status."""
    evaluated = []
    for step in steps:
        tool = registry.get(step.tool_name)
        if tool is None:
            step.risk_level = RiskLevel.HIGH
            step.approval = ApprovalStatus.PENDING
        else:
            action = step.args.get("action", "")
            step.risk_level = tool.risk_for(action, step.args)
            if step.risk_level == RiskLevel.LOW:
                step.approval = ApprovalStatus.AUTO_APPROVED
            else:
                step.approval = ApprovalStatus.PENDING
        evaluated.append(step)
    return evaluated


def overall_risk(steps: list[AgentStepSchema]) -> RiskLevel:
    if any(s.risk_level == RiskLevel.HIGH for s in steps):
        return RiskLevel.HIGH
    if any(s.risk_level == RiskLevel.MEDIUM for s in steps):
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def requires_approval(steps: list[AgentStepSchema]) -> bool:
    return any(s.approval == ApprovalStatus.PENDING for s in steps)
