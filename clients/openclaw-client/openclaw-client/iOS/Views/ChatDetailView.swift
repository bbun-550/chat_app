import SwiftUI

struct ChatDetailView: View {
    let conversationId: String
    @StateObject private var chatVM = ChatViewModel()

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(chatVM.messages) { message in
                        let isUser = message.role == "user"
                        VStack(alignment: isUser ? .trailing : .leading, spacing: 4) {
                            HStack(spacing: 6) {
                                Text(isUser ? "You" : "Assistant")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                if !isUser, let model = message.model {
                                    Text(model)
                                        .font(.caption2)
                                        .foregroundStyle(.tertiary)
                                }
                            }
                            Text(message.content)
                                .padding(10)
                                .background(isUser ? Color.accentColor : Color(.secondarySystemBackground))
                                .foregroundStyle(isUser ? Color.white : Color.primary)
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
                    }
                }
                .padding()
            }

            Divider()

            VStack(spacing: 8) {
                HStack {
                    Text("Latency: \(chatVM.lastLatencyMs)ms")
                    Spacer()
                    Text("In: \(chatVM.lastInputTokens)")
                    Text("Out: \(chatVM.lastOutputTokens)")
                }
                .font(.caption)
                .foregroundStyle(.secondary)

                Picker("Model", selection: $chatVM.model) {
                    Text("Flash").tag("gemini-3-flash-preview")
                    Text("Pro").tag("gemini-2.5-pro")
                    Text("Exp").tag("gemini-2.5-pro-exp-03-25")
                }
                .pickerStyle(.segmented)

                HStack {
                    TextField("Message...", text: $chatVM.inputText, axis: .vertical)
                        .textFieldStyle(.roundedBorder)
                        .lineLimit(1...5)
                    Button {
                        Task { await chatVM.send() }
                    } label: {
                        if chatVM.isSending {
                            ProgressView().controlSize(.small)
                        } else {
                            Image(systemName: "arrow.up")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(chatVM.isSending || chatVM.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
            .padding()
        }
        .navigationTitle("Chat")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .toolbar {
            ToolbarItem(placement: .automatic) {
                if chatVM.isSending {
                    ProgressView()
                }
            }
        }
        .task {
            chatVM.bindConversation(conversationId)
            await chatVM.loadMessages()
        }
        .alert("Error", isPresented: Binding(get: { chatVM.errorMessage != nil }, set: { _ in chatVM.errorMessage = nil })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(chatVM.errorMessage ?? "")
        }
    }
}
