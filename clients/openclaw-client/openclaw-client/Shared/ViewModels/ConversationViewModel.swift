import Foundation
import Combine

@MainActor
final class ConversationViewModel: ObservableObject {
    @Published var conversations: [Conversation] = []
    @Published var selectedConversationId: String?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var searchText = ""

    var filteredConversations: [Conversation] {
        if searchText.isEmpty { return conversations }
        return conversations.filter {
            $0.title.localizedCaseInsensitiveContains(searchText)
            || ($0.category ?? "").localizedCaseInsensitiveContains(searchText)
        }
    }

    func loadConversations() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let items = try await APIClient.shared.fetchConversations()
            conversations = items
            if selectedConversationId == nil {
                selectedConversationId = items.first?.id
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func createConversation(title: String = "New Chat") async {
        do {
            let created = try await APIClient.shared.createConversation(title: title)
            conversations.insert(created, at: 0)
            selectedConversationId = created.id
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func renameConversation(id: String, title: String) async {
        do {
            let updated = try await APIClient.shared.patchConversation(id: id, title: title, category: nil)
            if let idx = conversations.firstIndex(where: { $0.id == id }) {
                conversations[idx] = updated
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func updateCategory(id: String, category: String?) async {
        do {
            let updated = try await APIClient.shared.patchConversation(id: id, title: nil, category: category)
            if let idx = conversations.firstIndex(where: { $0.id == id }) {
                conversations[idx] = updated
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deleteConversation(id: String) async {
        do {
            _ = try await APIClient.shared.deleteConversation(id: id)
            conversations.removeAll { $0.id == id }
            if selectedConversationId == id {
                selectedConversationId = conversations.first?.id
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
