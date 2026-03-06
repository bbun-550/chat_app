import Foundation

struct Conversation: Codable, Identifiable, Hashable {
    let id: String
    let title: String
    let category: String?
    let created_at: String
    let updated_at: String

    var relativeUpdatedAt: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        guard let date = formatter.date(from: updated_at) ?? ISO8601DateFormatter().date(from: updated_at) else {
            return ""
        }
        let relative = RelativeDateTimeFormatter()
        relative.unitsStyle = .abbreviated
        return relative.localizedString(for: date, relativeTo: Date())
    }
}
