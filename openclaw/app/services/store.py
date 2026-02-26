import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.services.db import get_conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_conversation(title: str = "New Chat") -> dict:
    conversation_id = str(uuid.uuid4())
    now = now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conversation_id, title, now, now),
        )
    return {
        "id": conversation_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
    }


def list_conversations() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(conversation_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
    return dict(row) if row else None


def update_conversation(conversation_id: str, title: str) -> Optional[dict]:
    with get_conn() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, now_iso(), conversation_id),
        )
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
    raw: Optional[dict],
) -> str:
    run_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO runs ("
            "id, message_id, provider, model, system_prompt_id, system_prompt_content, "
            "params_json, latency_ms, input_tokens, output_tokens, raw_json, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
    notes: Optional[str] = None,
) -> dict:
    tags_json = json.dumps(tags, ensure_ascii=False) if tags else None
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO message_meta (message_id, task_type, quality_score, tags, notes) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(message_id) DO UPDATE SET "
            "task_type = COALESCE(excluded.task_type, task_type), "
            "quality_score = COALESCE(excluded.quality_score, quality_score), "
            "tags = COALESCE(excluded.tags, tags), "
            "notes = COALESCE(excluded.notes, notes)",
            (message_id, task_type, quality_score, tags_json, notes),
        )
    return {
        "message_id": message_id,
        "task_type": task_type,
        "quality_score": quality_score,
    }


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
