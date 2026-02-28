# OpenClaw Swift Client API Contract (Phase 0)

## Base
- Base URL: configurable (default `http://127.0.0.1:8000`)
- Content-Type: `application/json`

## Endpoints

### GET /conversations
Response item fields:
- `id: String`
- `title: String`
- `category: String?`
- `created_at: String`
- `updated_at: String`

### POST /conversations
Request:
- `title: String`

Response:
- same as conversation object

### PATCH /conversations/{id}
Request:
- `title: String?`
- `category: String?`

### DELETE /conversations/{id}
Response:
- `deleted: Bool`

### GET /conversations/{id}/messages
Response item fields:
- `id: String`
- `conversation_id: String`
- `role: String` (`user|assistant|system`)
- `content: String`
- `created_at: String`

### POST /chat
Request:
- `conversation_id: String`
- `message: String`
- `provider: String`
- `model: String?`
- `system_prompt_id: String?`
- `temperature: Double`
- `max_tokens: Int`
- `top_p: Double?`
- `top_k: Int?`
- `candidate_count: Int?`

Response:
- `reply: String`
- `provider: String`
- `model: String`
- `latency_ms: Int`
- `input_tokens: Int?`
- `output_tokens: Int?`

### GET /runs?conversation_id={id}
Response item fields:
- `id: String`
- `message_id: String`
- `provider: String`
- `model: String`
- `system_prompt_id: String?`
- `system_prompt_content: String?`
- `latency_ms: Int`
- `input_tokens: Int?`
- `output_tokens: Int?`
- `created_at: String`

### PUT /messages/{message_id}/meta
Request:
- `task_type: String?`
- `quality_score: Int?`
- `teacher_rationale: String?`
- `is_rejected: Int?`
- `notes: String?`

### GET /export/{conversation_id}?format={json|sft|kd}
### GET /export/all?format={json|sft|kd}&min_quality={Int?}

## Error
- Non-2xx body uses `{"detail": "..."}`
