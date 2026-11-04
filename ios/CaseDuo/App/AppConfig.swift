import Foundation

/// Where the backend is and which mode the app runs in.
enum AppConfig {
    /// `APIBaseURL` from Info.plist (project.yml), overridable in debug builds with the launch
    /// argument `-apiBaseURL http://localhost:8000/api`.
    static var apiBaseURL: URL {
        #if DEBUG
        if let override = UserDefaults.standard.string(forKey: "apiBaseURL"), let url = URL(string: override) {
            return url
        }
        #endif
        let raw = Bundle.main.object(forInfoDictionaryKey: "APIBaseURL") as? String
        return URL(string: raw ?? "") ?? URL(string: "https://caseduo.riskybusinesses.uk/api")!
    }

    /// The site root, for the admin review page (`/admin/review/{date}` lives outside `/api`).
    static var siteURL: URL {
        var text = apiBaseURL.absoluteString
        if text.hasSuffix("/") { text.removeLast() }
        if text.hasSuffix("/api") { text.removeLast(4) }
        return URL(string: text) ?? apiBaseURL
    }

    /// Canned data, no network: CI screenshots and previews (`-uiDemo YES`, debug builds only).
    static var isDemo: Bool {
        #if DEBUG
        return UserDefaults.standard.bool(forKey: "uiDemo")
        #else
        return false
        #endif
    }

    /// The APNs environment the token belongs to.
    static var pushEnvironment: String {
        #if DEBUG
        return "sandbox"
        #else
        return "production"
        #endif
    }

    static let appGroup = "group.uk.riskybusinesses.caseduo"
}
