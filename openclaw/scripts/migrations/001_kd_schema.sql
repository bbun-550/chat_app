ALTER TABLE conversations ADD COLUMN category TEXT;

ALTER TABLE message_meta ADD COLUMN teacher_rationale TEXT;
ALTER TABLE message_meta ADD COLUMN rating_source TEXT;
ALTER TABLE message_meta ADD COLUMN is_rejected INTEGER NOT NULL DEFAULT 0;
ALTER TABLE message_meta ADD COLUMN language TEXT;
ALTER TABLE message_meta ADD COLUMN safety_flags TEXT;

ALTER TABLE runs ADD COLUMN top_p REAL;
ALTER TABLE runs ADD COLUMN top_k INTEGER;
ALTER TABLE runs ADD COLUMN candidate_count INTEGER;

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

CREATE INDEX IF NOT EXISTS idx_kd_examples_category_quality
  ON kd_examples(category, quality_score, is_rejected);
