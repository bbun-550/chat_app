import Foundation
import Combine

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var serverURLText: String = AppConfig.baseURL.absoluteString
    @Published var apiToken: String = AppConfig.apiToken ?? ""
    @Published var provider: String = "gemini"
    @Published var model: String = "gemini-2.0-flash"
    @Published var errorMessage: String?
    @Published var showSaveConfirmation = false
    @Published var showResetConfirmation = false

    private var saveConfirmationTask: Task<Void, Never>?
    private var resetConfirmationTask: Task<Void, Never>?

    func saveServerURL() {
        guard URL(string: serverURLText) != nil else {
            errorMessage = "Invalid server URL"
            showSaveConfirmation = false
            return
        }
        errorMessage = nil
        AppConfig.setBaseURL(serverURLText)
        AppConfig.setAPIToken(apiToken.trimmingCharacters(in: .whitespacesAndNewlines))
        showTemporarySaveConfirmation()
    }

    func resetServerURL() {
        AppConfig.resetBaseURL()
        AppConfig.setAPIToken(nil)
        serverURLText = AppConfig.baseURL.absoluteString
        apiToken = ""
        errorMessage = nil
        showTemporaryResetConfirmation()
    }

    private func showTemporarySaveConfirmation() {
        saveConfirmationTask?.cancel()
        showSaveConfirmation = true

        saveConfirmationTask = Task {
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            guard !Task.isCancelled else { return }
            showSaveConfirmation = false
        }
    }

    private func showTemporaryResetConfirmation() {
        resetConfirmationTask?.cancel()
        showResetConfirmation = true

        resetConfirmationTask = Task {
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            guard !Task.isCancelled else { return }
            showResetConfirmation = false
        }
    }
}
