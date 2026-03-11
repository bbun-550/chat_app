import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, delete, update, and_, desc

from app.services.db import get_session
from app.services.models import (
    AgentLog,
    AgentStep,
    Conversation,
    Event,
    Job,
    Message,
    SystemPrompt,
    Report,
    Run,
    MessageMeta,
    KDExample,
    DailySummary,
    VectorMemory,
    MemoryNode,
    MemoryEdge,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conv_to_dict(c: Conversation) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "category": c.category,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def _msg_to_dict(m: Message) -> dict:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "role": m.role,
        "content": m.content,
        "model": m.model,
        "created_at": m.created_at,
        "is_bookmarked": m.is_bookmarked,
    }


def _prompt_to_dict(p: SystemPrompt) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "content": p.content,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def _run_to_dict(r: Run, conversation_id: Optional[str] = None) -> dict:
    d = {
        "id": r.id,
        "message_id": r.message_id,
        "provider": r.provider,
        "model": r.model,
        "system_prompt_id": r.system_prompt_id,
        "system_prompt_content": r.system_prompt_content,
        "params_json": r.params_json,
        "latency_ms": r.latency_ms,
        "input_tokens": r.input_tokens,
        "output_tokens": r.output_tokens,
        "top_p": r.top_p,
        "top_k": r.top_k,
        "candidate_count": r.candidate_count,
        "raw_json": r.raw_json,
        "created_at": r.created_at,
    }
    if conversation_id is not None:
        d["conversation_id"] = conversation_id
    return d


def _meta_to_dict(mm: MessageMeta) -> dict:
    return {
        "message_id": mm.message_id,
        "task_type": mm.task_type,
        "quality_score": mm.quality_score,
        "tags": mm.tags,
        "teacher_rationale": mm.teacher_rationale,
        "rating_source": mm.rating_source,
        "is_rejected": mm.is_rejected,
        "language": mm.language,
        "safety_flags": mm.safety_flags,
        "notes": mm.notes,
    }


def _kd_to_dict(k: KDExample) -> dict:
    return {
        "id": k.id,
        "conversation_id": k.conversation_id,
        "user_message_id": k.user_message_id,
        "assistant_message_id": k.assistant_message_id,
        "system_prompt": k.system_prompt,
        "prompt_text": k.prompt_text,
        "teacher_rationale": k.teacher_rationale,
        "answer_text": k.answer_text,
        "category": k.category,
        "quality_score": k.quality_score,
        "task_type": k.task_type,
        "is_rejected": k.is_rejected,
        "provider": k.provider,
        "model": k.model,
        "run_id": k.run_id,
        "dataset_version": k.dataset_version,
        "created_at": k.created_at,
    }


# ── Conversations ──


def create_conversation(title: str = "New Chat", category: Optional[str] = None) -> dict:
    conversation_id = str(uuid.uuid4())
    now = now_iso()
    with get_session() as s:
        s.add(Conversation(
            id=conversation_id, title=title, category=category,
            created_at=now, updated_at=now,
        ))
    return {
        "id": conversation_id, "title": title, "category": category,
        "created_at": now, "updated_at": now,
    }


def list_conversations() -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(Conversation).order_by(desc(Conversation.updated_at))
        ).scalars().all()
        return [_conv_to_dict(r) for r in rows]


def get_conversation(conversation_id: str) -> Optional[dict]:
    with get_session() as s:
        c = s.get(Conversation, conversation_id)
        return _conv_to_dict(c) if c else None


def update_conversation(
    conversation_id: str, title: Optional[str] = None, category: Optional[str] = None
) -> Optional[dict]:
    if title is None and category is None:
        return get_conversation(conversation_id)
    values: dict = {"updated_at": now_iso()}
    if title is not None:
        values["title"] = title
    if category is not None:
        values["category"] = category
    with get_session() as s:
        s.execute(
            update(Conversation).where(Conversation.id == conversation_id).values(**values)
        )
    return get_conversation(conversation_id)


def delete_conversation(conversation_id: str) -> bool:
    with get_session() as s:
        result = s.execute(
            delete(Conversation).where(Conversation.id == conversation_id)
        )
        return result.rowcount > 0


