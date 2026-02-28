import Foundation

struct Message: Codable, Identifiable, Hashable {
    let id: String
    let conversation_id: String
    let role: String
    let content: String
    let created_at: String
}
