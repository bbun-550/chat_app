import Foundation

struct RunStats: Codable, Identifiable, Hashable {
    let id: String
    let message_id: String
    let provider: String
    let model: String
    let system_prompt_id: String?
    let system_prompt_content: String?
    let latency_ms: Int
    let input_tokens: Int?
    let output_tokens: Int?
    let created_at: String
}
