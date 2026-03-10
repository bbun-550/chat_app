import SwiftUI

struct ChatSplitView: View {
    @StateObject private var convVM = ConversationViewModel()
    @StateObject private var chatVM = ChatViewModel()

    var body: some View {
        NavigationSplitView {
            conversationSidebar
        } detail: {
            chatDetailView
        }
        .alert("Error", isPresented: errorBinding) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(chatVM.errorMessage ?? convVM.errorMessage ?? "")
        }
    }
    
    private var conversationSidebar: some View {
        List(convVM.conversations, selection: $convVM.selectedConversationId) { conversation in
            ConversationRow(conversation: conversation)
                .tag(conversation.id as String?)
        }
        .navigationTitle("Conversations")
        .toolbar {
            ToolbarItem {
                Button {
                    Task { await convVM.createConversation() }
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .overlay {
            if convVM.isLoading {
                ProgressView()
            }
        }
        .task {
            await convVM.loadConversations()
        }
        .onChange(of: convVM.selectedConversationId) { _, value in
            chatVM.bindConversation(value)
            Task { await chatVM.loadMessages() }
        }
    }
    
    private var chatDetailView: some View {
        VStack(spacing: 0) {
            modelPickerHeader
            Divider()
            messageScrollView
            Divider()
            inputArea
            statsBar
        }
    }
    
    private var modelPickerHeader: some View {
        HStack(spacing: 12) {
            Picker("Model", selection: $chatVM.model) {
                Text("Flash").tag("gemini-3-flash-preview")
                Text("Pro").tag("gemini-2.5-pro")
                Text("Exp").tag("gemini-2.5-pro-exp-03-25")
            }
            .pickerStyle(.segmented)
            .frame(width: 260)

            Spacer()

            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    chatVM.isSearching.toggle()
                    if !chatVM.isSearching { chatVM.searchText = "" }
                }
            } label: {
                Image(systemName: chatVM.isSearching ? "xmark.circle.fill" : "magnifyingglass")
            }
            .buttonStyle(.plain)

            if chatVM.isSending {
                ProgressView().controlSize(.small)
            }
        }
        .padding()
    }
    
    private var messageScrollView: some View {
        VStack(spacing: 0) {
            if chatVM.isSearching {
                HStack {
                    Image(systemName: "magnifyingglass").foregroundStyle(.secondary)
                    TextField("Search messages...", text: $chatVM.searchText)
                    if !chatVM.searchText.isEmpty {
                        Text("\(chatVM.filteredMessages.count) results")
                            .font(.caption).foregroundStyle(.secondary)
                        Button { chatVM.searchText = "" } label: {
                            Image(systemName: "xmark.circle.fill").foregroundStyle(.secondary)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal)
                .padding(.vertical, 6)
                Divider()
            }
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(chatVM.filteredMessages) { message in
                        MessageBubble(message: message) {
                            Task { await chatVM.toggleBookmark(message.id) }
                        }
                    }
                }
                .padding()
            }
        }
    }
    
    private var inputArea: some View {
        HStack {
            TextField("Message...", text: $chatVM.inputText, axis: .vertical)
                .textFieldStyle(.roundedBorder)
            Button("Send") {
                Task { await chatVM.send() }
            }
            .disabled(chatVM.isSending)
        }
        .padding()
    }
    
    private var statsBar: some View {
        HStack(spacing: 16) {
            Text("Latency: \(chatVM.lastLatencyMs)ms")
            Text("In: \(chatVM.lastInputTokens)")
            Text("Out: \(chatVM.lastOutputTokens)")
            Spacer()
        }
        .font(.caption)
        .foregroundStyle(.secondary)
        .padding([.horizontal, .bottom])
    }
    
    private var errorBinding: Binding<Bool> {
        Binding(
            get: { chatVM.errorMessage != nil || convVM.errorMessage != nil },
            set: { _ in
                chatVM.errorMessage = nil
                convVM.errorMessage = nil
            }
        )
    }
}

// MARK: - Supporting Views

private struct ConversationRow: View {
    let conversation: Conversation
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(conversation.title)
            if let category = conversation.category, !category.isEmpty {
                Text(category)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

private struct MessageBubble: View {
    let message: Message
    var onToggleBookmark: (() -> Void)? = nil

    private var isUser: Bool { message.role == "user" }
    private var isBookmarked: Bool { message.is_bookmarked == 1 }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(isUser ? "You" : "Assistant")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if isBookmarked {
                    Image(systemName: "bookmark.fill")
                        .font(.caption)
                        .foregroundStyle(.orange)
                }
            }
            Group {
                if isUser {
                    Text(message.content)
                } else {
                    MarkdownContentView(text: message.content)
                }
            }
            .textSelection(.enabled)
            .padding(10)
            .background(.thinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .contextMenu {
                Button {
                    NSPasteboard.general.setString(message.content, forType: .string)
                } label: {
                    Label("Copy", systemImage: "doc.on.doc")
                }
                Button {
                    onToggleBookmark?()
                } label: {
                    Label(
                        isBookmarked ? "북마크 해제" : "북마크",
                        systemImage: isBookmarked ? "bookmark.slash" : "bookmark"
                    )
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
    }
}