def touch_conversation(conversation_id: str) -> None:
    with get_session() as s:
        s.execute(
            update(Conversation).where(Conversation.id == conversation_id)
            .values(updated_at=now_iso())
        )


# ── Messages ──


def get_messages(conversation_id: str) -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        ).scalars().all()
        return [_msg_to_dict(r) for r in rows]


def insert_message(conversation_id: str, role: str, content: str, model: str = "gemini-2.0-flash") -> str:
    message_id = str(uuid.uuid4())
    with get_session() as s:
        s.add(Message(
            id=message_id, conversation_id=conversation_id,
            role=role, content=content, model=model, created_at=now_iso(),
        ))
    return message_id


def get_message(message_id: str) -> Optional[dict]:
    with get_session() as s:
        m = s.get(Message, message_id)
        return _msg_to_dict(m) if m else None


def toggle_bookmark(message_id: str) -> Optional[dict]:
    with get_session() as s:
        m = s.get(Message, message_id)
        if not m:
            return None
        m.is_bookmarked = 0 if m.is_bookmarked else 1
        s.flush()
        return _msg_to_dict(m)


def list_bookmarked_messages() -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(Message)
            .where(Message.is_bookmarked == 1)
            .order_by(desc(Message.created_at))
        ).scalars().all()
        return [_msg_to_dict(r) for r in rows]


# ── System Prompts ──


def create_system_prompt(name: str, content: str) -> dict:
    prompt_id = str(uuid.uuid4())
    now = now_iso()
    with get_session() as s:
        s.add(SystemPrompt(
            id=prompt_id, name=name, content=content,
            created_at=now, updated_at=now,
        ))
    return {"id": prompt_id, "name": name, "content": content, "created_at": now, "updated_at": now}


def list_system_prompts() -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(SystemPrompt).order_by(desc(SystemPrompt.updated_at))
        ).scalars().all()
        return [_prompt_to_dict(r) for r in rows]


def get_system_prompt(prompt_id: str) -> Optional[dict]:
    with get_session() as s:
        p = s.get(SystemPrompt, prompt_id)
        return _prompt_to_dict(p) if p else None


def update_system_prompt(prompt_id: str, name: str, content: str) -> Optional[dict]:
    with get_session() as s:
        s.execute(
            update(SystemPrompt).where(SystemPrompt.id == prompt_id)
            .values(name=name, content=content, updated_at=now_iso())
        )
    return get_system_prompt(prompt_id)


def delete_system_prompt(prompt_id: str) -> bool:
    with get_session() as s:
        result = s.execute(
            delete(SystemPrompt).where(SystemPrompt.id == prompt_id)
        )
        return result.rowcount > 0


# ── Runs ──


def insert_run(
    message_id: str,
    provider: str,
    model: str,
    system_prompt_id: Optional[str],
    system_prompt_content: Optional[str],
    params: dict,
    latency_ms: int,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
    candidate_count: Optional[int] = None,
    raw: Optional[dict] = None,
) -> str:
    run_id = str(uuid.uuid4())
    with get_session() as s:
        s.add(Run(
            id=run_id,
            message_id=message_id,
            provider=provider,
            model=model,
            system_prompt_id=system_prompt_id,
            system_prompt_content=system_prompt_content,
            params_json=json.dumps(params, ensure_ascii=False),
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            top_p=top_p,
            top_k=top_k,
            candidate_count=candidate_count,
            raw_json=json.dumps(raw, ensure_ascii=False) if raw else None,
            created_at=now_iso(),
        ))
    return run_id


def list_runs(conversation_id: Optional[str] = None) -> list[dict]:
    with get_session() as s:
        stmt = select(Run, Message.conversation_id).join(Message, Run.message_id == Message.id)
        if conversation_id:
            stmt = stmt.where(Message.conversation_id == conversation_id)
        stmt = stmt.order_by(desc(Run.created_at))
        rows = s.execute(stmt).all()
        return [_run_to_dict(run, conv_id) for run, conv_id in rows]


# ── Message Meta ──


