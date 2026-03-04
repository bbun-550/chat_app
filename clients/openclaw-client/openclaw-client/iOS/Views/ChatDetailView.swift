import SwiftUI

struct ChatDetailView: View {
    let conversationId: String
    @StateObject private var chatVM = ChatViewModel()
    @State private var showScrollToBottomButton = false
    @State private var bottomAnchorMinY: CGFloat = .zero
    @FocusState private var isInputFocused: Bool

    private let bottomAnchorID = "chat-detail-bottom-anchor"

    var body: some View {
        VStack(spacing: 0) {
            messagesView

            Divider()

            composerControls
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
            Button("Retry") { Task { await chatVM.send() } }
            Button("OK", role: .cancel) {}
        } message: {
            Text(chatVM.errorMessage ?? "")
        }
    }

    private var messagesView: some View {
        GeometryReader { viewport in
            ScrollViewReader { proxy in
                ZStack(alignment: .bottomTrailing) {
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 10) {
                            ForEach(chatVM.messages) { message in
                                MessageBubbleView(message: message)
                                    .id(message.id)
                            }
                            Color.clear
                                .frame(height: 1)
                                .id(bottomAnchorID)
                                .background(
                                    GeometryReader { geometry in
                                        Color.clear.preference(
                                            key: BottomAnchorOffsetKey.self,
                                            value: geometry.frame(in: .named("chat-scroll")).minY
                                        )
                                    }
                                )
                        }
                        .padding()
                    }
                    .coordinateSpace(name: "chat-scroll")
                    .onAppear {
                        scrollToBottom(using: proxy, animated: false)
                    }
                    .onChange(of: chatVM.messages.count) { _, _ in
                        scrollToBottom(using: proxy, animated: true)
                    }
                    .onPreferenceChange(BottomAnchorOffsetKey.self) { newValue in
                        bottomAnchorMinY = newValue
                        updateScrollButton(viewportHeight: viewport.size.height)
                    }
                    .onChange(of: viewport.size.height) { _, newValue in
                        updateScrollButton(viewportHeight: newValue)
                    }

                    if showScrollToBottomButton {
                        Button {
                            scrollToBottom(using: proxy, animated: true)
                        } label: {
                            Image(systemName: "chevron.down")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(.white)
                                .frame(width: 36, height: 36)
                                .background(Color.accentColor)
                                .clipShape(Circle())
                                .shadow(radius: 4)
                        }
                        .padding(.trailing, 16)
                        .padding(.bottom, 12)
                        .transition(.scale.combined(with: .opacity))
                        .accessibilityLabel("Scroll to latest message")
                    }
                }
            }
        }
    }

    private var composerControls: some View {
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
                    .focused($isInputFocused)
                Button {
                    isInputFocused = false
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

    private func scrollToBottom(using proxy: ScrollViewProxy, animated: Bool) {
        guard !chatVM.messages.isEmpty else { return }

        if animated {
            withAnimation(.easeInOut(duration: 0.22)) {
                proxy.scrollTo(bottomAnchorID, anchor: .bottom)
                showScrollToBottomButton = false
            }
        } else {
            proxy.scrollTo(bottomAnchorID, anchor: .bottom)
            showScrollToBottomButton = false
        }
    }

    private func updateScrollButton(viewportHeight: CGFloat) {
        let threshold: CGFloat = 120
        let shouldShow = (bottomAnchorMinY - viewportHeight) > threshold
        guard shouldShow != showScrollToBottomButton else { return }

        withAnimation(.easeInOut(duration: 0.2)) {
            showScrollToBottomButton = shouldShow
        }
    }
}

private struct BottomAnchorOffsetKey: PreferenceKey {
    static var defaultValue: CGFloat = .zero

    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

private struct MessageBubbleView: View {
    let message: Message
    
    private var isUser: Bool {
        message.role == "user"
    }
    
    var body: some View {
        VStack(alignment: isUser ? .trailing : .leading, spacing: 4) {
            Text(isUser ? "You" : "Assistant")
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(message.content)
                .textSelection(.enabled)
                .padding(10)
                .background(isUser ? Color.accentColor : Color.secondary.opacity(0.16))
                .foregroundStyle(isUser ? Color.white : Color.primary)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .contextMenu {
                    Button {
                        UIPasteboard.general.string = message.content
                    } label: {
                        Label("Copy", systemImage: "doc.on.doc")
                    }
                }
        }
        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
    }
}
