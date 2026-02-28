import SwiftUI

struct ChatSplitView: View {
    @StateObject private var convVM = ConversationViewModel()
    @StateObject private var chatVM = ChatViewModel()

    var body: some View {
        NavigationSplitView {
            List(convVM.conversations, selection: $convVM.selectedConversationId) { conversation in
                VStack(alignment: .leading, spacing: 4) {
                    Text(conversation.title)
                    if let category = conversation.category, !category.isEmpty {
                        Text(category).font(.caption).foregroundStyle(.secondary)
                    }
                }
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
        } detail: {
            VStack(spacing: 0) {
                HStack {
                    Text("Provider")
                    TextField("provider", text: $chatVM.provider)
                        .frame(width: 120)
                    Text("Model")
                    TextField("model", text: $chatVM.model)
                        .frame(width: 220)
                    Spacer()
                    if chatVM.isSending {
                        ProgressView()
                    }
                }
                .padding()

                Divider()

                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 10) {
                        ForEach(chatVM.messages) { message in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(message.role).font(.caption).foregroundStyle(.secondary)
                                Text(message.content)
                                    .padding(10)
                                    .background(.thinMaterial)
                                    .clipShape(RoundedRectangle(cornerRadius: 10))
                            }
                        }
                    }
                    .padding()
                }

                Divider()

                HStack {
                    TextField("Message...", text: $chatVM.inputText, axis: .vertical)
                        .textFieldStyle(.roundedBorder)
                    Button("Send") {
                        Task { await chatVM.send() }
                    }
                    .disabled(chatVM.isSending)
                }
                .padding()

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
        }
        .alert("Error", isPresented: Binding(get: { chatVM.errorMessage != nil || convVM.errorMessage != nil }, set: { _ in
            chatVM.errorMessage = nil
            convVM.errorMessage = nil
        })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(chatVM.errorMessage ?? convVM.errorMessage ?? "")
        }
    }
}