def upsert_message_meta(
    message_id: str,
    task_type: Optional[str] = None,
    quality_score: Optional[int] = None,
    tags: Optional[list] = None,
    teacher_rationale: Optional[str] = None,
    rating_source: Optional[str] = None,
    is_rejected: Optional[int] = None,
    language: Optional[str] = None,
    safety_flags: Optional[list] = None,
    notes: Optional[str] = None,
) -> dict:
    tags_json = json.dumps(tags, ensure_ascii=False) if tags else None
    safety_flags_json = json.dumps(safety_flags, ensure_ascii=False) if safety_flags else None
    with get_session() as s:
        existing = s.get(MessageMeta, message_id)
        if existing:
            if task_type is not None:
                existing.task_type = task_type
            if quality_score is not None:
                existing.quality_score = quality_score
            if tags_json is not None:
                existing.tags = tags_json
            if teacher_rationale is not None:
                existing.teacher_rationale = teacher_rationale
            if rating_source is not None:
                existing.rating_source = rating_source
            if is_rejected is not None:
                existing.is_rejected = is_rejected
            if language is not None:
                existing.language = language
            if safety_flags_json is not None:
                existing.safety_flags = safety_flags_json
            if notes is not None:
                existing.notes = notes
            s.flush()
            return {
                "message_id": existing.message_id,
                "task_type": existing.task_type,
                "quality_score": existing.quality_score,
                "teacher_rationale": existing.teacher_rationale,
                "is_rejected": existing.is_rejected,
            }
        else:
            mm = MessageMeta(
                message_id=message_id,
                task_type=task_type,
                quality_score=quality_score,
                tags=tags_json,
                teacher_rationale=teacher_rationale,
                rating_source=rating_source,
                is_rejected=is_rejected if is_rejected is not None else 0,
                language=language,
                safety_flags=safety_flags_json,
                notes=notes,
            )
            s.add(mm)
            s.flush()
            return {
                "message_id": mm.message_id,
                "task_type": mm.task_type,
                "quality_score": mm.quality_score,
                "teacher_rationale": mm.teacher_rationale,
                "is_rejected": mm.is_rejected,
            }


# ── KD Examples ──


def upsert_kd_example(
    conversation_id: str,
    user_message_id: str,
    assistant_message_id: str,
    system_prompt: Optional[str],
    prompt_text: str,
    answer_text: str,
    provider: str,
    model: str,
    run_id: Optional[str],
    dataset_version: str = "v1",
) -> str:
    kd_id = str(uuid.uuid4())
    meta = get_message_meta_by_message_id(assistant_message_id)
    conversation = get_conversation(conversation_id)
    with get_session() as s:
        existing = s.execute(
            select(KDExample).where(KDExample.assistant_message_id == assistant_message_id)
        ).scalar_one_or_none()
        if existing:
            existing.system_prompt = system_prompt
            existing.prompt_text = prompt_text
            if meta.get("teacher_rationale"):
                existing.teacher_rationale = meta["teacher_rationale"]
            existing.answer_text = answer_text
            existing.category = conversation.get("category") if conversation else None
            if meta.get("quality_score") is not None:
                existing.quality_score = meta["quality_score"]
            if meta.get("task_type"):
                existing.task_type = meta["task_type"]
            existing.is_rejected = int(meta.get("is_rejected") or 0)
            existing.provider = provider
            existing.model = model
            existing.run_id = run_id
            existing.dataset_version = dataset_version
            return existing.id
        else:
            s.add(KDExample(
                id=kd_id,
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                assistant_message_id=assistant_message_id,
                system_prompt=system_prompt,
                prompt_text=prompt_text,
                teacher_rationale=meta.get("teacher_rationale"),
                answer_text=answer_text,
                category=conversation.get("category") if conversation else None,
                quality_score=meta.get("quality_score"),
                task_type=meta.get("task_type"),
                is_rejected=int(meta.get("is_rejected") or 0),
                provider=provider,
                model=model,
                run_id=run_id,
                dataset_version=dataset_version,
                created_at=now_iso(),
            ))
            return kd_id


def get_message_meta_by_message_id(message_id: str) -> dict:
    with get_session() as s:
        mm = s.get(MessageMeta, message_id)
        return _meta_to_dict(mm) if mm else {}


