from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse, UpsertMessageMetaRequest
from app.services import store
from app.services.llm_router import LLMRouter
from app.services.providers.base import ChatMessage, LLMRequest

router = APIRouter(tags=["chat"])
_llm_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router


@router.post("/chat", response_model=ChatResponse)
def send_message(req: ChatRequest):
    conversation = store.get_conversation(req.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    system_prompt_content = None
    if req.system_prompt_id:
        prompt = store.get_system_prompt(req.system_prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="System prompt not found")
        system_prompt_content = prompt["content"]

    selected_model = req.model or "gemini-3-flash-preview"
    user_message_id = store.insert_message(req.conversation_id, "user", req.message, selected_model)
    history = store.get_messages(req.conversation_id)
    provider_messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in history]

    llm_req = LLMRequest(
        messages=provider_messages,
        system_prompt=system_prompt_content,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        metadata={"conversation_id": req.conversation_id},
    )

    try:
        llm_res = get_llm_router().generate(req.provider, llm_req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"LLM provider error: {exc}") from exc

    assistant_message_id = store.insert_message(
        req.conversation_id, "assistant", llm_res.reply_text, llm_res.model
    )
    run_id = store.insert_run(
        message_id=assistant_message_id,
        provider=llm_res.provider,
        model=llm_res.model,
        system_prompt_id=req.system_prompt_id,
        system_prompt_content=system_prompt_content,
        params={
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        },
        latency_ms=llm_res.latency_ms,
        input_tokens=llm_res.input_tokens,
        output_tokens=llm_res.output_tokens,
        top_p=req.top_p,
        top_k=req.top_k,
        candidate_count=req.candidate_count,
        raw=llm_res.raw,
    )
    store.upsert_kd_example(
        conversation_id=req.conversation_id,
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
        system_prompt=system_prompt_content,
        prompt_text=req.message,
        answer_text=llm_res.reply_text,
        provider=llm_res.provider,
        model=llm_res.model,
        run_id=run_id,
    )
    store.touch_conversation(req.conversation_id)

    return ChatResponse(
        reply=llm_res.reply_text,
        provider=llm_res.provider,
        model=llm_res.model,
        latency_ms=llm_res.latency_ms,
        input_tokens=llm_res.input_tokens,
        output_tokens=llm_res.output_tokens,
    )


@router.get("/runs")
def list_runs(conversation_id: str | None = None):
    return store.list_runs(conversation_id)


@router.put("/messages/{message_id}/meta")
def upsert_message_meta(message_id: str, req: UpsertMessageMetaRequest):
    message = store.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    updated = store.upsert_message_meta(
        message_id=message_id,
        task_type=req.task_type,
        quality_score=req.quality_score,
        tags=req.tags,
        teacher_rationale=req.teacher_rationale,
        rating_source=req.rating_source,
        is_rejected=req.is_rejected,
        language=req.language,
        safety_flags=req.safety_flags,
        notes=req.notes,
    )
    store.sync_kd_example_labels(message_id)
    return updated
