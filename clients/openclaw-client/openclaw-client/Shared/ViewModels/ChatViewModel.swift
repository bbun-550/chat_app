import Foundation
import Combine

@MainActor
final class ChatViewModel: ObservableObject {
    @Published var messages: [Message] = []
    @Published var inputText: String = ""

    @Published var isLoadingMessages = false
    @Published var isSending = false
    @Published var errorMessage: String?

    @Published var lastProvider = "-"
    @Published var lastModel = "-"
    @Published var lastLatencyMs = "-"
    @Published var lastInputTokens = "-"
    @Published var lastOutputTokens = "-"

    @Published var provider = "gemini"
    @Published var model = "gemini-3-flash-preview"
    @Published var availableProviders: [String] = []
    @Published var availableModels: [String] = []
    @Published var temperature: Double = 0.2
    @Published var maxTokens: Int = 2048
    @Published var topP: Double? = nil
    @Published var topK: Int? = nil
    @Published var candidateCount: Int? = nil

    private var conversationId: String?

    func bindConversation(_ id: String?) {
        conversationId = id
    }

    func loadMessages() async {
        guard let cid = conversationId else { return }
        isLoadingMessages = true
        errorMessage = nil
        defer { isLoadingMessages = false }

        do {
            messages = try await APIClient.shared.fetchMessages(conversationId: cid)
            let runs = try await APIClient.shared.fetchRuns(conversationId: cid)
            applyRunStats(runs.first)
        } catch {
            errorMessage = error.localizedDescription
        }

        await loadProviders()
    }

    func loadProviders() async {
        do {
            let providers = try await APIClient.shared.fetchProviders()
            availableProviders = providers
            if !providers.contains(provider), let first = providers.first {
                provider = first
            }
            await loadModels()
        } catch {
            availableProviders = ["gemini"]
        }
    }

    func loadModels() async {
        do {
            let models = try await APIClient.shared.fetchModels(provider: provider)
            availableModels = models
            if !models.contains(model), let first = models.first {
                model = first
            }
        } catch {
            availableModels = []
        }
    }

    func switchProvider(_ newProvider: String) {
        provider = newProvider
        Task { await loadModels() }
    }

    func send() async {
        guard let cid = conversationId else {
            errorMessage = "No conversation selected"
            return
        }

        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.isEmpty || isSending { return }

        isSending = true
        errorMessage = nil

        let selectedModel = model.isEmpty ? availableModels.first ?? "gemini-3-flash-preview" : model
        let localUser = Message(
            id: UUID().uuidString,
            conversation_id: cid,
            role: "user",
            content: text,
            created_at: ISO8601DateFormatter().string(from: Date())
        )
        messages.append(localUser)
        inputText = ""

        let req = ChatRequest(
            conversation_id: cid,
            message: text,
            provider: provider,
            model: selectedModel,
            system_prompt_id: nil,
            temperature: temperature,
            max_tokens: maxTokens,
            top_p: topP,
            top_k: topK,
            candidate_count: candidateCount
        )

        var placeholder = Message(
            id: UUID().uuidString,
            conversation_id: cid,
            role: "assistant",
            content: "",
            created_at: ISO8601DateFormatter().string(from: Date())
        )
        messages.append(placeholder)
        let placeholderIndex = messages.count - 1

        do {
            for try await chunk in APIClient.shared.sendMessageStream(req) {
                if let error = chunk.error {
                    throw APIError.serverError(500, error)
                }

                // Sync local user message ID with server-persisted ID
                if let serverUserId = chunk.user_message_id,
                   let idx = messages.firstIndex(where: { $0.id == localUser.id }) {
                    messages[idx] = Message(
                        id: serverUserId,
                        conversation_id: cid,
                        role: "user",
                        content: text,
                        created_at: messages[idx].created_at
                    )
                }

                messages[placeholderIndex].content += chunk.delta

                if chunk.done {
                    lastProvider = chunk.provider ?? provider
                    lastModel = chunk.model ?? selectedModel
                    lastLatencyMs = chunk.latency_ms.map(String.init) ?? "-"
                    lastInputTokens = chunk.input_tokens.map(String.init) ?? "-"
                    lastOutputTokens = chunk.output_tokens.map(String.init) ?? "-"
                }
            }
        } catch {
            // Remove empty assistant placeholder
            if messages[placeholderIndex].content.isEmpty {
                messages.remove(at: placeholderIndex)
            }
            // Remove optimistic local user message to prevent duplicates on reload
            if let userIdx = messages.firstIndex(where: { $0.id == localUser.id }) {
                messages.remove(at: userIdx)
            }
            errorMessage = error.localizedDescription
            isSending = false
            // Reload from server to get actual persisted state
            await loadMessages()
            return
        }

        isSending = false
    }

    func toggleBookmark(_ messageId: String) async {
        do {
            let updated = try await APIClient.shared.toggleBookmark(messageId: messageId)
            if let idx = messages.firstIndex(where: { $0.id == messageId }) {
                messages[idx].is_bookmarked = updated.is_bookmarked
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func applyRunStats(_ run: RunStats?) {
        guard let run else { return }
        lastProvider = run.provider
        lastModel = run.model
        lastLatencyMs = "\(run.latency_ms)"
        lastInputTokens = run.input_tokens.map(String.init) ?? "-"
        lastOutputTokens = run.output_tokens.map(String.init) ?? "-"
    }
}
