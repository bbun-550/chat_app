PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL DEFAULT 'New Chat',
  category TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
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
  message_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  system_prompt_id TEXT,
  system_prompt_content TEXT,
  params_json TEXT NOT NULL,
  latency_ms INTEGER NOT NULL,
  input_tokens INTEGER,
  output_tokens INTEGER,
  top_p REAL,
  top_k INTEGER,
  candidate_count INTEGER,
  raw_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
  FOREIGN KEY (system_prompt_id) REFERENCES system_prompts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS message_meta (
  message_id TEXT PRIMARY KEY,
  task_type TEXT,
  quality_score INTEGER CHECK (quality_score BETWEEN 1 AND 5),
  tags TEXT,
  teacher_rationale TEXT,
  rating_source TEXT,
  is_rejected INTEGER NOT NULL DEFAULT 0,
  language TEXT,
  safety_flags TEXT,
  notes TEXT,
  FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS kd_examples (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  user_message_id TEXT NOT NULL,
  assistant_message_id TEXT NOT NULL UNIQUE,
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
  run_id TEXT,
  dataset_version TEXT NOT NULL DEFAULT 'v1',
  created_at TEXT NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
  FOREIGN KEY (user_message_id) REFERENCES messages(id) ON DELETE CASCADE,
  FOREIGN KEY (assistant_message_id) REFERENCES messages(id) ON DELETE CASCADE,
  FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conv_created
  ON messages(conversation_id, created_at);

CREATE INDEX IF NOT EXISTS idx_runs_message
  ON runs(message_id, created_at);

CREATE INDEX IF NOT EXISTS idx_conversations_updated
  ON conversations(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_kd_examples_category_quality
  ON kd_examples(category, quality_score, is_rejected);
