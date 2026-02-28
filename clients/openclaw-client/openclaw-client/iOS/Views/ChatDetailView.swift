import SwiftUI

struct ChatDetailView: View {
    let conversationId: String
    @StateObject private var chatVM = ChatViewModel()

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(chatVM.messages) { message in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(message.role)
                                .font(.caption)
                                .foregroundStyle(.secondary)
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

            VStack(spacing: 8) {
                HStack {
                    Text("Latency: \(chatVM.lastLatencyMs)ms")
                    Spacer()
                    Text("In: \(chatVM.lastInputTokens)")
                    Text("Out: \(chatVM.lastOutputTokens)")
                }
                .font(.caption)
                .foregroundStyle(.secondary)

                HStack {
                    TextField("Message...", text: $chatVM.inputText, axis: .vertical)
                        .textFieldStyle(.roundedBorder)
                    Button("Send") {
                        Task { await chatVM.send() }
                    }
                    .disabled(chatVM.isSending)
                }
            }
            .padding()
        }
        .navigationTitle("Chat")
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
