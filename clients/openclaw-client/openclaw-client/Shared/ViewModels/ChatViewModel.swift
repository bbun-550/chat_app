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
    @Published var temperature: Double = 0.2
    @Published var maxTokens: Int = 512
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

        let selectedModel = model.isEmpty ? "gemini-3-flash-preview" : model
        let localUser = Message(
            id: UUID().uuidString,
            conversation_id: cid,
            role: "user",
            content: text,
            created_at: ISO8601DateFormatter().string(from: Date())
        )
        messages.append(localUser)
        inputText = ""

        do {
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
            let res = try await APIClient.shared.sendMessage(req)

            let localAssistant = Message(
                id: UUID().uuidString,
                conversation_id: cid,
                role: "assistant",
                content: res.reply,
                created_at: ISO8601DateFormatter().string(from: Date())
            )
            messages.append(localAssistant)

            lastProvider = res.provider
            lastModel = res.model
            lastLatencyMs = "\(res.latency_ms)"
            lastInputTokens = res.input_tokens.map(String.init) ?? "-"
            lastOutputTokens = res.output_tokens.map(String.init) ?? "-"
        } catch {
            errorMessage = error.localizedDescription
        }

        isSending = false
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
