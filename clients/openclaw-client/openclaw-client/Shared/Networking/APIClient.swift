import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case requestFailed
    case decodingFailed
    case serverError(Int, String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .requestFailed:
            return "Request failed"
        case .decodingFailed:
            return "Failed to decode response"
        case .serverError(let code, let message):
            return "Server error \(code): \(message)"
        }
    }
}

final class APIClient {
    static let shared = APIClient()
    private init() {}

    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 20
        config.timeoutIntervalForResource = 30
        return URLSession(configuration: config)
    }()

    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .useDefaultKeys
        return decoder
    }()

    private func buildURL(for endpoint: Endpoint) -> URL? {
        URL(string: endpoint.path, relativeTo: AppConfig.baseURL)
    }

    func request<T: Decodable>(endpoint: Endpoint, body: Data? = nil) async throws -> T {
        try await requestWithRetry(endpoint: endpoint, body: body, retries: 1)
    }

    private func requestWithRetry<T: Decodable>(
        endpoint: Endpoint,
        body: Data? = nil,
        retries: Int
    ) async throws -> T {
        guard let url = buildURL(for: endpoint) else {
            throw APIError.invalidURL
        }

        var req = URLRequest(url: url)
        req.httpMethod = endpoint.method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = AppConfig.apiToken {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = body

        do {
            let (data, response) = try await session.data(for: req)

            guard let http = response as? HTTPURLResponse else {
                throw APIError.requestFailed
            }

            guard 200..<300 ~= http.statusCode else {
                let detail = (try? decoder.decode(APIErrorResponse.self, from: data).detail) ?? "Unknown"
                if retries > 0 && (500...599).contains(http.statusCode) {
                    try await Task.sleep(nanoseconds: 300_000_000)
                    return try await requestWithRetry(endpoint: endpoint, body: body, retries: retries - 1)
                }
                throw APIError.serverError(http.statusCode, detail)
            }

            do {
                return try decoder.decode(T.self, from: data)
            } catch {
                throw APIError.decodingFailed
            }
        } catch {
            if retries > 0 {
                try await Task.sleep(nanoseconds: 300_000_000)
                return try await requestWithRetry(endpoint: endpoint, body: body, retries: retries - 1)
            }
            throw error
        }
    }
}

extension APIClient {
    func fetchConversations() async throws -> [Conversation] {
        try await request(endpoint: .conversations)
    }

    func createConversation(title: String = "New Chat") async throws -> Conversation {
        let body = try JSONSerialization.data(withJSONObject: ["title": title])
        return try await request(endpoint: .createConversation, body: body)
    }

    func patchConversation(id: String, title: String?, category: String?) async throws -> Conversation {
        var payload: [String: Any] = [:]
        if let title { payload["title"] = title }
        if let category { payload["category"] = category }
        let body = try JSONSerialization.data(withJSONObject: payload)
        return try await request(endpoint: .patchConversation(id: id), body: body)
    }

    func deleteConversation(id: String) async throws -> DeleteResponse {
        try await request(endpoint: .deleteConversation(id: id))
    }

    func fetchMessages(conversationId: String) async throws -> [Message] {
        try await request(endpoint: .messages(conversationId: conversationId))
    }

    func sendMessage(_ requestModel: ChatRequest) async throws -> ChatResponse {
        let body = try JSONEncoder().encode(requestModel)
        return try await request(endpoint: .chat, body: body)
    }

    func fetchRuns(conversationId: String?) async throws -> [RunStats] {
        try await request(endpoint: .runs(conversationId: conversationId))
    }

    func upsertMessageMeta(messageId: String, requestModel: MessageMetaUpsertRequest) async throws -> [String: String] {
        let body = try JSONEncoder().encode(requestModel)
        return try await request(endpoint: .upsertMessageMeta(messageId: messageId), body: body)
    }
}
