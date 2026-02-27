from typing import Any, Optional

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    title: str = "New Chat"


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    provider: str = Field(default="gemini")
    model: Optional[str] = None
    system_prompt_id: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    candidate_count: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    provider: str
    model: str
    latency_ms: int
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class CreateSystemPromptRequest(BaseModel):
    name: str
    content: str


class SystemPromptResponse(BaseModel):
    id: str
    name: str
    content: str
    created_at: str
    updated_at: str


class UpdateSystemPromptRequest(BaseModel):
    name: str
    content: str


class ExportResponse(BaseModel):
    conversation: Optional[dict[str, Any]]
    messages: list[dict[str, Any]]
    runs: list[dict[str, Any]]
    meta: list[dict[str, Any]]


class UpsertMessageMetaRequest(BaseModel):
    task_type: Optional[str] = None
    quality_score: Optional[int] = None
    tags: Optional[list[str]] = None
    teacher_rationale: Optional[str] = None
    rating_source: Optional[str] = None
    is_rejected: Optional[int] = None
    language: Optional[str] = None
    safety_flags: Optional[list[str]] = None
    notes: Optional[str] = None
