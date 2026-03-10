import Foundation

enum Endpoint {
    case conversations
    case createConversation
    case patchConversation(id: String)
    case deleteConversation(id: String)
    case messages(conversationId: String)
    case chat
    case chatStream
    case runs(conversationId: String?)
    case upsertMessageMeta(messageId: String)
    case toggleBookmark(messageId: String)
    case bookmarks
    case providers
    case providerModels(provider: String)
    case exportConversation(conversationId: String, format: String)
    case exportAll(format: String, minQuality: Int?)

    var path: String {
        switch self {
        case .conversations, .createConversation:
            return "/conversations"
        case .patchConversation(let id), .deleteConversation(let id):
            return "/conversations/\(id)"
        case .messages(let id):
            return "/conversations/\(id)/messages"
        case .chat:
            return "/chat"
        case .chatStream:
            return "/chat/stream"
        case .runs(let conversationId):
            if let id = conversationId {
                return "/runs?conversation_id=\(id)"
            }
            return "/runs"
        case .upsertMessageMeta(let messageId):
            return "/messages/\(messageId)/meta"
        case .toggleBookmark(let messageId):
            return "/messages/\(messageId)/bookmark"
        case .bookmarks:
            return "/bookmarks"
        case .providers:
            return "/providers"
        case .providerModels(let provider):
            return "/providers/\(provider)/models"
        case .exportConversation(let conversationId, let format):
            return "/export/\(conversationId)?format=\(format)"
        case .exportAll(let format, let minQuality):
            if let minQuality {
                return "/export/all?format=\(format)&min_quality=\(minQuality)"
            }
            return "/export/all?format=\(format)"
        }
    }

    var method: String {
        switch self {
        case .createConversation, .chat, .chatStream, .toggleBookmark:
            return "POST"
        case .patchConversation:
            return "PATCH"
        case .deleteConversation:
            return "DELETE"
        case .upsertMessageMeta:
            return "PUT"
        default:
            return "GET"
        }
    }
}
