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
                HStack(spacing: 12) {
                    Picker("Model", selection: $chatVM.model) {
                        Text("Flash").tag("gemini-3-flash-preview")
                        Text("Pro").tag("gemini-2.5-pro")
                        Text("Exp").tag("gemini-2.5-pro-exp-03-25")
                    }
                    .pickerStyle(.segmented)
                    .frame(width: 260)

                    Spacer()

                    if chatVM.isSending {
                        ProgressView().controlSize(.small)
                    }
                }
                .padding()

                Divider()

                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 10) {
                        ForEach(chatVM.messages) { message in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack(spacing: 6) {
                                    Text(message.role == "user" ? "You" : "Assistant")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    if message.role == "assistant", let model = message.model {
                                        Text(model)
                                            .font(.caption2)
                                            .foregroundStyle(.tertiary)
                                    }
                                }
                                Text(message.content)
                                    .textSelection(.enabled)
                                    .padding(10)
                                    .background(.thinMaterial)
                                    .clipShape(RoundedRectangle(cornerRadius: 10))
                            }
                            .frame(maxWidth: .infinity, alignment: message.role == "user" ? .trailing : .leading)
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
