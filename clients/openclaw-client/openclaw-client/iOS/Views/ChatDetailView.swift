import SwiftUI
#if os(iOS)
import UIKit
#elseif os(macOS)
import AppKit
#endif

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
                .frame(maxWidth: .infinity, maxHeight: .infinity)

            Divider()

            composerControls
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
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

    @State private var viewportHeight: CGFloat = 0

    private var messagesView: some View {
        ScrollViewReader { proxy in
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
            .scrollDismissesKeyboard(.interactively)
            .onAppear {
                scrollToBottom(using: proxy, animated: false)
            }
            .onChange(of: chatVM.messages.count) { _, _ in
                scrollToBottom(using: proxy, animated: true)
            }
            .onPreferenceChange(BottomAnchorOffsetKey.self) { newValue in
                bottomAnchorMinY = newValue
                updateScrollButton(viewportHeight: viewportHeight)
            }
            .overlay(alignment: .bottomTrailing) {
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
            .background(
                GeometryReader { geometry in
                    Color.clear
                        .onAppear { viewportHeight = geometry.size.height }
                        .onChange(of: geometry.size.height) { _, newValue in
                            viewportHeight = newValue
                            updateScrollButton(viewportHeight: newValue)
                        }
                }
            )
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

            if chatVM.availableProviders.count > 1 {
                Picker("Provider", selection: Binding(
                    get: { chatVM.provider },
                    set: { chatVM.switchProvider($0) }
                )) {
                    ForEach(chatVM.availableProviders, id: \.self) { p in
                        Text(p.capitalized).tag(p)
                    }
                }
                .pickerStyle(.segmented)
            }

            Menu {
                ForEach(chatVM.availableModels, id: \.self) { m in
                    Button {
                        chatVM.model = m
                    } label: {
                        HStack {
                            Text(modelDisplayName(m))
                            if m == chatVM.model {
                                Image(systemName: "checkmark")
                            }
                        }
                    }
                }
            } label: {
                HStack {
                    Text(modelDisplayName(chatVM.model))
                        .font(.subheadline)
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.caption2)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Color.secondary.opacity(0.12), in: RoundedRectangle(cornerRadius: 8))
            }

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

    private func modelDisplayName(_ model: String) -> String {
        if model.hasPrefix("gemini-") {
            if model.contains("flash") { return "Flash" }
            if model.contains("pro-exp") { return "Exp" }
            if model.contains("pro") { return "Pro" }
        }
        return model.components(separatedBy: ":").first ?? model
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
            Group {
                if isUser {
                    Text(message.content)
                } else {
                    MarkdownContentView(text: message.content)
                }
            }
            .textSelection(.enabled)
            .padding(10)
            .background(isUser ? Color.accentColor : Color.secondary.opacity(0.16))
            .foregroundStyle(isUser ? Color.white : Color.primary)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .contextMenu {
                Button {
                    #if os(iOS)
                    UIPasteboard.general.string = message.content
                    #elseif os(macOS)
                    NSPasteboard.general.setString(message.content, forType: .string)
                    #endif
                } label: {
                    Label("Copy", systemImage: "doc.on.doc")
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
    }
}
