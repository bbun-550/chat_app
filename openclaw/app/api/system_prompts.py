from fastapi import APIRouter, HTTPException

from app.schemas.chat import (
    CreateSystemPromptRequest,
    SystemPromptResponse,
    UpdateSystemPromptRequest,
)
from app.services import store

router = APIRouter(prefix="/system-prompts", tags=["system-prompts"])


@router.post("", response_model=SystemPromptResponse, status_code=201)
def create_system_prompt(req: CreateSystemPromptRequest):
    return store.create_system_prompt(req.name, req.content)


@router.get("")
def list_system_prompts():
    return store.list_system_prompts()


@router.get("/{prompt_id}", response_model=SystemPromptResponse)
def get_system_prompt(prompt_id: str):
    prompt = store.get_system_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="System prompt not found")
    return prompt


@router.put("/{prompt_id}", response_model=SystemPromptResponse)
def update_system_prompt(prompt_id: str, req: UpdateSystemPromptRequest):
    prompt = store.update_system_prompt(prompt_id, req.name, req.content)
    if not prompt:
        raise HTTPException(status_code=404, detail="System prompt not found")
    return prompt


@router.delete("/{prompt_id}")
def delete_system_prompt(prompt_id: str):
    deleted = store.delete_system_prompt(prompt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="System prompt not found")
    return {"deleted": True}
