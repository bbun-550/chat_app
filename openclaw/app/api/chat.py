import json
import logging
import queue
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse, UpsertMessageMetaRequest
from app.services import store
from app.services.llm_router import LLMRouter
from app.services.llm.prompt_builder import build_prompt
from app.services.memory.vector_store import extract_and_store_memories
from app.services.memory.summarizer import auto_summarize_if_needed
from app.services.providers.base import ChatMessage, LLMRequest
from app.services.llm.intent_classifier import classify_intent
from app.services.llm.tool_dispatcher import ToolDispatcher
from app.services.llm.router_config import ROUTER_ENABLED

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])
_llm_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router


@router.get("/providers")
def list_providers():
    return get_llm_router().list_providers()


@router.get("/providers/{provider_name}/models")
def list_provider_models(provider_name: str):
    try:
        return get_llm_router().list_models(provider_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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

    # ── Router LLM ──────────────────────────────────────────────────────────
    if req.enable_routing and ROUTER_ENABLED:
        try:
            _router = get_llm_router()
            _llm_fn = lambda r: _router.generate(req.provider, r)
            classified = classify_intent(req.message, _llm_fn)
            tool_reply = ToolDispatcher().dispatch(classified, req.message, _llm_fn)
            if tool_reply is not None:
                assistant_message_id = store.insert_message(
                    req.conversation_id, "assistant", tool_reply, selected_model
                )
                store.upsert_kd_example(
                    conversation_id=req.conversation_id,
                    user_message_id=user_message_id,
                    assistant_message_id=assistant_message_id,
                    system_prompt=system_prompt_content,
                    prompt_text=req.message,
                    answer_text=tool_reply,
                    provider=req.provider,
                    model=selected_model,
                    run_id=None,
                )
                store.touch_conversation(req.conversation_id)
                return ChatResponse(
                    reply=tool_reply,
                    provider=req.provider,
                    model=selected_model,
                    latency_ms=0,
                    input_tokens=None,
                    output_tokens=None,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Router LLM failed, falling back to standard pipeline: %s", exc)

    llm_req = build_prompt(
        conversation_id=req.conversation_id,
        user_message=req.message,
        system_prompt=system_prompt_content,
        model=selected_model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
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

    # Memory extraction (async-safe, non-blocking)
    try:
        router = get_llm_router()
        llm_fn = lambda r: router.generate(req.provider, r)
        messages = store.get_messages(req.conversation_id)
        extract_and_store_memories(messages, req.conversation_id, llm_generate_fn=llm_fn)
        auto_summarize_if_needed(req.conversation_id, llm_generate_fn=llm_fn)
    except Exception as e:
        logger.warning("Memory extraction failed (non-critical): %s", e)

    return ChatResponse(
        reply=llm_res.reply_text,
        provider=llm_res.provider,
        model=llm_res.model,
        latency_ms=llm_res.latency_ms,
        input_tokens=llm_res.input_tokens,
        output_tokens=llm_res.output_tokens,
    )


@router.post("/chat/stream")
def send_message_stream(req: ChatRequest):
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

    # ── Router LLM (stream variant) ─────────────────────────────────────────
    if req.enable_routing and ROUTER_ENABLED:
        try:
            _router = get_llm_router()
            _llm_fn = lambda r: _router.generate(req.provider, r)
            classified = classify_intent(req.message, _llm_fn)
            tool_reply = ToolDispatcher().dispatch(classified, req.message, _llm_fn)
            if tool_reply is not None:
                import json as _json

                def _tool_stream():
                    init = {"delta": "", "done": False, "user_message_id": user_message_id}
                    yield f"data: {_json.dumps(init)}\n\n"
                    chunk_event = {"delta": tool_reply, "done": False}
                    yield f"data: {_json.dumps(chunk_event)}\n\n"
                    # Persist before the final done event so DB ops are not skipped
                    # if the client closes the connection after receiving done.
                    _asst_id = store.insert_message(
                        req.conversation_id, "assistant", tool_reply, selected_model
                    )
                    store.upsert_kd_example(
                        conversation_id=req.conversation_id,
                        user_message_id=user_message_id,
                        assistant_message_id=_asst_id,
                        system_prompt=system_prompt_content,
                        prompt_text=req.message,
                        answer_text=tool_reply,
                        provider=req.provider,
                        model=selected_model,
                        run_id=None,
                    )
                    store.touch_conversation(req.conversation_id)
                    done_event = {
                        "delta": "", "done": True,
                        "provider": req.provider, "model": selected_model,
                        "latency_ms": 0, "input_tokens": None, "output_tokens": None,
                    }
                    yield f"data: {_json.dumps(done_event)}\n\n"

                return StreamingResponse(
                    _tool_stream(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Router LLM (stream) failed, falling back: %s", exc)

    llm_req = build_prompt(
        conversation_id=req.conversation_id,
        user_message=req.message,
        system_prompt=system_prompt_content,
        model=selected_model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )

    def generate():
        start = time.time()
        full_text = []
        input_tokens = None
        output_tokens = None
        chunk_queue: queue.Queue = queue.Queue()

        # Send init event with server-side user_message_id for client dedup
        init_event = {
            "delta": "",
            "done": False,
            "user_message_id": user_message_id,
        }
        yield f"data: {json.dumps(init_event, ensure_ascii=False)}\n\n"

        def _stream_worker():
            try:
                for chunk in get_llm_router().generate_stream(req.provider, llm_req):
                    chunk_queue.put(chunk)
                    if chunk.done:
                        break
            except Exception as exc:
                chunk_queue.put(exc)
            finally:
                chunk_queue.put(None)  # sentinel

        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(_stream_worker)

        try:
            while True:
                try:
                    item = chunk_queue.get(timeout=15)
                except queue.Empty:
                    yield ": heartbeat\n\n"
                    continue

                if item is None:
                    break
                if isinstance(item, Exception):
                    error_event = {"error": str(item), "done": True}
                    yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                    return

                chunk = item
                if chunk.delta_text:
                    full_text.append(chunk.delta_text)
                if chunk.input_tokens is not None:
                    input_tokens = chunk.input_tokens
                if chunk.output_tokens is not None:
                    output_tokens = chunk.output_tokens

                event = {"delta": chunk.delta_text, "done": chunk.done}
                if chunk.done:
                    latency_ms = int((time.time() - start) * 1000)
                    event.update({
                        "provider": req.provider,
                        "model": selected_model,
                        "latency_ms": latency_ms,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    })
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if chunk.done:
                    break
        except GeneratorExit:
            logger.info("Client disconnected for conversation %s", req.conversation_id)
            executor.shutdown(wait=False)
            return
        finally:
            executor.shutdown(wait=False)

        reply_text = "".join(full_text)
        latency_ms = int((time.time() - start) * 1000)

        assistant_message_id = store.insert_message(
            req.conversation_id, "assistant", reply_text, selected_model
        )
        run_id = store.insert_run(
            message_id=assistant_message_id,
            provider=req.provider,
            model=selected_model,
            system_prompt_id=req.system_prompt_id,
            system_prompt_content=system_prompt_content,
            params={"temperature": req.temperature, "max_tokens": req.max_tokens},
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            top_p=req.top_p,
            top_k=req.top_k,
            candidate_count=req.candidate_count,
            raw=None,
        )
        store.upsert_kd_example(
            conversation_id=req.conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            system_prompt=system_prompt_content,
            prompt_text=req.message,
            answer_text=reply_text,
            provider=req.provider,
            model=selected_model,
            run_id=run_id,
        )
        store.touch_conversation(req.conversation_id)

        try:
            router = get_llm_router()
            llm_fn = lambda r: router.generate(req.provider, r)
            messages = store.get_messages(req.conversation_id)
            extract_and_store_memories(messages, req.conversation_id, llm_generate_fn=llm_fn)
            auto_summarize_if_needed(req.conversation_id, llm_generate_fn=llm_fn)
        except Exception as e:
            logger.warning("Memory extraction failed (non-critical): %s", e)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runs")
def list_runs(conversation_id: str | None = None):
    return store.list_runs(conversation_id)


@router.post("/messages/{message_id}/bookmark")
def toggle_bookmark(message_id: str):
    result = store.toggle_bookmark(message_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return result


@router.get("/bookmarks")
def list_bookmarks():
    return store.list_bookmarked_messages()


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
