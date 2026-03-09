import Foundation

struct ChatRequest: Codable {
    let conversation_id: String
    let message: String
    let provider: String
    let model: String?
    let system_prompt_id: String?
    let temperature: Double
    let max_tokens: Int
    let top_p: Double?
    let top_k: Int?
    let candidate_count: Int?
}

struct ChatResponse: Codable {
    let reply: String
    let provider: String
    let model: String
    let latency_ms: Int
    let input_tokens: Int?
    let output_tokens: Int?
}

struct DeleteResponse: Codable {
    let deleted: Bool
}

struct MessageMetaUpsertRequest: Codable {
    let task_type: String?
    let quality_score: Int?
    let tags: [String]?
    let teacher_rationale: String?
    let rating_source: String?
    let is_rejected: Int?
    let language: String?
    let safety_flags: [String]?
    let notes: String?
}

struct StreamedChatChunk: Codable {
    let delta: String
    let done: Bool
    let provider: String?
    let model: String?
    let latency_ms: Int?
    let input_tokens: Int?
    let output_tokens: Int?
    let error: String?
}

struct APIErrorResponse: Codable {
    let detail: String
}
