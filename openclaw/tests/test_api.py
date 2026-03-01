"""Integration tests for the FastAPI application.

The `client` fixture:
  1. Creates a temp SQLite file (tmp_path),
  2. Applies the full schema from scripts/init_db.sql,
  3. Applies migration 002_add_model_to_messages.sql so the messages table
     has the `model` column required by the current store.insert_message(),
  4. Patches the LLM router so /chat tests do NOT call the real Gemini API,
  5. Returns a TestClient (without using it as a context manager) so that the
     FastAPI lifespan is NOT invoked -- the DB is already initialised by step 2.

All tests use FastAPI's TestClient (backed by httpx).
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.main import app
from app.services import db as db_service
from app.services.providers.base import LLMResponse

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "migrations"
DDL_PATH = Path(__file__).resolve().parents[1] / "scripts" / "init_db.sql"


# ---------------------------------------------------------------------------
# Fake LLM router – replaces the real Gemini router so no network call is made
# ---------------------------------------------------------------------------


class FakeRouter:
    def generate(self, provider_name, req):  # noqa: ANN001
        return LLMResponse(
            reply_text="assistant reply",
            provider=provider_name,
            model=req.model or "gemini-2.0-flash",
            latency_ms=123,
            input_tokens=11,
            output_tokens=22,
            raw={"mock": True},
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Return a TestClient wired to a fresh, fully-migrated temp SQLite DB.

    The TestClient is returned (not used as a context manager) so that the
    FastAPI lifespan handler is not triggered.  The DB is already fully
    initialised (base schema + migration 002) before the client is created.
    """
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("OPENCLAW_DB_PATH", str(db_path))
    monkeypatch.setattr(db_service, "DB_PATH", str(db_path))

    ddl = DDL_PATH.read_text(encoding="utf-8")
    migration_002 = (MIGRATIONS_DIR / "002_add_model_to_messages.sql").read_text(
        encoding="utf-8"
    )

    with db_service.get_conn() as conn:
        conn.executescript(ddl)
        # Apply migration that adds `model` column to messages.
        conn.executescript(migration_002)

    monkeypatch.setattr(chat_api, "get_llm_router", lambda: FakeRouter())
    chat_api._llm_router = None

    # Do NOT use TestClient as a context manager here — that would trigger the
    # FastAPI lifespan which calls init_db() and tries to re-apply migrations
    # against the already-initialised DB, causing duplicate-column errors.
    return TestClient(app)


# ---------------------------------------------------------------------------
# Conversations: POST /conversations
# ---------------------------------------------------------------------------


def test_create_conversation(client: TestClient):
    """POST /conversations creates a conversation and returns 201."""
    res = client.post("/conversations", json={"title": "My Chat"})
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "My Chat"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


def test_create_conversation_default_title(client: TestClient):
    """POST /conversations with empty body uses default title 'New Chat'."""
    res = client.post("/conversations", json={})
    assert res.status_code == 201
    assert res.json()["title"] == "New Chat"


# ---------------------------------------------------------------------------
# Conversations: GET /conversations
# ---------------------------------------------------------------------------


def test_list_conversations_empty(client: TestClient):
    """GET /conversations returns an empty list when no conversations exist."""
    res = client.get("/conversations")
    assert res.status_code == 200
    assert res.json() == []


def test_list_conversations(client: TestClient):
    """GET /conversations lists all created conversations."""
    client.post("/conversations", json={"title": "First"})
    client.post("/conversations", json={"title": "Second"})

    res = client.get("/conversations")
    assert res.status_code == 200
    titles = [c["title"] for c in res.json()]
    assert "First" in titles
    assert "Second" in titles
    assert len(titles) == 2


# ---------------------------------------------------------------------------
# Conversations: PATCH /conversations/{id}
# ---------------------------------------------------------------------------


def test_patch_conversation_title(client: TestClient):
    """PATCH /conversations/{id} renames a conversation."""
    conv = client.post("/conversations", json={"title": "Old Title"}).json()
    res = client.patch(f"/conversations/{conv['id']}", json={"title": "New Title"})
    assert res.status_code == 200
    assert res.json()["title"] == "New Title"


def test_patch_conversation_category(client: TestClient):
    """PATCH /conversations/{id} updates the category field without error."""
    conv = client.post("/conversations", json={"title": "Cat Test"}).json()
    res = client.patch(f"/conversations/{conv['id']}", json={"category": "coding"})
    assert res.status_code == 200


def test_patch_conversation_not_found(client: TestClient):
    """PATCH /conversations/{id} returns 404 for an unknown id."""
    res = client.patch("/conversations/nonexistent-id", json={"title": "X"})
    assert res.status_code == 404


def test_patch_conversation_no_fields_returns_400(client: TestClient):
    """PATCH /conversations/{id} with no update fields returns 400."""
    conv = client.post("/conversations", json={"title": "Empty Patch"}).json()
    res = client.patch(f"/conversations/{conv['id']}", json={})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Conversations: DELETE /conversations/{id}
# ---------------------------------------------------------------------------


def test_delete_conversation(client: TestClient):
    """DELETE /conversations/{id} removes the conversation."""
    conv = client.post("/conversations", json={"title": "To Delete"}).json()
    res = client.delete(f"/conversations/{conv['id']}")
    assert res.status_code == 200
    assert res.json()["deleted"] is True

    # Confirm it is gone from the list.
    listed = client.get("/conversations").json()
    assert all(c["id"] != conv["id"] for c in listed)


def test_delete_conversation_not_found(client: TestClient):
    """DELETE /conversations/{id} returns 404 for an unknown id."""
    res = client.delete("/conversations/does-not-exist")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /conversations/{id}/messages