def sync_kd_example_labels(assistant_message_id: str) -> None:
    meta = get_message_meta_by_message_id(assistant_message_id)
    values: dict = {}
    if meta.get("teacher_rationale") is not None:
        values["teacher_rationale"] = meta["teacher_rationale"]
    if meta.get("quality_score") is not None:
        values["quality_score"] = meta["quality_score"]
    if meta.get("task_type") is not None:
        values["task_type"] = meta["task_type"]
    if meta.get("is_rejected") is not None:
        values["is_rejected"] = meta["is_rejected"]
    if not values:
        return
    with get_session() as s:
        s.execute(
            update(KDExample)
            .where(KDExample.assistant_message_id == assistant_message_id)
            .values(**values)
        )


def list_kd_examples(
    min_quality: Optional[int] = None,
    category: Optional[str] = None,
    exclude_rejected: bool = True,
) -> list[dict]:
    with get_session() as s:
        stmt = select(KDExample)
        conditions = []
        if min_quality is not None:
            conditions.append(KDExample.quality_score >= min_quality)
        if category:
            conditions.append(KDExample.category == category)
        if exclude_rejected:
            conditions.append(KDExample.is_rejected == 0)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(desc(KDExample.created_at))
        rows = s.execute(stmt).scalars().all()
        return [_kd_to_dict(r) for r in rows]


def export_kd_examples(
    conversation_id: Optional[str] = None,
    min_quality: Optional[int] = None,
    category: Optional[str] = None,
    exclude_rejected: bool = True,
) -> list[dict]:
    with get_session() as s:
        stmt = select(KDExample)
        conditions = []
        if conversation_id:
            conditions.append(KDExample.conversation_id == conversation_id)
        if min_quality is not None:
            conditions.append(KDExample.quality_score >= min_quality)
        if category:
            conditions.append(KDExample.category == category)
        if exclude_rejected:
            conditions.append(KDExample.is_rejected == 0)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(desc(KDExample.created_at))
        rows = s.execute(stmt).scalars().all()
        return [_kd_to_dict(r) for r in rows]


def get_message_meta(conversation_id: str) -> list[dict]:
    with get_session() as s:
        stmt = (
            select(MessageMeta)
            .join(Message, MessageMeta.message_id == Message.id)
            .where(Message.conversation_id == conversation_id)
        )
        rows = s.execute(stmt).scalars().all()
        return [_meta_to_dict(r) for r in rows]


# ── Export ──


def export_conversation(conversation_id: str) -> dict:
    return {
        "conversation": get_conversation(conversation_id),
        "messages": get_messages(conversation_id),
        "runs": list_runs(conversation_id),
        "meta": get_message_meta(conversation_id),
    }


def export_sft(conversation_id: str) -> list[dict]:
    messages = get_messages(conversation_id)
    runs = list_runs(conversation_id)
    meta_list = get_message_meta(conversation_id)
    meta_map = {item["message_id"]: item for item in meta_list}

    system_prompt = ""
    if runs:
        system_prompt = runs[0].get("system_prompt_content", "") or ""

    conversations = []
    for msg in messages:
        if msg["role"] in ("user", "assistant"):
            conversations.append({"role": msg["role"], "content": msg["content"]})

    best_quality = None
    task_type = None
    for msg in messages:
        if msg["id"] not in meta_map:
            continue
        item = meta_map[msg["id"]]
        score = item.get("quality_score")
        if score and (best_quality is None or score > best_quality):
            best_quality = score
        if item.get("task_type") and not task_type:
            task_type = item["task_type"]

    model = runs[0].get("model", "unknown") if runs else "unknown"
    return [
        {
            "system": system_prompt,
            "conversations": conversations,
            "metadata": {
                "quality_score": best_quality,
                "task_type": task_type,
                "model": model,
                "conversation_id": conversation_id,
            },
        }
    ]


# ── Daily Summaries (new) ──


def insert_daily_summary(
    conversation_id: Optional[str], summary_text: str, fact_count: int = 0
) -> str:
    summary_id = str(uuid.uuid4())
    with get_session() as s:
        s.add(DailySummary(
            id=summary_id,
            conversation_id=conversation_id,
            summary_text=summary_text,
            fact_count=fact_count,
            created_at=now_iso(),
        ))
    return summary_id


