from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.main import app
from app.services import db as db_service
from app.services.providers.base import LLMResponse


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


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("OPENCLAW_DB_PATH", str(db_path))
    db_service.DB_PATH = str(db_path)

    ddl_path = Path(__file__).resolve().parents[1] / "scripts" / "init_db.sql"
    with db_service.get_conn() as conn:
        conn.executescript(ddl_path.read_text(encoding="utf-8"))

    monkeypatch.setattr(chat_api, "get_llm_router", lambda: FakeRouter())
    chat_api._llm_router = None

    return TestClient(app)


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
