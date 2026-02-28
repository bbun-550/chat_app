import Foundation

struct Conversation: Codable, Identifiable, Hashable {
    let id: String
    let title: String
    let category: String?
    let created_at: String
    let updated_at: String
}