def get_daily_summaries(limit: int = 10) -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(DailySummary).order_by(desc(DailySummary.created_at)).limit(limit)
        ).scalars().all()
        return [
            {
                "id": r.id,
                "conversation_id": r.conversation_id,
                "summary_text": r.summary_text,
                "fact_count": r.fact_count,
                "created_at": r.created_at,
            }
            for r in rows
        ]


def get_latest_daily_summary() -> Optional[dict]:
    summaries = get_daily_summaries(limit=1)
    return summaries[0] if summaries else None


# ── Vector Memories (new) ──


def insert_vector_memory(
    content: str, embedding: list[float], memory_type: str = "fact",
    source_conversation_id: Optional[str] = None,
) -> str:
    memory_id = str(uuid.uuid4())
    with get_session() as s:
        s.add(VectorMemory(
            id=memory_id,
            content=content,
            embedding=embedding,
            memory_type=memory_type,
            source_conversation_id=source_conversation_id,
            created_at=now_iso(),
        ))
    return memory_id


def search_vector_memories(
    embedding: list[float], limit: int = 5, threshold: float = 0.7
) -> list[dict]:
    with get_session() as s:
        distance = VectorMemory.embedding.cosine_distance(embedding)
        stmt = (
            select(VectorMemory, distance.label("distance"))
            .where(distance < (1 - threshold))
            .order_by(distance)
            .limit(limit)
        )
        rows = s.execute(stmt).all()
        return [
            {
                "id": vm.id,
                "content": vm.content,
                "memory_type": vm.memory_type,
                "source_conversation_id": vm.source_conversation_id,
                "created_at": vm.created_at,
                "similarity": 1 - dist,
            }
            for vm, dist in rows
        ]


# ── Agent Logs ──


def _agent_log_to_dict(r: AgentLog) -> dict:
    return {
        "id": r.id,
        "plan_id": r.plan_id,
        "conversation_id": r.conversation_id,
        "intent": r.intent,
        "plan_json": r.plan_json,
        "overall_risk": r.overall_risk,
        "status": r.status,
        "provider": r.provider,
        "model": r.model,
        "created_at": r.created_at,
        "completed_at": r.completed_at,
    }


def _agent_step_to_dict(r: AgentStep) -> dict:
    return {
        "id": r.id,
        "agent_log_id": r.agent_log_id,
        "step_index": r.step_index,
        "tool_name": r.tool_name,
        "args_json": r.args_json,
        "risk_level": r.risk_level,
        "approval": r.approval,
        "description": r.description,
        "success": r.success,
        "output_json": r.output_json,
        "error": r.error,
        "duration_ms": r.duration_ms,
        "created_at": r.created_at,
    }


