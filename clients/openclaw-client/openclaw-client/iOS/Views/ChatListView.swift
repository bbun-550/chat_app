import SwiftUI

struct ChatListView: View {
    @StateObject private var convVM = ConversationViewModel()

    var body: some View {
        NavigationStack {
            List(convVM.conversations) { conversation in
                NavigationLink(value: conversation.id) {
                    VStack(alignment: .leading) {
                        Text(conversation.title)
                        if let category = conversation.category, !category.isEmpty {
                            Text(category).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .navigationTitle("Chats")
            .toolbar {
                ToolbarItem(placement: .automatic) {
                    Button {
                        Task { await convVM.createConversation() }
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .refreshable {
                await convVM.loadConversations()
            }
            .task {
                await convVM.loadConversations()
            }
            .navigationDestination(for: String.self) { conversationId in
                ChatDetailView(conversationId: conversationId)
            }
            .overlay {
                if convVM.isLoading {
                    ProgressView()
                }
            }
            .alert("Error", isPresented: Binding(get: { convVM.errorMessage != nil }, set: { _ in convVM.errorMessage = nil })) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(convVM.errorMessage ?? "")
            }
        }
    }
}
