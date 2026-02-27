import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.services.db import get_conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_conversation(title: str = "New Chat", category: Optional[str] = None) -> dict:
    conversation_id = str(uuid.uuid4())
    now = now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, category, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, title, category, now, now),
        )
    return {
        "id": conversation_id,
        "title": title,
        "category": category,
        "created_at": now,
        "updated_at": now,
    }


def list_conversations() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, category, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(conversation_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, title, category, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
    return dict(row) if row else None


def update_conversation(
    conversation_id: str, title: Optional[str] = None, category: Optional[str] = None
) -> Optional[dict]:
    if title is None and category is None:
        return get_conversation(conversation_id)
    updates = []
    args: list = []
    if title is not None:
        updates.append("title = ?")
        args.append(title)
    if category is not None:
        updates.append("category = ?")
        args.append(category)
    updates.append("updated_at = ?")
    args.append(now_iso())
    args.append(conversation_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?", tuple(args))
    return get_conversation(conversation_id)


def delete_conversation(conversation_id: str) -> bool:
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return cursor.rowcount > 0


def touch_conversation(conversation_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now_iso(), conversation_id),
        )


def get_messages(conversation_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, conversation_id, role, content, created_at "
            "FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def insert_message(conversation_id: str, role: str, content: str) -> str:
    message_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (message_id, conversation_id, role, content, now_iso()),
        )
    return message_id


def get_message(message_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, conversation_id, role, content, created_at FROM messages WHERE id = ?",
            (message_id,),
        ).fetchone()
    return dict(row) if row else None


def create_system_prompt(name: str, content: str) -> dict:
    prompt_id = str(uuid.uuid4())
    now = now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO system_prompts (id, name, content, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (prompt_id, name, content, now, now),
        )
    return {
        "id": prompt_id,
        "name": name,
        "content": content,
        "created_at": now,
        "updated_at": now,
    }


def list_system_prompts() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, content, created_at, updated_at FROM system_prompts "
            "ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_system_prompt(prompt_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, content, created_at, updated_at FROM system_prompts WHERE id = ?",
            (prompt_id,),
        ).fetchone()
    return dict(row) if row else None


def update_system_prompt(prompt_id: str, name: str, content: str) -> Optional[dict]:
    with get_conn() as conn:
        conn.execute(
            "UPDATE system_prompts SET name = ?, content = ?, updated_at = ? WHERE id = ?",
            (name, content, now_iso(), prompt_id),
        )
    return get_system_prompt(prompt_id)


def delete_system_prompt(prompt_id: str) -> bool:
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM system_prompts WHERE id = ?", (prompt_id,))
    return cursor.rowcount > 0


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
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO runs ("
            "id, message_id, provider, model, system_prompt_id, system_prompt_content, "
            "params_json, latency_ms, input_tokens, output_tokens, top_p, top_k, candidate_count, raw_json, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                message_id,
                provider,
                model,
                system_prompt_id,
                system_prompt_content,
                json.dumps(params, ensure_ascii=False),
                latency_ms,
                input_tokens,
                output_tokens,
                top_p,
                top_k,
                candidate_count,
                json.dumps(raw, ensure_ascii=False) if raw else None,
                now_iso(),
            ),
        )
    return run_id