def insert_agent_log(
    plan_id: str,
    conversation_id: str,
    intent: str,
    plan_json: str,
    overall_risk: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    log_id = str(uuid.uuid4())
    with get_session() as s:
        s.add(AgentLog(
            id=log_id,
            plan_id=plan_id,
            conversation_id=conversation_id,
            intent=intent,
            plan_json=plan_json,
            overall_risk=overall_risk,
            status="pending",
            provider=provider,
            model=model,
            created_at=now_iso(),
        ))
    return log_id


def get_agent_log_by_plan_id(plan_id: str) -> Optional[dict]:
    with get_session() as s:
        row = s.execute(
            select(AgentLog).where(AgentLog.plan_id == plan_id)
        ).scalar_one_or_none()
        return _agent_log_to_dict(row) if row else None


def update_agent_log_status(plan_id: str, status: str) -> None:
    values: dict = {"status": status}
    if status in ("completed", "failed"):
        values["completed_at"] = now_iso()
    with get_session() as s:
        s.execute(
            update(AgentLog).where(AgentLog.plan_id == plan_id).values(**values)
        )


def list_agent_logs(conversation_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    with get_session() as s:
        stmt = select(AgentLog).order_by(desc(AgentLog.created_at)).limit(limit)
        if conversation_id:
            stmt = stmt.where(AgentLog.conversation_id == conversation_id)
        rows = s.execute(stmt).scalars().all()
        return [_agent_log_to_dict(r) for r in rows]


def insert_agent_step(
    agent_log_id: str,
    step_index: int,
    tool_name: str,
    args_json: str,
    risk_level: str,
    approval: str,
    description: str = "",
) -> str:
    step_id = str(uuid.uuid4())
    with get_session() as s:
        s.add(AgentStep(
            id=step_id,
            agent_log_id=agent_log_id,
            step_index=step_index,
            tool_name=tool_name,
            args_json=args_json,
            risk_level=risk_level,
            approval=approval,
            description=description,
            created_at=now_iso(),
        ))
    return step_id


def update_agent_step_result(
    step_id: str, success: bool, output_json: Optional[str] = None,
    error: Optional[str] = None, duration_ms: int = 0,
) -> None:
    with get_session() as s:
        s.execute(
            update(AgentStep).where(AgentStep.id == step_id).values(
                success=1 if success else 0,
                output_json=output_json,
                error=error,
                duration_ms=duration_ms,
            )
        )


def get_agent_steps(agent_log_id: str) -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(AgentStep)
            .where(AgentStep.agent_log_id == agent_log_id)
            .order_by(AgentStep.step_index)
        ).scalars().all()
        return [_agent_step_to_dict(r) for r in rows]


# ── Jobs ──


def _job_to_dict(j: Job) -> dict:
    return {
        "id": j.id, "name": j.name, "task_type": j.task_type,
        "cron_expression": j.cron_expression, "params_json": j.params_json,
        "enabled": j.enabled, "last_run_at": j.last_run_at,
        "next_run_at": j.next_run_at,
        "created_at": j.created_at, "updated_at": j.updated_at,
    }


def create_job(
    name: str, task_type: str, cron_expression: str, params: dict | None = None
) -> dict:
    job_id = str(uuid.uuid4())
    now = now_iso()
    with get_session() as s:
        j = Job(
            id=job_id, name=name, task_type=task_type,
            cron_expression=cron_expression,
            params_json=json.dumps(params or {}, ensure_ascii=False),
            enabled=1, created_at=now, updated_at=now,
        )
        s.add(j)
        s.flush()
        return _job_to_dict(j)


def list_jobs(enabled_only: bool = False) -> list[dict]:
    with get_session() as s:
        stmt = select(Job).order_by(desc(Job.created_at))
        if enabled_only:
            stmt = stmt.where(Job.enabled == 1)
        rows = s.execute(stmt).scalars().all()
        return [_job_to_dict(r) for r in rows]


def get_job(job_id: str) -> Optional[dict]:
    with get_session() as s:
        j = s.get(Job, job_id)
        return _job_to_dict(j) if j else None


def update_job(job_id: str, **kwargs) -> Optional[dict]:
    kwargs["updated_at"] = now_iso()
    with get_session() as s:
        s.execute(update(Job).where(Job.id == job_id).values(**kwargs))
    return get_job(job_id)


def delete_job(job_id: str) -> bool:
    with get_session() as s:
        result = s.execute(delete(Job).where(Job.id == job_id))
        return result.rowcount > 0


def update_job_last_run(job_id: str, next_run_at: Optional[str] = None) -> None:
    values: dict = {"last_run_at": now_iso(), "updated_at": now_iso()}
    if next_run_at:
        values["next_run_at"] = next_run_at
    with get_session() as s:
        s.execute(update(Job).where(Job.id == job_id).values(**values))


# ── Reports ──


def _report_to_dict(r: Report) -> dict:
    return {
        "id": r.id, "job_id": r.job_id, "report_type": r.report_type,
        "title": r.title, "content": r.content, "summary": r.summary,
        "params_json": r.params_json, "provider": r.provider, "model": r.model,
        "latency_ms": r.latency_ms, "input_tokens": r.input_tokens,
        "output_tokens": r.output_tokens, "status": r.status,
        "created_at": r.created_at,
    }


def insert_report(
    report_type: str, title: str, content: str,
    job_id: Optional[str] = None, summary: Optional[str] = None,
    params: Optional[dict] = None, provider: Optional[str] = None,
    model: Optional[str] = None, latency_ms: Optional[int] = None,
    input_tokens: Optional[int] = None, output_tokens: Optional[int] = None,
    status: str = "completed",
) -> str:
    report_id = str(uuid.uuid4())
    with get_session() as s:
        s.add(Report(
            id=report_id, job_id=job_id, report_type=report_type,
            title=title, content=content, summary=summary,
            params_json=json.dumps(params or {}, ensure_ascii=False),
            provider=provider, model=model, latency_ms=latency_ms,
            input_tokens=input_tokens, output_tokens=output_tokens,
            status=status, created_at=now_iso(),
        ))
    return report_id


def list_reports(report_type: Optional[str] = None, limit: int = 50) -> list[dict]:
    with get_session() as s:
        stmt = select(Report).order_by(desc(Report.created_at)).limit(limit)
        if report_type:
            stmt = stmt.where(Report.report_type == report_type)
        rows = s.execute(stmt).scalars().all()
        return [_report_to_dict(r) for r in rows]


def get_report(report_id: str) -> Optional[dict]:
    with get_session() as s:
        r = s.get(Report, report_id)
        return _report_to_dict(r) if r else None


def update_report_status(
    report_id: str, status: str, content: Optional[str] = None
) -> None:
    values: dict = {"status": status}
    if content is not None:
        values["content"] = content
    with get_session() as s:
        s.execute(update(Report).where(Report.id == report_id).values(**values))


# ── Events ──


def _event_to_dict(e: Event) -> dict:
    return {
        "id": e.id, "event_type": e.event_type, "title": e.title,
        "body": e.body, "ref_id": e.ref_id, "ref_type": e.ref_type,
        "is_read": e.is_read, "created_at": e.created_at,
    }


def insert_event(
    event_type: str, title: str, body: Optional[str] = None,
    ref_id: Optional[str] = None, ref_type: Optional[str] = None,
) -> str:
    event_id = str(uuid.uuid4())
    with get_session() as s:
        s.add(Event(
            id=event_id, event_type=event_type, title=title,
            body=body, ref_id=ref_id, ref_type=ref_type,
            is_read=0, created_at=now_iso(),
        ))
    return event_id


def list_events(unread_only: bool = False, limit: int = 50) -> list[dict]:
    with get_session() as s:
        stmt = select(Event).order_by(desc(Event.created_at)).limit(limit)
        if unread_only:
            stmt = stmt.where(Event.is_read == 0)
        rows = s.execute(stmt).scalars().all()
        return [_event_to_dict(r) for r in rows]


def mark_event_read(event_id: str) -> None:
    with get_session() as s:
        s.execute(update(Event).where(Event.id == event_id).values(is_read=1))


def get_events_after(after_iso: str, limit: int = 100) -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(Event).where(Event.created_at > after_iso)
            .order_by(Event.created_at).limit(limit)
        ).scalars().all()
        return [_event_to_dict(r) for r in rows]


