import Foundation
import Combine

@MainActor
final class ServerSettings: ObservableObject {
    static let shared = ServerSettings()

    @Published private(set) var baseURL: URL

    private init() {
        self.baseURL = AppConfig.baseURL
    }

    func updateBaseURL(_ raw: String) throws {
        guard let url = URL(string: raw) else {
            throw URLError(.badURL)
        }
        AppConfig.setBaseURL(raw)
        baseURL = url
    }
}
