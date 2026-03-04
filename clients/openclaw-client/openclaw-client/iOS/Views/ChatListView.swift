import SwiftUI

struct ChatListView: View {
    @StateObject private var convVM = ConversationViewModel()
    @State private var showDeleteConfirmation = false
    @State private var conversationToDelete: Conversation?
    @State private var showRenameAlert = false
    @State private var conversationToRename: Conversation?
    @State private var renameText = ""

    var body: some View {
        NavigationStack {
            List(convVM.filteredConversations) { conversation in
                NavigationLink(value: conversation.id) {
                    VStack(alignment: .leading) {
                        Text(conversation.title)
                        if let category = conversation.category, !category.isEmpty {
                            Text(category).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                .swipeActions(edge: .leading, allowsFullSwipe: false) {
                    Button {
                        conversationToRename = conversation
                        renameText = conversation.title
                        showRenameAlert = true
                    } label: {
                        Label("Rename", systemImage: "pencil")
                    }
                    .tint(.orange)
                }
                .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                    Button(role: .destructive) {
                        conversationToDelete = conversation
                        showDeleteConfirmation = true
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                }
            }
            .navigationTitle("Chats")
            .searchable(text: $convVM.searchText, prompt: "Search chats")
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
                } else if convVM.filteredConversations.isEmpty && !convVM.searchText.isEmpty {
                    ContentUnavailableView.search(text: convVM.searchText)
                } else if convVM.conversations.isEmpty {
                    ContentUnavailableView(
                        "No Conversations",
                        systemImage: "bubble.left.and.bubble.right",
                        description: Text("Tap + to start a new chat")
                    )
                }
            }
            .alert("Error", isPresented: Binding(get: { convVM.errorMessage != nil }, set: { _ in convVM.errorMessage = nil })) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(convVM.errorMessage ?? "")
            }
            .alert("Delete Chat?", isPresented: $showDeleteConfirmation) {
                Button("Delete", role: .destructive) {
                    guard let conversation = conversationToDelete else { return }
                    Task { await convVM.deleteConversation(id: conversation.id) }
                    conversationToDelete = nil
                }
                Button("Cancel", role: .cancel) {
                    conversationToDelete = nil
                }
            } message: {
                Text("This conversation and all messages will be permanently deleted.")
            }
            .alert("Rename Chat", isPresented: $showRenameAlert) {
                TextField("Chat name", text: $renameText)
                Button("Save") {
                    guard let conversation = conversationToRename else { return }
                    let trimmed = renameText.trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !trimmed.isEmpty else {
                        conversationToRename = nil
                        return
                    }
                    Task { await convVM.renameConversation(id: conversation.id, title: trimmed) }
                    conversationToRename = nil
                }
                Button("Cancel", role: .cancel) {
                    conversationToRename = nil
                }
            }
        }
    }
}