# ── Memory Graph ──


def _node_to_dict(n: MemoryNode) -> dict:
    return {
        "id": n.id, "label": n.label, "node_type": n.node_type,
        "content": n.content, "metadata_json": n.metadata_json,
        "source_conversation_id": n.source_conversation_id,
        "created_at": n.created_at, "updated_at": n.updated_at,
    }


def _edge_to_dict(e: MemoryEdge) -> dict:
    return {
        "id": e.id, "source_id": e.source_id, "target_id": e.target_id,
        "relation_type": e.relation_type, "weight": e.weight,
        "metadata_json": e.metadata_json, "created_at": e.created_at,
    }


def upsert_memory_node(
    label: str,
    node_type: str,
    content: str,
    embedding: list[float],
    metadata: dict | None = None,
    source_conversation_id: str | None = None,
) -> str:
    """Insert or update a memory node by label (upsert)."""
    now = now_iso()
    with get_session() as s:
        existing = s.execute(
            select(MemoryNode).where(MemoryNode.label == label)
        ).scalar_one_or_none()
        if existing:
            existing.content = content
            existing.embedding = embedding
            existing.node_type = node_type
            existing.metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
            existing.updated_at = now
            return existing.id
        node_id = str(uuid.uuid4())
        s.add(MemoryNode(
            id=node_id, label=label, node_type=node_type, content=content,
            embedding=embedding,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            source_conversation_id=source_conversation_id,
            created_at=now, updated_at=now,
        ))
        return node_id


