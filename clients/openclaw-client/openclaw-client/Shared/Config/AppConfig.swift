import Foundation

enum AppConfig {
    private static let key = "openclaw_server_url"
    private static let tokenKey = "openclaw_api_token"

    static var defaultURL: URL {
        URL(string: "http://127.0.0.1:8000")!
    }

    static var baseURL: URL {
        if let raw = UserDefaults.standard.string(forKey: key), let url = URL(string: raw) {
            return url
        }
        return defaultURL
    }

    static func setBaseURL(_ raw: String) {
        UserDefaults.standard.set(raw, forKey: key)
    }

    static func resetBaseURL() {
        UserDefaults.standard.removeObject(forKey: key)
    }

    static var apiToken: String? {
        UserDefaults.standard.string(forKey: tokenKey)
    }

    static func setAPIToken(_ token: String?) {
        if let token, !token.isEmpty {
            UserDefaults.standard.set(token, forKey: tokenKey)
        } else {
            UserDefaults.standard.removeObject(forKey: tokenKey)
        }
    }
}
