from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ApprovalStatus(str, Enum):
    AUTO_APPROVED = "auto_approved"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AgentStepSchema(BaseModel):
    step_index: int
    tool_name: str
    args: dict[str, Any]
    risk_level: RiskLevel
    approval: ApprovalStatus
    description: str


class PlanRequest(BaseModel):
    conversation_id: str
    message: str
    provider: str = Field(default="gemini")
    model: Optional[str] = None


class PlanResponse(BaseModel):
    plan_id: str
    intent: str
    steps: list[AgentStepSchema]
    overall_risk: RiskLevel
    requires_approval: bool


class StepApproval(BaseModel):
    step_index: int
    approved: bool


class ExecuteRequest(BaseModel):
    plan_id: str
    approvals: list[StepApproval] = Field(default_factory=list)


class StepResult(BaseModel):
    step_index: int
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0


class ExecuteResponse(BaseModel):
    plan_id: str
    status: str
    results: list[StepResult]
    summary: str


class AgentLogResponse(BaseModel):
    id: str
    plan_id: str
    conversation_id: Optional[str]
    intent: str
    overall_risk: str
    status: str
    created_at: str