# ---------------------------------------------------------------------------


def test_get_conversation_messages_empty(client: TestClient):
    """GET /conversations/{id}/messages returns [] when no messages exist."""
    conv = client.post("/conversations", json={"title": "Empty Messages"}).json()
    res = client.get(f"/conversations/{conv['id']}/messages")
    assert res.status_code == 200
    assert res.json() == []


def test_get_conversation_messages_not_found(client: TestClient):
    """GET /conversations/{id}/messages returns 404 for an unknown conversation."""
    res = client.get("/conversations/ghost-id/messages")
    assert res.status_code == 404


def test_get_conversation_messages_after_chat(client: TestClient):
    """GET /conversations/{id}/messages returns messages including the model field."""
    conv = client.post("/conversations", json={"title": "With Messages"}).json()
    conv_id = conv["id"]

    chat_res = client.post(
        "/chat",
        json={
            "conversation_id": conv_id,
            "message": "hello",
            "provider": "gemini",
            "model": "gemini-2.0-flash",
        },
    )
    assert chat_res.status_code == 200

    msgs_res = client.get(f"/conversations/{conv_id}/messages")
    assert msgs_res.status_code == 200
    messages = msgs_res.json()

    assert len(messages) == 2  # one user, one assistant
    for msg in messages:
        assert "model" in msg, "model field missing from message response"
        assert "role" in msg
        assert "content" in msg
        assert "id" in msg


# ---------------------------------------------------------------------------
# Broader integration tests (existing, updated fixture handles migration 002)
# ---------------------------------------------------------------------------


def test_conversation_crud(client: TestClient):
    created = client.post("/conversations", json={"title": "hello"})
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    listed = client.get("/conversations")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    patched = client.patch(f"/conversations/{conversation_id}", json={"title": "updated"})
    assert patched.status_code == 200
    assert patched.json()["title"] == "updated"

    deleted = client.delete(f"/conversations/{conversation_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_chat_and_runs(client: TestClient):
    conv_res = client.post("/conversations", json={"title": "chat"})
    conversation_id = conv_res.json()["id"]

    prompt_res = client.post(
        "/system-prompts",
        json={"name": "coder", "content": "You are a coding assistant."},
    )
    prompt_id = prompt_res.json()["id"]

    chat_res = client.post(
        "/chat",
        json={
            "conversation_id": conversation_id,
            "message": "hello",
            "provider": "gemini",
            "model": "gemini-2.0-flash",
            "system_prompt_id": prompt_id,
            "temperature": 0.7,
            "max_tokens": 256,
        },
    )
    assert chat_res.status_code == 200
    body = chat_res.json()
    assert body["reply"] == "assistant reply"
    assert body["latency_ms"] == 123

    messages_res = client.get(f"/conversations/{conversation_id}/messages")
    assert messages_res.status_code == 200
    assert len(messages_res.json()) == 2

    runs_res = client.get(f"/runs?conversation_id={conversation_id}")
    assert runs_res.status_code == 200
    assert len(runs_res.json()) == 1
    assert runs_res.json()[0]["provider"] == "gemini"

    messages = messages_res.json()
    assistant_message_id = [m for m in messages if m["role"] == "assistant"][0]["id"]
    meta_res = client.put(
        f"/messages/{assistant_message_id}/meta",
        json={
            "task_type": "coding",
            "quality_score": 5,
            "teacher_rationale": "analyze then answer",
            "is_rejected": 0,
        },
    )
    assert meta_res.status_code == 200
    assert meta_res.json()["quality_score"] == 5


def test_export_endpoints(client: TestClient):
    conv_res = client.post("/conversations", json={"title": "export"})
    conversation_id = conv_res.json()["id"]

    client.post(
        "/chat",
        json={
            "conversation_id": conversation_id,
            "message": "create sample",
            "provider": "gemini",
            "model": "gemini-2.0-flash",
            "temperature": 0.2,
            "max_tokens": 128,
        },
    )

    export_json = client.get(f"/export/{conversation_id}?format=json")
    assert export_json.status_code == 200
    assert export_json.json()["conversation"]["id"] == conversation_id

    export_sft = client.get(f"/export/{conversation_id}?format=sft")
    assert export_sft.status_code == 200
    assert isinstance(export_sft.json(), list)

    export_kd = client.get(f"/export/{conversation_id}?format=kd")
    assert export_kd.status_code == 200
    assert isinstance(export_kd.json(), list)

    export_all = client.get("/export/all?format=sft")
    assert export_all.status_code == 200
    assert len(export_all.json()) >= 1

    export_all_kd = client.get("/export/all?format=kd")
    assert export_all_kd.status_code == 200
    assert isinstance(export_all_kd.json(), list)


def test_chat_with_missing_conversation_returns_404(client: TestClient):
    res = client.post(
        "/chat",
        json={
            "conversation_id": "missing-id",
            "message": "hello",
            "provider": "gemini",
        },
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Conversation not found"


def test_chat_with_missing_system_prompt_returns_404(client: TestClient):
    conv_res = client.post("/conversations", json={"title": "missing prompt"})
    conversation_id = conv_res.json()["id"]

    res = client.post(
        "/chat",
        json={
            "conversation_id": conversation_id,
            "message": "hello",
            "provider": "gemini",
            "system_prompt_id": "missing-prompt",
        },
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "System prompt not found"


def test_export_with_invalid_format_returns_400(client: TestClient):
    conv_res = client.post("/conversations", json={"title": "bad format"})
    conversation_id = conv_res.json()["id"]

    res = client.get(f"/export/{conversation_id}?format=xml")
    assert res.status_code == 400
    assert "format must be one of" in res.json()["detail"]