def list_runs(conversation_id: Optional[str] = None) -> list[dict]:
    query = "SELECT r.*, m.conversation_id FROM runs r JOIN messages m ON r.message_id = m.id "
    args: tuple = ()
    if conversation_id:
        query += "WHERE m.conversation_id = ? "
        args = (conversation_id,)
    query += "ORDER BY r.created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(query, args).fetchall()
    return [dict(row) for row in rows]


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
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO message_meta ("
            "message_id, task_type, quality_score, tags, teacher_rationale, rating_source, "
            "is_rejected, language, safety_flags, notes"
            ") VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, 0), ?, ?, ?) "
            "ON CONFLICT(message_id) DO UPDATE SET "
            "task_type = COALESCE(excluded.task_type, task_type), "
            "quality_score = COALESCE(excluded.quality_score, quality_score), "
            "tags = COALESCE(excluded.tags, tags), "
            "teacher_rationale = COALESCE(excluded.teacher_rationale, teacher_rationale), "
            "rating_source = COALESCE(excluded.rating_source, rating_source), "
            "is_rejected = COALESCE(excluded.is_rejected, is_rejected), "
            "language = COALESCE(excluded.language, language), "
            "safety_flags = COALESCE(excluded.safety_flags, safety_flags), "
            "notes = COALESCE(excluded.notes, notes)",
            (
                message_id,
                task_type,
                quality_score,
                tags_json,
                teacher_rationale,
                rating_source,
                is_rejected,
                language,
                safety_flags_json,
                notes,
            ),
        )
        row = conn.execute(
            "SELECT message_id, task_type, quality_score, teacher_rationale, is_rejected "
            "FROM message_meta WHERE message_id = ?",
            (message_id,),
        ).fetchone()
    return dict(row)


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
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO kd_examples ("
            "id, conversation_id, user_message_id, assistant_message_id, system_prompt, "
            "prompt_text, teacher_rationale, answer_text, category, quality_score, task_type, "
            "is_rejected, provider, model, run_id, dataset_version, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(assistant_message_id) DO UPDATE SET "
            "system_prompt = excluded.system_prompt, "
            "prompt_text = excluded.prompt_text, "
            "teacher_rationale = COALESCE(excluded.teacher_rationale, kd_examples.teacher_rationale), "
            "answer_text = excluded.answer_text, "
            "category = excluded.category, "
            "quality_score = COALESCE(excluded.quality_score, kd_examples.quality_score), "
            "task_type = COALESCE(excluded.task_type, kd_examples.task_type), "
            "is_rejected = excluded.is_rejected, "
            "provider = excluded.provider, "
            "model = excluded.model, "
            "run_id = excluded.run_id, "
            "dataset_version = excluded.dataset_version",
            (
                kd_id,
                conversation_id,
                user_message_id,
                assistant_message_id,
                system_prompt,
                prompt_text,
                meta.get("teacher_rationale"),
                answer_text,
                conversation.get("category") if conversation else None,
                meta.get("quality_score"),
                meta.get("task_type"),
                int(meta.get("is_rejected") or 0),
                provider,
                model,
                run_id,
                dataset_version,
                now_iso(),
            ),
        )
    return kd_id


def get_message_meta_by_message_id(message_id: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM message_meta WHERE message_id = ?", (message_id,)
        ).fetchone()
    return dict(row) if row else {}


def sync_kd_example_labels(assistant_message_id: str) -> None:
    meta = get_message_meta_by_message_id(assistant_message_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE kd_examples SET "
            "teacher_rationale = COALESCE(?, teacher_rationale), "
            "quality_score = COALESCE(?, quality_score), "
            "task_type = COALESCE(?, task_type), "
            "is_rejected = COALESCE(?, is_rejected) "
            "WHERE assistant_message_id = ?",
            (
                meta.get("teacher_rationale"),
                meta.get("quality_score"),
                meta.get("task_type"),
                meta.get("is_rejected"),
                assistant_message_id,
            ),
        )


def list_kd_examples(
    min_quality: Optional[int] = None,
    category: Optional[str] = None,
    exclude_rejected: bool = True,
) -> list[dict]:
    query = "SELECT * FROM kd_examples WHERE 1=1 "
    args: list = []
    if min_quality is not None:
        query += "AND quality_score >= ? "
        args.append(min_quality)
    if category:
        query += "AND category = ? "
        args.append(category)
    if exclude_rejected:
        query += "AND is_rejected = 0 "
    query += "ORDER BY created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(query, tuple(args)).fetchall()
    return [dict(row) for row in rows]


def export_kd_examples(
    conversation_id: Optional[str] = None,
    min_quality: Optional[int] = None,
    category: Optional[str] = None,
    exclude_rejected: bool = True,
) -> list[dict]:
    query = "SELECT * FROM kd_examples WHERE 1=1 "
    args: list = []
    if conversation_id:
        query += "AND conversation_id = ? "
        args.append(conversation_id)
    if min_quality is not None:
        query += "AND quality_score >= ? "
        args.append(min_quality)
    if category:
        query += "AND category = ? "
        args.append(category)
    if exclude_rejected:
        query += "AND is_rejected = 0 "
    query += "ORDER BY created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(query, tuple(args)).fetchall()
    return [dict(row) for row in rows]


def get_message_meta(conversation_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT mm.* FROM message_meta mm "
            "JOIN messages m ON mm.message_id = m.id "
            "WHERE m.conversation_id = ?",
            (conversation_id,),
        ).fetchall()
    return [dict(row) for row in rows]


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
