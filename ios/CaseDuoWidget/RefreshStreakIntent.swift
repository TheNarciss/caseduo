import AppIntents
import CaseDuoCore
import Foundation
import WidgetKit

/// The widget's refresh button: asks the backend for the day's numbers with the session cookie
/// the app keeps in the App Group, then redraws. Without network, the last snapshot stays.
struct RefreshStreakIntent: AppIntent {
    static let title: LocalizedStringResource = "Actualiser la série"
    static let description = IntentDescription("Relit la série et les exercices restants.")

    func perform() async throws -> some IntentResult {
        let configuration = URLSessionConfiguration.default
        configuration.httpCookieStorage = HTTPCookieStorage.sharedCookieStorage(forGroupContainerIdentifier: WidgetSnapshot.appGroup)
        configuration.timeoutIntervalForRequest = 15
        let session = URLSession(configuration: configuration)
        let base = (Bundle.main.object(forInfoDictionaryKey: "APIBaseURL") as? String) ?? "https://caseduo.riskybusinesses.uk/api"
        guard let url = URL(string: base.trimmingCharacters(in: CharacterSet(charactersIn: "/")) + "/widget") else { return .result() }
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let (data, response) = try? await session.data(for: request),
           (response as? HTTPURLResponse)?.statusCode == 200,
           let info = try? CaseDuoJSON.decoder.decode(WidgetInfo.self, from: data) {
            let zone = SharedSnapshot.load()?.timezone ?? TimeZone.current.identifier
            SharedSnapshot.save(WidgetSnapshot(widget: info, timezone: zone))
        }
        WidgetCenter.shared.reloadAllTimelines()
        return .result()
    }
}
