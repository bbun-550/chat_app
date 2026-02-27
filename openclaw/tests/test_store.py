from pathlib import Path

import pytest

from app.services import db as db_service
from app.services import store


@pytest.fixture()
def initialized_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("OPENCLAW_DB_PATH", str(db_path))
    db_service.DB_PATH = str(db_path)

    ddl_path = Path(__file__).resolve().parents[1] / "scripts" / "init_db.sql"
    ddl = ddl_path.read_text(encoding="utf-8")
    with db_service.get_conn() as conn:
        conn.executescript(ddl)

    return db_path


def test_conversation_message_run_flow(initialized_db):
    conversation = store.create_conversation("First", category="coding")
    user_message_id = store.insert_message(conversation["id"], "user", "hello")
    assistant_message_id = store.insert_message(conversation["id"], "assistant", "hi")

    run_id = store.insert_run(
        message_id=assistant_message_id,
        provider="gemini",
        model="gemini-2.0-flash",
        system_prompt_id=None,
        system_prompt_content="system prompt",
        params={"temperature": 0.7},
        latency_ms=100,
        input_tokens=10,
        output_tokens=20,
        raw={"ok": True},
    )

    assert user_message_id
    assert run_id
    assert len(store.get_messages(conversation["id"])) == 2

    runs = store.list_runs(conversation["id"])
    assert len(runs) == 1
    assert runs[0]["model"] == "gemini-2.0-flash"
    assert store.get_conversation(conversation["id"])["category"] == "coding"


def test_system_prompt_crud(initialized_db):
    created = store.create_system_prompt("reviewer", "be strict")
    fetched = store.get_system_prompt(created["id"])
    assert fetched is not None
    assert fetched["name"] == "reviewer"

    updated = store.update_system_prompt(created["id"], "architect", "be concise")
    assert updated is not None
    assert updated["name"] == "architect"

    deleted = store.delete_system_prompt(created["id"])
    assert deleted is True
    assert store.get_system_prompt(created["id"]) is None


def test_export_and_meta(initialized_db):
    conversation = store.create_conversation("Export Test")
    store.insert_message(conversation["id"], "user", "question")
    assistant_id = store.insert_message(conversation["id"], "assistant", "answer")
    store.upsert_message_meta(
        message_id=assistant_id,
        task_type="code_generation",
        quality_score=5,
        tags=["python", "api"],
        teacher_rationale="step by step",
        is_rejected=0,
        notes="good",
    )
    run_id = store.insert_run(
        message_id=assistant_id,
        provider="gemini",
        model="gemini-2.0-flash",
        system_prompt_id=None,
        system_prompt_content="act as coder",
        params={"temperature": 0.3},
        latency_ms=250,
        input_tokens=32,
        output_tokens=64,
        raw=None,
    )
    store.upsert_kd_example(
        conversation_id=conversation["id"],
        user_message_id=store.get_messages(conversation["id"])[0]["id"],
        assistant_message_id=assistant_id,
        system_prompt="act as coder",
        prompt_text="question",
        answer_text="answer",
        provider="gemini",
        model="gemini-2.0-flash",
        run_id=run_id,
    )

    exported = store.export_conversation(conversation["id"])
    assert exported["conversation"]["id"] == conversation["id"]
    assert len(exported["messages"]) == 2
    assert len(exported["runs"]) == 1
    assert len(exported["meta"]) == 1

    sft = store.export_sft(conversation["id"])
    assert len(sft) == 1
    assert sft[0]["metadata"]["quality_score"] == 5
    assert sft[0]["metadata"]["task_type"] == "code_generation"
    kd = store.export_kd_examples(conversation_id=conversation["id"], min_quality=4)
    assert len(kd) == 1
    assert kd[0]["teacher_rationale"] == "step by step"
