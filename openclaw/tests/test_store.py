"""Integration tests for app/services/store.py.

Each test gets a fresh SQLite file via the `initialized_db` fixture, which:
  1. Creates a temp file (tmp_path),
  2. Applies the full schema from scripts/init_db.sql, and
  3. Applies migration 002_add_model_to_messages.sql so the messages table
     has the `model` column that store.insert_message() now requires.
"""
from pathlib import Path

import pytest

from app.services import db as db_service
from app.services import store

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "migrations"
DDL_PATH = Path(__file__).resolve().parents[1] / "scripts" / "init_db.sql"


@pytest.fixture()
def initialized_db(tmp_path, monkeypatch):
    """Set up a fresh temp SQLite DB with base schema + migration 002."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("OPENCLAW_DB_PATH", str(db_path))
    # db_service.DB_PATH is read at module level; patch the attribute so
    # get_conn() picks up the temp path for the duration of this test.
    monkeypatch.setattr(db_service, "DB_PATH", str(db_path))

    ddl = DDL_PATH.read_text(encoding="utf-8")
    migration_002 = (MIGRATIONS_DIR / "002_add_model_to_messages.sql").read_text(
        encoding="utf-8"
    )

    with db_service.get_conn() as conn:
        conn.executescript(ddl)
        # Apply migration that adds the `model` column to messages.
        conn.executescript(migration_002)

    return db_path


# ---------------------------------------------------------------------------
# Existing integration tests (updated fixture handles migration 002)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# New tests for migration 002: model column on messages
# ---------------------------------------------------------------------------


def test_insert_message_saves_explicit_model(initialized_db):
    """insert_message() persists the model name that is explicitly passed in."""
    conversation = store.create_conversation("Model Test")
    message_id = store.insert_message(
        conversation["id"], "user", "ping", model="gemini-1.5-pro"
    )

    fetched = store.get_message(message_id)
    assert fetched is not None
    assert fetched["model"] == "gemini-1.5-pro"


def test_insert_message_default_model(initialized_db):
    """insert_message() uses 'gemini-2.0-flash' when model is not supplied.

    The Python-level default in store.insert_message() is 'gemini-2.0-flash'.
    Migration 002 sets the SQL column default to 'gemini-3-flash-preview', but
    the Python default is always passed explicitly in the INSERT statement, so
    the Python value wins.
    """
    conversation = store.create_conversation("Default Model Test")
    message_id = store.insert_message(conversation["id"], "assistant", "pong")

    fetched = store.get_message(message_id)
    assert fetched is not None
    assert fetched["model"] == "gemini-2.0-flash"


def test_get_messages_returns_model_field(initialized_db):
    """get_messages() includes the 'model' key in every returned dict."""
    conversation = store.create_conversation("Get Messages Model Test")
    store.insert_message(conversation["id"], "user", "hello", model="gemini-2.0-flash")
    store.insert_message(
        conversation["id"], "assistant", "world", model="gemini-1.5-pro"
    )

    messages = store.get_messages(conversation["id"])
    assert len(messages) == 2

    # Both messages must expose the model field.
    for msg in messages:
        assert "model" in msg, "model field missing from get_messages() result"

    # Values must match what was inserted.
    user_msg = next(m for m in messages if m["role"] == "user")
    assistant_msg = next(m for m in messages if m["role"] == "assistant")
    assert user_msg["model"] == "gemini-2.0-flash"
    assert assistant_msg["model"] == "gemini-1.5-pro"


def test_insert_message_model_persists_across_conversations(initialized_db):
    """Model values are correctly scoped per message, not shared across conversations."""
    conv_a = store.create_conversation("Conv A")
    conv_b = store.create_conversation("Conv B")

    store.insert_message(conv_a["id"], "user", "msg a", model="gemini-2.0-flash")
    store.insert_message(conv_b["id"], "user", "msg b", model="gemini-1.5-pro")

    msgs_a = store.get_messages(conv_a["id"])
    msgs_b = store.get_messages(conv_b["id"])

    assert msgs_a[0]["model"] == "gemini-2.0-flash"
    assert msgs_b[0]["model"] == "gemini-1.5-pro"
