import Foundation

struct Message: Codable, Identifiable, Hashable {
    let id: String
    let conversation_id: String
    let role: String
    var content: String
    let created_at: String
    var is_bookmarked: Int?
}