def insert_memory_edge(
    source_id: str, target_id: str, relation_type: str,
    weight: float = 1.0, metadata: dict | None = None,
) -> str:
    edge_id = str(uuid.uuid4())
    with get_session() as s:
        s.add(MemoryEdge(
            id=edge_id, source_id=source_id, target_id=target_id,
            relation_type=relation_type, weight=weight,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            created_at=now_iso(),
        ))
    return edge_id


def search_memory_nodes(
    embedding: list[float],
    limit: int = 10,
    threshold: float = 0.5,
    node_types: list[str] | None = None,
) -> list[dict]:
    """Vector similarity search on memory nodes."""
    with get_session() as s:
        distance = MemoryNode.embedding.cosine_distance(embedding)
        stmt = (
            select(MemoryNode, distance.label("distance"))
            .where(distance < (1 - threshold))
        )
        if node_types:
            stmt = stmt.where(MemoryNode.node_type.in_(node_types))
        stmt = stmt.order_by(distance).limit(limit)
        rows = s.execute(stmt).all()
        return [
            {**_node_to_dict(n), "similarity": 1 - dist}
            for n, dist in rows
        ]


def get_memory_node_neighbors(
    node_ids: list[str], relation_types: list[str] | None = None,
) -> list[dict]:
    """Get direct neighbors of given nodes (both directions)."""
    if not node_ids:
        return []
    with get_session() as s:
        # Outgoing edges
        stmt_out = (
            select(MemoryEdge, MemoryNode)
            .join(MemoryNode, MemoryEdge.target_id == MemoryNode.id)
            .where(MemoryEdge.source_id.in_(node_ids))
        )
        # Incoming edges
        stmt_in = (
            select(MemoryEdge, MemoryNode)
            .join(MemoryNode, MemoryEdge.source_id == MemoryNode.id)
            .where(MemoryEdge.target_id.in_(node_ids))
        )
        if relation_types:
            stmt_out = stmt_out.where(MemoryEdge.relation_type.in_(relation_types))
            stmt_in = stmt_in.where(MemoryEdge.relation_type.in_(relation_types))

        results = []
        seen = set(node_ids)
        for edge, node in list(s.execute(stmt_out).all()) + list(s.execute(stmt_in).all()):
            if node.id not in seen:
                seen.add(node.id)
                results.append({
                    "node": _node_to_dict(node),
                    "edge": _edge_to_dict(edge),
                })
        return results


def get_memory_nodes_by_type_and_date(
    node_type: str, before: str | None = None, after: str | None = None,
) -> list[dict]:
    """Get memory nodes filtered by type and date range."""
    with get_session() as s:
        stmt = select(MemoryNode).where(MemoryNode.node_type == node_type)
        if before:
            stmt = stmt.where(MemoryNode.created_at < before)
        if after:
            stmt = stmt.where(MemoryNode.created_at >= after)
        stmt = stmt.order_by(desc(MemoryNode.created_at))
        rows = s.execute(stmt).scalars().all()
        return [_node_to_dict(n) for n in rows]


def count_node_edges(node_id: str) -> int:
    """Count total edges connected to a node (for deletion protection)."""
    with get_session() as s:
        from sqlalchemy import func
        count = s.execute(
            select(func.count()).where(
                (MemoryEdge.source_id == node_id) | (MemoryEdge.target_id == node_id)
            )
        ).scalar()
        return count or 0


def delete_memory_nodes(node_ids: list[str]) -> int:
    """Delete memory nodes (edges cascade-deleted). Returns count deleted."""
    if not node_ids:
        return 0
    with get_session() as s:
        result = s.execute(
            delete(MemoryNode).where(MemoryNode.id.in_(node_ids))
        )
        return result.rowcount


def get_latest_summary_node(
    node_types: list[str] | None = None,
) -> dict | None:
    """Get the most recent summary node, preferring monthly > weekly > daily."""
    priority = node_types or ["summary_monthly", "summary_weekly", "summary_daily"]
    with get_session() as s:
        for nt in priority:
            row = s.execute(
                select(MemoryNode)
                .where(MemoryNode.node_type == nt)
                .order_by(desc(MemoryNode.created_at))
                .limit(1)
            ).scalar_one_or_none()
            if row:
                return _node_to_dict(row)
    return None
