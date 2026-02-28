import Foundation
import Combine

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var serverURLText: String = AppConfig.baseURL.absoluteString
    @Published var apiToken: String = AppConfig.apiToken ?? ""
    @Published var provider: String = "gemini"
    @Published var model: String = "gemini-2.0-flash"
    @Published var errorMessage: String?

    func saveServerURL() {
        guard URL(string: serverURLText) != nil else {
            errorMessage = "Invalid server URL"
            return
        }
        errorMessage = nil
        AppConfig.setBaseURL(serverURLText)
        AppConfig.setAPIToken(apiToken.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    func resetServerURL() {
        AppConfig.resetBaseURL()
        AppConfig.setAPIToken(nil)
        serverURLText = AppConfig.baseURL.absoluteString
        apiToken = ""
    }
}
