CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL DEFAULT 'New Chat',
  category TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  model TEXT NOT NULL DEFAULT 'gemini-3-flash-preview',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_prompts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  system_prompt_id TEXT REFERENCES system_prompts(id) ON DELETE SET NULL,
  system_prompt_content TEXT,
  params_json TEXT NOT NULL,
  latency_ms INTEGER NOT NULL,
  input_tokens INTEGER,
  output_tokens INTEGER,
  top_p REAL,
  top_k INTEGER,
  candidate_count INTEGER,
  raw_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS message_meta (
  message_id TEXT PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
  task_type TEXT,
  quality_score INTEGER CHECK (quality_score BETWEEN 1 AND 5),
  tags TEXT,
  teacher_rationale TEXT,
  rating_source TEXT,
  is_rejected INTEGER NOT NULL DEFAULT 0,
  language TEXT,
  safety_flags TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS kd_examples (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  user_message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  assistant_message_id TEXT NOT NULL UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
  system_prompt TEXT,
  prompt_text TEXT NOT NULL,
  teacher_rationale TEXT,
  answer_text TEXT NOT NULL,
  category TEXT,
  quality_score INTEGER,
  task_type TEXT,
  is_rejected INTEGER NOT NULL DEFAULT 0,
  provider TEXT,
  model TEXT,
  run_id TEXT REFERENCES runs(id) ON DELETE SET NULL,
  dataset_version TEXT NOT NULL DEFAULT 'v1',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_migrations (
  name TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
);

-- New tables for Phase 1

CREATE TABLE IF NOT EXISTS daily_summaries (
  id TEXT PRIMARY KEY,
  conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
  summary_text TEXT NOT NULL,
  fact_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vector_memories (
  id TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  embedding vector(384) NOT NULL,
  memory_type TEXT NOT NULL DEFAULT 'fact',
  source_conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
  created_at TEXT NOT NULL
);

-- Indexes

CREATE INDEX IF NOT EXISTS idx_messages_conv_created ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_runs_message ON runs(message_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_kd_examples_category_quality ON kd_examples(category, quality_score, is_rejected);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_created ON daily_summaries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vector_memories_type ON vector_memories(memory_type, created_at DESC);
